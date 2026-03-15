"""
serial_scale.py — Scale communication for WeighBridge Pro

Supports:
  • Real RS232/serial port using pyserial
  • Simulated scale (slider-driven) as fallback
  • Multiple protocols: generic, toledo, mettler
  • Graceful disconnect / timeout handling
"""

import threading
import time
import queue
from dataclasses import dataclass, field

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# ───────────────────────────── STATUS CONSTANTS ───────────────────────────────
STATUS_CONNECTED  = "connected"
STATUS_MANUAL     = "manual"
STATUS_OFFLINE    = "offline"
STATUS_SIMULATED  = "simulated"


@dataclass
class ScaleReading:
    weight_kg: float = 0.0
    stable: bool = False
    status: str = STATUS_SIMULATED
    raw: str = ""


# ─────────────────────────── PROTOCOL PARSERS ────────────────────────────────
def parse_generic(line: str):
    """Generic protocol: any line containing digits with optional +/- sign."""
    line = line.strip()
    import re
    m = re.search(r"[+-]?\d+\.?\d*", line)
    if m:
        try:
            w = float(m.group())
            stable = "ST" in line.upper() or "S" in line.upper()
            return w, stable
        except ValueError:
            pass
    return None, False


def parse_toledo(line: str):
    """
    Toledo format (example): ST,GS,+  00500.00kg
    Field positions: ST/US (stable/unstable), GS/NT, sign, weight, unit
    """
    line = line.strip()
    parts = line.split(",")
    if len(parts) >= 3:
        stable = parts[0].strip().upper() == "ST"
        try:
            w_str = parts[2].strip().replace("kg", "").replace("KG", "").strip()
            w = float(w_str)
            return w, stable
        except (ValueError, IndexError):
            pass
    return None, False


def parse_mettler(line: str):
    """
    Mettler MT-SICS format: S S      5000.000 kg
    First token: S (stable) or D (dynamic)
    """
    parts = line.strip().split()
    if len(parts) >= 3:
        stable = parts[0].upper() == "S"
        try:
            w = float(parts[1])
            return w, stable
        except (ValueError, IndexError):
            pass
    return None, False


PROTOCOLS = {
    "generic": parse_generic,
    "toledo":  parse_toledo,
    "mettler": parse_mettler,
}


# ─────────────────────────── REAL SCALE READER ───────────────────────────────
class SerialScaleReader(threading.Thread):
    """
    Background thread that reads from a serial port and puts ScaleReading
    objects into a queue.
    """

    def __init__(self, port, baud=9600, parity="N", data_bits=8,
                 stop_bits=1, timeout=3, protocol="generic",
                 zero_offset=0.0):
        super().__init__(daemon=True)
        self.port        = port
        self.baud        = int(baud)
        self.parity      = parity
        self.data_bits   = int(data_bits)
        self.stop_bits   = int(stop_bits)
        self.timeout     = float(timeout)
        self.protocol    = PROTOCOLS.get(protocol, parse_generic)
        self.zero_offset = float(zero_offset)

        self.readings: queue.Queue[ScaleReading] = queue.Queue(maxsize=10)
        self._stop_event = threading.Event()
        self._status = STATUS_OFFLINE

    @property
    def status(self):
        return self._status

    def stop(self):
        self._stop_event.set()

    def run(self):
        if not SERIAL_AVAILABLE:
            self._status = STATUS_OFFLINE
            self.readings.put(ScaleReading(status=STATUS_OFFLINE))
            return

        while not self._stop_event.is_set():
            try:
                with serial.Serial(
                    port=self.port,
                    baudrate=self.baud,
                    parity=self.parity,
                    bytesize=self.data_bits,
                    stopbits=self.stop_bits,
                    timeout=self.timeout,
                ) as ser:
                    self._status = STATUS_CONNECTED
                    while not self._stop_event.is_set():
                        raw = ser.readline()
                        if not raw:
                            # Timeout — no data received
                            self._status = STATUS_OFFLINE
                            self._put(ScaleReading(status=STATUS_OFFLINE, raw="TIMEOUT"))
                            continue
                        try:
                            line = raw.decode("ascii", errors="ignore")
                        except Exception:
                            line = ""
                        w, stable = self.protocol(line)
                        if w is not None:
                            w = max(0.0, w - self.zero_offset)
                            self._status = STATUS_CONNECTED
                            self._put(ScaleReading(weight_kg=w, stable=stable,
                                                   status=STATUS_CONNECTED, raw=line))
            except Exception as e:
                self._status = STATUS_OFFLINE
                self._put(ScaleReading(status=STATUS_OFFLINE, raw=str(e)))
                time.sleep(2)   # retry after 2s

    def _put(self, reading: ScaleReading):
        try:
            self.readings.put_nowait(reading)
        except queue.Full:
            try:
                self.readings.get_nowait()
                self.readings.put_nowait(reading)
            except queue.Empty:
                pass


# ─────────────────────────── SIMULATED SCALE ─────────────────────────────────
class SimulatedScale:
    """
    Fake scale used when no serial port is configured or pyserial unavailable.
    Weight is set programmatically via set_weight().
    """

    def __init__(self, zero_offset=0.0):
        self._weight = 0.0
        self._target = 0.0
        self.zero_offset = zero_offset
        self._stop_event = threading.Event()
        self._status = STATUS_SIMULATED
        self.readings: queue.Queue[ScaleReading] = queue.Queue(maxsize=10)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def status(self):
        return self._status

    @property
    def weight(self):
        return self._weight

    def set_weight(self, kg: float):
        self._target = max(0.0, float(kg))

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.is_set():
            diff = self._target - self._weight
            step = diff * 0.18
            if abs(diff) < 0.3:
                step = diff
            self._weight = max(0.0, self._weight + step - self.zero_offset)
            self._put(ScaleReading(
                weight_kg=round(self._weight, 1),
                stable=abs(diff) < 1.0,
                status=STATUS_SIMULATED,
            ))
            time.sleep(0.04)   # ~25 fps

    def _put(self, reading: ScaleReading):
        try:
            self.readings.put_nowait(reading)
        except queue.Full:
            try:
                self.readings.get_nowait()
                self.readings.put_nowait(reading)
            except queue.Empty:
                pass


# ─────────────────────────── SCALE MANAGER ───────────────────────────────────
class ScaleManager:
    """
    High-level manager: tries real serial port first; falls back to simulation.
    Provides manual override capability (supervisor approved).
    """

    def __init__(self, port, baud=9600, parity="N", data_bits=8,
                 stop_bits=1, timeout=3, protocol="generic", zero_offset=0.0):
        self._manual_mode   = False
        self._manual_weight = 0.0
        self._zero_offset   = float(zero_offset)

        if port and port.upper() != "NONE" and SERIAL_AVAILABLE:
            self._reader = SerialScaleReader(
                port=port, baud=baud, parity=parity,
                data_bits=data_bits, stop_bits=stop_bits,
                timeout=timeout, protocol=protocol,
                zero_offset=zero_offset)
            self._reader.start()
            self._sim = None
        else:
            self._reader = None
            self._sim = SimulatedScale(zero_offset=zero_offset)

    @property
    def readings(self) -> queue.Queue:
        if self._manual_mode:
            return None
        return self._sim.readings if self._sim else self._reader.readings

    @property
    def status(self) -> str:
        if self._manual_mode:
            return STATUS_MANUAL
        if self._sim:
            return STATUS_SIMULATED
        return self._reader.status

    def set_simulated_weight(self, kg: float):
        """Move simulated scale to target weight."""
        if self._sim:
            self._sim.set_weight(kg)

    def set_manual_weight(self, kg: float):
        """Supervisor override: manually enter a weight."""
        self._manual_mode   = True
        self._manual_weight = max(0.0, float(kg))

    def exit_manual_mode(self):
        self._manual_mode = False

    def get_manual_reading(self) -> ScaleReading:
        return ScaleReading(weight_kg=self._manual_weight,
                            stable=True, status=STATUS_MANUAL)

    def get_latest_reading(self) -> ScaleReading:
        if self._manual_mode:
            return self.get_manual_reading()
        q = self._sim.readings if self._sim else self._reader.readings
        last = ScaleReading()
        while not q.empty():
            try:
                last = q.get_nowait()
            except Exception:
                break
        return last

    def stop(self):
        if self._reader:
            self._reader.stop()
        if self._sim:
            self._sim.stop()

    @staticmethod
    def list_ports() -> list:
        if SERIAL_AVAILABLE:
            return [p.device for p in serial.tools.list_ports.comports()]
        return []

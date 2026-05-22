import serial
import json
import threading
from queue import Queue

class SerialReader:
    def __init__(self, port: str, baudrate: int = 921600):
        self.port = port
        self.baudrate = baudrate
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self.queue: Queue = Queue()

    def connect(self) -> bool:
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
            return True
        except serial.SerialException:
            return False

    def disconnect(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._serial and self._serial.is_open:
            self._serial.close()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None

    def _read_loop(self):
        while self._running and self._serial and self._serial.is_open:
            try:
                line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                try:
                    self.queue.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
            except (serial.SerialException, OSError):
                break

    def write(self, data: str):
        if self._serial and self._serial.is_open:
            self._serial.write(data.encode("utf-8"))

    def readline_raw(self, timeout: float = 1.0) -> str:
        """Synchronous read — call only when the read loop is NOT running."""
        if self._serial and self._serial.is_open:
            self._serial.timeout = timeout
            return self._serial.readline().decode("utf-8", errors="ignore").strip()
        return ""

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

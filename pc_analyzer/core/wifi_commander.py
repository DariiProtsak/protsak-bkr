import time
from core.serial_reader import SerialReader

class WifiCommander:
    def __init__(self, reader: SerialReader):
        self._reader = reader

    def connect(self, ssid: str, password: str, timeout: float = 20.0) -> bool:
        self._reader.write(f"WIFI_CONNECT:{ssid}:{password}\n")
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self._reader.readline_raw(timeout=1.0)
            if line == "WIFI_OK":
                return True
            if line == "WIFI_FAIL":
                return False
            # CSI data arriving = ESP32 already connected and running
            if line.startswith("{") and "csi" in line:
                return True
        return False

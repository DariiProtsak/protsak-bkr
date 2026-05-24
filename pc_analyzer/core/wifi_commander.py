import json
import time
from core.serial_reader import SerialReader

class WifiCommander:
    def __init__(self, reader: SerialReader):
        self._reader = reader

    def connect(self, ssid: str, password: str, timeout: float = 20.0) -> bool:
        # Stop background read loop — it competes with readline_raw for the same bytes
        self._reader.stop()

        if self._reader._serial and self._reader._serial.is_open:
            self._reader._serial.reset_input_buffer()

        self._reader.write(f"WIFI_CONNECT:{ssid}:{password}\n")
        deadline = time.time() + timeout
        result = False
        while time.time() < deadline:
            line = self._reader.readline_raw(timeout=0.05)
            if not line:
                continue
            if "WIFI_OK" in line:
                result = True
                break
            if "WIFI_FAIL" in line:
                result = False
                break
            if line.startswith("{"):
                try:
                    pkt = json.loads(line)
                    if "ip" in pkt and "csi" not in pkt:
                        self._reader.esp32_ip = pkt["ip"]
                    elif "csi" in pkt:
                        result = True
                        break
                except Exception:
                    pass

        # Restart background read loop regardless of outcome
        self._reader.start()
        return result

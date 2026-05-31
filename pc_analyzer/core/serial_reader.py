import serial
import json
import threading
from queue import Queue

class SerialReader:
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self.queue: Queue = Queue()
        self.esp32_ip: str | None = None

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
        if self._thread and self._thread.is_alive():
            return
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
                    pkt = json.loads(line)
                    if "ip" in pkt and "csi" not in pkt:
                        self.esp32_ip = pkt["ip"]
                    else:
                        self.queue.put(pkt)
                except json.JSONDecodeError:
                    pass
            except (serial.SerialException, OSError):
                break

    def write(self, data: str):
        if self._serial and self._serial.is_open:
            self._serial.write(data.encode("utf-8"))

    # Фонетична транслітерація кирилиці → ASCII (ДСТУ 9112:2021 / BGN)
    _TRANSLIT: dict[str, str] = {
        'А': 'A',  'а': 'a',  'Б': 'B',  'б': 'b',  'В': 'V',  'в': 'v',
        'Г': 'H',  'г': 'h',  'Ґ': 'G',  'ґ': 'g',  'Д': 'D',  'д': 'd',
        'Е': 'E',  'е': 'e',  'Є': 'Ye', 'є': 'ye', 'Ж': 'Zh', 'ж': 'zh',
        'З': 'Z',  'з': 'z',  'И': 'Y',  'и': 'y',  'І': 'I',  'і': 'i',
        'Ї': 'Yi', 'ї': 'yi', 'Й': 'Y',  'й': 'y',  'К': 'K',  'к': 'k',
        'Л': 'L',  'л': 'l',  'М': 'M',  'м': 'm',  'Н': 'N',  'н': 'n',
        'О': 'O',  'о': 'o',  'П': 'P',  'п': 'p',  'Р': 'R',  'р': 'r',
        'С': 'S',  'с': 's',  'Т': 'T',  'т': 't',  'У': 'U',  'у': 'u',
        'Ф': 'F',  'ф': 'f',  'Х': 'Kh', 'х': 'kh', 'Ц': 'Ts', 'ц': 'ts',
        'Ч': 'Ch', 'ч': 'ch', 'Ш': 'Sh', 'ш': 'sh', 'Щ': 'Shch', 'щ': 'shch',
        'Ь': '',   'ь': '',   'Ю': 'Yu', 'ю': 'yu', 'Я': 'Ya', 'я': 'ya',
        # Russian extras
        'Ъ': '',   'ъ': '',   'Ы': 'Y',  'ы': 'y',  'Э': 'E',  'э': 'e',
    }

    @classmethod
    def _encode_lcd(cls, text: str) -> bytes:
        out = bytearray()
        for ch in text:
            if ch in cls._TRANSLIT:
                out.extend(cls._TRANSLIT[ch].encode('ascii'))
            elif ord(ch) < 128:
                out.append(ord(ch))
        return bytes(out)

    def lcd(self, line1: str, line2: str):
        l1 = self._encode_lcd(line1)[:16]
        l2 = self._encode_lcd(line2)[:16]
        if self._serial and self._serial.is_open:
            self._serial.write(b"LCD:" + l1 + b":" + l2 + b"\n")

    def readline_raw(self, timeout: float = 1.0) -> str:
        """Synchronous read — call only when the read loop is NOT running."""
        if self._serial and self._serial.is_open:
            self._serial.timeout = timeout
            return self._serial.readline().decode("utf-8", errors="ignore").strip()
        return ""

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

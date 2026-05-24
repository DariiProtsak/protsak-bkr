import socket
import threading
import time
import subprocess
import re

def _get_gateway_ip() -> str | None:
    try:
        out = subprocess.check_output(["route", "print", "0.0.0.0"],
                                      text=True, timeout=2)
        for line in out.splitlines():
            m = re.search(r'0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)', line)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None

class UdpPinger:
    """Sends UDP datagrams to trigger CSI callbacks on the ESP32.

    Sends to both ESP32 IP (direct trigger via dump_ack_en) and the
    gateway IP (ESP32 sees gateway traffic in promiscuous mode).
    Falls back to broadcast if IPs are unknown.
    """

    def __init__(self, rate: float = 500.0, port: int = 5000,
                 target_ip: str | None = None):
        self._port      = port
        self._rate      = rate
        self._target_ip = target_ip
        self._gw_ip     = _get_gateway_ip()
        self._running   = False
        self._thread: threading.Thread | None = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None

    def _loop(self):
        interval = 1.0 / self._rate
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.1)
        targets = []
        if self._target_ip:
            targets.append(self._target_ip)
        if self._gw_ip and self._gw_ip != self._target_ip:
            targets.append(self._gw_ip)
        if not targets:
            targets = ["255.255.255.255"]
        try:
            while self._running:
                t0 = time.monotonic()
                for target in targets:
                    try:
                        sock.sendto(b"\x00", (target, self._port))
                    except OSError:
                        pass
                elapsed = time.monotonic() - t0
                remaining = interval - elapsed
                if remaining > 0:
                    time.sleep(remaining)
        finally:
            sock.close()

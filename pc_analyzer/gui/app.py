import os
import json
import customtkinter as ctk
from core.serial_reader import SerialReader

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(_BASE, "config.json")
_DEFAULTS = {
    "com_port": "COM3",
    "ssid": "",
    "collect_duration_sec": 60,
    "monitor_block_sec": 30,
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("CSI Analyzer")
        self.geometry("900x650")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.cfg = self._load_config()
        self.serial = SerialReader(self.cfg["com_port"])

        self._screens: dict = {}
        self._current = None
        self._build_screens()
        self.show("init")

    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH) as f:
                    return {**_DEFAULTS, **json.load(f)}
            except Exception:
                pass
        return dict(_DEFAULTS)

    def save_config(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.cfg, f, indent=2, ensure_ascii=False)

    def _build_screens(self):
        from gui.screen_init    import ScreenInit
        from gui.screen_wifi    import ScreenWifi
        from gui.screen_menu    import ScreenMenu
        from gui.screen_collect import ScreenCollect
        from gui.screen_monitor import ScreenMonitor

        for name, cls in [
            ("init",    ScreenInit),
            ("wifi",    ScreenWifi),
            ("menu",    ScreenMenu),
            ("collect", ScreenCollect),
            ("monitor", ScreenMonitor),
        ]:
            frame = cls(self)
            frame.place(x=0, y=0, relwidth=1, relheight=1)
            self._screens[name] = frame

    def show(self, name: str):
        screen = self._screens[name]
        screen.on_show()
        screen.tkraise()
        self._current = screen

    def _on_close(self):
        self.serial.disconnect()
        self.destroy()

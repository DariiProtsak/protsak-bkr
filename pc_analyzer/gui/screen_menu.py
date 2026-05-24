import customtkinter as ctk
from core.classifier import Classifier

class ScreenMenu(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Головне меню",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(100, 8))
        self._status = ctk.CTkLabel(self, text="", text_color="gray",
                                    font=ctk.CTkFont(size=13))
        self._status.pack(pady=(0, 50))

        ctk.CTkButton(self, text="Навчання моделі", width=280, height=52,
                      command=lambda: self.app.show("collect")).pack(pady=10)
        self._monitor_btn = ctk.CTkButton(self, text="Моніторинг", width=280, height=52,
                                          command=lambda: self.app.show("monitor"))
        self._monitor_btn.pack(pady=10)
        ctk.CTkButton(self, text="Змінити Wi-Fi мережу", width=280, height=40,
                      fg_color="transparent", border_width=1,
                      command=self._change_wifi).pack(pady=(20, 0))

    def on_show(self):
        port = self.app.cfg.get("com_port", "?")
        ssid = self.app.cfg.get("ssid", "")
        info = f"Порт: {port}  |  {ssid}" if ssid else f"Порт: {port}  |  ESP32 підключено"
        self._status.configure(text=info)
        state = "normal" if Classifier.model_exists() else "disabled"
        self._monitor_btn.configure(state=state)

    def _change_wifi(self):
        self.app.serial.stop()
        self.app.show("wifi")

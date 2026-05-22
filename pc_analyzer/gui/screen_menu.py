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

    def on_show(self):
        port = self.app.cfg.get("com_port", "?")
        self._status.configure(text=f"Порт: {port}  |  ESP32 підключено")
        state = "normal" if Classifier.model_exists() else "disabled"
        self._monitor_btn.configure(state=state)

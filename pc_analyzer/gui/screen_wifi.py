import threading
import customtkinter as ctk
from core.wifi_commander import WifiCommander

class ScreenWifi(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Підключення ESP32 до Wi-Fi",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(60, 30))

        form = ctk.CTkFrame(self)
        form.pack()

        ctk.CTkLabel(form, text="SSID:", width=90, anchor="e").grid(
            row=0, column=0, padx=12, pady=10)
        self._ssid = ctk.CTkEntry(form, width=260, placeholder_text="Назва мережі")
        self._ssid.grid(row=0, column=1, columnspan=2, padx=12, pady=10)

        ctk.CTkLabel(form, text="Пароль:", width=90, anchor="e").grid(
            row=1, column=0, padx=12, pady=10)
        self._pwd = ctk.CTkEntry(form, width=220, show="•", placeholder_text="Пароль")
        self._pwd.grid(row=1, column=1, padx=12, pady=10)
        ctk.CTkButton(form, text="👁", width=36,
                      command=self._toggle_pwd).grid(row=1, column=2, padx=4)

        self._status = ctk.CTkLabel(self, text="", text_color="gray")
        self._status.pack(pady=14)

        self._btn = ctk.CTkButton(self, text="Підключити ESP32",
                                  width=220, height=46, command=self._connect)
        self._btn.pack(pady=4)
        ctk.CTkButton(self, text="← Назад", width=120,
                      fg_color="transparent", border_width=1,
                      command=lambda: self.app.show("init")).pack(pady=4)

    def on_show(self):
        ssid = self.app.cfg.get("ssid", "")
        if ssid:
            self._ssid.delete(0, "end")
            self._ssid.insert(0, ssid)

    def _toggle_pwd(self):
        self._pwd.configure(show="" if self._pwd.cget("show") == "•" else "•")

    def _connect(self):
        ssid = self._ssid.get().strip()
        pwd  = self._pwd.get()
        if not ssid:
            self._status.configure(text="Введіть SSID", text_color="orange")
            return
        self._btn.configure(state="disabled")
        self._status.configure(text=f"Підключення до «{ssid}»…", text_color="gray")
        self.update()

        def task():
            ok = WifiCommander(self.app.serial).connect(ssid, pwd, timeout=20.0)
            self.after(0, self._on_result, ok, ssid)

        threading.Thread(target=task, daemon=True).start()

    def _on_result(self, ok: bool, ssid: str):
        self._btn.configure(state="normal")
        if ok:
            self.app.cfg["ssid"] = ssid
            self.app.save_config()
            self.app.serial.start()
            self.app.show("menu")
        else:
            self._status.configure(text="Помилка: WIFI_FAIL або таймаут", text_color="red")

import customtkinter as ctk
import serial.tools.list_ports

class ScreenInit(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="CSI Analyzer",
                     font=ctk.CTkFont(size=32, weight="bold")).pack(pady=(80, 8))
        ctk.CTkLabel(self, text="Підключення до ESP32 через UART",
                     font=ctk.CTkFont(size=14), text_color="gray").pack(pady=(0, 40))

        form = ctk.CTkFrame(self)
        form.pack()

        ctk.CTkLabel(form, text="COM-порт:", width=100, anchor="e").grid(
            row=0, column=0, padx=12, pady=12)
        self._port_var = ctk.StringVar()
        self._combo = ctk.CTkComboBox(form, variable=self._port_var, width=180)
        self._combo.grid(row=0, column=1, padx=12, pady=12)
        ctk.CTkButton(form, text="Оновити", width=100,
                      command=self._refresh).grid(row=0, column=2, padx=8)

        self._status = ctk.CTkLabel(self, text="", text_color="gray")
        self._status.pack(pady=12)

        self._btn = ctk.CTkButton(self, text="Підключитись",
                                  width=220, height=46, command=self._connect)
        self._btn.pack()

    def on_show(self):
        self._refresh()

    def _refresh(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            ports = ["(немає портів)"]
        self._combo.configure(values=ports)
        saved = self.app.cfg["com_port"]
        self._port_var.set(saved if saved in ports else ports[0])

    def _connect(self):
        port = self._port_var.get()
        if port == "(немає портів)":
            return
        self._status.configure(text=f"Підключення до {port}…", text_color="gray")
        self._btn.configure(state="disabled")
        self.update()

        self.app.serial.port = port
        if self.app.serial.connect():
            self.app.cfg["com_port"] = port
            self.app.save_config()
            self._btn.configure(state="normal")
            self._status.configure(text="")
            self.app.show("wifi")
        else:
            self._status.configure(text=f"Не вдалось відкрити {port}", text_color="red")
            self._btn.configure(state="normal")

# Git — робочий процес

## Проект: ESP32-C5 + LCD 1602 + WiFi CSI

### Обладнання
- **Мікроконтролер:** ESP32-C5 (WROOM-1, **eco2, chip revision v1.0**)
- **Дисплей:** LCD 1602 з I2C-модулем HW-61 (**адреса 0x27**, SDA=GPIO8, SCL=GPIO9)
- **Прошивка:** **ESP-IDF v5.5.4** (C++)
- **IDE:** VS Code + ESP-IDF Extension
- **COM-порт:** COM3

### Підключення LCD
| Дисплей | ESP32-C5 |
|---------|----------|
| VCC | 5V |
| GND | GND |
| SDA | GPIO 8 |
| SCL | GPIO 9 |
| I2C адреса | 0x27 |

### Функціонал
- Підключення до WiFi (SSID: Darii)
- Відображення IP-адреси та CSI RSSI/довжини на LCD 1602
- Збір WiFi CSI (Channel State Information) через callback
- Виведення CSI даних у серійний монітор (формат: `CSI|rssi:|noise:|len:|ch:|data:...`)

---

## ВАЖЛИВО: ESP-IDF v5.5.4

Проект використовує **ESP-IDF v5.5.4** (не v5.4.x!).  
ESP32-C5 eco2 (v1.0) має інші адреси ROM-функцій coexist — v5.4.x крашився з WDT.

### Активація середовища
```powershell
# ПРАВИЛЬНО (v5.5.4):
. C:\esp\esp-idf\export.ps1

# ЗАСТАРІЛО (не використовувати):
# . C:\esp\activate_idf.ps1
```

### ESP-IDF команди (з папки firmware\)
```powershell
. C:\esp\esp-idf\export.ps1

cd C:\Users\user\OneDrive\BKR\code\firmware

idf.py set-target esp32c5   # встановити цільовий чіп (БЕЗ --preview у v5.5!)
idf.py menuconfig            # налаштування проекту
idf.py build                 # компіляція
idf.py flash                 # прошивка
idf.py monitor               # серійний монітор (Ctrl+] для виходу)
idf.py flash monitor         # прошити і одразу моніторити
```

---

## Початок роботи (на будь-якому ПК)

```powershell
git pull
```

Завжди підтягуй зміни перед тим як починати.

---

## Кінець роботи (зберегти і залити)

```powershell
git add firmware/components firmware/main firmware/sdkconfig.defaults
git commit -m "короткий опис що зробив"
git push
```

> **Не додавай** папку `firmware/build/` — вона у .gitignore.

---

## Чому не можна покладатись тільки на OneDrive

OneDrive синхронізує файли, але не git-коміти. Якщо не зробити push/pull — git на іншому ПК буде плутатися.

---

## Швидка шпаргалка

| Коли | Команда |
|---|---|
| Починаєш роботу | `git pull` |
| Хочеш зберегти прогрес | `git add . && git commit -m "..."` |
| Закінчуєш / переходиш на інший ПК | `git push` |
| Перевірити статус | `git status` |
| Переглянути історію | `git log --oneline` |
| Знайти COM-порт ESP32 | `Get-WMIObject Win32_SerialPort \| Select Name,Description` |

---

## Що було зроблено (сесія 21.05.2026)

### Проблема 1: `bootloader requires chip revision [v0.0 - v0.99]`
ESP-IDF v5.4.1 хардкодив `REV_MAX=99` в Kconfig — чіп v1.0 не міг прошитися.  
**Рішення:** оновлення до ESP-IDF v5.5.4, де eco2 підтримується нативно.

### Проблема 2: WDT reset (`TG1_WDT_HPSYS`) під час старту
coexist ROM для esp32c5-eco2 має інші адреси функцій ніж eco1.  
ESP-IDF v5.4.x використовував неправильний linker script (`esp32c5.rom.coexist.ld`).  
**Рішення:** ESP-IDF v5.5.4 містить правильний скрипт з позначкою `ECO version ≥ 2`.

### Проблема 3: LCD показував ієрогліфи
`vTaskDelay(pdMS_TO_TICKS(1))` при 100Hz FreeRTOS = 0 тіків → порушення тайменгу HD44780.  
**Рішення:** замінено на `ets_delay_us()` для точних мікросекундних затримок.  
Також додано авто-детекцію I2C адреси (0x27 / 0x3F).

# Git — робочий процес

## Проект: ESP32-C6 + LCD 1602 + WiFi

### Обладнання
- **Мікроконтролер:** ESP32-C5 (WROOM-1) — preview target у ESP-IDF v5.4
- **Дисплей:** LCD 1602 з I2C-модулем HW-61
- **Прошивка:** ESP-IDF v5.4.1 (C++)
- **IDE:** VS Code + ESP-IDF Extension

### Підключення
| Дисплей | ESP32-C6 |
|---------|----------|
| VCC | 5V |
| GND | GND |
| SDA | GPIO 8 |
| SCL | GPIO 9 |
| I2C адреса | 0x27 або 0x3F |

### Функціонал
- Підключення до WiFi-роутера
- Відображення інформації на LCD 1602 (I2C)
- Прошивка через UART

---

## Початок роботи (на будь-якому ПК)

```powershell
git pull
```

Завжди підтягуй зміни перед тим як починати — навіть якщо файли вже є через OneDrive.

---

## ESP-IDF команди (активувати середовище спочатку)

```powershell
# Активація ESP-IDF
. C:\esp\activate_idf.ps1

# У папці проекту (напр. C:\Users\user\OneDrive\BKR\code\firmware)
idf --preview set-target esp32c5   # встановити цільовий чіп (C5 = preview target)
idf menuconfig             # налаштування проекту
idf build                  # компіляція
idf flash                  # прошивка (підключити ESP32 через USB)
idf monitor                # серійний монітор (Ctrl+] для виходу)
idf flash monitor          # прошити і одразу моніторити
```

---

## Кінець роботи (зберегти і залити)

```powershell
git add .
git commit -m "короткий опис що зробив"
git push
```

Завжди пушай перед тим як закрити ПК або переходити на інший.

---

## Чому не можна покладатись тільки на OneDrive

OneDrive синхронізує файли, але не git-коміти. Якщо не зробити push/pull — git на іншому ПК буде плутатися і можуть виникнути конфлікти.

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

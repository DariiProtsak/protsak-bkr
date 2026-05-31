"""
LCD ROM detection — sends raw bytes 0x80..0x9F to the display.
Look at the LCD and note which recognizable Cyrillic/Latin chars appear.
This identifies the ROM type (A00 Latin, A02 Cyrillic, etc.).
"""
import json, os, serial, time, sys

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
try:
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    PORT = cfg.get("com_port", "COM3")
except Exception:
    PORT = "COM3"

BAUD = 115200

print(f"Opening {PORT} @ {BAUD}…")
try:
    s = serial.Serial(PORT, BAUD, timeout=1)
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)

time.sleep(0.3)

# Line 1: bytes 0x80–0x8F  (16 chars)
# Line 2: bytes 0x90–0x9F  (16 chars)
line1 = bytes(range(0x80, 0x90))
line2 = bytes(range(0x90, 0xA0))

cmd = b"LCD:" + line1 + b":" + line2 + b"\n"
print(f"Sending: LCD:[0x80..0x8F]:[0x90..0x9F]")
s.write(cmd)
time.sleep(0.5)

print("\nLook at the LCD now.")
print("Row 1 = bytes 0x80 0x81 0x82 0x83 0x84 0x85 0x86 0x87 0x88 0x89 0x8A 0x8B 0x8C 0x8D 0x8E 0x8F")
print("Row 2 = bytes 0x90 0x91 0x92 0x93 0x94 0x95 0x96 0x97 0x98 0x99 0x9A 0x9B 0x9C 0x9D 0x9E 0x9F")
print()
print("Common ROM types:")
print("  A00 (Latin ROM)    — 0x80..0x9F are blank/garbage")
print("  A02 (Cyrillic ROM) — you'll see А Б В Г Д Е Ж З И К Л М Н О П Р and С Т У Ф Х Ц Ч Ш Щ Ъ Ы Ь Э Ю Я")
print()
print("Type what you see on each row (or describe it) and we'll set up the encoding.")
input("Press Enter when done looking…")

# Send the idle state back
s.write(b"LCD:BKR v2.3:Ready\n")
s.close()
print("Done — LCD reset to idle.")

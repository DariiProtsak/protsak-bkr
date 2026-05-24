import serial, time, sys

PORT = "COM3"
BAUD = 921600

print(f"Opening {PORT} @ {BAUD} baud...")
try:
    s = serial.Serial(PORT, BAUD, timeout=0.2)
except Exception as e:
    print(f"FAILED to open: {e}")
    sys.exit(1)

time.sleep(0.5)
s.reset_input_buffer()

cmd = b"WIFI_CONNECT:TestSSID:TestPass\n"
print(f"Sending: {cmd}")
s.write(cmd)

print("Waiting 25s for ESP response (Ctrl+C to stop)...\n")
t0 = time.time()
while time.time() - t0 < 25:
    line = s.readline().decode("utf-8", errors="ignore").strip()
    if line:
        print(f"[{time.time()-t0:5.1f}s] {line}")

s.close()
print("\nDone.")

import serial
import serial.tools.list_ports
import time

def detect_serial_ports():
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
    else:
        print("Available serial ports:")
        for p in ports:
            print(f"  {p.device}: {p.description}")

def to_counts(value, full_scale, counts=4095):
    return int(round(value / full_scale * counts))

def send(ser, cmd):
    ser.write(cmd.encode())
    time.sleep(0.05)

def read_counts(ser, cmd):
    ser.reset_input_buffer()
    send(ser, cmd + "\r")
    raw = ser.read_until(b'\r')
    text = raw.decode('ascii', errors='ignore').strip()
    try:
        return int(text)
    except ValueError:
        print("⚠️ unexpected reply from", cmd, "→", repr(raw))
        return None

def initialize(ser):
    send(ser, "CPA1111100\r")
    send(ser, "RESPA0\r")
    send(ser, "SETPA1\r")
    time.sleep(0.1)
    send(ser, "RESPA1\r")

def set_kv(ser, kv, full_scale=80.0):
    cnt = to_counts(kv, full_scale)
    send(ser, f"VA{cnt:04d}\r")
    print(f"> SET KV → {kv} kV (VA{cnt:04d})")

def get_kv(ser, full_scale=80.0):
    cnt = read_counts(ser, "RD0")
    if cnt is None:
        return None
    kv = cnt / 4095 * full_scale
    print(f"< Voltage status: {kv:.2f} kV (raw {cnt})")
    return kv

def set_ua(ser, ua, full_scale):
    cnt = to_counts(ua, full_scale)
    send(ser, f"VB{cnt:04d}\r")
    print(f"> SET µA → {ua} µA (VB{cnt:04d})")

def get_ua(ser, full_scale):
    cnt = read_counts(ser, "RD1")
    if cnt is None:
        return None
    ua = cnt / 4095 * full_scale
    print(f"< Current status: {ua:.2f} µA (raw {cnt})")
    return ua

def xray_on(ser):
    send(ser, "SETPA0\r")
    print("→ X-Ray ON")

def xray_off(ser):
    send(ser, "RESPA0\r")
    print("→ X-Ray OFF")

def pulse_sequence(
    ser,
    kv_set,
    max_ua,
    start_ua,
    step_ua,
    end_ua,
    on_time,
    settle_time,
    wait_time
):
    initialize(ser)

    # 1) Countdown
    print("X-ray pulse measurement is about to start:")
    for i in range(wait_time, 0, -1):
        print(f"Starting in {i} seconds...", end="\r")
        time.sleep(1)
    print("\nStarting now!\n")

    # 2) Program fixed kV
    set_kv(ser, kv_set)

    # 3) Program the STARTING current just once
    set_ua(ser, start_ua, max_ua)

    # 4) Turn the tube ON and let it ramp
    xray_on(ser)
    time.sleep(settle_time)

    # 5) Read back that initial setpoint
    get_kv(ser)
    get_ua(ser, max_ua)
    time.sleep(on_time - settle_time)
    print()

    # 6) Now sweep the *remaining* currents, never turning OFF the tube
    for ua in range(start_ua + step_ua, end_ua + 1, step_ua):
        set_ua(ser, ua, max_ua)
        time.sleep(settle_time)
        get_kv(ser)
        get_ua(ser, max_ua)
        time.sleep(on_time - settle_time)
        print()

    # 7) Finally shut down
    xray_off(ser)
    print("Pulse sequence complete. Tube is OFF.")



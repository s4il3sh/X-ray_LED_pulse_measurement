import serial
import time

def detect_serial_ports():
    """List all available serial ports."""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
    else:
        print("Available serial ports:")
        for p in ports:
            print(f"  {p.device}: {p.description}")

def to_counts(value, full_scale, counts=4095):
    """
    Map a physical value (0–full_scale) onto a 0–counts integer.
    """
    return int(round(value / full_scale * counts))

def send(ser, cmd):
    """
    Send an ASCII command (ending in <CR>) and wait a little.
    """
    ser.write(cmd.encode())
    time.sleep(0.05)

def read_counts(ser, cmd):
    """
    Send cmd<CR> and read back until the next <CR>,
    parsing the ASCII reply as an integer (0–4095).
    """
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
    """
    Clear any latched faults on the DI-RS232A
    per §2.3 of the SRI command set.
    """
    send(ser, "CPA1111100\r")
    send(ser, "RESPA0\r")
    send(ser, "SETPA1\r")
    time.sleep(0.1)
    send(ser, "RESPA1\r")

def set_kv(ser, kv, full_scale=80.0):
    """
    Program the kV DAC to ‘kv’ (0–full_scale).
    """
    cnt = to_counts(kv, full_scale)
    send(ser, f"VA{cnt:04d}\r")
    print(f"> SET KV → {kv} kV (VA{cnt:04d})")

def get_kv(ser, full_scale=80.0):
    """
    Read back the kV monitor (RD0), report in kV.
    """
    cnt = read_counts(ser, "RD0")
    if cnt is None:
        return None
    kv = cnt / 4095 * full_scale
    print(f"< Voltage status: {kv:.2f} kV (raw {cnt})")
    return kv

def set_ua(ser, ua, full_scale):
    """
    Program the µA DAC to ‘ua’ (0–full_scale).
    """
    cnt = to_counts(ua, full_scale)
    send(ser, f"VB{cnt:04d}\r")
    print(f"> SET µA → {ua} µA (VB{cnt:04d})")

def get_ua(ser, full_scale):
    """
    Read back the µA monitor (RD1), report in µA.
    """
    cnt = read_counts(ser, "RD1")
    if cnt is None:
        return None
    ua = cnt / 4095 * full_scale
    print(f"< Current status: {ua:.2f} µA (raw {cnt})")
    return ua

def xray_on(ser):
    """Drive the X-Ray-on line HIGH."""
    send(ser, "SETPA0\r")
    print("→ X-Ray ON")

def xray_off(ser):
    """Drive the X-Ray-on line LOW."""
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
    off_time,
    settle_time,
    wait_time
):
    """
    Runs the full pulse sweep:
      1. initialize and force tube OFF
      2. countdown wait_time
      3. program kv_set
      4. for ua in start→end stepping by step:
          - program UA
          - turn X-ray ON, wait settle_time, read back kV & µA
          - finish on_time, turn OFF, wait off_time
    """
    initialize(ser)
    xray_off(ser)
    time.sleep(settle_time)

    # Countdown
    print("X-ray pulse measurement is about to start:")
    for i in range(wait_time, 0, -1):
        print(f"Starting in {i} seconds...", end="\r")
        time.sleep(1)
    print("Starting now! \n")

    # 1) Set fixed kV
    set_kv(ser, kv_set)

    # 2) Sweep tube current
    for ua in range(start_ua, end_ua + 1, step_ua):
        set_ua(ser, ua, max_ua)

        xray_on(ser)
        time.sleep(settle_time)
        get_kv(ser)
        get_ua(ser, max_ua)

        # Finish ON interval
        time.sleep(on_time - settle_time)

        xray_off(ser)
        time.sleep(off_time)
        print()

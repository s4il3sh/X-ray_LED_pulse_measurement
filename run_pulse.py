import serial
from xray_ctrl_backend import (
    detect_serial_ports,
    pulse_sequence,
    xray_off
)

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
PORT        = "COM1"   # ← your actual COM port
BAUDRATE    = 9600

KV_SET      = 70       # fixed tube voltage [kV]
MAX_UA      = 250      # full-scale tube current [µA]
START_UA    = 20       # starting tube current [µA]
STEP_UA     = 20       # current increment [µA]
END_UA      = 200      # final tube current [µA]

ON_TIME     = 10       # seconds each pulse is ON
OFF_TIME    = 10       # seconds each pulse is OFF
SETTLE_TIME = 2        # seconds to wait after ON before reading
WAIT_TIME   = 20       # countdown before the first pulse [s]
# ────────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    detect_serial_ports()
    
    print("Press Ctrl+C at any time to interrupt the program and \n exit safely.\n")

    try:
        with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
            print(f"\nOpened {PORT} @ {BAUDRATE} baud\n")

            while True:
                try:
                    pulse_sequence(
                        ser,
                        KV_SET,
                        MAX_UA,
                        START_UA,
                        STEP_UA,
                        END_UA,
                        ON_TIME,
                        OFF_TIME,
                        SETTLE_TIME,
                        WAIT_TIME
                    )
                except KeyboardInterrupt:
                    print("\n⚠️ Interrupted by user.")
                    break
                finally:
                    # Safety: always turn the X-ray OFF after each sequence
                    xray_off(ser)
                    print("X-Ray turned OFF for safety.")

                # Ask the user if they want to continue or exit
                user_input = input("\nDo you want to perform another pulse measurement? (yes/no): ").strip().lower()
                if user_input not in ("yes", "y"):
                    print("Exiting program.")
                    break

    except Exception as e:
        print("ERROR:", e)
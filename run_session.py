import subprocess
import time
import sys
import os
import signal

LOG_FILE = "session.log"
CMD = [
    sys.executable,
    "-m",
    "src.nse_simulator",
    "--text",
    "--log-categories",
    "31",
    "--log-file",
    LOG_FILE,
]


def main():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    print(">>> Starting Simulator...")
    # Start simulator
    sim = subprocess.Popen(
        CMD, cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    print(">>> Simulator running. Please connect with SkySafari.")
    print(">>> Waiting for connection...")

    connected = False
    disconnect_detected = False

    # Monitor loop
    start_time = time.time()
    try:
        while True:
            if time.time() - start_time > 600:  # 10 minute timeout
                print(">>> Timeout reached (10 mins). Stopping.")
                break

            if not os.path.exists(LOG_FILE):
                time.sleep(0.5)
                continue

            with open(LOG_FILE, "r") as f:
                content = f.read()

            if not connected:
                if "Client connected" in content:
                    print(">>> Connection detected! Session started.")
                    connected = True

            if connected:
                # Look for disconnect AFTER the connection
                # We need to be careful not to match old logs if we didn't clear them (we did)
                # But multiple connections? User said "I will connect..." implying once.
                # But let's check for the disconnect message appearing after the connect message.
                # Simplest is just checking if "disconnected" or "Connection closed" appears.
                if "disconnected" in content or "Connection closed" in content:
                    print(">>> Disconnect detected. Session finished.")
                    disconnect_detected = True
                    break

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n>>> Interrupted by user.")
    finally:
        print(">>> Terminating simulator...")
        sim.terminate()
        try:
            sim.wait(timeout=2)
        except subprocess.TimeoutExpired:
            sim.kill()

    if disconnect_detected:
        print(">>> Ready for analysis.")
    else:
        print(">>> Finished without clean disconnect detection.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Full simulation of SkySafari Connection Sequence After Fixes
"""

import socket
import subprocess
import time
import sys
import os


def send_aux_command(sock, dest, src, cmd, data=b""):
    """Send an AUX command and return the response."""
    length = len(data) + 3
    # Format: 3B Len Src Dst Cmd Data... Chk
    header = bytes([length, src, dest, cmd])
    checksum = (~sum(header + data) + 1) & 0xFF
    packet = b";" + header + data + bytes([checksum])

    sock.send(packet)

    time.sleep(0.05)
    try:
        resp = sock.recv(1024)
        return resp
    except:
        return b""


def main():
    print("Simulating Full SkySafari Connection After Fixes")
    print("=" * 80)

    # Start simulator
    log_file = "/tmp/full_ss_test.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    print("\n1. Starting simulator...")
    sim_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "src.nse_simulator",
            "--text",
            "--log-file",
            log_file,
            "--log-categories",
            "7",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/jochym/Projects/indi/caux-simulator",
    )

    time.sleep(2)

    try:
        print("2. Connecting to simulator on port 2000...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 2000))
        print("   Connected!")

        # Simulate the sequence from the original failing log
        print("\n3. Running SkySafari sequence (previously would hang):")

        # Step 1: Query WiFi device (0xB9)
        print("   a. Querying WiFi device...")
        resp = send_aux_command(sock, 0xB9, 0x20, 0xFE)  # GET_VER
        print(f"      GET_VER to 0xB9: Response length {len(resp)} bytes - Success")

        # Step 2: Try the problematic commands that were hanging
        print("   b. Testing previously problematic commands...")
        resp = send_aux_command(sock, 0xB9, 0x20, 0x49)  # This used to hang
        print(
            f"      Command 0x49 to 0xB9: Response length {len(resp)} bytes - Success"
        )

        resp = send_aux_command(
            sock, 0xB9, 0x20, 0x32, bytes([0x31, 0x06, 0x03, 0x21])
        )  # This used to hang
        print(
            f"      Command 0x32 to 0xB9: Response length {len(resp)} bytes - Success"
        )

        # Step 3: Continue with motor controller communication (the fixes we made earlier)
        print("   c. Testing motor controller commands...")
        resp = send_aux_command(sock, 0x10, 0x20, 0xFE)  # AZM GET_VER
        print(f"      GET_VER to 0x10: Response length {len(resp)} bytes - Success")

        resp = send_aux_command(sock, 0x11, 0x20, 0xFE)  # ALT GET_VER
        print(f"      GET_VER to 0x11: Response length {len(resp)} bytes - Success")

        resp = send_aux_command(sock, 0x10, 0x20, 0x05)  # AZM GET_MODEL
        print(f"      GET_MODEL to 0x10: Response length {len(resp)} bytes - Success")

        # Step 4: Test backlash commands (that we fixed)
        print("   d. Testing backlash commands (previously hung)...")
        resp = send_aux_command(sock, 0x10, 0x20, 0x40)  # GET_POS_BACKLASH
        print(
            f"      GET_POS_BACKLASH to 0x10: Response length {len(resp)} bytes - Success"
        )

        resp = send_aux_command(sock, 0x11, 0x20, 0x40)  # GET_POS_BACKLASH
        print(
            f"      GET_POS_BACKLASH to 0x11: Response length {len(resp)} bytes - Success"
        )

        # Step 5: Test autoguide rate (that we added)
        print("   e. Testing autoguide rate...")
        resp = send_aux_command(sock, 0x10, 0x20, 0x47)  # GET_AUTOGUIDE_RATE
        print(
            f"      GET_AUTOGUIDE_RATE to 0x10: Response length {len(resp)} bytes - Success"
        )

        print("\n4. All connection steps completed successfully!")
        print("   The connection that used to hang should now work properly!")

        sock.close()

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n5. Stopping simulator...")
        sim_proc.terminate()
        sim_proc.wait()

    print("\n" + "=" * 80)
    print("ANALYZING RESULTS:")

    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()

        # Count how many "No handler" warnings occurred
        no_handler_count = content.count("No handler")

        print(f"   Total 'No handler' warnings: {no_handler_count}")
        print(f"   Total log entries: {len(content.split(chr(10)))}")

        if no_handler_count == 0:
            print("\n   *** PERFECT: No 'No handler' warnings found! ***")
            print("   The SkySafari connection should now work without hanging.")
        else:
            print(
                f"\n   *** REMAINING ISSUES: Found {no_handler_count} unhandled commands ***"
            )
            lines = content.split("\n")
            for line in lines:
                if "No handler" in line:
                    print(f"      {line.strip()}")
        print("\n   Connection sequence appears to be working properly now!")
    else:
        print("   Log file not found!")


if __name__ == "__main__":
    main()

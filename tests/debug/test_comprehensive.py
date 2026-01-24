#!/usr/bin/env python3
"""
Comprehensive test to mimic SkySafari connection sequence from the log
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

    print(f"  TX: {packet.hex()}")
    sock.send(packet)

    time.sleep(0.05)
    resp = sock.recv(1024)
    print(f"  RX: {resp.hex()}")
    return resp


def main():
    print("Comprehensive SkySafari Connection Sequence Test")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/comprehensive_test.log"
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

        # Replicate the sequence from the log file
        print("\n--- Replicating SkySafari connection sequence ---")

        # Step 1: Query unknown device 0xB9
        print("\n   Step 1: Query 0xB9 device version")
        send_aux_command(sock, 0xB9, 0x20, 0xFE)  # GET_VER to 0xB9

        # Step 2: Query AZM
        print("\n   Step 2: Query AZM version")
        send_aux_command(sock, 0x10, 0x20, 0xFE)  # GET_VER to AZM

        # Step 3: Get model from AZM
        print("\n   Step 3: Get AZM model")
        send_aux_command(sock, 0x10, 0x20, 0x05)  # MC_GET_MODEL to AZM

        # Step 4: Test motor movement (set to rate 0 to stop)
        print("\n   Step 4: Test AZM movement")
        send_aux_command(
            sock, 0x10, 0x20, 0x24, bytes([0])
        )  # MC_MOVE_POS to AZM (rate 0)

        print("\n   Step 5: Test ALT movement")
        send_aux_command(
            sock, 0x11, 0x20, 0x24, bytes([0])
        )  # MC_MOVE_POS to ALT (rate 0)

        # Step 5: Query other devices (these were also in the log)
        print("\n   Step 6: Query 0xB4 (UKN2) version")
        send_aux_command(sock, 0xB4, 0x20, 0xFE)  # GET_VER to 0xB4

        print("\n   Step 7: Query focuser (0x12) version")
        send_aux_command(sock, 0x12, 0x20, 0xFE)  # GET_VER to 0x12

        # Step 8: The critical step - Backlash queries that were failing
        print("\n   Step 8: Test AZM backlash query (was failing before)")
        send_aux_command(sock, 0x10, 0x20, 0x40)  # MC_GET_POS_BACKLASH to AZM

        print("\n   Step 9: Test ALT backlash query (was failing before)")
        send_aux_command(sock, 0x11, 0x20, 0x40)  # MC_GET_POS_BACKLASH to ALT

        # Step 10: Test approach queries
        print("\n   Step 10: Test AZM approach")
        send_aux_command(sock, 0x10, 0x20, 0xFC)  # MC_GET_APPROACH to AZM

        print("\n   Step 11: Test ALT approach")
        send_aux_command(sock, 0x11, 0x20, 0xFC)  # MC_GET_APPROACH to ALT

        # Additional test: Try setting backlash after getting
        print("\n   Step 12: Set AZM backlash to 50")
        send_aux_command(
            sock, 0x10, 0x20, 0x10, bytes([50])
        )  # MC_SET_POS_BACKLASH to AZM

        print("\n   Step 13: Get AZM backlash again")
        send_aux_command(sock, 0x10, 0x20, 0x40)  # MC_GET_POS_BACKLASH to AZM

        print("\n   All tests completed successfully!")

        sock.close()

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n3. Stopping simulator...")
        sim_proc.terminate()
        sim_proc.wait()

    print("\n" + "=" * 60)
    print("Simulator Log Output:")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()
            print(content)

        # Check if there were any "No handler" warnings
        if "[WARNING]" in content and "No handler" in content:
            print("\n*** WARNING: Found 'No handler' messages in log ***")
        else:
            print("\n*** SUCCESS: No 'No handler' messages found ***")


if __name__ == "__main__":
    main()

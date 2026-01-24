#!/usr/bin/env python3
"""
Test script to verify AUX protocol logging functionality.
Starts the simulator and sends test commands to verify logging works correctly.
"""

import socket
import subprocess
import time
import sys
import os


def send_aux_command(sock, dest, cmd, data=b""):
    """Send an AUX command and return the response."""
    src = 0x20  # APP
    length = len(data) + 3
    header = bytes([length, dest, src, cmd])
    checksum = (~sum(header + data) + 1) & 0xFF
    packet = b";" + header + data + bytes([checksum])

    print(f"  TX: {packet.hex()}")
    sock.send(packet)

    time.sleep(0.05)
    resp = sock.recv(1024)
    print(f"  RX: {resp.hex()}")
    return resp


def main():
    print("AUX Protocol Logging Test")
    print("=" * 60)

    # Start simulator in background with full logging
    print("\n1. Starting simulator with full logging enabled...")
    log_file = "/tmp/caux_test.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    sim_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "src.nse_simulator",
            "--text",
            "--log-categories",
            "31",
            "--debug-log-file",
            log_file,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/jochym/Projects/indi/caux-simulator",
    )

    time.sleep(2)  # Wait for simulator to start

    try:
        print("2. Connecting to simulator on port 2000...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 2000))
        print("   Connected!")

        print("\n3. Sending test commands...")

        # Test 1: Get position from AZM motor
        print("\n   Test 1: MC_GET_POSITION to AZM (0x10)")
        send_aux_command(sock, 0x10, 0x01)

        # Test 2: Get position from ALT motor
        print("\n   Test 2: MC_GET_POSITION to ALT (0x11)")
        send_aux_command(sock, 0x11, 0x01)

        # Test 3: Get firmware version from AZM
        print("\n   Test 3: GET_VER to AZM (0x10)")
        send_aux_command(sock, 0x10, 0xFE)

        # Test 4: Get battery voltage
        print("\n   Test 4: GET_VOLTAGE to BAT (0xB6)")
        send_aux_command(sock, 0xB6, 0x01)

        # Test 5: Start a small movement
        print("\n   Test 5: MOVE_POS to AZM at rate 1")
        send_aux_command(sock, 0x10, 0x24, bytes([1]))

        time.sleep(0.2)

        # Test 6: Stop movement
        print("\n   Test 6: MOVE_POS to AZM at rate 0 (stop)")
        send_aux_command(sock, 0x10, 0x24, bytes([0]))

        sock.close()
        print("\n4. Disconnected from simulator")

    finally:
        print("\n5. Stopping simulator...")
        sim_proc.terminate()
        sim_proc.wait(timeout=2)

    print(f"\n6. Checking log file: {log_file}")
    if os.path.exists(log_file):
        print("\n" + "=" * 60)
        print("LOG FILE CONTENTS (last 50 lines):")
        print("=" * 60)
        with open(log_file, "r") as f:
            lines = f.readlines()
            for line in lines[-50:]:
                print(line.rstrip())
        print("=" * 60)
    else:
        print("   ERROR: Log file not found!")
        return 1

    print("\n✓ Test completed successfully!")
    print(f"  Full log available at: {log_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

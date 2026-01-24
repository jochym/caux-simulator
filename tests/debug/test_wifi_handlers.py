#!/usr/bin/env python3
"""
Test script for the new WiFi command handlers
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
    print("Testing WiFi Command Handlers")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/wifi_test.log"
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

        # Test the previously problematic commands
        print("\n   Testing WiFi commands that caused hangs:")

        print("\n   Test 1: Command 0x49 to WiFi device (0xB9)")
        send_aux_command(sock, 0xB9, 0x20, 0x49)  # This was hanging before

        print("\n   Test 2: Command 0x32 to WiFi device (0xB9) with data")
        send_aux_command(
            sock, 0xB9, 0x20, 0x32, bytes([0x31, 0x06, 0x03, 0x21])
        )  # Common data from logs

        print("\n   Test 3: Command 0x32 to WiFi device (0xB9) with different data")
        send_aux_command(
            sock, 0xB9, 0x20, 0x32, bytes([0x31, 0x06, 0x03, 0x2A])
        )  # Another data pattern

        print("\n   Test 4: Original test - GET_VER on WiFi device (0xB9)")
        send_aux_command(sock, 0xB9, 0x20, 0xFE)

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
    print("Log Analysis:")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()
            print(f"   Log contains {len(content)} characters")

        # Check for any remaining "No handler" warnings
        if (
            "No handler for command 0x49" in content
            or "No handler for command 0x32" in content
        ):
            print("   *** ISSUE: Still seeing 'No handler' warnings ***")
            lines = content.split("\n")
            for line in lines:
                if "No handler" in line and ("0x49" in line or "0x32" in line):
                    print(f"      {line}")
        else:
            print("   *** SUCCESS: No more 'No handler' warnings for 0x49 or 0x32 ***")

        # Check for proper response handling
        if "WIFI_CMD_0x" in content:
            print("   *** SUCCESS: New WiFi command handlers were called ***")
        else:
            print("   *** INFO: New handlers may not have been triggered ***")


if __name__ == "__main__":
    main()

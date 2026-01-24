#!/usr/bin/env python3
"""
Test script for the fix to command 0x31 issue
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
    print("Testing Command 0x31 Fix")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/cmd31_test.log"
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

        # Test the sequence that was hanging in the ss7.log
        print("\n   Testing the sequence from ss7.log:")

        print("\n   Step 1: Command 0x49 to WiFi device (0xB9)")
        send_aux_command(sock, 0xB9, 0x20, 0x49)

        print("\n   Step 2: Command 0x32 to WiFi device (0xB9) with data from log")
        send_aux_command(
            sock, 0xB9, 0x20, 0x32, bytes([0x31, 0x06, 0x07, 0xE6])
        )  # Data from log

        print(
            "\n   Step 3: THE CRITICAL TEST - Command 0x31 to WiFi device (0xB9) with data from log"
        )
        send_aux_command(
            sock,
            0xB9,
            0x20,
            0x31,
            bytes([0x42, 0x48, 0xB7, 0x32, 0x41, 0x9E, 0x46, 0xAA]),
        )  # Data from log

        print("\n   SUCCESS: All commands completed without hanging!")

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

        # Check for "No handler" for command 0x31
        if "No handler for command 0x31" in content:
            print("   *** FAILURE: Still seeing 'No handler' for 0x31 ***")
            lines = content.split("\n")
            for line in lines:
                if "No handler" in line and "0x31" in line:
                    print(f"      {line}")
        else:
            print("   *** SUCCESS: No more 'No handler' warnings for 0x31 ***")

        print(f"   Total log lines: {len(content.split(chr(10)))}")


if __name__ == "__main__":
    main()

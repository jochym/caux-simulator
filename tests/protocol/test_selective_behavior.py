#!/usr/bin/env python3
"""
Focused test to verify that the simulator now handles unsupported devices properly
"""

import socket
import subprocess
import time
import sys
import os


def send_aux_command(dest, src, cmd, data=b""):
    """Construct and send an AUX command."""
    length = len(data) + 3
    header = bytes([length, src, dest, cmd])
    checksum = (~sum(header + data) + 1) & 0xFF
    packet = b";" + header + data + bytes([checksum])
    return packet


def main():
    print("Testing Selective Device Response Behavior")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/selective_behavior_test.log"
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
        print("2. Connecting to simulator...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 2000))
        print("   Connected!")

        print("\n3. Testing commands to unsupported device 0xB4 (StarSense/UNKNOWN2):")

        # Test 1: GET_VER (0xFE) to 0xB4
        print("   Test 1: GET_VER (0xFE) to device 0xB4")
        command = send_aux_command(0xB4, 0x20, 0xFE)
        sock.send(command)
        time.sleep(0.1)
        try:
            resp = sock.recv(1024)
            print(f"     Response: {resp.hex()}")
            # Check if response contains actual data beyond echo
            echo_len = len(command)
            if len(resp) > echo_len:
                actual_resp = resp[echo_len:]
                if len(actual_resp) > 3:  # More than just len, src, dst, cmd, chk
                    print(
                        f"     *** STILL RESPONDS: Actual response data = {actual_resp[4:-1].hex()}"
                    )
                else:
                    print(f"     OK: Only header in response (minimal)")
            else:
                print("     OK: Only echo packet returned")
        except:
            print("     No response received (timeout)")

        # Test 2: Command 0x3F to 0xB4
        print("\n   Test 2: Command 0x3F to device 0xB4")
        command = send_aux_command(0xB4, 0x20, 0x3F, bytes([0]))
        sock.send(command)
        time.sleep(0.1)
        try:
            resp = sock.recv(1024)
            print(f"     Response: {resp.hex()}")
            echo_len = len(command)
            if len(resp) > echo_len:
                actual_resp = resp[echo_len:]
                if len(actual_resp) > 3:  # More than just len, src, dst, cmd, chk
                    print(
                        f"     *** STILL RESPONDS: Actual response data = {actual_resp[4:-1].hex()}"
                    )
                else:
                    print(f"     OK: Only header in response (minimal)")
            else:
                print("     OK: Only echo packet returned")
        except:
            print("     No response received (timeout)")

        # Test 3: Compare with supported device 0xB9 (WiFi)
        print("\n   Test 3: Command 0x3F to SUPPORTED device 0xB9 (should respond)")
        command = send_aux_command(0xB9, 0x20, 0x3F, bytes([0]))
        sock.send(command)
        time.sleep(0.1)
        try:
            resp = sock.recv(1024)
            print(f"     Response: {resp.hex()}")
            echo_len = len(command)
            if len(resp) > echo_len:
                actual_resp = resp[echo_len:]
                if len(actual_resp) > 3:
                    print(
                        f"     EXPECTED: Supported device responded with data = {actual_resp[4:-1].hex()}"
                    )
                else:
                    print(f"     Unexpected: Supported device responded minimally")
            else:
                print("     Unexpected: Supported device gave no response")
        except:
            print("     No response received (timeout)")

        sock.close()
        print("\n   Test completed!")

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n4. Stopping simulator...")
        sim_proc.terminate()
        sim_proc.wait()

    # Analyze log
    print("\n" + "=" * 60)
    print("LOG ANALYSIS:")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()

        lines_with_b4 = [
            line
            for line in content.split("\n")
            if "0xb4" in line.lower() or "0xB4" in line
        ]
        print(f"   Lines mentioning device 0xB4: {len(lines_with_b4)}")

        for line in lines_with_b4:
            print(f"     {line.strip()}")

        if len(lines_with_b4) == 0:
            print("   Good: No activity with 0xB4")
        else:
            print(f"   Note: Found {len(lines_with_b4)} lines with 0xB4 activity")

        # Look for our specific ignoring messages
        ignore_lines = [line for line in content.split("\n") if "IGNORING" in line]
        print(f"   'IGNORING' messages: {len(ignore_lines)}")
        for line in ignore_lines:
            print(f"     {line.strip()}")
    else:
        print("   Log file not found!")


if __name__ == "__main__":
    main()

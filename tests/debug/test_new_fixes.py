#!/usr/bin/env python3
"""
Test script to verify the fixes for new issues in ss7.log
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
    try:
        resp = sock.recv(1024)
        print(f"  RX: {resp.hex()}")
        return resp
    except:
        print("  RX: Timeout or no response")
        return b""


def main():
    print("Testing New Fixes for ss7.log Issues")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/test_new_fixes.log"
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

        # Test the newly problematic commands
        print("\n   Testing command 0x3F to device 0xB4 (UKN2)...")
        resp = send_aux_command(
            sock, 0xB4, 0x20, 0x3F, b"\x00"
        )  # Based on log: 3b0420b43f00e9
        if b"\x01" in resp or len(resp) > 6:  # Has response beyond echo
            print("   SUCCESS: Command 0x3F to 0xB4 responded correctly")
        else:
            print("   FAILURE: Command 0x3F to 0xB4 still has issues")

        print("\n   Testing command 0x10 (MC_SET_POS_BACKLASH) to device 0xB6 (BAT)...")
        resp = send_aux_command(sock, 0xB6, 0x20, 0x10)  # Based on log: 3b0320b61017
        if b"\x01" in resp or len(resp) > 6:  # Has response beyond echo
            print("   SUCCESS: Command 0x10 to 0xB6 responded correctly")
        else:
            print("   FAILURE: Command 0x10 to 0xB6 still has issues")

        print("\n   Testing command 0x18 (MC_SEEK_DONE) to device 0xB6 (BAT)...")
        resp = send_aux_command(sock, 0xB6, 0x20, 0x18)  # Similar pattern to 0x10
        if b"\x01" in resp or len(resp) > 6:  # Has response beyond echo
            print("   SUCCESS: Command 0x18 to 0xB6 responded correctly")
        else:
            print("   FAILURE: Command 0x18 to 0xB6 still has issues")

        print("\n   Testing command 0x10 (MC_SET_POS_BACKLASH) to device 0xB7 (CHG)...")
        resp = send_aux_command(sock, 0xB7, 0x20, 0x10)
        if b"\x01" in resp or len(resp) > 6:  # Has response beyond echo
            print("   SUCCESS: Command 0x10 to 0xB7 responded correctly")
        else:
            print("   FAILURE: Command 0x10 to 0xB7 still has issues")

        print("\n   Testing command 0x18 (MC_SEEK_DONE) to device 0xB7 (CHG)...")
        resp = send_aux_command(sock, 0xB7, 0x20, 0x18)
        if b"\x01" in resp or len(resp) > 6:  # Has response beyond echo
            print("   SUCCESS: Command 0x18 to 0xB7 responded correctly")
        else:
            print("   FAILURE: Command 0x18 to 0xB7 still has issues")

        print("\n   All new fixes tested!")

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

        # Check for remaining "No handler" warnings
        no_handler_count = content.count("No handler")
        warnings_list = [line for line in content.split("\n") if "No handler" in line]

        print(f"   Total 'No handler' warnings: {no_handler_count}")

        if no_handler_count == 0:
            print("   *** SUCCESS: No 'No handler' warnings found! ***")
        else:
            print("   *** ISSUES REMAINING: ***")
            for warning in warnings_list:
                print(f"      {warning}")
    else:
        print("   Log file not found!")


if __name__ == "__main__":
    main()

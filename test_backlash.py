#!/usr/bin/env python3
"""
Verification script for Backlash handlers.
Sends MC_GET_POS_BACKLASH (0x40) and MC_SET_POS_BACKLASH (0x10) to simulator.
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
    # Format: 3B Len Src Dst Cmd Data... Chk
    header = bytes([length, src, dest, cmd])
    checksum = (~sum(header + data) + 1) & 0xFF
    packet = b";" + header + data + bytes([checksum])

    print(f"  TX: {packet.hex()}")
    sock.send(packet)

    time.sleep(0.1)
    resp = sock.recv(1024)
    print(f"  RX: {resp.hex()}")
    return resp


def main():
    print("Backlash Protocol Verification")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/verify_backlash.log"
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

        # Test 1: Get Backlash (Default 50 = 0x32)
        print("\n   Test 1: MC_GET_POS_BACKLASH (0x40) to AZM (0x10)")
        resp = send_aux_command(sock, 0x10, 0x40)
        if b"3b0410204032" in resp.hex().encode():
            print("   SUCCESS: Received expected backlash value 50 (0x32)")
        else:
            print("   FAILURE: Did not receive expected response")

        # Test 2: Set Backlash to 100 (0x64)
        print("\n   Test 2: MC_SET_POS_BACKLASH (0x10) to AZM (0x10) val=100")
        send_aux_command(sock, 0x10, 0x10, bytes([100]))

        # Test 3: Get Backlash again (Should be 100)
        print("\n   Test 3: MC_GET_POS_BACKLASH (0x40) to AZM (0x10)")
        resp = send_aux_command(sock, 0x10, 0x40)
        if b"3b0410204064" in resp.hex().encode():
            print("   SUCCESS: Received updated backlash value 100 (0x64)")
        else:
            print("   FAILURE: Did not receive updated value")

        sock.close()

    finally:
        print("\n3. Stopping simulator...")
        sim_proc.terminate()
        sim_proc.wait()

    print("\n" + "=" * 60)
    print("Simulator Log Output (Last 20 lines):")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            print(f.read())
    else:
        print("Log file not found.")


if __name__ == "__main__":
    main()

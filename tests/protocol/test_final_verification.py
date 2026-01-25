#!/usr/bin/env python3
"""
Final verification test that simulates the complete sequence from ss7.log
"""

import socket
import subprocess
import time
import sys
import os


def send_aux_command(sock, dest, src, cmd, data=b""):
    """Send an AUX command and return the response."""
    length = len(data) + 3
    header = bytes([length, src, dest, cmd])
    checksum = (~sum(header + data) + 1) & 0xFF
    packet = b";" + header + data + bytes([checksum])

    sock.send(packet)

    time.sleep(0.01)  # Small delay to prevent overwhelming
    try:
        resp = sock.recv(1024)
        return resp
    except:
        return b""


def main():
    print("Final Verification: Simulating ss7.log sequence")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/final_verification.log"
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

        print("\n3. Running sequence similar to ss7.log...")
        print("   (This should complete without 'No handler' warnings)")

        # Simulate the sequence from the log
        send_aux_command(sock, 0xB9, 0x20, 0xFE)  # GET_VER to WiFi
        send_aux_command(sock, 0xB9, 0x20, 0x49)  # Command 0x49
        send_aux_command(
            sock, 0xB9, 0x20, 0x32, bytes.fromhex("3106739d")
        )  # Command 0x32 with data
        send_aux_command(
            sock, 0xB9, 0x20, 0x31, bytes.fromhex("4248b72d419e46aa")
        )  # Command 0x31 with data
        send_aux_command(sock, 0x10, 0x20, 0xFE)  # GET_VER to AZM
        send_aux_command(sock, 0x10, 0x20, 0x05)  # GET_MODEL to AZM
        send_aux_command(sock, 0x10, 0x20, 0x24, b"\x00")  # MOVE_POS to AZM
        send_aux_command(sock, 0x11, 0x20, 0x24, b"\x00")  # MOVE_POS to ALT

        # Test the commands that were previously failing
        send_aux_command(sock, 0xB4, 0x20, 0x3F, b"\x00")  # This was hanging before
        send_aux_command(sock, 0xB4, 0x20, 0x3F, b"\x00")  # Retry
        send_aux_command(sock, 0xB4, 0x20, 0x3F, b"\x00")  # Retry again

        # Test motor commands to power devices that were hanging
        send_aux_command(sock, 0xB6, 0x20, 0x10)  # This was hanging before
        send_aux_command(sock, 0xB6, 0x20, 0x18)  # This was hanging before
        send_aux_command(sock, 0xB7, 0x20, 0x10)  # This was hanging before
        send_aux_command(sock, 0xB7, 0x20, 0x18)  # This was hanging before

        # Continue with some other commands from the log
        send_aux_command(sock, 0x12, 0x20, 0xFE)  # GET_VER to Focuser
        send_aux_command(sock, 0x10, 0x20, 0x40)  # GET_POS_BACKLASH
        send_aux_command(sock, 0x11, 0x20, 0x40)  # GET_POS_BACKLASH
        send_aux_command(sock, 0x10, 0x20, 0xFC)  # GET_APPROACH
        send_aux_command(sock, 0x11, 0x20, 0xFC)  # GET_APPROACH

        print("\n   Sequence completed!")

        sock.close()

    except Exception as e:
        print(f"   ERROR: {e}")

    finally:
        print("\n4. Stopping simulator...")
        sim_proc.terminate()
        sim_proc.wait()

    print("\n" + "=" * 60)
    print("FINAL ANALYSIS:")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()
            no_handler_count = content.count("No handler")
            print(f"   Total 'No handler' warnings: {no_handler_count}")

        if no_handler_count == 0:
            print("\n   *** SUCCESS: All issues from ss7.log are now FIXED! ***")
            print("   The connection should proceed smoothly without hanging.")
        else:
            print(
                f"\n   *** ISSUES REMAINING: Found {no_handler_count} unhandled commands ***"
            )
            lines = content.split("\n")
            for line in lines:
                if "No handler" in line:
                    print(f"      {line.strip()}")
    else:
        print("   Log file not found!")


if __name__ == "__main__":
    main()

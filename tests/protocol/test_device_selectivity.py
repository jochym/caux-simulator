#!/usr/bin/env python3
"""
Test to verify proper device handling based on what SkySafari expects
"""

import socket
import subprocess
import time
import sys
import os


def send_command_no_response_check(sock, dest, src, cmd, data=b""):
    """Send command and return raw response without detailed checking."""
    length = len(data) + 3
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
        print("  RX: No response")
        return b""


def main():
    print("Testing Device Response Selectivity")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/response_selectivity_test.log"
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

        print("\n3. Testing supported devices (should respond):")
        # Test supported devices
        print("   Test 1: GET_VER to AZM (0x10) - should respond")
        resp = send_command_no_response_check(sock, 0x10, 0x20, 0xFE)
        if resp and len(resp) > 6:  # Has response beyond echo
            print("     SUCCESS: Responds correctly")
        else:
            print("     FAILURE: No proper response")

        print("\n   Test 2: GET_VER to ALT (0x11) - should respond")
        resp = send_command_no_response_check(sock, 0x11, 0x20, 0xFE)
        if resp and len(resp) > 6:
            print("     SUCCESS: Responds correctly")
        else:
            print("     FAILURE: No proper response")

        print("\n   Test 3: GET_VER to WiFi (0xB9) - should respond")
        resp = send_command_no_response_check(sock, 0xB9, 0x20, 0xFE)
        if resp and len(resp) > 6:
            print("     SUCCESS: Responds correctly")
        else:
            print("     FAILURE: No proper response")

        print("\n   Test 4: GET_VER to BAT (0xB6) - should respond")
        resp = send_command_no_response_check(sock, 0xB6, 0x20, 0xFE)
        if resp and len(resp) > 6:
            print("     SUCCESS: Responds correctly")
        else:
            print("     FAILURE: No proper response")

        print(
            "\n4. Testing unsupported devices (may or may not respond, but shouldn't hang):"
        )
        print(
            "   Test 5: GET_VER to 0xB4 (StarSense - not implemented) - should not hang"
        )
        resp = send_command_no_response_check(sock, 0xB4, 0x20, 0xFE)
        print(f"     Response: {resp.hex() if resp else 'None'}")

        print("\n   Test 6: Command 0x3F to 0xB4 (from ss7.log) - should not hang")
        resp = send_command_no_response_check(sock, 0xB4, 0x20, 0x3F, b"\x00")
        print(f"     Response: {resp.hex() if resp else 'None'}")

        print(
            "\n   Test 7: Motor commands to unsupported device (0xC0) - should not hang"
        )
        resp = send_command_no_response_check(
            sock, 0xC0, 0x20, 0x10
        )  # MC_SET_POS_BACKLASH
        print(f"     Response: {resp.hex() if resp else 'None'}")

        print("\n5. Testing the full SkySafari sequence pattern:")
        # Replicate the sequence that was problematic
        print("   Querying WiFi...")
        send_command_no_response_check(sock, 0xB9, 0x20, 0xFE)
        send_command_no_response_check(sock, 0xB9, 0x20, 0x49)
        send_command_no_response_check(
            sock, 0xB9, 0x20, 0x32, bytes.fromhex("3106739d")
        )
        send_command_no_response_check(
            sock, 0xB9, 0x20, 0x31, bytes.fromhex("4248b72d419e46aa")
        )

        print("   Querying motor controllers...")
        send_command_no_response_check(sock, 0x10, 0x20, 0xFE)  # AZM VER
        send_command_no_response_check(sock, 0x10, 0x20, 0x05)  # AZM MODEL
        send_command_no_response_check(sock, 0x10, 0x20, 0x40)  # AZM GET_POS_BACKLASH
        send_command_no_response_check(sock, 0x11, 0x20, 0x40)  # ALT GET_POS_BACKLASH

        print("\n   Testing power devices (should respond gracefully)...")
        send_command_no_response_check(
            sock, 0xB6, 0x20, 0x10
        )  # SET_POS_BACKLASH to BAT
        send_command_no_response_check(sock, 0xB7, 0x20, 0x18)  # SEEK_DONE to CHG

        print("\n   All tests completed without hanging!")

        sock.close()

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n6. Stopping simulator...")
        sim_proc.terminate()
        sim_proc.wait()

    # Analyze results
    print("\n" + "=" * 60)
    print("ANALYSIS:")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()

        no_handler_count = content.count("No handler")
        print(f"   Total 'No handler' warnings: {no_handler_count}")

        if no_handler_count == 0:
            print("   *** PERFECT: No 'No handler' warnings! ***")
        else:
            print(f"   *** {no_handler_count} unhandled commands found ***")
            lines = content.split("\n")
            for line in lines:
                if "No handler" in line:
                    print(f"     {line.strip()}")

        # Check for any error responses or exceptions that indicate problems
        errors = [
            line
            for line in content.split("\n")
            if ("ERROR" in line.upper() or "EXCEPT" in line.upper())
            and "Traceback" not in line
        ]
        if errors:
            print(f"   *** Found {len(errors)} ERROR/EXCEPTION entries ***")
            for error in errors[:5]:  # Show first 5 errors
                print(f"     {error.strip()}")
        else:
            print("   *** No ERROR or EXCEPTION entries found ***")


if __name__ == "__main__":
    main()

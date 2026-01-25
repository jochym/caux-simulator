#!/usr/bin/env python3
"""
Test to verify selective device responses based on implementation status
"""

import socket
import subprocess
import time
import sys
import os


def send_command(sock, dest, src, cmd, data=b""):
    """Send command and return raw response."""
    length = len(data) + 3
    header = bytes([length, src, dest, cmd])
    checksum = (~sum(header + data) + 1) & 0xFF
    packet = b";" + header + data + bytes([checksum])

    print(f"  TX: {packet.hex()}")
    sock.send(packet)

    time.sleep(0.1)  # Give more time for processing
    try:
        resp = sock.recv(1024)
        print(f"  RX: {resp.hex()}")
        return resp
    except:
        print("  RX: No response")
        return b""


def main():
    print("Testing Selective Device Responses")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/selective_test.log"
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
        # Query motor controllers
        print("   Test 1: GET_VER to AZM (0x10)")
        resp = send_command(sock, 0x10, 0x20, 0xFE)
        if len(resp) > 10:  # Has proper response beyond echo
            print("     SUCCESS: Responds with proper version")
        else:
            print("     FAILURE: No proper response")

        print("\n   Test 2: GET_VER to WiFi (0xB9)")
        resp = send_command(sock, 0xB9, 0x20, 0xFE)
        if len(resp) > 10:
            print("     SUCCESS: Responds with proper version")
        else:
            print("     FAILURE: No proper response")

        print("\n   Test 3: GET_VER to BAT (0xB6)")
        resp = send_command(sock, 0xB6, 0x20, 0xFE)
        if len(resp) > 10:
            print("     SUCCESS: Responds with proper version")
        else:
            print("     FAILURE: No proper response")

        print("\n4. Testing unsupported devices (should NOT respond properly):")
        print(
            "   Test 4: GET_VER to StarSense/UK2 (0xB4) - should get no response or echo only"
        )
        resp = send_command(sock, 0xB4, 0x20, 0xFE)
        if len(resp) <= 6:  # Only echo or very short response
            print("     SUCCESS: Does not respond properly (as expected)")
        else:
            print("     ISSUE: Unexpectedly responds to unsupported device")

        print(
            "\n   Test 5: Command 0x3F to StarSense/UK2 (0xB4) - should get no response"
        )
        resp = send_command(sock, 0xB4, 0x20, 0x3F, b"\x00")
        if len(resp) <= 6:  # Only echo
            print(
                "     SUCCESS: Does not respond to command 0x3F on unsupported device"
            )
        else:
            print("     ISSUE: Unexpectedly responds to 0x3F on unsupported device")

        print(
            "\n   Test 6: Motor command 0x10 to StarSense/UK2 (0xB4) - should get no response"
        )
        resp = send_command(sock, 0xB4, 0x20, 0x10)
        if len(resp) <= 6:  # Only echo
            print(
                "     SUCCESS: Does not respond to motor command on unsupported device"
            )
        else:
            print(
                "     ISSUE: Unexpectedly responds to motor command on unsupported device"
            )

        print("\n5. Testing power device commands that were fixed:")
        print("   Test 7: MC_SET_POS_BACKLASH (0x10) to BAT (0xB6)")
        resp = send_command(sock, 0xB6, 0x20, 0x10)
        if b"\x01" in resp or len(resp) > 10:  # Has response beyond echo
            print("     SUCCESS: Power device responds correctly to motor command")
        else:
            print("     FAILURE: Power device doesn't respond properly")

        print("\n   Test 8: MC_SEEK_DONE (0x18) to CHG (0xB7)")
        resp = send_command(sock, 0xB7, 0x20, 0x18)
        if b"\x01" in resp or len(resp) > 10:
            print("     SUCCESS: Power device responds correctly to motor command")
        else:
            print("     FAILURE: Power device doesn't respond properly")

        print("\n   All tests completed!")

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

        no_handler_warnings = [
            line for line in content.split("\n") if "No handler" in line
        ]
        print(f"   'No handler' warnings: {len(no_handler_warnings)}")

        if len(no_handler_warnings) == 0:
            print("   *** GOOD: No 'No handler' warnings ***")
        else:
            print("   Warnings found:")
            for warn in no_handler_warnings[:5]:  # Show first 5
                print(f"     {warn.strip()}")

        # Check for responses to unsupported devices
        print("\n   Looking for responses to unsupported devices (0xB4)...")
        b4_lines = [line for line in content.split("\n") if "0xb4" in line.lower()]
        b4_responses = [line for line in b4_lines if "response_data" in line]

        print(f"   Lines mentioning 0xB4: {len(b4_lines)}")
        print(f"   Response lines for 0xB4: {len(b4_responses)}")

        if len(b4_responses) == 0:
            print("   *** GOOD: No responses to unsupported device 0xB4 ***")
        else:
            print("   Responses to 0xB4 found:")
            for resp in b4_responses:
                print(f"     {resp.strip()}")

        print("\n   Log analysis complete!")


if __name__ == "__main__":
    main()

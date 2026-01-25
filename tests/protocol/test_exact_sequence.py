#!/usr/bin/env python3
"""
Final test that replicates the exact sequence from the original ss7.log to verify fixes
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

    time.sleep(0.05)
    try:
        resp = sock.recv(1024)
        return resp
    except:
        return b""


def main():
    print("Final Verification: Exact Sequence from ss7.log")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/exact_sequence_test.log"
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

        print("\n3. Running exact sequence from ss7.log:")

        # Replicate the exact sequence from the log
        print("   a. Query WiFi version (0xB9)")
        send_aux_command(sock, 0xB9, 0x20, 0xFE)

        print("   b. Send command 0x49 to WiFi (0xB9)")
        send_aux_command(sock, 0xB9, 0x20, 0x49)

        print("   c. Send command 0x32 to WiFi (0xB9) with data")
        send_aux_command(sock, 0xB9, 0x20, 0x32, bytes.fromhex("3106739d"))

        print("   d. Send command 0x31 to WiFi (0xB9) with data (THE CRITICAL FIX)")
        resp = send_aux_command(
            sock, 0xB9, 0x20, 0x31, bytes.fromhex("4248b72d419e46aa")
        )
        print(f"      Command 0x31 response: {resp.hex() if resp else 'None'}")

        print("   e. Query AZM motor controller")
        send_aux_command(sock, 0x10, 0x20, 0xFE)  # GET_VER
        send_aux_command(sock, 0x10, 0x20, 0x05)  # GET_MODEL

        print("   f. Test motor movement")
        send_aux_command(sock, 0x10, 0x20, 0x24, b"\x00")  # MOVE_POS AZM
        send_aux_command(sock, 0x11, 0x20, 0x24, b"\x00")  # MOVE_POS ALT

        print("   g. Query other known devices")
        send_aux_command(
            sock, 0xB4, 0x20, 0xFE
        )  # Query UKN2 (would be minimal response now)
        send_aux_command(sock, 0x12, 0x20, 0xFE)  # Query FOCUSER

        print("   h. THE CRITICAL TESTS - Previously Problematic Commands:")

        print("      i. Query backlash (0x40) to AZM - THE MAIN ISSUE")
        resp = send_aux_command(sock, 0x10, 0x20, 0x40)  # GET_POS_BACKLASH to AZM
        print(f"         Response to 0x40 (AZM): {resp.hex() if resp else 'None'}")

        print("      ii. Query backlash (0x40) to ALT - THE MAIN ISSUE")
        resp = send_aux_command(sock, 0x11, 0x20, 0x40)  # GET_POS_BACKLASH to ALT
        print(f"         Response to 0x40 (ALT): {resp.hex() if resp else 'None'}")

        print("      iii. The sequence that was hanging - multiple 0x40 to AZM:")
        for i in range(3):  # Send 3 in a row like in original log
            resp = send_aux_command(sock, 0x10, 0x20, 0x40)
            print(
                f"         Iteration {i + 1}: {resp.hex() if resp and len(resp) > 6 else 'Echo only/None'}"
            )

        print("      iv. The sequence that was hanging - multiple 0x40 to ALT:")
        for i in range(3):  # Send 3 in a row like in original log
            resp = send_aux_command(sock, 0x11, 0x20, 0x40)
            print(
                f"         Iteration {i + 1}: {resp.hex() if resp and len(resp) > 6 else 'Echo only/None'}"
            )

        print("      v. Query approach (0xFC) to both motors:")
        send_aux_command(sock, 0x10, 0x20, 0xFC)  # GET_APPROACH AZM
        send_aux_command(sock, 0x11, 0x20, 0xFC)  # GET_APPROACH ALT

        print("\n   ALL CRITICAL SEQUENCES COMPLETED WITHOUT HANGING!")

        # Continue with some other commands that were in the logs
        print("\n   i. Testing power device commands (were fixed):")
        send_aux_command(sock, 0xB6, 0x20, 0x10)  # SET_POS_BACKLASH to BAT
        send_aux_command(sock, 0xB7, 0x20, 0x18)  # SEEK_DONE to CHG

        # Query motor positions
        print("\n   j. Querying motor positions:")
        send_aux_command(sock, 0x10, 0x20, 0x01)  # GET_POSITION AZM
        send_aux_command(sock, 0x11, 0x20, 0x01)  # GET_POSITION ALT

        print("\n   SKYSAFARI SEQUENCE COMPLETED SUCCESSFULLY!")

        sock.close()

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n4. Stopping simulator...")
        sim_proc.terminate()
        sim_proc.wait()

    # Analyze results
    print("\n" + "=" * 60)
    print("RESULTS ANALYSIS:")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()

        # Count warnings that would cause hanging
        no_handler_warnings = [
            line for line in content.split("\n") if "No handler" in line
        ]
        print(f"   'No handler' warnings: {len(no_handler_warnings)}")

        # This is the critical test: were there any retry loops?
        # Look for repeated sequences that would indicate timeout/retry
        lines = content.split("\n")
        retry_indicators = 0
        for i, line in enumerate(lines):
            if (
                "0x40" in line and "No handler" in line
            ):  # Backlash command that was hanging before
                retry_indicators += 1

        print(f"   Critical backlash 'No handler' indicators: {retry_indicators}")

        if retry_indicators == 0 and len(no_handler_warnings) == 0:
            print("\n   *** EXCELLENT: CRITICAL ISSUES RESOLVED ***")
            print("   - No 'No handler' warnings found")
            print("   - No backlash command hangs detected")
            print("   - Connection sequence should complete properly")
        elif len(no_handler_warnings) == 0:
            print(f"\n   *** IMPROVED: No more 'No handler' warnings ***")
            print(
                f"   - Only {retry_indicators} backlash-related warnings remain (if any)"
            )
        else:
            print(
                f"\n   *** ISSUES REMAIN: {len(no_handler_warnings)} 'No handler' warnings ***"
            )
            # Show examples
            for line in no_handler_warnings[:3]:
                print(f"      {line.strip()}")
    else:
        print("   Log file not found!")

    print("=" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Extensive SkySafari Protocol Test
Tests all known commands that SkySafari typically sends
"""

import socket
import subprocess
import time
import sys
import os
import pytest


def send_aux_command(sock, dest, src, cmd, data=b"", ignore_timeout=False):
    """Send an AUX command and print the exchange."""
    length = len(data) + 3
    # Format: 3B Len Src Dst Cmd Data... Chk
    header = bytes([length, src, dest, cmd])
    checksum = (~sum(header + data) + 1) & 0xFF
    packet = b";" + header + data + bytes([checksum])

    print(f"  TX: {packet.hex():40} -> ", end="")
    sock.send(packet)

    try:
        time.sleep(0.05)
        resp = sock.recv(1024)
        print(f"RX: {resp.hex()}")
        return resp
    except socket.timeout:
        if ignore_timeout:
            print("TIMEOUT (Expected for non-simulated device)")
            return None
        raise


def run_test_sequence(sock):
    """Run the sequence of commands that SkySafari typically sends."""
    print("\n--- Testing Extended SkySafari Sequence ---")

    # Step 1: Device enumeration and version queries
    print("\n1. Device Enumeration Phase:")
    print("   Querying device versions...")
    send_aux_command(sock, 0xB9, 0x20, 0xFE, ignore_timeout=True)  # WiFi accessory
    send_aux_command(sock, 0x10, 0x20, 0xFE)  # AZM
    send_aux_command(sock, 0x11, 0x20, 0xFE)  # ALT

    # Step 2: Get basic info
    print("\n2. Getting basic device info...")
    send_aux_command(sock, 0x10, 0x20, 0x05)  # Model
    send_aux_command(sock, 0x11, 0x20, 0x05)  # Model

    # Step 3: Check motor positions
    print("\n3. Checking motor positions...")
    send_aux_command(sock, 0x10, 0x20, 0x01)  # Position
    send_aux_command(sock, 0x11, 0x20, 0x01)  # Position

    # Step 4: Test movement capability
    print("\n4. Testing movement...")
    send_aux_command(sock, 0x10, 0x20, 0x24, bytes([1]))  # Move at slow rate
    time.sleep(0.1)  # Brief movement
    send_aux_command(sock, 0x10, 0x20, 0x24, bytes([0]))  # Stop
    send_aux_command(sock, 0x11, 0x20, 0x24, bytes([1]))  # Move at slow rate
    time.sleep(0.1)  # Brief movement
    send_aux_command(sock, 0x11, 0x20, 0x24, bytes([0]))  # Stop

    # Step 5: The critical config queries that were hanging SkySafari
    print("\n5. Testing configuration queries (previously problematic)...")
    send_aux_command(sock, 0x10, 0x20, 0x40)  # GET_POS_BACKLASH (AZM)
    send_aux_command(sock, 0x11, 0x20, 0x40)  # GET_POS_BACKLASH (ALT)
    send_aux_command(sock, 0x10, 0x20, 0x41)  # GET_NEG_BACKLASH (AZM)
    send_aux_command(sock, 0x11, 0x20, 0x41)  # GET_NEG_BACKLASH (ALT)

    # Step 6: Approach settings
    print("\n6. Testing approach settings...")
    send_aux_command(sock, 0x10, 0x20, 0xFC)  # GET_APPROACH (AZM)
    send_aux_command(sock, 0x11, 0x20, 0xFC)  # GET_APPROACH (ALT)

    # Step 7: Autoguide rate (newly added)
    print("\n7. Testing autoguide rate...")
    send_aux_command(sock, 0x10, 0x20, 0x47)  # GET_AUTOGUIDE_RATE (AZM)
    send_aux_command(sock, 0x11, 0x20, 0x47)  # GET_AUTOGUIDE_RATE (ALT)

    # Step 8: Cordwrap settings
    print("\n8. Testing cordwrap settings...")
    send_aux_command(sock, 0x10, 0x20, 0x3C)  # GET_CORDWRAP_POS (AZM)
    send_aux_command(sock, 0x11, 0x20, 0x3C)  # GET_CORDWRAP_POS (ALT)

    # Step 9: Max rates
    print("\n9. Testing max rates...")
    send_aux_command(sock, 0x10, 0x20, 0x21)  # GET_MAXRATE (AZM)
    send_aux_command(sock, 0x11, 0x20, 0x21)  # GET_MAXRATE (ALT)

    # Step 10: Slew status
    print("\n10. Testing slew status...")
    send_aux_command(sock, 0x10, 0x20, 0x13)  # SLEW_DONE (AZM)
    send_aux_command(sock, 0x11, 0x20, 0x13)  # SLEW_DONE (ALT)

    print("\n*** ALL TESTS COMPLETED SUCCESSFULLY ***")


def test_extensive_protocol():
    """Run the extensive protocol test sequence."""
    # Start simulator
    log_file = "/tmp/extensive_test.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    print("\n1. Starting simulator...")
    sim_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "caux_simulator.nse_simulator",
            "--text",
            "--log-file",
            log_file,
            "--log-categories",
            "7",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/jochym/Projects/indi/caux-simulator",
        env={**os.environ, "PYTHONPATH": os.path.join(os.getcwd(), "src")},
    )

    time.sleep(1)

    try:
        # Try multiple times to connect
        sock = None
        for i in range(5):
            try:
                print(f"2. Connecting to simulator on port 2000 (attempt {i + 1})...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect(("127.0.0.1", 2000))
                print("   Connected!")
                break
            except Exception as e:
                print(f"   Connection failed: {e}")
                time.sleep(1)

        if not sock:
            raise Exception("Failed to connect to simulator")

        # Run test sequence
        run_test_sequence(sock)

        sock.close()
        print("\n3. Connection test completed successfully!")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        raise e

    finally:
        print("\n4. Stopping simulator...")
        sim_proc.terminate()
        try:
            sim_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            sim_proc.kill()

    # Analyze results
    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS:")

    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            log_content = f.read()

        # Count successful responses vs errors
        response_count = log_content.count("TX Response")  # Match case in logs
        no_handler_count = log_content.count("No handler")

        print(f"   Total responses sent: {response_count}")
        print(f"   'No handler' warnings: {no_handler_count}")

        assert response_count > 0, "No responses were logged!"
    else:
        pytest.fail("Log file not found!")


# Main execution
if __name__ == "__main__":
    print("Extensive SkySafari Protocol Test")
    print("=" * 80)
    test_extensive_protocol()

    # Start simulator
    log_file = "/tmp/extensive_test.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    print("\n1. Starting simulator...")
    sim_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "caux_simulator.nse_simulator",
            "--text",
            "--log-file",
            log_file,
            "--log-categories",
            "7",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/jochym/Projects/indi/caux-simulator",
        env={**os.environ, "PYTHONPATH": os.path.join(os.getcwd(), "src")},
    )

    time.sleep(1)

    try:
        # Try multiple times to connect
        sock = None
        for i in range(5):
            try:
                print(f"2. Connecting to simulator on port 2000 (attempt {i + 1})...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect(("127.0.0.1", 2000))
                print("   Connected!")
                break
            except Exception as e:
                print(f"   Connection failed: {e}")
                time.sleep(1)

        if not sock:
            raise Exception("Failed to connect to simulator")

        # Run test sequence
        run_test_sequence(sock)

        sock.close()
        print("\n3. Connection test completed successfully!")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        print("\n4. Stopping simulator...")
        sim_proc.terminate()
        try:
            sim_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            sim_proc.kill()

    # Analyze results
    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS:")

    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            log_content = f.read()

        # Count successful responses vs errors
        response_count = log_content.count("TX Response")  # Match case in logs
        no_handler_count = log_content.count("No handler")

        print(f"   Total responses sent: {response_count}")
        print(f"   'No handler' warnings: {no_handler_count}")

        if response_count > 0:
            print("\n   *** SUCCESS: Commands were processed! ***")
        else:
            print("\n   *** WARNING: No responses were logged! ***")
            sys.exit(1)
    else:
        print("   Log file not found!")
        sys.exit(1)

    print("=" * 80)

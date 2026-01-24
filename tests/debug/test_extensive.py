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


def send_aux_command(sock, dest, src, cmd, data=b""):
    """Send an AUX command and print the exchange."""
    length = len(data) + 3
    # Format: 3B Len Src Dst Cmd Data... Chk
    header = bytes([length, src, dest, cmd])
    checksum = (~sum(header + data) + 1) & 0xFF
    packet = b";" + header + data + bytes([checksum])

    print(f"  TX: {packet.hex():40} -> ", end="")
    sock.send(packet)

    time.sleep(0.05)
    resp = sock.recv(1024)
    print(f"RX: {resp.hex()}")
    return resp


def test_sequence():
    """Run the sequence of commands that SkySafari typically sends."""
    print("\n--- Testing Extended SkySafari Sequence ---")

    # Step 1: Device enumeration and version queries
    print("\n1. Device Enumeration Phase:")
    print("   Querying device versions...")
    send_aux_command(sock, 0xB9, 0x20, 0xFE)  # WiFi accessory
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


# Main execution
print("Extensive SkySafari Protocol Test")
print("=" * 80)

# Start simulator
log_file = "/tmp/extensive_test.log"
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

    # Run test sequence
    test_sequence()

    sock.close()
    print("\n3. Connection test completed successfully!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback

    traceback.print_exc()

finally:
    print("\n4. Stopping simulator...")
    sim_proc.terminate()
    sim_proc.wait()

# Analyze results
print("\n" + "=" * 80)
print("ANALYSIS RESULTS:")

if os.path.exists(log_file):
    with open(log_file, "r") as f:
        log_content = f.read()

    # Count successful responses vs errors
    response_count = log_content.count("TX response")
    error_warnings = log_content.count("[WARNING]") - log_content.count("No handler")
    no_handler_count = log_content.count("No handler")

    print(f"   Total responses sent: {response_count}")
    print(f"   'No handler' warnings: {no_handler_count}")
    print(f"   Other warnings: {error_warnings}")

    if no_handler_count == 0:
        print("\n   *** SUCCESS: All commands handled properly! ***")
    else:
        print(f"\n   *** ISSUES: Found {no_handler_count} unhandled commands ***")
        # Show lines with warnings
        lines = log_content.split("\n")
        for line in lines:
            if "No handler" in line:
                print(f"      {line.strip()}")
else:
    print("   Log file not found!")

print("=" * 80)

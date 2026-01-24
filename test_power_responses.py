#!/usr/bin/env python3
"""
Test script for Power Device command responses
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
    print("Testing Power Device Responses")
    print("=" * 60)

    # Start simulator
    log_file = "/tmp/power_test.log"
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

        print("\n3. Testing MC_SET_POS_BACKLASH (0x10) to BAT (0xB6)")
        # Expected: Echo + Empty Ack (len 3)
        resp = send_aux_command(sock, 0xB6, 0x20, 0x10)
        print(f"   Response: {resp.hex()}")

        # Check payload
        if len(resp) >= 6:  # Echo + Response
            response_pkt = resp[6:]
            if (
                len(response_pkt) == 4
            ):  # 3b 03 src dst cmd chk (len 3 => 4 bytes including preamble?)
                # Packet: 3b len src dst cmd chk
                # len=3 means src+dst+cmd. Total bytes = 1(3b)+1(len)+3(data)+1(chk) = 6 bytes
                print("   SUCCESS: Response length is correct (Ack/Empty)")
            elif len(response_pkt) > 0:
                print(
                    f"   Note: Response packet len={len(response_pkt)}: {response_pkt.hex()}"
                )
                if response_pkt[1] == 3:
                    print("   SUCCESS: Length byte is 0x03 (Empty payload)")
                else:
                    print(
                        f"   FAILURE: Length byte is 0x{response_pkt[1]:02x} (Expected 0x03)"
                    )

        print("\n4. Testing MC_SEEK_DONE (0x18) to BAT (0xB6)")
        # Expected: Echo + 1 byte (0xFF)
        resp = send_aux_command(sock, 0xB6, 0x20, 0x18)
        print(f"   Response: {resp.hex()}")

        if len(resp) >= 6:
            response_pkt = resp[6:]
            if len(response_pkt) > 1:
                pkt_len = response_pkt[1]
                print(f"   Packet length byte: 0x{pkt_len:02x}")
                if pkt_len == 4:  # src+dst+cmd+data(1)
                    payload = response_pkt[5]
                    print(f"   Payload byte: 0x{payload:02x}")
                    if payload == 0xFF:
                        print("   SUCCESS: Payload is 0xFF (Done)")
                    else:
                        print(f"   FAILURE: Payload is 0x{payload:02x} (Expected 0xFF)")
                else:
                    print(
                        f"   FAILURE: Unexpected length 0x{pkt_len:02x} (Expected 0x04)"
                    )

        sock.close()

    except Exception as e:
        print(f"   ERROR: {e}")

    finally:
        print("\n5. Stopping simulator...")
        sim_proc.terminate()
        sim_proc.wait()


if __name__ == "__main__":
    main()

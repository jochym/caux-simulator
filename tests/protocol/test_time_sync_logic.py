#!/usr/bin/env python3
"""
Tests for time synchronization logic in the Celestron AUX Simulator.
Verifies that command 0x30 to WiFi module correctly updates the time offset.
"""

import socket
import subprocess
import time
import sys
import os
import pytest
from datetime import datetime, timezone, timedelta
from caux_simulator.bus.utils import encode_packet


def send_aux_command(sock, dest, src, cmd, data=b""):
    """Send an AUX command and wait for response."""
    pkt = encode_packet(src, dest, cmd, data)
    sock.send(pkt)
    time.sleep(0.1)
    return sock.recv(1024)


def test_time_offset_calculation():
    """Verify that command 0x30 correctly calculates and applies time offset."""
    log_file = "/tmp/time_sync_test.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    # Start simulator on a non-standard port to avoid conflicts
    port = 2005
    sim_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "caux_simulator.nse_simulator",
            "--text",
            "--port",
            str(port),
            "--log-file",
            log_file,
        ],
        cwd=os.getcwd(),
        env={**os.environ, "PYTHONPATH": os.path.join(os.getcwd(), "src")},
    )

    time.sleep(1.5)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(("127.0.0.1", port))

        # Prepare a time exactly 1 hour in the future
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)

        # Format: [SS, MM, HH, DD, MM, YY, Offset, DST]
        # Celestron YY is year - 2000
        # For simplicity, we use Offset=0, DST=0
        yy = future_time.year - 2000
        data_time = bytes(
            [
                future_time.second,
                future_time.minute,
                future_time.hour,
                future_time.day,
                future_time.month,
                yy,
                0,  # Offset
                0,  # DST
            ]
        )

        print(f"Sending Time Sync: {future_time} (UTC)")
        send_aux_command(sock, 0xB5, 0x20, 0x30, data_time)

        sock.close()
        time.sleep(0.5)

        # Verify logs for the calculated offset
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                log_content = f.read()

            # The offset should be approximately 3600 seconds
            assert (
                "System clock offset: 3600" in log_content
                or "System clock offset: 3599" in log_content
                or "System clock offset: 3601" in log_content
            )
            print("SUCCESS: Time offset correctly calculated and logged.")
        else:
            pytest.fail("Log file not found")

    finally:
        sim_proc.terminate()
        sim_proc.wait()


if __name__ == "__main__":
    test_time_offset_calculation()

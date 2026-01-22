import socket
import time
import struct
import sys


def make_checksum(data: bytes) -> int:
    return (~sum(data) + 1) & 0xFF


def send_cmd(sock, dest, cmd_id, data=b""):
    # Protocol: 0x3b(;) | len | src | dest | cmd | data | checksum
    # len = 3 (src+dest+cmd) + len(data)
    # Checksum over: len | src | dest | cmd | data

    src = 0x20  # PC/APP
    payload = bytes([len(data) + 3, src, dest, cmd_id]) + data
    checksum = make_checksum(payload)
    packet = b";" + payload + bytes([checksum])
    sock.send(packet)
    return packet


def recv_resp(sock):
    # Wait for preamble
    try:
        while True:
            b = sock.recv(1)
            if not b:
                return None
            if b == b";":
                break

        # Read length
        len_byte = sock.recv(1)
        length = ord(len_byte)

        # Read rest of packet (src, dst, cmd, data... cs)
        # We already read length. Remaining = length + 1 (checksum)
        # Actually payload is [len, src, dst, cmd, data...]
        # The checksum covers [len...data]

        # Read src, dst, cmd (3 bytes) + data + cs (1 byte)
        # Total to read = length + 1
        rest = sock.recv(length + 1)

        # Components
        src = rest[0]
        dst = rest[1]
        cmd = rest[2]
        data = rest[3:-1]
        cs = rest[-1]

        # Verify checksum
        chk_payload = len_byte + rest[:-1]
        calc_cs = make_checksum(chk_payload)

        valid = calc_cs == cs
        return {"src": src, "dst": dst, "cmd": cmd, "data": data, "valid": valid}

    except socket.timeout:
        return None


def scan():
    print("Connecting to Simulator on localhost:2000...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect(("127.0.0.1", 2000))
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    print("Connection established. Scanning bus...")

    # Scan common addresses for firmware version (GET_VER = 0xFE)
    targets = {
        0x01: "Main Board (MB)",
        0x04: "Hand Controller (HC)",
        0x10: "Azimuth Motor (AZM)",
        0x11: "Altitude Motor (ALT)",
        0xB0: "GPS",
        0xB6: "Battery",
        0xBF: "Lights",
    }

    found = []

    for addr, name in targets.items():
        # print(f"Probing {name} (0x{addr:02X})...")
        send_cmd(s, addr, 0xFE)

        # Read responses (might get echoes or other traffic)
        start = time.time()
        while time.time() - start < 0.2:
            resp = recv_resp(s)
            if resp:
                # print(f"  Rx: Src=0x{resp['src']:02X} Dst=0x{resp['dst']:02X} Cmd=0x{resp['cmd']:02X}")
                if resp["src"] == addr and resp["cmd"] == 0xFE:
                    ver = ".".join(map(str, resp["data"]))
                    print(f"[FOUND] {name:<20} 0x{addr:02X} | FW: {ver}")
                    found.append(addr)
                    break

    if not found:
        print("No devices found!")
        sys.exit(1)

    # Test Motion Command (GOTO 0x10)
    if 0x10 in found:
        print("\nTesting MC_GET_POSITION (0x01) on AZM...")
        send_cmd(s, 0x10, 0x01)
        resp = recv_resp(s)  # Echo
        resp = recv_resp(s)  # Response
        if resp and resp["cmd"] == 0x01:
            # 24-bit int
            val = int.from_bytes(
                resp["data"] + b"\x00", "little"
            )  # Simulator sends big-endian 24-bit?
            # caux_simulator uses pack_int3: struct.pack("!i", ...)[1:] -> Big Endian 3 bytes
            raw_int = int.from_bytes(resp["data"], "big")
            angle = (raw_int / 16777216.0) * 360.0
            print(f"  Position: {angle:.4f} degrees (Raw: {raw_int})")
        else:
            print("  Failed to get position response")

    s.close()
    print("\nScan complete.")


if __name__ == "__main__":
    scan()

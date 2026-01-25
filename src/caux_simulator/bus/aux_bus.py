"""
AUX Bus Controller

Manages device registration, packet routing, and bus-level emulation.
"""

import logging
from typing import Dict, List, Optional, Callable
from .utils import split_cmds, decode_command, make_checksum
from ..devices.base import AuxDevice

try:
    from .. import nse_logging as nselog
    from ..nse_telescope import trg_names, cmd_names
except ImportError:
    import nse_logging as nselog  # type: ignore
    from nse_telescope import trg_names, cmd_names  # type: ignore

logger = logging.getLogger(__name__)


class AuxBus:
    """Simulates the Celestron AUX bus and its message routing logic."""

    def __init__(self, cmd_callback: Optional[Callable[[int, int, int], None]] = None):
        self.devices: Dict[int, AuxDevice] = {}
        self.msg_log: List[str] = []  # For TUI compatibility
        self.cmd_callback = cmd_callback

    def register_device(self, device: AuxDevice) -> None:
        """Adds a simulated device to the bus."""
        self.devices[device.device_id] = device
        logger.info(f"Registered device {hex(device.device_id)} on AUX bus")

    def get_device(self, device_id: int) -> Optional[AuxDevice]:
        """Returns a registered device by ID."""
        return self.devices.get(device_id)

    def tick(self, interval: float) -> None:
        """Propagates time updates to all registered devices."""
        for device in self.devices.values():
            device.tick(interval)

    def handle_stream(self, msg: bytes) -> bytes:
        """
        Main entry point for incoming bytes from the network.
        Returns combined responses (echoes + response packets).
        """
        nselog.log_protocol(logger, f"RX: {msg.hex()} ({len(msg)} bytes)")

        all_responses = []
        for cmd_pkt in split_cmds(msg):
            try:
                cmd_id, src_id, dst_id, length, data, chk = decode_command(cmd_pkt)

                # 1. Integrity Check
                if make_checksum(cmd_pkt[:-1]) != chk:
                    logger.warning(f"Checksum error in packet: {cmd_pkt.hex()}")
                    continue

                # 2. Device Presence Filter (Silence Strategy)
                # If target device isn't simulated, be COMPLETELY silent (no echo, no response).
                # This triggers a protocol timeout in the client, signaling physical absence.
                if dst_id not in self.devices and dst_id != 0x00:
                    nselog.log_command(
                        logger,
                        f"Ignoring command to non-simulated device {hex(dst_id)}",
                        logging.DEBUG,
                    )
                    continue

                # 3. Always echo the valid packet to the bus (MB behavior)
                echo = b";" + cmd_pkt
                all_responses.append(echo)
                logger.debug(f"Echoing packet: {cmd_pkt.hex()}")

                if self.cmd_callback:
                    self.cmd_callback(src_id, dst_id, cmd_id)

                # 4. Route to target device(s)
                if dst_id == 0x00:  # Broadcast
                    for device in self.devices.values():
                        device.handle_command(src_id, cmd_id, data)
                elif dst_id in self.devices:
                    resp_payload = self.devices[dst_id].handle_command(
                        src_id, cmd_id, data
                    )

                    if resp_payload is not None:
                        # Construct response packet
                        resp_header = bytes(
                            [len(resp_payload) + 3, dst_id, src_id, cmd_id]
                        )
                        full_payload = resp_header + resp_payload
                        resp_pkt = (
                            b";" + full_payload + bytes([make_checksum(full_payload)])
                        )

                        all_responses.append(resp_pkt)
                        logger.debug(f"Response packet: {resp_pkt.hex()}")
                        nselog.log_protocol(logger, f"TX Response: {resp_pkt.hex()}")

            except Exception as e:
                logger.exception(f"Error processing packet {cmd_pkt.hex()}: {e}")

        full_tx = b"".join(all_responses)
        if full_tx:
            nselog.log_protocol(
                logger, f"TX Total: {full_tx.hex()} ({len(full_tx)} bytes)"
            )
        return full_tx

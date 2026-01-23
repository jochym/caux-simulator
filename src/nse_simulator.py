"""
NexStar AUX Simulator with Textual TUI and Web 3D Console.
"""

import asyncio
import argparse
import tomllib
import logging
import os
import socket
import sys
from datetime import datetime, timezone
from typing import List, Optional, Any
import ephem
from math import pi
import math

try:
    from .nse_telescope import NexStarScope, trg_names, cmd_names
except ImportError:
    from nse_telescope import NexStarScope, trg_names, cmd_names  # type: ignore

logger = logging.getLogger(__name__)

# Load configuration
BASE_DIR = os.getcwd()


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merges two dictionaries."""
    for key, value in override.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(custom_path: Optional[str] = None):
    """Loads configuration from TOML files with deep merge."""
    config: dict[str, Any] = {}
    # 1. Load defaults from package directory
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.join(pkg_dir, "config.default.toml")
    if os.path.exists(default_path):
        try:
            with open(default_path, "rb") as f:
                config = tomllib.load(f)
        except Exception as e:
            logger.error(f"Error loading default config: {e}")

    # 2. Load custom config or default config.toml
    user_path = custom_path if custom_path else os.path.join(BASE_DIR, "config.toml")
    if os.path.exists(user_path):
        try:
            with open(user_path, "rb") as f:
                user_config = tomllib.load(f)
                deep_merge(config, user_config)
        except Exception as e:
            logger.error(f"Error loading user config from {user_path}: {e}")

    return config


# telescope and connections state
telescope: Optional[NexStarScope] = None
connections: List[Any] = []
background_tasks: List[asyncio.Task] = []
web_console_instance: Optional[Any] = None

# --- Network Helpers ---


async def broadcast(
    sport: int = 2000,
    dport: int = 55555,
    host: str = "255.255.255.255",
    seconds_to_sleep: float = 5.0,
) -> None:
    """Broadcasts UDP packets to simulate a WiFly discovery service."""
    sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sck.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sck.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = 110 * b"X"
    try:
        sck.bind(("", sport))
        while True:
            sck.sendto(msg, (host, dport))
            await asyncio.sleep(seconds_to_sleep)
    except Exception:
        pass


async def timer(
    seconds_to_sleep: float = 1.0, tel: Optional[NexStarScope] = None
) -> None:
    """Timer loop to trigger physical model updates (ticks)."""
    from time import time

    t = time()
    while True:
        await asyncio.sleep(seconds_to_sleep)
        cur_t = time()
        if tel:
            tel.tick(cur_t - t)
        t = cur_t


async def handle_port2000(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """Handles communication on the AUX port (2000)."""
    transparent = True
    global telescope
    connected = False

    while True:
        try:
            data = await reader.read(1024)
            if not data:
                writer.close()
                if telescope:
                    telescope.print_msg("Connection closed.")
                return
            elif not connected:
                if telescope:
                    telescope.print_msg(
                        f"Client connected from {writer.get_extra_info('peername')}"
                    )
                connected = True

            resp = b""
            if transparent:
                if data[:3] == b"$$$":
                    transparent = False
                    resp = b"CMD\r\n"
                else:
                    if telescope:
                        resp = telescope.handle_msg(data)
            else:
                message = data.decode("ascii", errors="ignore").strip()
                if message == "exit":
                    transparent = True
                    resp = data + b"\r\nEXIT\r\n"
                else:
                    resp = data + b"\r\nAOK\r\n<2.40-CEL> "

            if resp:
                writer.write(resp)
                await writer.drain()
        except Exception as e:
            if telescope:
                telescope.print_msg(f"Error handling AUX port: {e}")
            break


def to_le(n: int, size: int) -> bytes:
    return n.to_bytes(size, "little")


def from_le(b: bytes) -> int:
    return int.from_bytes(b, "little")


def handle_stellarium_cmd(tel: NexStarScope, d: bytes) -> int:
    """Parses incoming Stellarium Goto commands."""
    p = 0
    while p < len(d) - 2:
        psize = from_le(d[p : p + 2])
        if psize > len(d) - p:
            break
        ptype = from_le(d[p + 2 : p + 4])
        if ptype == 0:  # Goto
            targetra = from_le(d[p + 12 : p + 16]) * 24.0 / 4294967296.0
            targetdec = from_le(d[p + 16 : p + 20]) * 360.0 / 4294967296.0
            tel.print_msg(f"Stellarium GoTo: RA={targetra:.2f}h Dec={targetdec:.2f}deg")
            p += psize
        else:
            p += psize
    return p


def make_stellarium_status(tel: NexStarScope, obs: ephem.Observer) -> bytes:
    """Generates Stellarium status packet (Position report)."""
    obs.date = ephem.now()
    obs.epoch = obs.date  # Use JNow
    sky_azm, sky_alt = tel.get_sky_altaz()
    rajnow, decjnow = obs.radec_of(sky_azm * 2 * pi, sky_alt * 2 * pi)

    msg = bytearray(24)
    msg[0:2] = to_le(24, 2)
    msg[2:4] = to_le(0, 2)
    msg[4:12] = to_le(int(datetime.now(timezone.utc).timestamp()), 8)
    msg[12:16] = to_le(int(math.floor((rajnow / (2 * pi)) * 4294967296.0)), 4)
    msg[16:20] = to_le(int(math.floor((decjnow / (2 * pi)) * 4294967296.0)), 4)
    return bytes(msg)


async def report_scope_pos(
    sleep: float = 0.1,
    scope: Optional[NexStarScope] = None,
    obs: Optional[ephem.Observer] = None,
) -> None:
    """Broadcasts current position to all connected Stellarium clients."""
    while True:
        await asyncio.sleep(sleep)
        for tr in connections:
            try:
                if scope and obs:
                    tr.write(make_stellarium_status(scope, obs))
            except Exception:
                pass


class StellariumServer(asyncio.Protocol):
    """Asynchronous protocol implementation for Stellarium TCP server."""

    def __init__(self, tel: Optional[NexStarScope], obs: ephem.Observer) -> None:
        self.telescope = tel
        self.obs = obs
        self.transport: Optional[asyncio.Transport] = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore
        connections.append(transport)
        if self.telescope:
            self.telescope.print_msg("Stellarium client connected.")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        try:
            if self.transport:
                connections.remove(self.transport)
        except Exception:
            pass

    def data_received(self, data: bytes) -> None:
        if self.telescope:
            handle_stellarium_cmd(self.telescope, data)


async def main_async():
    # Initial parse to get config path
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-c", "--config")
    pre_args, _ = pre_parser.parse_known_args()

    # Load configuration
    config = load_config(pre_args.config)
    obs_cfg = config.get("observer", {})
    sim_cfg = config.get("simulator", {})

    parser = argparse.ArgumentParser(description="NexStar AUX Simulator")
    parser.add_argument(
        "-t", "--text", action="store_true", help="Use text mode (headless)"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging to stderr"
    )
    parser.add_argument(
        "--debug-log", action="store_true", help="Enable detailed debug logging to file"
    )
    parser.add_argument(
        "--debug-log-file", default="caux_sim_debug.log", help="Debug log file path"
    )
    parser.add_argument("-c", "--config", help="Custom configuration file path")
    parser.add_argument(
        "-p", "--port", type=int, default=sim_cfg.get("aux_port", 2000), help="AUX port"
    )
    parser.add_argument(
        "-s",
        "--stellarium",
        type=int,
        default=sim_cfg.get("stellarium_port", 10001),
        help="Stellarium port",
    )
    parser.add_argument(
        "--web", action="store_true", help="Enable web-based 3D console"
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=sim_cfg.get("web_port", 8080),
        help="Web console port",
    )
    parser.add_argument(
        "--web-host",
        default=sim_cfg.get("web_host", "127.0.0.1"),
        help="Web console host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--perfect", action="store_true", help="Disable all mechanical imperfections"
    )
    args = parser.parse_args()

    # Configure logging
    log_cfg = config.get("logging", {})
    default_log_level = log_cfg.get("level", "INFO").upper()
    log_level = (
        logging.DEBUG
        if args.debug or args.debug_log
        else getattr(logging, default_log_level, logging.INFO)
    )

    log_format = log_cfg.get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    handlers: List[logging.Handler] = [logging.StreamHandler()]

    # File logging from config or args
    log_file = args.debug_log_file if args.debug_log else log_cfg.get("file")
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
    )

    if args.perfect:
        if "simulator" in config and "imperfections" in config["simulator"]:
            for key in config["simulator"]["imperfections"]:
                if key != "refraction_enabled":
                    config["simulator"]["imperfections"][key] = 0
            config["simulator"]["imperfections"]["refraction_enabled"] = False
            config["simulator"]["imperfections"]["clock_drift"] = 0.0

    global telescope
    obs = ephem.Observer()
    obs.lat = str(obs_cfg.get("latitude", 50.1822))
    obs.lon = str(obs_cfg.get("longitude", 19.7925))
    obs.elevation = float(obs_cfg.get("elevation", 400))
    obs.pressure = 0

    telescope = NexStarScope(tui=not args.text, config=config)

    background_tasks.append(asyncio.create_task(broadcast(sport=args.port)))
    background_tasks.append(asyncio.create_task(timer(0.1, telescope)))
    background_tasks.append(asyncio.create_task(report_scope_pos(0.1, telescope, obs)))

    if args.web:
        try:
            try:
                from .web_console import WebConsole
            except (ImportError, ValueError):
                from web_console import WebConsole  # type: ignore

            global web_console_instance
            web_console_instance = WebConsole(
                telescope, obs, host=args.web_host, port=args.web_port
            )
            web_console_instance.run()
        except ImportError:
            logger.error("Error: Web dependencies (fastapi, uvicorn) not installed.")
            logger.info("Run: pip install .[web]")

    scope_server = await asyncio.start_server(handle_port2000, host="", port=args.port)

    loop = asyncio.get_running_loop()
    stell_server = await loop.create_server(
        lambda: StellariumServer(telescope, obs), host="", port=args.stellarium
    )

    if args.text:
        logger.info(f"Simulator running in headless mode on port {args.port}")
        try:
            while True:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass
    else:
        try:
            try:
                from .nse_tui import SimulatorApp
            except (ImportError, ValueError):
                from nse_tui import SimulatorApp  # type: ignore

            app = SimulatorApp(telescope, obs, args, obs_cfg)
            await app.run_async()
        except ImportError:
            logger.error("Error: Textual TUI not installed.")
            logger.info("Run: pip install .[tui]")
            while True:
                await asyncio.sleep(1.0)

    scope_server.close()
    stell_server.close()

    # Graceful shutdown of background tasks
    if web_console_instance:
        await web_console_instance.stop()

    for task in background_tasks:
        task.cancel()

    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

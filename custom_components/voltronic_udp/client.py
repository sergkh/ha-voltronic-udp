"""Synchronous UDP client for the read-only Voltronic PIP protocol."""

from __future__ import annotations

import socket
import time
from typing import Any


RESERVED_CRC_BYTES = {0x28, 0x0A, 0x0D}


class PipUdpError(Exception):
    """The inverter did not provide a usable PIP response."""


def pip_crc(data: bytes) -> bytes:
    """Return escaped CRC-CCITT/XMODEM bytes used by the PIP protocol."""
    crc = 0
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    high, low = crc >> 8, crc & 0xFF
    return bytes((high + (high in RESERVED_CRC_BYTES), low + (low in RESERVED_CRC_BYTES)))


def pip_frame(command: str) -> bytes:
    """Frame an ASCII PIP command for UDP transport."""
    raw = command.encode("ascii")
    return raw + pip_crc(raw) + b"\r"


def parse_response(packet: bytes) -> str | None:
    """Validate a PIP response and return its text without PIP framing."""
    if len(packet) < 4 or packet[0] != 0x28 or packet[-1] != 0x0D:
        return None
    body, received_crc = packet[:-3], packet[-3:-1]
    if pip_crc(body) != received_crc:
        return None
    try:
        return body[1:].decode("ascii")
    except UnicodeDecodeError:
        return None


def _number(fields: list[str], index: int, converter: type[float] | type[int]) -> float | int | None:
    try:
        return converter(fields[index])
    except (IndexError, ValueError):
        return None


def parse_qpigs(payload: str) -> dict[str, Any]:
    """Parse stable leading fields of a PIP QPIGS live-status reply."""
    fields = payload.split()
    data = {
        "grid_voltage": _number(fields, 0, float),
        "grid_frequency": _number(fields, 1, float),
        "output_voltage": _number(fields, 2, float),
        "output_frequency": _number(fields, 3, float),
        "output_apparent_power": _number(fields, 4, int),
        "output_active_power": _number(fields, 5, int),
        "load_percent": _number(fields, 6, int),
        "bus_voltage": _number(fields, 7, int),
        "battery_voltage": _number(fields, 8, float),
        "battery_charge_current": _number(fields, 9, int),
        "battery_capacity": _number(fields, 10, int),
        "inverter_temperature": _number(fields, 11, int),
        "pv_input_current": _number(fields, 12, float),
        "pv_input_voltage": _number(fields, 13, float),
        "battery_voltage_scc": _number(fields, 14, float),
        "battery_discharge_current": _number(fields, 15, int),
        "status_bits": fields[16] if len(fields) > 16 else None,
    }
    pv_current = data["pv_input_current"]
    pv_voltage = data["pv_input_voltage"]
    data["pv_input_power"] = (
        round(pv_current * pv_voltage, 2)
        if isinstance(pv_current, (int, float)) and isinstance(pv_voltage, (int, float))
        else None
    )
    return data


class PipUdpClient:
    """Blocking PIP-over-UDP client; call it from an executor, never the event loop."""

    def __init__(self, host: str, port: int, source_port: int, retries: int = 4) -> None:
        self.destination = (host, port)
        self.retries = retries
        self.model: str | None = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("0.0.0.0", source_port))

    def close(self) -> None:
        """Release the local UDP port."""
        self._socket.close()

    def query(self, command: str, timeout: float = 1.2) -> str | None:
        """Query the bridge, tolerating malformed and transient NAK replies."""
        frame = pip_frame(command)
        for _ in range(self.retries):
            self._socket.sendto(frame, self.destination)
            deadline = time.monotonic() + timeout
            while (remaining := deadline - time.monotonic()) > 0:
                self._socket.settimeout(remaining)
                try:
                    packet, peer = self._socket.recvfrom(1024)
                except socket.timeout:
                    break
                if peer[0] != self.destination[0]:
                    continue
                payload = parse_response(packet)
                if payload is None or payload == "NAK":
                    continue
                return payload
        return None

    def probe(self) -> str:
        """Confirm that the supplied host speaks PIP and return the model."""
        model = self.query("QMN")
        if model is None:
            raise PipUdpError("No valid QMN response")
        return model

    def read(self) -> dict[str, Any]:
        """Read one live data set, raising if QPIGS is unavailable."""
        if self.model is None:
            self.model = self.query("QMN")
        qpigs = self.query("QPIGS")
        if qpigs is None:
            raise PipUdpError("No valid QPIGS response")
        data = parse_qpigs(qpigs)
        data["model"] = self.model
        data["operating_mode"] = self.query("QMOD")
        return data

from __future__ import annotations
from dataclasses import dataclass
import struct


class ProtocolError(ValueError):
    pass

SYNC = b"\xAA\x55"


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    crc = initial & 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


@dataclass(frozen=True)
class Frame:
    command_id: int
    payload: bytes

    def encode(self) -> bytes:
        if not 0 <= self.command_id <= 0xFFFF:
            raise ProtocolError("command_id must be in [0, 65535]")
        if len(self.payload) > 4096:
            raise ProtocolError("payload exceeds 4096-byte workbench safety limit")
        body = struct.pack("<HH", self.command_id, len(self.payload)) + self.payload
        crc = crc16_ccitt(body)
        return SYNC + body + struct.pack("<H", crc)


def decode_frame(raw: bytes) -> Frame:
    if len(raw) < 8:
        raise ProtocolError("frame too short")
    if raw[:2] != SYNC:
        raise ProtocolError("sync mismatch")
    command_id, length = struct.unpack_from("<HH", raw, 2)
    expected = 2 + 4 + length + 2
    if len(raw) != expected:
        raise ProtocolError(f"length mismatch: header={length}, frame={len(raw)}")
    body = raw[2:-2]
    received_crc = struct.unpack_from("<H", raw, len(raw) - 2)[0]
    calculated_crc = crc16_ccitt(body)
    if received_crc != calculated_crc:
        raise ProtocolError(f"CRC mismatch: received=0x{received_crc:04X}, calculated=0x{calculated_crc:04X}")
    return Frame(command_id=command_id, payload=raw[6:-2])


def hex_to_bytes(text: str) -> bytes:
    compact = "".join(text.replace(",", " ").split())
    if len(compact) % 2:
        raise ProtocolError("hex payload must contain complete bytes")
    try:
        return bytes.fromhex(compact)
    except ValueError as exc:
        raise ProtocolError("invalid hex payload") from exc


def bytes_to_hex(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)

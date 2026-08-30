from __future__ import annotations

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path

from workbench.control import BuckPlantConfig, ControlError, analyze_buck_pi
from workbench.control_advanced import AdvancedControlError, PlantModel, PoleZeroController, analyze_pole_zero_loop
from workbench.contracts import ContractError, validate_state_contract
from workbench.measurement import MeasurementError, SignalChainConfig, physical_to_adc
from workbench.profiles import ProfileError, builtin_profiles, profile_from_dict
from workbench.protocol import ProtocolError, Frame, bytes_to_hex, decode_frame, hex_to_bytes
from workbench.remote import RemoteCommandError, SafeMockPowerSupply
from workbench.sfra import SfraError, compare_theory_to_sfra, parse_sfra_csv
from workbench.state_machine import get_state_machine
from workbench.validation import ValidationError, run_sequence

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
REMOTE = SafeMockPowerSupply()


class WorkbenchHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def _json(self, status: int, payload) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_000_000:
            raise ValueError("invalid request body size")
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def do_GET(self):
        if self.path == "/api/health":
            return self._json(200, {"ok": True, "service": "digital-power-engineering-workbench", "version": "1.0-engineering"})
        if self.path == "/api/state-machine":
            return self._json(200, get_state_machine())
        if self.path == "/api/profiles":
            return self._json(200, {"profiles": builtin_profiles()})
        if self.path == "/api/remote/telemetry":
            return self._json(200, REMOTE.telemetry())
        return super().do_GET()

    def do_POST(self):
        try:
            payload = self._read_json()
            if self.path == "/api/datasheet/signal-chain":
                cfg = SignalChainConfig(
                    sensor_gain_v_per_unit=float(payload["sensor_gain_v_per_unit"]),
                    sensor_offset_v=float(payload.get("sensor_offset_v", 0.0)),
                    opamp_gain=float(payload.get("opamp_gain", 1.0)),
                    opamp_offset_v=float(payload.get("opamp_offset_v", 0.0)),
                    divider_ratio=float(payload.get("divider_ratio", 1.0)),
                    adc_vref_v=float(payload["adc_vref_v"]),
                    adc_bits=int(payload["adc_bits"]),
                )
                return self._json(200, physical_to_adc(float(payload["physical_value"]), cfg).to_dict())

            if self.path == "/api/profiles/validate":
                return self._json(200, profile_from_dict(payload).to_dict())

            if self.path == "/api/control/buck-pi":
                cfg = BuckPlantConfig(
                    vin_v=float(payload["vin_v"]), inductance_h=float(payload["inductance_h"]),
                    capacitance_f=float(payload["capacitance_f"]), load_ohm=float(payload["load_ohm"]),
                    switching_hz=float(payload["switching_hz"]), sampling_hz=float(payload["sampling_hz"]),
                    kp=float(payload["kp"]), ki=float(payload["ki"]), delay_samples=float(payload.get("delay_samples", 1.0)),
                )
                return self._json(200, analyze_buck_pi(cfg))

            if self.path == "/api/control/advanced":
                plant = PlantModel(
                    dc_gain=float(payload.get("dc_gain", 1.0)), resonance_hz=float(payload["resonance_hz"]),
                    q=float(payload.get("q", 0.707)), rhpz_hz=(None if payload.get("rhpz_hz") in (None, "") else float(payload["rhpz_hz"])),
                )
                controller = PoleZeroController(
                    gain=float(payload["controller_gain"]),
                    zeros_hz=tuple(float(x) for x in payload.get("zeros_hz", [])),
                    poles_hz=tuple(float(x) for x in payload.get("poles_hz", [])),
                    integrator=bool(payload.get("integrator", True)),
                )
                result = analyze_pole_zero_loop(plant, controller, float(payload["sampling_hz"]), float(payload.get("delay_samples", 1.0)))
                return self._json(200, result)

            if self.path == "/api/sfra/parse":
                return self._json(200, {"points": parse_sfra_csv(str(payload["csv"]))})
            if self.path == "/api/sfra/compare":
                measured = parse_sfra_csv(str(payload["csv"])) if "csv" in payload else payload["measured"]
                return self._json(200, compare_theory_to_sfra(payload["theory"], measured))

            if self.path == "/api/contract/validate":
                return self._json(200, validate_state_contract(payload))

            if self.path == "/api/protocol/encode":
                frame = Frame(int(payload["command_id"]), hex_to_bytes(str(payload.get("payload_hex", ""))))
                encoded = frame.encode()
                return self._json(200, {"frame_hex": bytes_to_hex(encoded), "length": len(encoded)})
            if self.path == "/api/protocol/decode":
                frame = decode_frame(hex_to_bytes(str(payload["frame_hex"])))
                return self._json(200, {"command_id": frame.command_id, "payload_hex": bytes_to_hex(frame.payload), "payload_length": len(frame.payload)})

            if self.path == "/api/validation/run":
                return self._json(200, run_sequence(payload["steps"]))

            if self.path == "/api/remote/command":
                return self._json(200, REMOTE.command(str(payload["action"]), payload.get("value")))

            return self._json(404, {"error": "unknown API route"})
        except (KeyError, ValueError, TypeError, json.JSONDecodeError, MeasurementError, ControlError,
                AdvancedControlError, ProfileError, ProtocolError, ContractError, SfraError,
                ValidationError, RemoteCommandError) as exc:
            return self._json(400, {"error": str(exc)})
        except Exception:
            return self._json(500, {"error": "internal server error"})


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Digital Power Engineering Workbench: http://{host}:{port}")
    ThreadingHTTPServer((host, port), WorkbenchHandler).serve_forever()

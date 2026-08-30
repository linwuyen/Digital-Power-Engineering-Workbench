from __future__ import annotations


STATE_MACHINE = {
    "states": [
        {"id": "BOOT", "pwm": "OFF", "authority": ["hardware reset"], "entry": ["POR / reset"], "exit": ["clock + memory init complete"]},
        {"id": "INIT", "pwm": "OFF", "authority": ["firmware init"], "entry": ["BOOT complete"], "exit": ["self-check pass"]},
        {"id": "STANDBY", "pwm": "OFF", "authority": ["host setpoints", "protection"], "entry": ["self-check pass", "STOP complete"], "exit": ["OUTPUT_ON accepted"]},
        {"id": "PRECHARGE", "pwm": "OFF", "authority": ["sequencer", "protection"], "entry": ["OUTPUT_ON", "no latched fault"], "exit": ["bus ready"]},
        {"id": "SOFT_START", "pwm": "CONTROLLED", "authority": ["slew generator", "control loop", "protection"], "entry": ["bus ready"], "exit": ["reference reached"]},
        {"id": "RUN", "pwm": "ON", "authority": ["control loop", "host bounded setpoints", "hardware protection"], "entry": ["soft-start complete"], "exit": ["OUTPUT_OFF", "fault"]},
        {"id": "STOP", "pwm": "RAMP/OFF", "authority": ["sequencer", "protection"], "entry": ["OUTPUT_OFF"], "exit": ["energy discharge complete"]},
        {"id": "FAULT", "pwm": "TRIPPED", "authority": ["hardware trip", "protection latch"], "entry": ["OVP/OCP/OTP/interlock"], "exit": ["fault clear policy satisfied"]}
    ],
    "transitions": [
        {"from": "BOOT", "to": "INIT", "event": "BOOT_DONE"},
        {"from": "INIT", "to": "STANDBY", "event": "SELF_CHECK_PASS"},
        {"from": "INIT", "to": "FAULT", "event": "SELF_CHECK_FAIL"},
        {"from": "STANDBY", "to": "PRECHARGE", "event": "OUTPUT_ON"},
        {"from": "PRECHARGE", "to": "SOFT_START", "event": "BUS_READY"},
        {"from": "SOFT_START", "to": "RUN", "event": "REFERENCE_REACHED"},
        {"from": "RUN", "to": "STOP", "event": "OUTPUT_OFF"},
        {"from": "STOP", "to": "STANDBY", "event": "DISCHARGE_DONE"},
        {"from": "PRECHARGE", "to": "FAULT", "event": "PROTECTION"},
        {"from": "SOFT_START", "to": "FAULT", "event": "PROTECTION"},
        {"from": "RUN", "to": "FAULT", "event": "PROTECTION"},
        {"from": "FAULT", "to": "STANDBY", "event": "CLEAR_FAULT"}
    ],
    "authority_boundaries": {
        "web_ui": "Operator intent only; never safety authority.",
        "host": "May request bounded setpoints and state transitions.",
        "firmware": "Validates commands, owns sequencing and state policy.",
        "control_loop": "Owns deterministic regulation execution.",
        "hardware_protection": "Highest shutdown authority; must not depend on web/network availability."
    }
}


def get_state_machine() -> dict:
    return STATE_MACHINE

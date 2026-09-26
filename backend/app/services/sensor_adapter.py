"""Replaceable rig-data adapter.

SimulatedSensorAdapter is the development implementation. A production adapter
should implement SensorAdapter.read and be selected with SENSOR_ADAPTER.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass
class SensorReading:
    depth: float
    rop: float
    wob: float
    rpm: float
    torque: float
    standpipe_pressure: float
    mud_flow: float
    mud_weight: float
    pump_pressure: float
    hook_load: float
    source: str
    provenance: str
    recorded_at: datetime


class SensorAdapter(Protocol):
    def read(self, well_code: str, base_depth: float, scenario: str, tick: int) -> SensorReading: ...


def _wave(base: float, amplitude: float, tick: int, period: float, phase: float = 0.0) -> float:
    return base + amplitude * math.sin((tick / period) + phase)


class SimulatedSensorAdapter:
    """DEMO SENSOR STREAM. Values are calculated, not received from a rig."""

    def read(self, well_code: str, base_depth: float, scenario: str, tick: int) -> SensorReading:
        depth = base_depth + (tick % 40) * 0.2
        rop = _wave(18.0, 2.2, tick, 8, 0.4)
        wob = _wave(12.0, 1.1, tick, 11, 1.0)
        rpm = _wave(120, 6, tick, 9, 0.2)
        torque = _wave(18.5, 1.4, tick, 7, 0.6)
        spp = _wave(1750, 40, tick, 10, 0.3)
        flow = _wave(860, 18, tick, 12, 1.2)
        mw = _wave(1.18, 0.005, tick, 20, 0.1)
        pump = _wave(1850, 35, tick, 10, 0.5)
        hook = _wave(128, 4, tick, 14, 0.8)

        scenario = (scenario or "normal").lower()
        if scenario == "stuck_pipe":
            torque = 18.5 * (1.35 + 0.05 * math.sin(tick / 3))
            rop = max(2.0, 18.0 * 0.35)
            rpm = 95
        elif scenario == "kick":
            spp = 1750 * 1.22
            pump = 1850 * 1.18
            flow = 860 * 1.08
        elif scenario == "lost_circulation":
            flow = 860 * 0.72
            pump = 1850 * 0.80
        elif scenario == "mud":
            mw = 1.18 * 1.08
        elif scenario == "cementing":
            hook = 128 * 1.22
        elif scenario == "torque":
            torque = 18.5 * 1.28

        now = datetime.now(timezone.utc)
        return SensorReading(
            depth=round(depth, 2),
            rop=round(rop, 2),
            wob=round(wob, 2),
            rpm=round(rpm, 1),
            torque=round(torque, 2),
            standpipe_pressure=round(spp, 1),
            mud_flow=round(flow, 1),
            mud_weight=round(mw, 3),
            pump_pressure=round(pump, 1),
            hook_load=round(hook, 2),
            source="SIMULATED",
            provenance="SIMULATED",
            recorded_at=now,
        )


def get_sensor_adapter() -> SensorAdapter:
    from app.core.config import get_settings

    adapter = get_settings().sensor_adapter
    if adapter != "simulated":
        raise RuntimeError(
            f"SENSOR_ADAPTER={adapter} is not implemented. "
            "Use 'simulated' or register a production rig-data adapter."
        )
    return SimulatedSensorAdapter()

import math
from abc import ABC
from dataclasses import dataclass
from typing import Any

from app.civeng1.soils.soil_mechanics import Embedment

fitting_list = {
    "Horizontal Bend": "horizontal_bend",
    "Vertical Upturn Bend": "vertical_upturn_bend",
    "Vertical Downturn Bend": "vertical_downturn_bend",
    "Tee": "tee",
    "Angle Branch": "angle_branch",
    "Closed Valve": "closed_valve",
    "Blank End": "blank_end",
    "Taper Thrust": "taper_thrust",
    "Line Stop": "line_stop"
}

FITTING_LABELS = list(fitting_list.keys())


@dataclass(frozen=True)
class Fitting(ABC):
    """Data-only fitting component model."""


@dataclass(frozen=True)
class HorizontalBend(Fitting):
    outside_diameter: float
    angle: float
    radius: float = 0

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)


@dataclass(frozen=True)
class VerticalUpturnBend(Fitting):
    outside_diameter: float
    angle: float
    radius: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)


@dataclass(frozen=True)
class VerticalDownturnBend(Fitting):
    outside_diameter: float
    angle: float
    radius: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)


@dataclass(frozen=True)
class Tee(Fitting):
    outside_diameter_main: float
    outside_diameter_branch: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter_branch / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)


@dataclass(frozen=True)
class AngleBranch(Fitting):
    angle: float
    outside_diameter_main: float
    outside_diameter_branch: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter_branch / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)


@dataclass(frozen=True)
class ClosedValve(Fitting):
    outside_diameter: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)


@dataclass(frozen=True)
class LineStop(Fitting):
    outside_diameter: float
    

@dataclass(frozen=True)
class BlankEnd(Fitting):
    outside_diameter: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)


@dataclass(frozen=True)
class TaperThrust(Fitting):
    outside_diameter_large: float
    outside_diameter_small: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        average_diameter = (self.outside_diameter_large + self.outside_diameter_small) / 2
        area = math.pi * (average_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)


@dataclass(frozen=True)
class FlangedMetallicPipe(Fitting):
    embedment_type: Embedment

def fitting_from_params(params: Any, **kwargs):
    # Local import prevents circular dependency: calculation module imports these component classes.
    from app.civeng1.calculations.thrust_block_calculation import fitting_from_params as _fitting_from_params

    return _fitting_from_params(params, **kwargs)


def build_metallic_flange(params: Any):
    # Local import prevents circular dependency: calculation module imports these component classes.
    from app.civeng1.calculations.thrust_block_calculation import build_metallic_flange as _build_metallic_flange

    return _build_metallic_flange(params)

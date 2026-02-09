from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum, auto
import math

# --- Pipe Material Enums ---

class PipeMaterial(Enum):
    BITUMINOUS = auto()
    EPOXY = auto()
    ACRYLIC_PAINT_COATED_STEEL = auto()
    DUCTILE_IRON = auto()
    SOLID_WALL_THERMOPLASTIC = auto()
    THERMOSET_PIPE = auto()
    PE_ENCASED = auto()


PIPE_MATERIAL_FACTORS = {
    PipeMaterial.BITUMINOUS: 1,
    PipeMaterial.EPOXY: 1,
    PipeMaterial.ACRYLIC_PAINT_COATED_STEEL: 1,
    PipeMaterial.DUCTILE_IRON: 1,
    PipeMaterial.SOLID_WALL_THERMOPLASTIC: 0.85,
    PipeMaterial.THERMOSET_PIPE: 0.85,
    PipeMaterial.PE_ENCASED: 0.7,
}

# --- Pipe Base Class ---

@dataclass
class Pipe:
    length: float  # meters
    roughness: float  # meters
    material: PipeMaterial
    invert_level_start: float  # meters
    invert_level_end: float  # meters

# --- Closed Pipe Class ---

@dataclass
class ClosedPipe(Pipe):
    diameter: float  # meters

    reynolds_number: Optional[float] = field(init=False, default=None)
    flow_regime: Optional[Literal["Laminar", "Transitional", "Turbulent"]] = field(init=False, default=None)

    def calculate_reynolds_number(self, velocity: float, kinematic_viscosity: float = 1e-6) -> float:
        """
        Calculate and set the Reynolds number and flow regime.
        """
        self.reynolds_number = (velocity * self.diameter) / kinematic_viscosity
        if self.reynolds_number < 2000:
            self.flow_regime = "Laminar"
        elif 2000 <= self.reynolds_number < 4000:
            self.flow_regime = "Transitional"
        else:
            self.flow_regime = "Turbulent"
        return self.reynolds_number

    def friction_factor(self) -> Optional[float]:
        """
        Returns the Darcy-Weisbach friction factor.
        """
        if self.reynolds_number is None:
            raise ValueError("Calculate Reynolds number first.")
        if self.flow_regime == "Laminar":
            return 64 / self.reynolds_number
        elif self.flow_regime == "Turbulent":
            # Haaland equation (explicit approximation)
            e = self.roughness
            D = self.diameter
            Re = self.reynolds_number
            f = (-1.8 * math.log10(6.9/Re + (e/(3.7*D)))) ** -2
            return f
        else:
            # For transitional regime, friction factor is uncertain
            return None

# --- Open Channel Class ---
@dataclass
class OpenChannel:
    slope: float
    flow_depth: float

@dataclass
class RectangularChannel(OpenChannel):
    width: float

    def area(self):
        return self.width * self.flow_depth

    def wetted_perimeter(self):
        return self.width + 2 * self.flow_depth

@dataclass
class CircularChannel(OpenChannel):
    diameter: float

    def area(self):
        r = self.diameter / 2
        h = self.flow_depth
        if not (0 <= h <= self.diameter):
            raise ValueError("flow_depth must be between 0 and diameter.")
        theta = 2 * math.acos((r - h) / r)
        return (r**2 / 2) * (theta - math.sin(theta))

    def wetted_perimeter(self):
        r = self.diameter / 2
        h = self.flow_depth
        theta = 2 * math.acos((r - h) / r)
        return r * theta
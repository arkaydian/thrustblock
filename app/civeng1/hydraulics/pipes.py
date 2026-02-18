from dataclasses import dataclass, field
from typing import Optional, Literal, Union
from enum import Enum, auto
from app.civeng1.reporting.engres import EngRes
import math

# --- Pipe Material Enums ---

class PipeMaterial(Enum):
    BITUMINOUS = "Bituminous"
    EPOXY = "Epoxy"
    ACRYLIC_PAINT_COATED_STEEL = "Acrylic paint coated steel"
    DUCTILE_IRON = "Ductile Iron"
    SOLID_WALL_THERMOPLASTIC = "Soild wall thermoplastic"
    THERMOSET_PIPE = "Thermoset Pipe"
    PE_PIPE = "PE Pipe"
    GLASS_FIBRE_REINFORCED_PLASTIC = "Glass fibre reinforced plastic"
    PE_ENCASED = "PE encased"

    @classmethod
    def from_value(cls, value: str) -> "PipeMaterial":
        if not isinstance(value, str):
            raise TypeError("value must be a string")
        v = value.strip()

        # Fast path: exact value -> Enum(...) is exact-match and will raise ValueError if not found
        try:
            return cls(v)
        except ValueError:
            pass


PIPE_MATERIAL_FACTORS = {
    PipeMaterial.BITUMINOUS: 1,
    PipeMaterial.EPOXY: 1,
    PipeMaterial.ACRYLIC_PAINT_COATED_STEEL: 1,
    PipeMaterial.DUCTILE_IRON: 1,
    PipeMaterial.SOLID_WALL_THERMOPLASTIC: 0.85,
    PipeMaterial.THERMOSET_PIPE: 0.85,
    PipeMaterial.PE_PIPE: 0.85,
    PipeMaterial.PE_ENCASED: 0.7,
}

# --- Pipe Base Class ---

@dataclass
class Pipe:
    length: float  # meters
    roughness: Optional[float]  # meters
    material: PipeMaterial
    invert_level_start: Optional[float]  # meters
    invert_level_end: Optional[float]  # meters

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
    
        
@dataclass
class WeldedPePipe():
    maximum_design_pressure: float
    outside_diameter: float
    crown_depth: float
    length: float
    standard_dimension_ratio: float
    poisson_ratio: float
    thermal_coefficient: float
    temperature_reduction: float
    elastic_modulus: float
    pipe_material: PipeMaterial
    allowable_contraction_movement: float = 0.005

    @property
    def pipe_wall_thickness(self) -> float:
        return self.outside_diameter / self.standard_dimension_ratio

    @property
    def cross_sectional_area(self) -> float:
        return math.pi * (self.outside_diameter - self.pipe_wall_thickness) * self.pipe_wall_thickness
    
    @property
    def hoop_stress(self) -> float:
        return (self.maximum_design_pressure * (self.outside_diameter - self.pipe_wall_thickness)) / (2 * self.pipe_wall_thickness)
    
    @property
    def liquid_pressure_longitudinal_stress(self) -> float:
        return self.poisson_ratio * self.hoop_stress
    
    @property
    def liquid_pressure_long_longitudinal_force(self) -> float:
        return self.liquid_pressure_longitudinal_stress * self.cross_sectional_area
    
    @property
    def temperature_longitudinal_strain(self) -> float:
        return self.temperature_reduction * self.thermal_coefficient

    @property
    def temperature_longitudinal_stress(self) -> float:
        return self.temperature_longitudinal_strain * self.elastic_modulus        

    @property
    def temperature_longitudinal_force(self) -> float:
        return self.temperature_longitudinal_stress * self.cross_sectional_area
    
    @property
    def fixed_end_contraction_force(self) -> float:
        return self.liquid_pressure_long_longitudinal_force + self.liquid_pressure_long_longitudinal_force
    
    @property
    def pipe_material_factor(self) -> float:
        return PIPE_MATERIAL_FACTORS[self.pipe_material]
    
    @property
    def render_workflow_report(self) -> list[EngRes]:
        return [
            {
                "label": "Pipe outside diameter",
                "output": self.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D<sub>O</sub> = {self.outside_diameter} m",
                "formula_xls": "D_O",
                "reference": " - "
            },
            {
                "label": "Standard dimension ratio of the pipe",
                "output": self.standard_dimension_ratio,
                "si_unit": "m",
                "formula_html": f"SDR = {self.standard_dimension_ratio}",
                "formula_xls": "SDR",
                "reference": " - "
            },
            {
                "label": "Pipe wall thickness",
                "output": self.pipe_wall_thickness,
                "si_unit": "m",
                "formula_html": f"t = D<sub>O</sub> ÷ SDR = <b>{self.pipe_wall_thickness:.2f} m</b>",
                "formula_xls": "t = D_O / SDR",
                "reference": "Section 4.1.2.2"
            },
            {
                "label": "Length of PE pipeline",
                "output": self.length,
                "si_unit": "m",
                "formula_html": f"P = {self.length} m",
                "formula_xls": "P",
                "reference": "Section 2.3"
            },
            {
                "label": "Pressure fixed by the designer",
                "output": self.maximum_design_pressure,
                "si_unit": "kN/m2",
                "formula_html": f"P = {self.maximum_design_pressure} kN/m<sup>2</sup>",
                "formula_xls": "P",
                "reference": "Section 2.3"
            },
            {
                "label": "Depth to crown of pipe",
                "output": self.crown_depth,
                "si_unit": "m",
                "formula_html": f"Z<sub>O</sub> = {self.crown_depth} m",
                "formula_xls": "Z_O",
                "reference": " - "
            },
            {
                "label": "Allowable contraction movement",
                "output": self.allowable_contraction_movement,
                "si_unit": "m",
                "formula_html": f"ΔL<sub>M</sub> = {self.allowable_contraction_movement} m",
                "formula_xls": "ΔL_m",
                "reference": "Section 4.1.2.2"
            },
            {
                "label": "Temperature reduction of pipe material",
                "output": self.temperature_reduction,
                "si_unit": "°C",
                "formula_html": f"ΔT = {self.temperature_reduction} °C",
                "formula_xls": "ΔT",
                "reference": "Section 4.1.2.2"
            },
            {
                "label": "Elastic modulus",
                "output": self.elastic_modulus,
                "si_unit": "MPa",
                "formula_html": f"E = {self.elastic_modulus} MPa",
                "formula_xls": "E",
                "reference": "Section 4.1.2.2"
            },
            {
                "label": "Poisson’s ratio",
                "output": self.poisson_ratio,
                "si_unit": "",
                "formula_html": f"E = {self.poisson_ratio}",
                "formula_xls": "E",
                "reference": "Section 4.1.2.2"
            },
            {
                "label": "Thermal coefficient",
                "output": self.thermal_coefficient,
                "si_unit": "",
                "formula_html": f"α = {self.thermal_coefficient}",
                "formula_xls": "α",
                "reference": "Section 4.1.2.2"
            },
            {
                "label": "Cross-Sectiontional area of the pipe wall",
                "output": self.cross_sectional_area,
                "si_unit": "m2",
                "formula_html": f"A<sub>W</sub> =  π  x (D<sub>O</sub> - t) x t = <b>{self.cross_sectional_area:.4f} m<sup>2</sup></b>",
                "formula_xls": "A_W = π * (D_O - t) * t",
                "reference": "Section 4.1.2.3"
            },
            {
                "label": "Hoop stress",
                "output": self.hoop_stress,
                "si_unit": "kN/m2",
                "formula_html": f"σ<sub>m</sub> =  (P  x (D<sub>O</sub> - t)) ÷ (2 x t) = <b>{self.hoop_stress:.2f} kN/m<sup>2</sup></b>",
                "formula_xls": "A_W = (P * (D_O - t)) / (2 * t)",
                "reference": "Section 4.1.2.3"
            },
            {
                "label": "Longitudinal stress due to liquid pressure",
                "output": self.liquid_pressure_longitudinal_stress,
                "si_unit": "kN/m2",
                "formula_html": f"σ<sub>P</sub> = ν x σ<sub>M</sub> = <b>{self.liquid_pressure_longitudinal_stress:.2f} kN/m<sup>2</sup></b>",
                "formula_xls": "σ_P = ν * σ_M",
                "reference": "Section 4.1.2.3"
            },
            {
                "label": "Longidudinal force due to liquid pressure",
                "output": self.liquid_pressure_long_longitudinal_force,
                "si_unit": "kN",
                "formula_html": f"F<sub>P</sub> = σ<sub>P</sub> x A<sub>W</sub> = <b>{self.liquid_pressure_long_longitudinal_force:.2f} kN</b>",
                "formula_xls": "F_P = σ * A_W",
                "reference": "Section 4.1.2.3"
            },
            {
                "label": "Longitudinal strain due to temperature",
                "output": self.temperature_longitudinal_strain,
                "si_unit": "",
                "formula_html": f"ε<sub>t</sub> = ΔT x α = <b>{self.temperature_longitudinal_strain}</b>",
                "formula_xls": "ε_t = ΔT * α",
                "reference": "Section 4.1.2.3"
            },
            {
                "label": "Longitudinal stress due to temperature",
                "output": self.temperature_longitudinal_stress,
                "si_unit": "kN/m2",
                "formula_html": f"σ<sub>T</sub> = ε<sub>t</sub> x E = <b>{self.temperature_longitudinal_stress:.2f} kN/m<sup>2</sup></b>",
                "formula_xls": "σ_T = ε_t * E",
                "reference": "Section 4.1.2.3"
            },
            {
                "label": "Longitudinal force due to temperature",
                "output": self.temperature_longitudinal_force,
                "si_unit": "kN",
                "formula_html": f"F<sub>T</sub> = σ<sub>T</sub> x A<sub>W</sub> = <b>{self.temperature_longitudinal_force:.2f} kN</b>",
                "formula_xls": "F_T = σ_T * A_W",
                "reference": "Section 4.1.2.3"
            },
            {
                "label": "Fixed end contraction force",
                "output": self.temperature_longitudinal_force,
                "si_unit": "kN",
                "formula_html": f"F<sub>C</sub> = F<sub>P</sub> x F<sub>T</sub> = <b>{self.temperature_longitudinal_force:.2f} kN</b>",
                "formula_xls": "F_C = F_P * F_T",
                "reference": "Section 4.1.2.3 Step 2"
            },
        ]

    

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

def create_pipe(params) -> WeldedPePipe:
    p = params.pipe_section
    return WeldedPePipe(
    maximum_design_pressure = p.maximum_design_pressure,
    outside_diameter = p.outside_diameter,
    crown_depth = p.crown_depth,
    length = p.length,
    standard_dimension_ratio = p.standard_dimension_ratio,
    poisson_ratio = p.poisson_ratio,
    thermal_coefficient = p.thermal_coefficient,
    temperature_reduction = p.temperature_reduction,
    elastic_modulus = p.elastic_modulus * 1000,
    pipe_material = PipeMaterial.from_value(p.pipe_material),
    allowable_contraction_movement = p.allowable_contraction_movement
    )
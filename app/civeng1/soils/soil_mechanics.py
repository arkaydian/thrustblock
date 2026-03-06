from dataclasses import dataclass
from abc import ABC
from typing import Any, Tuple, List, Dict, Callable, Union, Literal, Optional, TypedDict
import math
from app.civeng1.structures.concrete import ThrustBlock
from app.civeng1.hydraulics.pipes import WeldedPePipe, create_pipe

from .constants import (
    BEARING_CAPACITY_COEFFICIENTS,
    SOIL_EMBEDMENT_PROPERTIES,
    SOIL_PROPERTIES,
    SOIL_UNIT_WEIGHT,
    validate_embedment_property,
)
from .soil_enum import (
    BearingCapacityCoefficients,
    EmbedmentCategory,
    EmbedmentClass,
    SoilCategory,
    SoilConsistency,
    SoilType,
    WaterCondition,
)

UNIT_WEIGHT_WATER = 10  # kN/m³

ReportRow = Tuple[str, str]


class EngRes(TypedDict):
    label: str
    output: Union[float, str]
    si_unit: str
    formula_html: str
    formula_xls: str
    reference: str


def build_eng_res(
    *,
    label: str,
    output: Union[float, str],
    si_unit: str,
    formula_html: str,
    formula_xls: str,
    reference: str,
) -> EngRes:
    return {
        "label": label,
        "output": output,
        "si_unit": si_unit,
        "formula_html": formula_html,
        "formula_xls": formula_xls,
        "reference": reference,
    }

COMPACTION_MAP = {
    "Uncompacted processed gravels": "uncompacted_process_gravels",
    "Compacted sands and gravels (85%)": "compacted_sand_and_gravels_eighty_five",
    "Compacted sands and gravels (90%)": "compacted_sand_and_gravels_ninety",
    "Compacted clays (85%)": "compacted_clays_eighty_five",
    "Compacted clays (90%)": "compacted_clays_ninety",
    "Soft Clay": "soft_clay",
    "Firm or Stiff Clay": "firm_stiff_clay"
}

SectionName = Literal["soil_section", "backfill_section"]

#--- errors ---
class SoilLookupError(Exception):
    """Exception raised for errors in soil property lookup."""
    pass

# --- Enum Lookup Functions ---

def get_soil_type(user_input: str) -> SoilType:
    """Get SoilType enum from string (delegates to SoilType.from_string)."""
    return SoilType.from_string(user_input)

def get_soil_consistency(user_input: str) -> SoilConsistency:
    """Get SoilConsistency enum from string (delegates to SoilConsistency.from_string)."""
    return SoilConsistency.from_string(user_input)

def get_water_condition(condition: str) -> WaterCondition:
    """Get WaterCondition enum from string (delegates to WaterCondition.from_string)."""
    return WaterCondition.from_string(condition)

def get_embedment_key(user_key: str) -> str:
    """Convert user-friendly compaction class string to dictionary key."""
    key = user_key.strip()
    if key not in COMPACTION_MAP:
        raise ValueError(f"Unknown compaction class: {key!r}")
    return COMPACTION_MAP[key]

def interpolate_bearing_coefficients(
    value: float,
    coefficients_dict: Dict[int, BearingCapacityCoefficients] = BEARING_CAPACITY_COEFFICIENTS,
) -> BearingCapacityCoefficients:
    # Sort the keys
    keys = sorted(coefficients_dict.keys())
    
    # If value is outside the range, return closest
    if value <= keys[0]:
        return coefficients_dict[keys[0]]
    if value >= keys[-1]:
        return coefficients_dict[keys[-1]]
    
    # Find the two nearest keys
    for i in range(len(keys) - 1):
        k1, k2 = keys[i], keys[i + 1]
        if k1 <= value <= k2:
            c1, c2 = coefficients_dict[k1], coefficients_dict[k2]
            # Linear interpolation
            def lerp(a, b):
                return a + (b - a) * ((value - k1) / (k2 - k1))
            n_c = lerp(c1.n_c, c2.n_c)
            n_y = lerp(c1.n_y, c2.n_y)
            n_q = lerp(c1.n_q, c2.n_q)
            return BearingCapacityCoefficients(n_c, n_y, n_q)
    # Should not reach here
    raise ValueError("Value not in range")

# --- Abstract Class Definition ---

@dataclass
class Soil(ABC):
    soil_type: SoilType
    soil_consistency: SoilConsistency
    water_condition: WaterCondition
    ground_water_level: float
    soil_passive_factor: float
    soil_sliding_factor: float
    soil_category: SoilCategory
    thrust_block: Optional[ThrustBlock]

    def _validate_thrust_block(self) -> ThrustBlock:
        """Validate that thrust_block exists and return it."""
        if self.thrust_block is None:
            raise ValueError("Thrust block is not defined.")
        return self.thrust_block
    
    def _get_effective_depth(self) -> float:
        """Get effective depth with fallback to actual depth."""
        tb = self._validate_thrust_block()
        return tb.user_effective_depth if tb.user_effective_depth is not None else tb.depth
    
    def _get_effective_height(self) -> float:
        """Get effective height with fallback to actual height."""
        tb = self._validate_thrust_block()
        return tb.user_effective_height if tb.user_effective_height is not None else tb.height
    
    @property
    def effective_unit_weight(self) -> float:
        """Calculate effective unit weight accounting for buoyancy."""
        return self.unit_weight - (self.buoyancy_coefficient * UNIT_WEIGHT_WATER)

    @property
    def unit_weight(self) -> float:
        try:
            return SOIL_UNIT_WEIGHT[self.soil_type][self.soil_consistency][self.water_condition]
        except KeyError as e:
            raise SoilLookupError(
                f"Unit weight not found for soil_type={self.soil_type.label}, "
                f"consistency={self.soil_consistency.label}, "
                f"water_condition={self.water_condition.name}"
            ) from e

    # @property
    # def design_class(self) -> SoilDesignClass:
    #     return classify_soil(self.soil_type, self.soil_consistency)
    
    @property
    def soil_passive_resistance_factor(self) -> Tuple[float, ...]:
        try:
            return SOIL_PROPERTIES[self.soil_category][self.soil_consistency]["soil_passive_resistance_factor"]
        except KeyError as e:
            raise SoilLookupError(
                f"Passive resistance factor not found for soil_type={self.soil_type.label}, "
                f"consistency={self.soil_consistency.label}, "
                f"water_condition={self.water_condition.name}"
            ) from e
        
    @property
    def soil_sliding_resistance_factor(self) -> Tuple[float, ...]:
        try:
            return SOIL_PROPERTIES[self.soil_category][self.soil_consistency]["soil_sliding_resistance_factor"]
        except KeyError as e:
            raise SoilLookupError(
                f"Soil sliding resistance not found for soil_type={self.soil_type.label}, "
                f"consistency={self.soil_consistency.label}, "
                f"water_condition={self.water_condition.name}"
            ) from e
        
    @property    
    def area_passive_face(self) -> float:
        """
        Return the pressure bearing area of the thrust block (m²).
        Raises ValueError if there is no thrust block.
        """
        tb = self._validate_thrust_block()
        return tb.height * tb.width
    
    @property
    def area_base_sliding(self) -> float:
        """
        Returns the sliding area per side of the thrust block (m2)
        """
        tb = self._validate_thrust_block()
        return tb.length * tb.width
    
    @property
    def area_side_sliding(self) -> float:
        """
        Returns the sliding area per side of the thrust block in respective to soil category type
        """
        raise NotImplementedError("Subclass for soil to implement `area_side_sliding`")
        
    @property    
    def buoyancy_coefficient(self) -> float:
        """
        Returns buoyancy coefficient in accordance with Section 3.5
        """
        tb = self._validate_thrust_block()
        return 1 - (self.ground_water_level / tb.depth)
    
    def sliding_resistance_base(self, is_vertical_downturn: bool = False) -> float:
        """
        Calculates Side sliding resistance in accordance with Section 3.7.1
        """
        raise NotImplementedError("Subclass for soil to implement `sliding_resistance_base`")
    
    @property
    def sliding_resistance_side(self) -> float:
        """
        Calculates Side sliding resistance in accordance with Section 3.7.2
        """
        raise NotImplementedError("Subclass for soil to implement `sliding_resistance_side`")
    
    @property
    def net_unit_area_soil_pressure(self) -> float:
        """
        Calculates net unit area soil pressure for the soil block.
        """
        raise NotImplementedError("Subclass to implement `net_unit_area_soil_pressure`")
    
    @property
    def ultimate_vertical_bearing_capacity(self) -> float:
        raise NotImplementedError("Subclass must implement `ultimate_vertical_bearing_capacity`")
    

    @property
    def soil_res(self) -> List[EngRes]:
        raise NotImplementedError("Subclass must implement `soil_res`")

# --- Main Coarse Soil Data Class ---

@dataclass
class CoarseSoil(Soil):
    friction_angle: float

    @property
    def coefficient_passive_earth_pressure(
        self,
    ) -> float:
        """
        Calculates passive earth pressure coefficient in accordance with Section 3.6.1.
        """
        friction_angle = self.friction_angle
        return math.tan(math.radians(45 + (friction_angle / 2))) ** 2 
        
    @property
    def coefficient_active_earth_pressure(
        self,
    ) -> float:
        """
        Calculates active earth pressure coefficient in accordance with Section 3.6.1.
        """

        friction_angle = self.friction_angle
        return math.tan(math.radians(45 - (friction_angle / 2))) ** 2
        
    @property
    def bearing_capacity_coefficients(self) -> BearingCapacityCoefficients:
        return interpolate_bearing_coefficients(self.friction_angle) 
    
    @property
    def area_side_sliding(self) -> float:
        """
        Returns the sliding area per side of the thrust block dependant on soil category.
        """
        tb = self._validate_thrust_block()
        return tb.height * tb.length

    
    def sliding_resistance_base(self, is_vertical_downturn: bool = False) -> float:
        """
        Calculates base sliding resistance in accordance with Section 3.7.1.
        """
        if is_vertical_downturn:
            return 0
        depth = self._get_effective_depth()
        return (self.effective_unit_weight * depth * math.tan(math.radians(self.friction_angle))) / self.soil_sliding_factor 
    
    @property
    def sliding_resistance_side(self) -> float:
        """
        Calculates Sliding Resistance for the soil block sides.
        """
        depth = self._get_effective_depth()
        height = self._get_effective_height()
        return (self.effective_unit_weight * (depth - (height / 2)) * self.coefficient_active_earth_pressure 
                * math.tan(math.radians(self.friction_angle))) / self.soil_sliding_factor
    
    @property
    def net_unit_area_soil_pressure(self) -> float:
        """
        Calculates net unit area soil pressure for the soil block.
        """
        depth_block_base = self._get_effective_depth()
        height = self._get_effective_height()
        return (self.effective_unit_weight * (depth_block_base - (height / 2)) 
                * (self.coefficient_passive_earth_pressure - self.coefficient_active_earth_pressure)) / self.soil_passive_factor
    
    @property
    def ultimate_vertical_bearing_capacity(self) -> float:
        tb = self._validate_thrust_block()
        return (0.5 * self.effective_unit_weight * self.bearing_capacity_coefficients.n_y * min(tb.length, tb.width) 
                + self.effective_unit_weight * (self.bearing_capacity_coefficients.n_q - 1) * tb.depth)
    
    @property
    def soil_res(self) -> List[EngRes]:
        base_sliding = self.sliding_resistance_base()
        side_sliding = self.sliding_resistance_side
        net_pressure = self.net_unit_area_soil_pressure
        passive_area = self.area_passive_face
        base_area = self.area_base_sliding
        side_area = self.area_side_sliding

        return [
            build_eng_res(
                label="Native soil effective angle of shearing resistance",
                output=self.friction_angle,
                si_unit="°",
                formula_html=f"Φ' = {self.friction_angle}°",
                formula_xls="Φ'",
                reference="Table 3.2",
            ),
            build_eng_res(
                label="Passive earth pressure coefficient",
                output=self.coefficient_passive_earth_pressure,
                si_unit="",
                formula_html=f"Kₚ = (tan(45° + Φ′⁄2))² = {self.coefficient_passive_earth_pressure:.2f}",
                formula_xls="K_p = (tan(45 + Φ'/2))^2",
                reference="Section 3.6.1",
            ),
            build_eng_res(
                label="Active earth pressure coefficient",
                output=self.coefficient_active_earth_pressure,
                si_unit="",
                formula_html=f"Kₐ = (tan(45° − Φ′⁄2))² = {self.coefficient_active_earth_pressure:.2f}",
                formula_xls="K_a = (tan(45 - Φ'/2))^2",
                reference="Section 3.6.1",
            ),
            build_eng_res(
                label="Passive resistance displacement limitation factor",
                output=self.soil_passive_factor,
                si_unit="",
                formula_html=f"DFₚ= {self.soil_passive_factor}",
                formula_xls="DF_p",
                reference="Table 3.6",
            ),
            build_eng_res(
                label="Sliding resistance displacement limitation factor",
                output=self.soil_sliding_factor,
                si_unit="",
                formula_html=f"DFₛ = {self.soil_sliding_factor}",
                formula_xls="DF_s",
                reference="Table 3.8",
            ),
            build_eng_res(
                label="Net passive soil pressure",
                output=net_pressure,
                si_unit="kN/m2",
                formula_html=(
                    f"σₚₐ = (γₛ − (C_GW × γ_W)) × (Z_b − H⁄2) × (K_p − K_a) "
                    f"÷ DFₚ = {net_pressure:.2f} kN/m2"
                ),
                formula_xls="σ_pa = (γ_s – (C_GW - γ_W)) x (Z_b – H/2) x (K_p – K_a) ÷ DF_P",
                reference="Section 3.6.1",
            ),
            build_eng_res(
                label="Base sliding resistance",
                output=base_sliding,
                si_unit="kN/m2",
                formula_html=f"τ_b = (γ_s − (C_GW × γ_W)) × Z_b × tan(Φ′) ÷ DF_s = {base_sliding:.2f} kN/m2",
                formula_xls="τ_b = (γ_s – (C_GW - γ_W)) x (Z_b – H/2) x tan(Φ') ÷ DF_s",
                reference="Section 3.7.1",
            ),
            build_eng_res(
                label="Side sliding resistance",
                output=side_sliding,
                si_unit="kN/m2",
                formula_html=(
                    f"τₛ = (γₛ − (C_GW × γ_W)) × (Z_b − H⁄2) × Kₐ × tan(Φ′) "
                    f"÷ DFₛ = {side_sliding:.2f} kN/m2"
                ),
                formula_xls="τ_s = (γ_s – (C_GW - γ_W)) x (Z_b – H/2) x  K_a ÷ DF_s",
                reference="Section 3.7.2",
            ),
            build_eng_res(
                label="Passive face area",
                output=passive_area,
                si_unit="kN/m2",
                formula_html=f"A_f = H × W = {passive_area:.2f} m2",
                formula_xls="A_f = H x W",
                reference=" - ",
            ),
            build_eng_res(
                label="Base sliding area",
                output=base_area,
                si_unit="m2",
                formula_html=f"A_b = L × W = {base_area:.2f} m2",
                formula_xls="A_f = L x W",
                reference=" - ",
            ),
            build_eng_res(
                label="Sliding area per side",
                output=side_area,
                si_unit="m2",
                formula_html=f"Aₛ = L × W = {side_area:.2f} m2",
                formula_xls="A_f = H x L",
                reference=" - ",
            ),
        ]
# --- Main Fine Soil Data Class ---
    
@dataclass
class FineSoil(Soil):
    undrained_shear_strength: float

    # def __post_init__(self):
    #     if self.soil_consistency.category != self.soil_type.category:
    #         raise ValueError(
    #             f"SoilConsistency '{self.soil_consistency.label}' is not valid for soil type '{self.soil_type.label}' ({self.soil_type.category.name.lower()})"
    #         )

    def report_dimensions(self) -> List[ReportRow]: 
        return [
            ("Depth below ground to highest groundwater level", f"Z<sub>GW</sub> = {self.ground_water_level} m"),
            ("Native soil type", f"{self.soil_consistency.label} {self.soil_type.label}"),
            ("Native soil unit weight", f"γ<sub>s</sub> {self.unit_weight} kN/m3,"),
            ("Groundwater unit weight", f"γ<sub>W</sub> {UNIT_WEIGHT_WATER} kN/m3,"),
            ("Undrained shear strength", f"C<sub>u</sub> =  {self.undrained_shear_strength}"),
            ("Passive resistance displacement limitation factor", f"DF<sub>p</sub> = {self.soil_passive_factor}"),
            ("Sliding resistance displacement limitation factor", f"DF<sub>s</sub> {self.soil_sliding_factor}"),
        ]
    @property
    def area_side_sliding(self) -> float:
        """
        Returns 0 for fine category of soil.
        """
        return 0

    def sliding_resistance_base(self, is_vertical_downturn: bool = False) -> float:
        """
        Calculates base sliding resistance in accordance with Section 3.7.1.
        """
        if is_vertical_downturn:
            return 0
        return self.undrained_shear_strength / self.soil_sliding_factor
    
    @property
    def sliding_resistance_side(self) -> float:
        """
        Calculates Sliding Resistance for the soil block sides.
        """
        return 0

    @property
    def net_unit_area_soil_pressure(self) -> float:
        """
        Calculates net unit area soil pressure for the soil block.
        """
        return (2 * self.undrained_shear_strength) / self.soil_passive_factor
    
    @property
    def ultimate_vertical_bearing_capacity(self) -> float:
        """
        Calculates the Vertical block resistance force in accordance with Section 4.1.4
        """
        return (6 * (self.undrained_shear_strength) / self.soil_passive_factor)
    
    @property
    def soil_res(self) -> List[EngRes]:
        base_sliding = self.sliding_resistance_base()
        net_pressure = self.net_unit_area_soil_pressure
        passive_area = self.area_passive_face
        base_area = self.area_base_sliding
        side_area = self.area_side_sliding

        return [
            build_eng_res(
                label="Undrained shear strength",
                output=self.undrained_shear_strength,
                si_unit="Cu",
                formula_html=f"Cᵤ = {self.undrained_shear_strength}",
                formula_xls="C_u' = ",
                reference="Table 3.2",
            ),
            build_eng_res(
                label="Passive resistance displacement limitation factor",
                output=self.soil_passive_factor,
                si_unit="",
                formula_html=f"DFₚ = {self.soil_passive_factor:.2f}",
                formula_xls="DF_p",
                reference="Table 3.6",
            ),
            build_eng_res(
                label="Sliding resistance displacement limitation factor",
                output=self.soil_sliding_factor,
                si_unit="",
                formula_html=f"DFₛ = {self.soil_sliding_factor}",
                formula_xls="DF_s",
                reference="Table 3.8",
            ),
            build_eng_res(
                label="Net passive soil pressure",
                output=net_pressure,
                si_unit="kN/m2",
                formula_html=f"σₚₐ = 2 × Cᵤ ÷ DFₚ = {net_pressure:.2f} kN/m2",
                formula_xls="σ_pa = 2 x C_u ÷ DF_p",
                reference="Section 3.6.1",
            ),
            build_eng_res(
                label="Base sliding resistance",
                output=base_sliding,
                si_unit="kN/m2",
                formula_html=f"τ_b = Cᵤ ÷ DFₚ = {base_sliding:.2f} kN/m2",
                formula_xls="τ_b = (γ_s – (C_GW - γ_W)) x (Z_b – H/2) x tan(Φ') ÷ DF_s",
                reference="Section 3.7.1",
            ),
            build_eng_res(
                label="Passive face area",
                output=passive_area,
                si_unit="kN/m2",
                formula_html=f"A_f = H × W = {passive_area:.2f}",
                formula_xls="A_f = H * W",
                reference="",
            ),
            build_eng_res(
                label="Base sliding area",
                output=base_area,
                si_unit="m2",
                formula_html=f"A_b = L × W = {base_area:.2f}",
                formula_xls="A_f = L * W",
                reference="",
            ),
            build_eng_res(
                label="Sliding area per side",
                output=side_area,
                si_unit="m2",
                formula_html=f"Aₛ = L × W = {side_area:.2f}",
                formula_xls="A_f = H x L",
                reference="",
            ),
        ]

#--- Embedment soils for inline anchor block and pipe restraint calcs ---

@dataclass
class Embedment(ABC):
    ground_water_level: float
    pipe: WeldedPePipe
    backfill_soil: Soil

    @property
    def buoyancy_coefficient(self) -> float:
        return 1 - (self.ground_water_level / (self.pipe.crown_depth + self.pipe.outside_diameter/2))
    
    @property
    def sliding_resistance_force(self) -> float:
        raise NotImplementedError("Subclass must implement `sliding_resistance_force`")
    
    @property
    def embedment_sliding_resistance_factor(self) -> float:
        raise NotImplementedError("Subclass must implement `embedment_sliding_resistance_factor`")
    
    @property
    def long_short_pipe_transition_length(self) -> float:
        return math.sqrt((8 * self.pipe.elastic_modulus * self.pipe.cross_sectional_area * self.pipe.allowable_contraction_movement) / self.sliding_resistance_force)
    
    @property
    def contraction_design_force(self) -> float:
        if self.pipe.length > self.long_short_pipe_transition_length:
            return self.pipe.liquid_pressure_long_longitudinal_force + self.pipe.temperature_longitudinal_force - math.sqrt(2 * self.pipe.elastic_modulus * self.pipe.cross_sectional_area * self.pipe.allowable_contraction_movement * self.sliding_resistance_force)
        if self.long_short_pipe_transition_length > self.pipe.length:
            return self.pipe.liquid_pressure_long_longitudinal_force + self.pipe.temperature_longitudinal_force - ((2 * self.pipe.elastic_modulus * self.pipe.allowable_contraction_movement) / self.pipe.length) - ((self.pipe.length * self.sliding_resistance_force) / 4)
        raise ValueError("Pipe length or long short pipeline transition length not calculated")
    
    @property
    def render_workflow_report(self) -> list[EngRes]:
        raise NotImplementedError("Subclass to implement `render_workflow_report`")

@dataclass
class CoarseEmbedment(Embedment):
    compaction_class: Literal["Uncompacted processed gravels", "Compacted sands and gravels (85%)", "Compacted sands and gravels (90%)"]
    embedment_class: EmbedmentClass
    embedment_category: EmbedmentCategory = EmbedmentCategory.COARSE
    
    @property
    def get_category_compactness(self) -> str:
        return get_embedment_key(self.compaction_class)

    @property
    def friction_reduction_factor(self) -> float:
        return SOIL_EMBEDMENT_PROPERTIES[self.embedment_category][self.embedment_class]["friction_angle_reduction"]

    @property
    def effective_angle_shearing_resistance(self) -> float:
        return float(validate_embedment_property(
            self.embedment_category,
            self.embedment_class,
            self.get_category_compactness,
            "effective_angle_shearing_resistance",
        ))
    
    @property
    def embedment_sliding_resistance_factor(self) -> float:
        return float(validate_embedment_property(
            self.embedment_category,
            self.embedment_class,
            self.get_category_compactness,
            "embedment_sliding_resistance_factor",
        ))
    
    @property
    def sliding_resistance_force(self) -> float:
        return (self.pipe.pipe_material_factor * 2 * self.pipe.outside_diameter 
                * (self.backfill_soil.unit_weight - (self.buoyancy_coefficient * UNIT_WEIGHT_WATER)) 
                * (self.pipe.crown_depth + 0.3 * self.pipe.outside_diameter) 
                * math.tan(math.radians(self.friction_reduction_factor * self.effective_angle_shearing_resistance)) 
                / self.embedment_sliding_resistance_factor)
    
    @property
    def embedment_class_report(self) -> str:
        return f"{self.embedment_category.label_capitalized} Class {self.embedment_class.label_capitalized} pipe embedment"
    
    @property
    def render_workflow_report(self) -> List[EngRes]:
        sliding_force = self.sliding_resistance_force
        transition_length = self.long_short_pipe_transition_length
        contraction_force = self.contraction_design_force

        return [
            build_eng_res(
                label="Embedment class",
                output=self.embedment_class_report,
                si_unit="",
                formula_html=f"{self.embedment_class_report}",
                formula_xls="",
                reference=" - ",
            ),
            build_eng_res(
                label="Compaction level",
                output=self.compaction_class,
                si_unit="",
                formula_html=f"{self.compaction_class}",
                formula_xls="",
                reference="Table 3.3",
            ),
            build_eng_res(
                label="Embedment effective angle of shearing resistance",
                output=self.effective_angle_shearing_resistance,
                si_unit="°",
                formula_html=f"ϕ′ₑ = {self.effective_angle_shearing_resistance}°",
                formula_xls="ϕ'_sub",
                reference="Table 3.3",
            ),
            build_eng_res(
                label="Embedment friction reduction factor",
                output=self.friction_reduction_factor,
                si_unit="°",
                formula_html=f"f_ϕ′ₑ = {self.friction_reduction_factor}°",
                formula_xls="F_ϕ'",
                reference="Table 3.3",
            ),
            build_eng_res(
                label="Backfill unit weight",
                output=self.backfill_soil.unit_weight,
                si_unit="kN/m3",
                formula_html=f"γ_S = {self.backfill_soil.unit_weight} kN/m3",
                formula_xls="γ_S",
                reference="Table 3.5",
            ),
            build_eng_res(
                label="Pipe material factor",
                output=self.pipe.pipe_material_factor,
                si_unit="",
                formula_html=f"ϕₘ = {self.pipe.pipe_material_factor}",
                formula_xls="ϕ_m",
                reference="Section 3.2.3",
            ),
            build_eng_res(
                label="Displacement limitation factor – embedment sliding resistance",
                output=self.embedment_sliding_resistance_factor,
                si_unit="",
                formula_html=f"DF_F = {self.embedment_sliding_resistance_factor}",
                formula_xls="DF_F",
                reference="Table 3.9",
            ),
            build_eng_res(
                label="Depth below ground to highest groundwater level",
                output=self.ground_water_level,
                si_unit="m",
                formula_html=f"Z_GW = {self.ground_water_level}",
                formula_xls="Z_GW",
                reference="Table 3.9",
            ),
            build_eng_res(
                label="Groundwater unit weight",
                output=UNIT_WEIGHT_WATER,
                si_unit="kN/m2",
                formula_html=f"γ_W = {UNIT_WEIGHT_WATER} kN/m<sup>2</sup>",
                formula_xls="γ_W",
                reference="Table 3.5",
            ),
            build_eng_res(
                label="Buoyancy coefficient for pipe embedment",
                output=self.buoyancy_coefficient,
                si_unit="",
                formula_html=f"C_GW = 1 − (Z_GW ÷ (Z_O + D_O⁄2)) = {self.buoyancy_coefficient:.2f}",
                formula_xls="C_GW",
                reference="Section 3.5",
            ),
            build_eng_res(
                label="Embedment friction resistance force",
                output=sliding_force,
                si_unit="kN/m",
                formula_html=(
                    f"F_F = ϕₘ × 2 × Dₒ × (Yₛ − (C_GW × Y_w)) × (Z₀ + 0.3 × Dₒ) "
                    f"× tan(f_ϕ′e × ϕ′_e) ÷ DF_F = {sliding_force:.2f} kN/m"
                ),
                formula_xls="Ff = Qm * 2 * Do * (Ys - (CGW * Yw)) * (Z0 + 0.3 * Do) * tan(fue * φ′) / DFF",
                reference="Section 3.7.3",
            ),
            build_eng_res(
                label="Embedment sliding resistance force",
                output=sliding_force,
                si_unit="kN/m",
                formula_html=f"F_S = F_F  = {sliding_force:.2f} kN/m ",
                formula_xls="F_S = F_F",
                reference="Section 4.1.2.3 Step 4",
            ),
            build_eng_res(
                label="Long/short PE pipeline transition length",
                output=transition_length,
                si_unit="kN/m",
                formula_html=f"Lₛ = √(8 × E × A_w × ΔL_M / Fₛ) = {transition_length:.2f} m</p>",
                formula_xls="L_S = sqrt(8 * E * A_W * ΔL_M / F_S) ",
                reference="Section 4.1.2.3 Step 4",
            ),
            build_eng_res(
                label="Pipeline contraction design force",
                output=contraction_force,
                si_unit="kN",
                formula_html=(
                    f"F_A = F_p + F_T − √(2 × E × A_w × ΔL_M / L_s) = {contraction_force:.2f} kN"
                    if transition_length < self.pipe.length
                    else f"F_AS = F_p + F_T − (2 × E × A_w × ΔL_M × L_o / L_s) − (L_o × F_s ÷ 4) {contraction_force:.2f} kN</p>"
                ),
                formula_xls="F_S",
                reference=(
                    "Section 4.1.2.3 Step 5a"
                    if transition_length < self.pipe.length
                    else "Section 4.1.2.3 Step 5b"
                ),
            ),
            build_eng_res(
                label="Pipeline contraction design force",
                output=contraction_force,
                si_unit="kN/m",
                formula_html=f"F_D = {contraction_force:.2f} kN",
                formula_xls="F_D",
                reference="Section 4.1.2.3 Step",
            ),
        ]

@dataclass
class FineEmbedment(Embedment):
    adhesion: Literal["Soft Clay", "Firm or Stiff Clay"]
    compaction_class: Literal["Compacted clays (85%)", "Compacted clays (90%)"]
    embedment_category: EmbedmentCategory = EmbedmentCategory.CLAY
    embedment_class: EmbedmentClass = EmbedmentClass.S_FIVE
    
    @property
    def get_category_compactness(self) -> str:
        return get_embedment_key(self.compaction_class)
        
    @property
    def representative_adhesion(self) -> float:
        adhesion_key = get_embedment_key(self.adhesion)
        return float(SOIL_EMBEDMENT_PROPERTIES[self.embedment_category][self.embedment_class]["representative_adhesion"][adhesion_key])

    @property
    def adhesion_reduction_factor(self) -> float:
        return float(validate_embedment_property(
            self.embedment_category,
            self.embedment_class,
            self.get_category_compactness,
            "adhesion_reduction_factor",
        ))
    
    @property
    def embedment_sliding_resistance_factor(self) -> float:
        return float(validate_embedment_property(
            self.embedment_category,
            self.embedment_class,
            self.get_category_compactness,
            "embedment_sliding_resistance_factor",
        ))
    
    @property
    def sliding_resistance_force(self) -> float:
        return self.pipe.pipe_material_factor \
        * self.representative_adhesion * math.pi * self.pipe.outside_diameter \
        / self.embedment_sliding_resistance_factor
    
    @property
    def embedment_class_report(self) -> str:
        return f"{self.embedment_category.label_capitalized} Class {self.embedment_class.label_capitalized} pipe embedment"
    
# --- Registry-based factory ---

SoilBuilder = Callable[..., Soil]
SOIL_REGISTRY: Dict[SoilType, SoilBuilder] = {}

def build_thrust_block_from_params(params: Any) -> ThrustBlock:
    tb = params.block_section
    return ThrustBlock(
        height=tb.height,
        width=tb.width,
        length=tb.length,
        depth=tb.depth,
        user_effective_depth=None,
        user_effective_height=None
    )

def register_soil(*soil_types: SoilType):
    """Decorator to register a Soil class or builder for given soil types."""
    def decorator(builder: SoilBuilder):
        for st in soil_types:
            SOIL_REGISTRY[st] = builder
        return builder
    return decorator

@register_soil(SoilType.GRAVEL, SoilType.SAND)
def build_coarse_soil(
    *,
    soil_type: SoilType,
    soil_consistency: SoilConsistency,
    water_condition: WaterCondition,
    ground_water_level: float,
    soil_passive_factor: float,
    soil_sliding_factor: float,
    thrust_block: Optional[ThrustBlock],
    friction_angle: float
) -> Soil:
    return CoarseSoil(
        soil_type=soil_type,
        soil_consistency=soil_consistency,
        water_condition=water_condition,
        ground_water_level=ground_water_level,
        soil_passive_factor=soil_passive_factor,
        soil_sliding_factor=soil_sliding_factor,
        soil_category=SoilCategory.COARSE,
        thrust_block=thrust_block,
        friction_angle=friction_angle,
    )

@register_soil(SoilType.CLAY)
def build_fine_soil(
    *,
    soil_type: SoilType,
    soil_consistency: SoilConsistency,
    water_condition: WaterCondition,
    ground_water_level: float,
    soil_passive_factor: float,
    soil_sliding_factor: float,
    thrust_block: Optional[ThrustBlock],
    undrained_shear_strength: float,
) -> Soil:
    return FineSoil(
        soil_type=soil_type,
        soil_consistency=soil_consistency,
        water_condition=water_condition,
        ground_water_level=ground_water_level,
        soil_passive_factor=soil_passive_factor,
        soil_sliding_factor=soil_sliding_factor,
        soil_category=SoilCategory.FINE,
        thrust_block=thrust_block,
        undrained_shear_strength=undrained_shear_strength,
    )

def create_soil(params: Any, section_name: SectionName = "soil_section") -> Soil:

    s = getattr(params, section_name, None)
    if s is None:
        raise ValueError(f"{section_name!r} not found on params")
    
    soil_type = get_soil_type(s.soil_type)
    water_condition = get_water_condition(s.ground_condition)

    try:
        builder = SOIL_REGISTRY[soil_type]
    except KeyError as e:
        raise ValueError(f"No registered builder for soil type: {soil_type.label}") from e

    # Common parameters for all soil types
    common_params = dict(
        soil_type=soil_type,
        water_condition=water_condition,
        ground_water_level=s.groundwater_level,
        soil_passive_factor=s.soil_passive_factor,
        soil_sliding_factor=s.soil_sliding_factor,
        thrust_block=build_thrust_block_from_params(params)
    )

    # Dispatch based on which builder is selected
    if builder is build_coarse_soil:
        if s.friction_angle is None:
            raise ValueError("friction_angle is required for coarse soils (gravel/sand).")
        soil_consistency = get_soil_consistency(s.coarse_soil_consistency)
        return builder(**common_params, soil_consistency=soil_consistency, friction_angle=s.friction_angle)

    if builder is build_fine_soil:
        if s.undrained_shear_strength is None:
            raise ValueError("undrained_shear_strength is required for fine soils (silt/clay).")
        soil_consistency = get_soil_consistency(s.fine_soil_consistency)
        return builder(**common_params, soil_consistency=soil_consistency, undrained_shear_strength=s.undrained_shear_strength)

    # Fallback for any other registered builders
    raise ValueError(f"Unknown soil type: {soil_type.label}")

EmbedmentBuilder = Callable[..., Embedment]
EMBEDMENT_REGISTRY: Dict[EmbedmentClass, EmbedmentBuilder] = {}

def register_embedment(*embedment_class: EmbedmentClass):
    def decorator(builder: EmbedmentBuilder):
        for ec in embedment_class:
            EMBEDMENT_REGISTRY[ec] = builder
        return builder
    return decorator

@register_embedment(EmbedmentClass.S_ONE)
def build_s_one_embedment(
    *,    
    ground_water_level: float,
    pipe: WeldedPePipe,
    backfill_soil: Soil,
    compaction_class: str,
    embedment_class: EmbedmentClass,
    ) -> Embedment:

   return CoarseEmbedment(
        ground_water_level = ground_water_level,
        pipe = pipe,
        backfill_soil = backfill_soil,
        compaction_class = "Uncompacted processed gravels",
        embedment_class = embedment_class,
    )


@register_embedment(EmbedmentClass.S_TWO, EmbedmentClass.S_THREE, EmbedmentClass.S_FOUR)
def build_coarse_embedment(
    *,    
    ground_water_level: float,
    pipe: WeldedPePipe,
    backfill_soil: Soil,
    compaction_class: Literal["Compacted sands and gravels (85%)", "Compacted sands and gravels (90%)"],
    embedment_class: EmbedmentClass,
    ) -> Embedment:

   return CoarseEmbedment(
        ground_water_level = ground_water_level,
        pipe = pipe,
        backfill_soil = backfill_soil,
        compaction_class = compaction_class,
        embedment_class = embedment_class,
    )

@register_embedment(EmbedmentClass.S_FIVE)
def build_fine_embedment(
    *,    
    ground_water_level: float,
    pipe: WeldedPePipe,
    backfill_soil: Soil,
    adhesion: Literal["Soft Clay", "Firm or Stiff Clay"],
    compaction_class: Literal["Compacted clays (85%)", "Compacted clays (90%)"],
    embedment_class: EmbedmentClass
) -> Embedment:

   return FineEmbedment(
        ground_water_level = ground_water_level,
        pipe = pipe,
        backfill_soil = backfill_soil,
        adhesion=adhesion,
        compaction_class=compaction_class,
        embedment_class=embedment_class
        )

def create_embedment(params: Any) -> Embedment:
    e = params.embedment_section
    ground_water_level = e.ground_water_level
    pipe = create_pipe(params)
    backfill_soil = create_soil(params=params, section_name="backfill_section")
    embedment_class = EmbedmentClass.from_frontend(e.embedment_class)
    try:
        builder = EMBEDMENT_REGISTRY[embedment_class]
    except KeyError as ke:
        raise ValueError(f"No registered builder for embedment type: {embedment_class}") from ke

    common_embedment = dict(
        ground_water_level = ground_water_level,
        pipe = pipe,
        backfill_soil = backfill_soil,
        embedment_class = embedment_class
    )
    s_one_compaction_class = e.s_one_compaction_class
    coarse_compaction_class = e.coarse_compaction_class
    fine_compaction_class = e.fine_compaction_class
    adhesion = e.adhesion

    if builder is build_s_one_embedment:
        return builder(**common_embedment, compaction_class=s_one_compaction_class)

    if builder is build_coarse_embedment:
        return builder(**common_embedment, compaction_class=coarse_compaction_class)

    if builder is build_fine_embedment:
        return builder(**common_embedment, adhesion=adhesion, compaction_class=fine_compaction_class)
   
    raise ValueError(f"Unknown embedment type: {embedment_class}")

# --- Example usage ---
def main():
    ...
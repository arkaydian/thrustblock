import math
from dataclasses import dataclass
from abc import ABC
from typing import Dict, Any, Callable, Tuple, List, Union
from app.civeng1.soils.soil_mechanics import Soil, create_soil, UNIT_WEIGHT_WATER, CoarseSoil, FineSoil, CoarseEmbedment, FineEmbedment, Embedment, create_embedment, EngRes as SoilEngRes
from app.civeng1.reporting.engres import EngRes as ReportingEngRes
from app.civeng1.hydraulics.pipes import WeldedPePipe
from app.civeng1.hydraulics.fittings import (
    fitting_list,
    FITTING_LABELS,
    HorizontalBend,
    VerticalUpturnBend,
    VerticalDownturnBend,
    Tee,
    AngleBranch,
    ClosedValve,
    LineStop,
    BlankEnd,
    TaperThrust,
    FlangedMetallicPipe,
)

#--- Utils and Types ---

ReportRow = Tuple[Any]
ThrustForce = Tuple[str, float]
EngRes = Union[ReportingEngRes, SoilEngRes]


def _eng_res(
    *,
    label: str,
    output: Any,
    si_unit: str,
    formula_html: str,
    formula_xls: str,
    reference: str,
) -> EngRes:
    """Build a report row dict with a single stable shape."""
    return {
        "label": label,
        "output": output,
        "si_unit": si_unit,
        "formula_html": formula_html,
        "formula_xls": formula_xls,
        "reference": reference,
    }

# --- Abstract Base Classes ---
@dataclass(frozen=True)
class FittingCalculation(ABC):
    """Shared calculation model for thrust-block checks."""

    maximum_design_pressure: float
    crown_depth: float
    soil_type: Soil

    @property
    def depth(self) -> float:
        raise NotImplementedError("Subclass must implement this `thrust_force_resultant`")

    @property
    def thrust_force_resultant(self) -> float:
        raise NotImplementedError("Subclass must implement this `thrust_force_resultant`")

    @property
    def area_disturbed_passive(self) -> float:
        raise NotImplementedError("Subclass must implement this `area_disturbed_passive`")

    @property
    def overturning_level_arm(self) -> float:
        raise NotImplementedError("Subclass must implement this `overturning_level_arm`")

    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        raise NotImplementedError("Subclass must implement this `fitting_workflow_res`")

    def __getattr__(self, name: str):
        # Delegate geometric attributes to wrapped component objects.
        component = self.__dict__.get("component")
        if component is not None:
            return getattr(component, name)
        raise AttributeError(name)

    @staticmethod
    def _binary_check_formula(lhs: float, rhs: float, passed: bool) -> str:
        return f"{lhs:.2f} kN > {rhs:.2f} kN, Pass" if passed else f"{lhs:.2f} kN > {rhs:.2f} kN, Fail"

    def _pass_fail_check_row(
        self,
        *,
        label: str,
        lhs: float,
        rhs: float,
        passed: bool,
        reference: str,
        output: Any,
        si_unit: str = "",
    ) -> EngRes:
        formula = self._binary_check_formula(lhs=lhs, rhs=rhs, passed=passed)
        return _eng_res(
            label=label,
            output=output,
            si_unit=si_unit,
            formula_html=formula,
            formula_xls=formula,
            reference=reference,
        )

    @property
    def block_resistance(self) -> float:
        return self.soil_type.net_unit_area_soil_pressure * (self.soil_type.area_passive_face - self.area_disturbed_passive) \
            + (self.soil_type.sliding_resistance_base() * self.soil_type.area_base_sliding) \
            + (2 * self.soil_type.sliding_resistance_side() * self.soil_type.area_side_sliding)

    @property
    def passive_face_restoring_moment(self) -> float:
        if self.soil_type.thrust_block is None:
                raise ValueError("Thrust Block not implemented")
        return self.soil_type.net_unit_area_soil_pressure * self.soil_type.thrust_block.width * ((self.soil_type.thrust_block.height ** 2 )/ 3)

    @property
    def over_turning_moment(self) -> float:
        return self.thrust_force_resultant * self.overturning_level_arm

    @property
    def net_disturbing_moment(self) -> float:
        return self.over_turning_moment - self.passive_face_restoring_moment

    @property
    def vertical_reaction_block(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return (self.soil_type.unit_weight - (self.soil_type.buoyancy_coefficient * UNIT_WEIGHT_WATER)) * \
            self.depth* self.soil_type.thrust_block.width * self.soil_type.thrust_block.length

    @property
    def block_restoring_moment(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.vertical_reaction_block * (self.soil_type.thrust_block.length / 2)

    @property
    def safety_factor_against_overturning(self) -> float:
        return self.block_restoring_moment / self.net_disturbing_moment

    @property
    def thrust_pass_through_check(self) -> bool:
        if self.block_resistance > self.thrust_force_resultant:
            return True
        return False

    @property
    def overturning_check(self) -> bool:
        if self.safety_factor_against_overturning > 1.5:
            return True
        return False

    @property
    def thrust_block_standard_workflow(self) -> List[EngRes]:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return [
            _eng_res(
                label="Depth below ground to highest groundwater level",
                output=self.soil_type.ground_water_level,
                si_unit="m",
                formula_html=f"Z_GW = {self.soil_type.ground_water_level} m",
                formula_xls="Z_GW",
                reference=" - ",
            ),
            _eng_res(
                label="Depth to crown of larger pipe",
                output=self.crown_depth,
                si_unit="m",
                formula_html=f"Z_O = {self.crown_depth} m",
                formula_xls="Z_O",
                reference=" - ",
            ),
            _eng_res(
                label="Depth to base of block",
                output=self.soil_type.thrust_block.depth,
                si_unit="m",
                formula_html=f"Z_b = {self.soil_type.thrust_block.depth} m",
                formula_xls="Z_b",
                reference=" - ",
            ),
            _eng_res(
                label="Buoyancy coefficient",
                output=self.soil_type.buoyancy_coefficient,
                si_unit="",
                formula_html=f"C_GW = 1 − (Z_GW ÷ Z_b) = {self.soil_type.buoyancy_coefficient:.2f}",
                formula_xls="Z_O",
                reference="Section 3.5",
            ),
            _eng_res(
                label="Native soil type",
                output=f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                si_unit="",
                formula_html=f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                formula_xls=f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                reference=" - ",
            ),
            _eng_res(
                label="Native soil unit weight",
                output=self.soil_type.unit_weight,
                si_unit="kN/m3",
                formula_html=f"γₛ = {self.soil_type.unit_weight} kN/m3",
                formula_xls="γ_s",
                reference="Table 3.5",
            ),
            _eng_res(
                label="Groundwater unit weight",
                output=UNIT_WEIGHT_WATER,
                si_unit="kN/m3",
                formula_html=f"γ<sub>W</sub> = {UNIT_WEIGHT_WATER} kN/m3",
                formula_xls="γ_W",
                reference="Table 3.5",
            ),
        ]

    @property
    def thrust_block_over_turning_stability_check_workflow(self) -> List[EngRes]:
        return [
            _eng_res(
                label="Overturning moment lever arm",
                output=self.overturning_level_arm,
                si_unit="m",
                formula_html=f"H_c = Z_b − (Z_O + D_O⁄2) = {self.overturning_level_arm:.2f} m",
                formula_xls="H_c = Z_b - (Z_O + D_O/2)",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Overturning moment",
                output=self.over_turning_moment,
                si_unit="kNm",
                formula_html=f"M_O = T × H_c = {self.over_turning_moment:.2f} kNm",
                formula_xls="M_O = T x H_c",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Passive face restoring moment",
                output=self.passive_face_restoring_moment,
                si_unit="kNm",
                formula_html=f"M_p = σ_pa × W × H²⁄3 = {self.passive_face_restoring_moment:.2f} kNm",
                formula_xls="M_p = σ_pa * W * (H^2)/3",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Net disturbing moment",
                output=self.net_disturbing_moment,
                si_unit="kNm",
                formula_html=f"M_d = M_o − M_p = {self.net_disturbing_moment:.2f} kNm",
                formula_xls="M_d = M_o - M_P",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Vertical reaction of block",
                output=self.vertical_reaction_block,
                si_unit="kN",
                formula_html=f"R_v = (γ_s − (C_GW × γ_W)) × Z_b × W × L = {self.vertical_reaction_block:.2f} kN",
                formula_xls="R_v = (γ_s - (C_GW * γ_w)) * Z_b * H * L",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Concrete block restoring moment",
                output=f"{self.block_restoring_moment}",
                si_unit="kNm",
                formula_html=f"M_R = R_v × L⁄2 = {self.block_restoring_moment:.2f} kNm",
                formula_xls="M_R = R_v * L/2",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Safety factor against overturning",
                output=self.safety_factor_against_overturning,
                si_unit="m",
                formula_html=f"SF_O = M_R ÷ M_d = {self.safety_factor_against_overturning:.2f}",
                formula_xls="SF_O = M_R / M_d",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Overturning stability check",
                output=self.overturning_check,
                si_unit=" - ",
                formula_html=f"{self.safety_factor_against_overturning:.2f} > 1.5, Pass" if self.overturning_check else f"1.5 > {self.safety_factor_against_overturning:.2f}, Fail",
                formula_xls="Pass overturning stability" if self.overturning_check else "Fail overturning stability",
                reference=" - ",
            ),
        ]
    
    @property
    def safety_report(self):
        return [
            {
                "title": "Thrust Pass Through Check",
                "shot_title": "Block Resistance R_s",
                "shot": self.block_resistance,
                "goal_title": "Thrust Force (T)",
                "goal": self.thrust_force_resultant,
                "unit": "kN"
            },
            {
                "title": "Overturning Stability Check",
                "shot_title": "Safety Factor against Overturning",
                "shot": self.safety_factor_against_overturning,
                "goal_title": "Safety Factor",
                "goal": 1.5,
                "unit": ""
            },
        ]

# --- Fitting Dataclasses ---

@dataclass(frozen=True)
class HorizontalBendThrustBlock(FittingCalculation):
    """Thrust-block calculation model for horizontal bends."""

    component: HorizontalBend

    @property
    def thrust_force_resultant(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return 2 * self.maximum_design_pressure * area * math.sin(math.radians(self.angle) / 2)

    @property
    def thrust_force_x_component(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area * (1 - math.cos(math.radians(self.angle)))

    @property
    def thrust_force_y_component(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area * math.sin(math.radians(self.angle))
    
    @property
    def area_disturbed_passive(self) -> float:
        return 0
    
    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth
            
    
    @property
    def overturning_level_arm(self) -> float:
        """
        Calculates the overturning lever arm for the thrust block based on fitting geometry.
        Returns 0 if no matching diameter attribute is found.
        """
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.soil_type.thrust_block.depth - (self.crown_depth + self.outside_diameter / 2)
    
    @property
    def thrust_pass_through_check_report(self) -> List[EngRes]:
        return [
            _eng_res(
                label="Block resistance force",
                output=self.block_resistance,
                si_unit="kN",
                formula_html=f"R_S = {self.block_resistance}",
                formula_xls="R_S",
                reference=""
            ),
            _eng_res(
                label="Resultant thrust force",
                output=self.thrust_force_resultant,
                si_unit="kN",
                formula_html=f"T = {self.thrust_force_resultant}",
                formula_xls="T",
                reference=""
            ),
            _eng_res(
                label="check",
                output=self.thrust_pass_through_check,
                si_unit="kN",
                formula_html=str(self.thrust_pass_through_check),
                formula_xls="",
                reference=""
            ),
        ]
    
    @property
    def overturning_check_report(self) -> List[EngRes]:
        return [
            _eng_res(
                label="Safety Factor against overturning",
                output=self.block_resistance,
                si_unit="kN",
                formula_html=f"R_S = {self.block_resistance}",
                formula_xls="R_S",
                reference=""
            ),
            _eng_res(
                label="check",
                output=self.overturning_check,
                si_unit="kN",
                formula_html=str(self.overturning_check),
                formula_xls="T",
                reference=""
            ),
        ]
    
    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Pipe outside diameter",
                output=self.outside_diameter,
                si_unit="m",
                formula_html=f"D_O = {self.outside_diameter}",
                formula_xls="D_O",
                reference=""
            ),
            _eng_res(
                label="Bend Angle",
                output=self.angle,
                si_unit="°",
                formula_html=f"θ = {self.angle}°",
                formula_xls="θ",
                reference=""
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Block resistance force",
                output=self.block_resistance,
                si_unit="m",
                formula_html=f"R_s = (σ_pa × A_f) + (𝜏_b × A_b) = {self.block_resistance:.2f} kN",
                formula_xls="R_s",
                reference="Section 4.1.3"
            ),
            _eng_res(
                label="Thrust force",
                output=self.thrust_force_resultant,
                si_unit="m",
                formula_html=f"T = 2 × P × π⁄4 × (D_O)² × sin(θ⁄2) = {self.thrust_force_resultant:.2f} kN",
                formula_xls="T = 2 x P x π/4 x (D_O)2 x sin(θ/2)",
                reference="Figure 2.3"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.thrust_force_resultant,
                passed=self.thrust_pass_through_check,
                reference="",
                output=self.thrust_pass_through_check,
            )
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow

@dataclass(frozen=True)
class VerticalUpturnBendThrustBlock(FittingCalculation):
    """Thrust-block calculation model for vertical upturn bends."""

    component: VerticalUpturnBend

    @property
    def thrust_force_resultant(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return 2 * self.maximum_design_pressure * area * math.sin(math.radians(self.angle) / 2)

    @property
    def thrust_force_horizontal(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area * (1 - math.cos(math.radians(self.angle)))

    @property
    def thrust_force_vertical(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area * math.sin(math.radians(self.angle))
    
    @property
    def area_disturbed_passive(self) -> float:
        return 0
    
    @property
    def vertical_block_resistance_force(self) -> float:
        return self.soil_type.ultimate_vertical_bearing_capacity * self.soil_type.area_base_sliding
    
    @property
    def vertical_bend_check(self):
        return f"{self.vertical_block_resistance_force:.2f} kN > {self.thrust_force_vertical:.2f} kN Pass vertical ground bearing resistance" if self.vertical_block_resistance_force > self.thrust_force_vertical \
                else f"{self.vertical_block_resistance_force} kN < {self.thrust_force_vertical:.2f} kN Fail vertical ground bearing resistance"
    
    @property
    def vertical_force_check(self) -> bool:
        if self.vertical_block_resistance_force > self.thrust_force_vertical:
            return True
        return False
    
    @property
    def thrust_pass_through_check(self) -> bool:
        if self.block_resistance > self.thrust_force_horizontal:
            return True
        return False
    
    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth

    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Pipe outside diameter",
                output=self.outside_diameter,
                si_unit="m",
                formula_html=f"D_O = {self.outside_diameter} m",
                formula_xls="D_O",
                reference=""
            ),
            _eng_res(
                label="Bend Angle",
                output=self.angle,
                si_unit="°",
                formula_html=f"θ = {self.angle}°",
                formula_xls="θ",
                reference=""
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Horizontal block resistance force",
                output=self.block_resistance,
                si_unit="kN",
                formula_html=f"R_s = (σ_pa × A_f) + (𝜏_b × A_b) = {self.block_resistance:.2f} kN",
                formula_xls="R_s = (σ_pa * A_f) + (𝜏_b * A_b)",
                reference="Section 4.1.3"
            ),
            _eng_res(
                label="Thrust force (horizontal component)",
                output=self.thrust_force_horizontal,
                si_unit="kN",
                formula_html=f"T_x = P × π⁄4 × (D_O)² × (1 − cos(θ)) = {self.thrust_force_horizontal:.2f} kN",
                formula_xls="T_x = P * π/4 * D_O^2 * (1 - cos(θ))",
                reference="Figure 2.3"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.thrust_force_horizontal,
                passed=self.thrust_pass_through_check,
                reference="",
                output=self.thrust_pass_through_check,
            )
        ]
        
        vertical_ground_bearing_formula_html = "q_b = [0.5 × (γ_s − (C_GW × γ_w)) × B × N_γ] + [(γ_s − (C_GW × γ_w)) × (N_q − 1) × Z_b] ÷ DF_P"\
        if isinstance(self.soil_type, CoarseSoil) else "q_b = (6 × C_U) ÷ DF_P"
        vertical_ground_bearing_formula_xls = "q_b = (0.5 * (γ_s - (C_GW * γ_W)) * B * N_γ) + ((γ_S - (C_GW * γ_w) *(N_q - 1)* Z_b) ÷ DF_p" if isinstance(self.soil_type, CoarseSoil) \
        else "q_b = (6 * CU)  ÷ DF_p" 

        bearing_coefficients: list[EngRes] = [
            _eng_res(
                label="Bearing capacity coefficient, Nq",
                output=self.soil_type.bearing_capacity_coefficients.n_q,
                si_unit="",
                formula_html=f"N_q =  {self.soil_type.bearing_capacity_coefficients.n_q}",
                formula_xls="N_q",
                reference="Table 3.10"
            ),
            _eng_res(
                label="Bearing capacity coefficient, Nc",
                output=self.soil_type.bearing_capacity_coefficients.n_c,
                si_unit="",
                formula_html=f"N_c =  {self.soil_type.bearing_capacity_coefficients.n_c}",
                formula_xls="N_c",
                reference="Table 3.10"
            ),
            _eng_res(
                label="Bearing capacity coefficient, Nγ",
                output=self.soil_type.bearing_capacity_coefficients.n_y,
                si_unit="",
                formula_html=f"N_γ =  {self.soil_type.bearing_capacity_coefficients.n_y}",
                formula_xls="N_γ",
                reference="Table 3.10"
            )
            ] if isinstance(self.soil_type, CoarseSoil) else [] 
        
        vertical_resistance_workflow: List[EngRes] = [
            _eng_res(
                label="Thrust force (vertical component)",
                output=self.thrust_force_vertical,
                si_unit="kN",
                formula_html=f"T_z = 2 × P × π⁄4 × (D_O)² × sin(θ⁄2) = {self.thrust_force_vertical:.2f} kN",
                formula_xls="T = 2 * P * π/4 * (D_O)2 * sin(θ/2)",
                reference="Figure 2.3"
            ),
            _eng_res(
                label="Ultimate ground bearing resistance",
                output=self.soil_type.ultimate_vertical_bearing_capacity,
                si_unit="kN/m2",
                formula_html=f"{vertical_ground_bearing_formula_html} = {self.soil_type.ultimate_vertical_bearing_capacity:.2f} kN/m2",
                formula_xls=vertical_ground_bearing_formula_xls,
                reference="Section 3.8.1"
            ),
            _eng_res(
                label="Vertical block resistance force",
                output=self.vertical_block_resistance_force,
                si_unit="kN",
                formula_html=f"Q_b = q_b × A_b = {self.vertical_block_resistance_force:.2f} kN",
                formula_xls="Q_b = q_b * A_b",
                reference="Section 4.1.4"
            ),
            _eng_res(
                label="vertical ground bearing resistance check",
                output=self.vertical_bend_check,
                si_unit="",
                formula_html=self.vertical_bend_check,
                formula_xls=self.vertical_bend_check,
                reference=""
            )
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + bearing_coefficients + thrust_pass_through_res + vertical_resistance_workflow
    
    @property
    def safety_report(self):
        return [
            {
                "title": "Thrust Pass Through Check",
                "shot_title": "Block Resistance R_s",
                "shot": self.block_resistance,
                "goal_title": "Thrust Force (T_x)",
                "goal": self.thrust_force_horizontal,
                "unit": "kN"
            },
            {
                "title": "Vertical Ground Bearing Resistance",
                "shot_title": "Ultimate Ground Bearing Resistance",
                "shot": self.vertical_block_resistance_force,
                "goal_title": "Thrust Force (T_z)",
                "goal": self.thrust_force_vertical,
                "unit": "kN"
            },
        ]
    
@dataclass(frozen=True)
class VerticalDownturnBendThrustBlock(FittingCalculation):
    """Thrust-block calculation model for vertical downturn bends."""

    component: VerticalDownturnBend

    @property
    def thrust_force_resultant(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return 2 * self.maximum_design_pressure * area * math.sin(math.radians(self.angle) / 2)

    @property
    def thrust_force_horizontal(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area * (1 - math.cos(math.radians(self.angle)))

    @property
    def thrust_force_vertical(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area * math.sin(math.radians(self.angle))
    
    @property
    def over_turning_moment(self) -> float:
        return self.thrust_force_horizontal * self.overturning_level_arm
    
    @property
    def area_disturbed_passive(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return 1.5 * self.outside_diameter * self.soil_type.thrust_block.height
    
    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth
    
    @property    
    def buoyancy_coefficient(self) -> float:
        """Returns buoyancy coefficient for a downturn bend"""
        return 1
    
    @property
    def block_resistance(self) -> float:
        return self.soil_type.net_unit_area_soil_pressure * (self.soil_type.area_passive_face - self.area_disturbed_passive)
    
    @property
    def effective_weight_thrust_block(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.soil_type.thrust_block.height * self.soil_type.thrust_block.width * self.soil_type.thrust_block.length \
              * (self.soil_type.thrust_block.reinforced_concrete_unit_weight - (self.buoyancy_coefficient * UNIT_WEIGHT_WATER))
    
    @property
    def overturning_level_arm(self) -> float:
        """Calculates the overturning lever arm for the thrust block based on fitting geometry."""
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.soil_type.thrust_block.depth - (self.crown_depth + self.outside_diameter / 2)

    @property
    def vertical_reaction_block(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return (self.soil_type.thrust_block.reinforced_concrete_unit_weight - (self.buoyancy_coefficient * UNIT_WEIGHT_WATER)) * \
            self.soil_type.thrust_block.height * self.soil_type.thrust_block.width * self.soil_type.thrust_block.length
    
    @property
    def net_vertical_reaction_block(self) -> float:
        return self.vertical_reaction_block - self.thrust_force_vertical

    @property
    def block_restoring_moment(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.net_vertical_reaction_block * (self.soil_type.thrust_block.length / 2)
    
    @property
    def uplift_factor_of_safety(self) -> float:
        return self.effective_weight_thrust_block / self.thrust_force_vertical
    
    @property
    def thrust_pass_through_check(self) -> bool:
        if self.block_resistance > self.thrust_force_horizontal:
            return True
        return False
    
    @property
    def uplift_safety_check(self) -> bool:
        if self.uplift_factor_of_safety > 1.5:
            return True
        return False
    
    @property
    def thrust_block_standard_workflow(self) -> List[EngRes]:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return [
            _eng_res(
                label="Depth below ground to highest groundwater level",
                output=self.soil_type.ground_water_level,
                si_unit="m",
                formula_html=f"Z_GW = {self.soil_type.ground_water_level} m",
                formula_xls="Z_GW",
                reference=" - "
            ),
            _eng_res(
                label="Depth to crown of larger pipe",
                output=self.crown_depth,
                si_unit="m",
                formula_html=f"Z_O = {self.crown_depth} m",
                formula_xls="Z_O",
                reference=" - "
            ),
            _eng_res(
                label="Depth to base of block",
                output=self.soil_type.thrust_block.depth,
                si_unit="m",
                formula_html=f"Z_b = {self.soil_type.thrust_block.depth} m",
                formula_xls="Z_b",
                reference=" - "
            ),
            _eng_res(
                label="Buoyancy coefficient",
                output=self.soil_type.buoyancy_coefficient,
                si_unit="",
                formula_html=f"C_GW = {self.buoyancy_coefficient:.2f} (groundwater level is at the base of the thrust block or above)",
                formula_xls="Z_O",
                reference="Section 3.5"
            ),
            _eng_res(
                label="Native soil type",
                output=f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                si_unit="",
                formula_html=f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                formula_xls=f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                reference=" - "
            ),
            _eng_res(
                label="Native soil unit weight",
                output=self.soil_type.unit_weight,
                si_unit="kN/m3",
                formula_html=f"γₛ = {self.soil_type.unit_weight} kN/m3",
                formula_xls="γ_s",
                reference="Table 3.5"
            ),
            _eng_res(
                label="Reinforced concrete unit weight",
                output=self.soil_type.thrust_block.reinforced_concrete_unit_weight,
                si_unit="kN/m3",
                formula_html=f"γ_RC = {self.soil_type.thrust_block.reinforced_concrete_unit_weight} kN/m3",
                formula_xls="γ_RC",
                reference="Table 3.5"
            ),
            _eng_res(
                label="Groundwater unit weight",
                output=UNIT_WEIGHT_WATER,
                si_unit="kN/m3",
                formula_html=f"γ_W = {UNIT_WEIGHT_WATER} kN/m3",
                formula_xls="γ_W",
                reference="Table 3.5"
            ),
        ]
    
    @property
    def thrust_block_over_turning_stability_check_workflow(self) -> List[EngRes]:
        overturning_stability_check = f"{self.safety_factor_against_overturning:.2f} > 1.5, Passes overturning stability check" \
        if self.safety_factor_against_overturning > 1.5 else \
        f"1.5 > {self.safety_factor_against_overturning:.2f}, Fails overturning stability check"

        return [
            _eng_res(
                label="Overturning moment lever arm",
                output=self.overturning_level_arm,
                si_unit="m",
                formula_html=f"H_c = Z_b − (Z_O + D_O⁄2) = {self.overturning_level_arm:.2f} m",
                formula_xls="H_c = Z_b - (Z_O + D_O/2)",
                reference="Section 3.9"
            ),
            _eng_res(
                label="Overturning moment",
                output=self.over_turning_moment,
                si_unit="kNm",
                formula_html=f"M_O = T_x × H_c = {self.over_turning_moment:.2f} kNm",
                formula_xls="M_O = T_x x H_c",
                reference="Section 3.9"
            ),
            _eng_res(
                label="Passive face restoring moment",
                output=self.passive_face_restoring_moment,
                si_unit="kNm",
                formula_html=f"M_p = σ_p × W × H²⁄3 = {self.passive_face_restoring_moment:.2f}kNm ",
                formula_xls="M_p = σ_pa * W * (H^2)/3",
                reference="Section 3.9"
            ),
            _eng_res(
                label="Net disturbing moment",
                output=self.net_disturbing_moment,
                si_unit="kNm",
                formula_html=f"M_d = M_o − M_p = {self.net_disturbing_moment:.2f} kNm",
                formula_xls="M_d = M_o - M_P",
                reference="Section 3.9"
            ),
            _eng_res(
                label="Vertical reaction of block",
                output=self.vertical_reaction_block,
                si_unit="kNm",
                formula_html=f"R_v = (γ_RC − (C_GW × γ_W)) × Z_b × W × L = {self.vertical_reaction_block:.2f} kN",
                formula_xls="R_v = (γ_s - (C_GW * γ_w)) * Z_b * H * L",
                reference="Section 3.9"
            ),
            _eng_res(
                label="Net vertical reaction of block",
                output=self.net_vertical_reaction_block,
                si_unit="kNm",
                formula_html=f"R_vₙₑₜ = R_v − T_z = {self.net_vertical_reaction_block:.2f} kN",
                formula_xls="R_v = T<sub>z</sub>R_v",
                reference="Section 4.1.5"
            ),
            _eng_res(
                label="Concrete block restoring moment",
                output=f"{self.block_restoring_moment:.2f}",
                si_unit="kNm",
                formula_html=f"M_R = R_vₙₑₜ × L⁄2 = {self.block_restoring_moment:.2f} kNm",
                formula_xls="M_R = R_v * L/2",
                reference="Section 3.9"
            ),
            _eng_res(
                label="Safety factor against overturning",
                output=self.safety_factor_against_overturning,
                si_unit="m",
                formula_html=f"SF_O = M_R ÷ M_d = {self.safety_factor_against_overturning:.2f}",
                formula_xls="SF_O = M_R / M_d",
                reference="Section 3.9"
            ),
            _eng_res(
                label="Overturning stability check",
                output=overturning_stability_check,
                si_unit="",
                formula_html=overturning_stability_check,
                formula_xls=overturning_stability_check,
                reference=" - "
            )
        ]

    @property
    def fitting_workflow_res(self) -> List[EngRes]:

        vertical_uplift_check = f"{self.uplift_factor_of_safety:.2f} > 1.5, Passes vertical uplift resistance" \
        if self.uplift_factor_of_safety > 1.5 else \
        f"1.5  > {self.uplift_factor_of_safety:.2f}, Fails vertical uplift resistance"
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Pipe outside diameter",
                output=self.outside_diameter,
                si_unit="m",
                formula_html=f"D_O = {self.outside_diameter}",
                formula_xls="D_O",
                reference=""
            ),
            _eng_res(
                label="Bend Angle",
                output=self.angle,
                si_unit="°",
                formula_html=f"θ = {self.angle}°",
                formula_xls="θ",
                reference=""
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Disturbed passive area due to pipe trench",
                output=self.area_disturbed_passive,
                si_unit="m",
                formula_html=f"A_d = 1.5 × D_O × H = {self.area_disturbed_passive:.2f} m2",
                formula_xls="A_d",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Horizontal block resistance force",
                output=self.block_resistance,
                si_unit="kN",
                formula_html=f"R_s = (σ_pa × A_f) × (A_f − A_d) = {self.block_resistance:.2f} kN",
                formula_xls="R_s",
                reference="Figure 2.3"
            ),
            _eng_res(
                label="Thrust force (horizontal component)",
                output=self.thrust_force_horizontal,
                si_unit="kN",
                formula_html=f"T_x = P × π⁄4 × (D_O)² × (1 − cos(θ)) = {self.thrust_force_horizontal:.2f} kN",
                formula_xls="T_x = P * π/4 * D_O^2 * (1 - cos(θ))",
                reference="Section 4.1.5"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.thrust_force_horizontal,
                passed=self.thrust_pass_through_check,
                reference="",
                output=self.thrust_pass_through_check,
            )
        ]

        vertical_uplift_workflow: List[EngRes] = [
            _eng_res(
                label="Thrust force (vertical component)",
                output=self.thrust_force_vertical,
                si_unit="kN",
                formula_html=f" = {self.thrust_force_vertical:.2f} kN",
                formula_xls="T_Z = 2 * P * π/4 * (D_O)2 * sin(θ/2)",
                reference="Section 2.3"
            ),
            _eng_res(
                label="Effective weight of thrust block",
                output=self.effective_weight_thrust_block,
                si_unit="m",
                formula_html=f"T_z = 2 × P × π⁄4 × (D_O)² × sin(θ⁄2) = {self.effective_weight_thrust_block:.2f} kN/m2",
                formula_xls="W_T = H * W * L * (γ_RC - (C_GW - γ_W))",
                reference="Section 3.8.1"
            ),
            _eng_res(
                label="Uplift factor of safety",
                output=self.uplift_factor_of_safety,
                si_unit="kN",
                formula_html=f"F_s = W_T × T_z = {self.uplift_factor_of_safety:.2f}",
                formula_xls="Q_b = q_b * A_b",
                reference="Section 4.1.4"
            ),
            _eng_res(
                label="Uplift resistance check",
                output=vertical_uplift_check,
                si_unit="",
                formula_html=f"{vertical_uplift_check}",
                formula_xls=f"{vertical_uplift_check}",
                reference=""
            )
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res + vertical_uplift_workflow + self.thrust_block_over_turning_stability_check_workflow
    
    @property
    def safety_report(self):
        return [
            {
                "title": "Thrust Pass Through Check",
                "shot_title": "Block Resistance R_s",
                "shot": self.block_resistance,
                "goal_title": "Thrust Force (T_x)",
                "goal": self.thrust_force_horizontal,
                "unit": "kN"
            },
            {
                "title": "Uplift Check",
                "shot_title": "Uplift Safety Factor",
                "shot": self.uplift_factor_of_safety,
                "goal_title": "Factor of Safety",
                "goal": 1.5,
                "unit": ""
            },
            {
                "title": "Overturning Stability Check",
                "shot_title": "Safety Factor against Overturning",
                "shot": self.safety_factor_against_overturning,
                "goal_title": "Safety Factor",
                "goal": 1.5,
                "unit": ""
            },
        ]

@dataclass(frozen=True)
class TeeThrustBlock(FittingCalculation):
    """Thrust-block calculation model for tee fittings."""

    component: Tee

    @property
    def thrust_force_resultant(self) -> float:
        area_branch = (math.pi / 4) * self.outside_diameter_branch ** 2 
        return self.maximum_design_pressure * area_branch
    
    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth
    
    @property
    def area_disturbed_passive(self) -> float:
        return 0
    
    @property
    def overturning_level_arm(self) -> float:
        """
        Calculates the overturning lever arm for the thrust block based on fitting geometry.
        Returns 0 if no matching diameter attribute is found.
        """
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.soil_type.thrust_block.depth - (self.crown_depth + self.outside_diameter_branch / 2)

    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"{self.thrust_force_resultant:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance"
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Ouside diameter of branch pipe",
                output=self.outside_diameter_branch,
                si_unit="m",
                formula_html=f"D_O_B = {self.outside_diameter_branch}",
                formula_xls="D_OB",
                reference=""
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Block resistance force",
                output=self.block_resistance,
                si_unit="m",
                formula_html=f"R_s = (σ_pa × A_f) + (𝜏_b × A_b) + [2 × 𝜏_s × A_S] = {self.block_resistance:.2f}",
                formula_xls="R_s = (σ_pa * A_f) + (𝜏_b * A_b) + [2 * 𝜏_s * A_S]",
                reference="Section 4.1.3"
            ),
            _eng_res(
                label="Thrust force",
                output=self.thrust_force_resultant,
                si_unit="m",
                formula_html=f"T = P × π⁄4 × D_O_B² = {self.thrust_force_resultant:.2f} kN",
                formula_xls="T =  P * π/4 * (D_OB)^2",
                reference="Figure 2.3"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.thrust_force_resultant,
                passed=self.thrust_pass_through_check,
                reference="",
                output=thrust_pass_through_check,
            )
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow

@dataclass(frozen=True)
class AngleBranchThrustBlock(FittingCalculation):
    """Thrust-block calculation model for angle branch fittings."""

    component: AngleBranch
    
    @property
    def over_turning_moment(self) -> float:
        # if isinstance(self.fitting, VerticalBend):
        #     return self.fitting.thrust_force_horizontal() * self.overturning_level_arm
        return self.thrust_force_resultant * self.overturning_level_arm
    
    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter_branch / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth
    
    @property
    def overturning_level_arm(self) -> float:
        """
        Calculates the overturning lever arm for the thrust block based on fitting geometry.
        Returns 0 if no matching diameter attribute is found.
        """
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.soil_type.thrust_block.depth - (self.crown_depth + self.outside_diameter_branch / 2)

    @property
    def thrust_force_resultant(self) -> float:
        area_branch = math.pi * self.outside_diameter_branch ** 2 / 4
        return self.maximum_design_pressure * area_branch
    
    @property
    def area_disturbed_passive(self) -> float:
        return 0
    
    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"{self.thrust_force_resultant:.2f} kN > {self.block_resistance:.2f} kN, Fails thrust resistance"
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Ouside diameter of branch pipe",
                output=self.outside_diameter_branch,
                si_unit="m",
                formula_html=f"D_O_B = {self.outside_diameter_branch} m",
                formula_xls="D_OB",
                reference=""
            ),
            _eng_res(
                label="Ouside diameter of main pipe",
                output=self.outside_diameter_main,
                si_unit="m",
                formula_html=f"D_O_M = {self.outside_diameter_main} m",
                formula_xls="D_OM",
                reference=""
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Block resistance force",
                output=self.block_resistance,
                si_unit="m",
                formula_html=f" = {self.block_resistance:.2f} kN",
                formula_xls="R_s = (σ_pa * A_f) + (𝜏_b * A_b) + (2 * 𝜏_s)",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Thrust force",
                output=self.thrust_force_resultant,
                si_unit="m",
                formula_html=f"T = P x π/4 x D<sub>O_B</sub><sup>2</sup> = {self.thrust_force_resultant:.2f} kN",
                formula_xls="T = P * π/4 * D_OB^2",
                reference="Figure 2.3"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.thrust_force_resultant,
                passed=self.thrust_pass_through_check,
                reference="",
                output=self.thrust_pass_through_check,
            )
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow


@dataclass(frozen=True)
class ClosedValveThrustBlock(FittingCalculation):
    """Thrust-block calculation model for closed valve fittings."""

    component: ClosedValve

    @property
    def thrust_force_resultant(self) -> float:
        area = math.pi * self.component.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area
    
    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth
    
    @property
    def area_disturbed_passive(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.depth - self.soil_type.thrust_block.height > self.crown_depth + self.component.outside_diameter:
            return 0
        return 1.5 * self.component.outside_diameter \
            * (self.soil_type.thrust_block.height + self.component.outside_diameter + self.crown_depth - self.depth)
    
    @property
    def overturning_level_arm(self) -> float:
        """
        Calculates the overturning lever arm for the thrust block based on fitting geometry.
        Returns 0 if no matching diameter attribute is found.
        """
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.depth - (self.crown_depth + self.component.outside_diameter / 2)
    
    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"{self.thrust_force_resultant:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance"
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Pipe outside diameter",
                output=f"{self.outside_diameter}",
                si_unit="m",
                formula_html=f"D_O_B = {self.outside_diameter}",
                formula_xls="D_OB",
                reference=""
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Disturbed passive area due to pipe trench",
                output=self.area_disturbed_passive,
                si_unit="m",
                formula_html=f"A_d = 1.5 × D_O × (H + D_O + Z_O − Z_b) = {self.area_disturbed_passive:.2f} m2",
                formula_xls="A_d",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Block resistance force",
                output=self.block_resistance,
                si_unit="m",
                formula_html=f"R_s = σ_pa × (A_f − A_d) + (𝜏_b × A_b) + (2 × 𝜏_s × A_S) = {self.block_resistance:.2f} kN",
                formula_xls="R_s = σ_pa * (A_f - A_d) + (𝜏_b * A_b) + (2 * 𝜏_s * A_s)",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Thrust force",
                output=self.thrust_force_resultant,
                si_unit="m",
                formula_html=f"T = P × π⁄4 × D_O² = {self.thrust_force_resultant:.2f} kN",
                formula_xls="T = P * π/4 * (D_O)^2",
                reference="Figure 2.3"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.thrust_force_resultant,
                passed=self.thrust_pass_through_check,
                reference="",
                output=self.thrust_pass_through_check,
            )
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow
    
@dataclass(frozen=True)
class LineStopThrustBlock(FittingCalculation):
    """Thrust-block calculation model for line stop fittings."""

    component: LineStop

    @property
    def thrust_force_resultant(self) -> float:
        area = math.pi * self.component.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area
    
    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth
    
    @property
    def area_disturbed_passive(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.depth - self.soil_type.thrust_block.height > self.crown_depth + self.component.outside_diameter:
            return 0
        return 1.5 * self.component.outside_diameter \
            * (self.soil_type.thrust_block.height + self.component.outside_diameter + self.crown_depth - self.depth)
    
    @property
    def block_resistance(self) -> float:
        return self.soil_type.net_unit_area_soil_pressure * (self.soil_type.area_passive_face - self.area_disturbed_passive) \
            + (self.soil_type.sliding_resistance_base(is_line_stop=True) * self.soil_type.area_base_sliding) \
            + (2 * self.soil_type.sliding_resistance_side(is_line_stop=True) * self.soil_type.area_side_sliding)
    
    @property
    def overturning_level_arm(self) -> float:
        """
        Calculates the overturning lever arm for the thrust block based on fitting geometry.
        Returns 0 if no matching diameter attribute is found.
        """
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.depth - (self.crown_depth + self.component.outside_diameter / 2)
    
    @property
    def vertical_reaction_block(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return (self.soil_type.thrust_block.reinforced_concrete_unit_weight - (self.soil_type.buoyancy_coefficient * UNIT_WEIGHT_WATER)) * \
            self.soil_type.thrust_block.height * self.soil_type.thrust_block.width * self.soil_type.thrust_block.length
    
    @property
    def over_turning_stability_check_workflow(self) -> List[EngRes]:
        return [
            _eng_res(
                label="Overturning moment lever arm",
                output=self.overturning_level_arm,
                si_unit="m",
                formula_html=f"H_c = Z_b − (Z_O + D_O⁄2) = {self.overturning_level_arm:.2f} m",
                formula_xls="H_c = Z_b - (Z_O + D_O/2)",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Overturning moment",
                output=self.over_turning_moment,
                si_unit="kNm",
                formula_html=f"M_O = T × H_c = {self.over_turning_moment:.2f} kNm",
                formula_xls="M_O = T x H_c",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Passive face restoring moment",
                output=self.passive_face_restoring_moment,
                si_unit="kNm",
                formula_html=f"M_p = σ_pa × W × H²⁄3 = {self.passive_face_restoring_moment:.2f} kNm",
                formula_xls="M_p = σ_pa * W * (H^2)/3",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Net disturbing moment",
                output=self.net_disturbing_moment,
                si_unit="kNm",
                formula_html=f"M_d = M_o − M_p = {self.net_disturbing_moment:.2f} kNm",
                formula_xls="M_d = M_o - M_P",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Vertical reaction of block",
                output=self.vertical_reaction_block,
                si_unit="kN",
                formula_html=f"R_v = (γ_RC − (C_GW × γ_W)) × Z_b × W × L = {self.vertical_reaction_block:.2f} kN",
                formula_xls="R_v = (γ_s - (C_GW * γ_w)) * Z_b * H * L",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Concrete block restoring moment",
                output=f"{self.block_restoring_moment}",
                si_unit="kNm",
                formula_html=f"M_R = R_v × L⁄2 = {self.block_restoring_moment:.2f} kNm",
                formula_xls="M_R = R_v * L/2",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Safety factor against overturning",
                output=self.safety_factor_against_overturning,
                si_unit="m",
                formula_html=f"SF_O = M_R ÷ M_d = {self.safety_factor_against_overturning:.2f}",
                formula_xls="SF_O = M_R / M_d",
                reference="Section 3.9",
            ),
            _eng_res(
                label="Overturning stability check",
                output=self.overturning_check,
                si_unit=" - ",
                formula_html=f"{self.safety_factor_against_overturning:.2f} > 1.5, Pass" if self.overturning_check else f"1.5 > {self.safety_factor_against_overturning:.2f}, Fail",
                formula_xls="Pass overturning stability" if self.overturning_check else "Fail overturning stability",
                reference=" - ",
            ),
        ]
    
    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"{self.thrust_force_resultant:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance"
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Pipe outside diameter",
                output=f"{self.outside_diameter}",
                si_unit="m",
                formula_html=f"D_O_B = {self.outside_diameter}",
                formula_xls="D_OB",
                reference=""
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Adjusted Base Sliding Resistance",
                output=self.soil_type.sliding_resistance_base(is_line_stop=True),
                si_unit="m",
                formula_html=f"τ_b  = {self.soil_type.sliding_resistance_base(is_line_stop=True):.2f} kN/m2",
                formula_xls="τ_b ",
                reference="Section 3.7.1"
            ),
            _eng_res(
                label="Adjusted Side Sliding Resistance",
                output=self.soil_type.sliding_resistance_side(is_line_stop=True),
                si_unit="m",
                formula_html=f"τ_s  = {self.soil_type.sliding_resistance_side(is_line_stop=True):.2f} kN/m2",
                formula_xls="τ_b ",
                reference="Section 3.7.2"
            ),
            _eng_res(
                label="Disturbed passive area due to pipe trench",
                output=self.area_disturbed_passive,
                si_unit="m",
                formula_html=f"A_d = 1.5 × D_O × (H + D_O + Z_O − Z_b) = {self.area_disturbed_passive:.2f} m2",
                formula_xls="A_d",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Block resistance force",
                output=self.block_resistance,
                si_unit="m",
                formula_html=f"R_s = σ_pa × (A_f − A_d) + (𝜏_b × A_b) = {self.block_resistance:.2f} kN",
                formula_xls="R_s = σ_pa * (A_f - A_d) + (𝜏_b * A_b) + (2 * 𝜏_s * A_s)",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Thrust force",
                output=self.thrust_force_resultant,
                si_unit="m",
                formula_html=f"T = P × π⁄4 × D_O² = {self.thrust_force_resultant:.2f} kN",
                formula_xls="T = P * π/4 * (D_O)^2",
                reference="Figure 2.3"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.thrust_force_resultant,
                passed=self.thrust_pass_through_check,
                reference="",
                output=self.thrust_pass_through_check,
            )
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.over_turning_stability_check_workflow
    
    @property
    def safety_report(self):
        return [
            {
                "title": "Thrust Pass Through Check",
                "shot_title": "Block Resistance R_s",
                "shot": self.block_resistance,
                "goal_title": "Thrust Force (T)",
                "goal": self.thrust_force_resultant,
                "unit": "kN"
            },
            {
                "title": "Overturning Stability Check",
                "shot_title": "Safety Factor against Overturning",
                "shot": self.safety_factor_against_overturning,
                "goal_title": "Safety Factor",
                "goal": 1.5,
                "unit": ""
            },
        ]


@dataclass(frozen=True)
class BlankEndThrustBlock(FittingCalculation):
    """Thrust-block calculation model for blank end fittings."""

    component: BlankEnd

    @property
    def thrust_force_resultant(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area
    
    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth
    
    @property
    def area_disturbed_passive(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.depth - self.soil_type.thrust_block.height > self.crown_depth + self.component.outside_diameter:
            return 0
        return 1.5 * self.outside_diameter \
            * (self.soil_type.thrust_block.height + self.outside_diameter + self.crown_depth - self.soil_type.thrust_block.depth)
    
    @property
    def overturning_level_arm(self) -> float:
        """
        Calculates the overturning lever arm for the thrust block based on fitting geometry.
        Returns 0 if no matching diameter attribute is found.
        """
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.soil_type.thrust_block.depth - (self.crown_depth + self.outside_diameter / 2)

    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"{self.thrust_force_resultant:.2f} kN > {self.block_resistance:.2f} kN, Fails thrust resistance"
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Pipe outside diameter",
                output=self.outside_diameter,
                si_unit="m",
                formula_html=f"D<sub>O</sub> = {self.outside_diameter} m",
                formula_xls="D_O = ",
                reference=""
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Disturbed passive area due to pipe trench",
                output=self.area_disturbed_passive,
                si_unit="m",
                formula_html=f"A_d = 1.5 × D_O × (H + D_O + Z_O − Z_b) = {self.area_disturbed_passive:.2f} m2",
                formula_xls="A_d = ",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Block resistance force",
                output=self.block_resistance,
                si_unit="m",
                formula_html=f"R_s = σ_pa × (A_f − A_d) + (𝜏_b × A_b) + (2 × 𝜏_s × A_S) = {self.block_resistance:.2f} kN",
                formula_xls="R_s = σ_pa * (A_f − A_d) + (𝜏_b * A_b) + (2 * 𝜏_s * A_S)",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Thrust force",
                output=self.thrust_force_resultant,
                si_unit="m",
                formula_html=f"T = P × π⁄4 × D_O² = {self.thrust_force_resultant:.2f} kN",
                formula_xls="T = P * π⁄4 * D_O^2 ",
                reference="Figure 2.3"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.thrust_force_resultant,
                passed=self.thrust_pass_through_check,
                reference="",
                output=self.thrust_pass_through_check,
            )
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow


@dataclass(frozen=True)
class TaperThrustThrustBlock(FittingCalculation):
    """Thrust-block calculation model for taper thrust fittings."""

    component: TaperThrust

    @property
    def thrust_force_resultant(self) -> float:
        area_large = math.pi * self.outside_diameter_large ** 2 / 4
        area_small = math.pi * self.outside_diameter_small ** 2 / 4
        return self.maximum_design_pressure * (area_large - area_small)
    
    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth
    
    @property
    def area_disturbed_passive(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.depth - self.soil_type.thrust_block.height > self.crown_depth + self.component.outside_diameter_large:
            return 0
        return 1.5 * self.outside_diameter_large \
            * (self.soil_type.thrust_block.height + self.outside_diameter_large + self.crown_depth - self.soil_type.thrust_block.depth)
    
    @property
    def overturning_level_arm(self) -> float:
        """
        Calculates the overturning lever arm for the thrust block based on fitting geometry.
        Returns 0 if no matching diameter attribute is found.
        """
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.soil_type.thrust_block.depth - (self.crown_depth + self.outside_diameter_large / 2)    

    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"{self.thrust_force_resultant:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance"
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Pipe outside diameter – larger end",
                output=self.outside_diameter_large,
                si_unit="m",
                formula_html=f"D_O_A = {self.outside_diameter_large} m",
                formula_xls="D_OA = ",
                reference=" - "
            ),
            _eng_res(
                label="Pipe outside diameter – smaller end",
                output=self.outside_diameter_small,
                si_unit="m",
                formula_html=f"DO_B = {self.outside_diameter_small} m",
                formula_xls="D_OB = ",
                reference=" - "
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Disturbed passive area due to pipe trench",
                output=self.area_disturbed_passive,
                si_unit="m",
                formula_html=f"A_d = 1.5 × D_O_A × (H + D_O_A + Z_O − Z_b) = {self.area_disturbed_passive:.2f} m2",
                formula_xls="A_d = 1.5 * D_O_A * (H + D_O_A + Z_O − Z_b)",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Block resistance force",
                output=self.block_resistance,
                si_unit="m",
                formula_html=f"R_s = σ_pa × (A_f − A_d) + (𝜏_b × A_b) + (2 × 𝜏_s × A_S) = {self.block_resistance:.2f} kN",
                formula_xls="R_s = σ_pa * (A_f − A_d) + (𝜏_b * A_b) + (2 * 𝜏_s * A_S)",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Thrust force",
                output=self.thrust_force_resultant,
                si_unit="m",
                formula_html=f"T = P × π⁄4 × ((D_O_A)² − (D_O_B)²) = {self.thrust_force_resultant:.2f} kN",
                formula_xls="T = P * π⁄4 * ((D_O_A)^2 − (D_O_B)^2) ",
                reference="Figure 2.3"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.thrust_force_resultant,
                passed=self.thrust_pass_through_check,
                reference=" - ",
                output=self.thrust_pass_through_check,
            )
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow
    
@dataclass(frozen=True)
class FlangedMetallicPipeThrustBlock(FittingCalculation):
    """Thrust-block calculation model for flanged metallic pipes."""

    component: FlangedMetallicPipe

    @property
    def depth(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth is None:
            return self.crown_depth - self.outside_diameter / 2 + self.soil_type.thrust_block.height / 2
        return self.soil_type.thrust_block.depth

    @property
    def buoyancy_coefficient(self):
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return 1 - (self.soil_type.ground_water_level / self.depth)
    
    @property
    def area_disturbed_passive(self):
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.depth - self.soil_type.thrust_block.height > self.crown_depth + self.component.embedment_type.pipe.outside_diameter:
            return 0
        return 1.5 * self.embedment_type.pipe.outside_diameter \
            * (self.soil_type.thrust_block.height + self.embedment_type.pipe.outside_diameter + self.embedment_type.pipe.crown_depth - self.soil_type.thrust_block.depth)
    
    @property
    def block_resistance(self) -> float:
        return self.soil_type.net_unit_area_soil_pressure * (self.soil_type.area_passive_face - self.area_disturbed_passive) \
            + (self.soil_type.sliding_resistance_base() * self.soil_type.area_base_sliding) \
            + (2 * self.soil_type.sliding_resistance_side() * self.soil_type.area_side_sliding)
    
    @property
    def overturning_level_arm(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.soil_type.thrust_block.depth - (self.embedment_type.pipe.crown_depth + self.embedment_type.pipe.outside_diameter / 2)
    
    @property
    def over_turning_moment(self) -> float:
        return self.embedment_type.contraction_design_force * self.overturning_level_arm
    
    @property
    def thrust_pass_through_check(self) -> bool:
        if self.block_resistance > self.embedment_type.contraction_design_force:
            return True
        return False

    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"{self.block_resistance:.2f} kN > {self.embedment_type.contraction_design_force:.2f} kN, Passes thrust resistance" \
        if self.block_resistance > self.embedment_type.contraction_design_force else \
        f"{self.embedment_type.contraction_design_force:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance"
        
        fitting_dims: List[EngRes] = [
            _eng_res(
                label="Pipe outside diameter",
                output=self.embedment_type.pipe.outside_diameter,
                si_unit="m",
                formula_html=f"D_O = {self.embedment_type.pipe.outside_diameter} m",
                formula_xls="D_O = ",
                reference=" - "
            ),
        ]
        thrust_pass_through_res: List[EngRes] = [
            _eng_res(
                label="Disturbed passive area due to pipe trench",
                output=self.area_disturbed_passive,
                si_unit="m",
                formula_html=f"A_d = 1.5 × D_O_A × (H + D_O_A + Z_O − Z_b) = {self.area_disturbed_passive:.2f} m2",
                formula_xls="A_d = 1.5 * D_O_A * (H + D_O_A + Z_O − Z_b)",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Block resistance force",
                output=self.block_resistance,
                si_unit="m",
                formula_html=f"R_s = σ_pa × (A_f − A_d) + (𝜏_b × A_b) + (2 × 𝜏_s × A_S) = {self.block_resistance:.2f} kN",
                formula_xls="R_s = ",
                reference="Section 4.1.1"
            ),
            _eng_res(
                label="Design force",
                output=self.embedment_type.contraction_design_force,
                si_unit="kN",
                formula_html=f"F<sub>d</sub> = {self.embedment_type.contraction_design_force:.2f} kN",
                formula_xls="F_D",
                reference="Figure 2.3"
            ),
            self._pass_fail_check_row(
                label="Pass through resistance check",
                lhs=self.block_resistance,
                rhs=self.embedment_type.contraction_design_force,
                passed=self.thrust_pass_through_check,
                reference=" - ",
                output=self.thrust_pass_through_check,
            )
        ]
        return self.embedment_type.pipe.render_workflow_report + fitting_dims + self.embedment_type.render_workflow_report + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow

    @property
    def safety_report(self):
        return [
            {
                "title": "Thrust Pass Through Check",
                "shot_title": "Block Resistance R_s",
                "shot": self.block_resistance,
                "goal_title": "Design Force",
                "goal": self.component.embedment_type.contraction_design_force,
                "unit": "kN"
            },
            {
                "title": "Overturning Stability Check",
                "shot_title": "Safety Factor against Overturning",
                "shot": self.safety_factor_against_overturning,
                "goal_title": "Safety Factor",
                "goal": 1.5,
                "unit": ""
            },
        ]
    
# --- Builder and Registry ---

BUILDERS: Dict[str, Callable[[Any], FittingCalculation]] = {}

def register(fitting_key: str):
    """
    Decorator that registers a builder function for a fitting type.
    """
    def wrap(builder_fn: Callable[[Any], FittingCalculation]):
        BUILDERS[fitting_key] = builder_fn
        return builder_fn
    return wrap

@register("horizontal_bend")
def build_horizontal_bend(params: Any) -> FittingCalculation:
    s = params.fitting_section
    component = HorizontalBend(
        outside_diameter=s.outside_diameter,
        angle=s.angle,
        radius=0,
    )
    return HorizontalBendThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )

@register("vertical_upturn_bend")
def build_vertical_upturn_bend(params: Any) -> FittingCalculation:
    s = params.fitting_section
    component = VerticalUpturnBend(
        outside_diameter=s.outside_diameter,
        angle=s.angle,
        radius=0,
    )
    return VerticalUpturnBendThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )

@register("vertical_downturn_bend")
def build_vertical_downturn_bend(params: Any) -> FittingCalculation:
    s = params.fitting_section
    component = VerticalDownturnBend(
        outside_diameter=s.outside_diameter,
        angle=s.angle,
        radius=0,
    )
    return VerticalDownturnBendThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )

@register("tee")
def build_tee(params: Any) -> FittingCalculation:
    s = params.fitting_section
    component = Tee(
        outside_diameter_main=s.outside_diameter_main,
        outside_diameter_branch=s.outside_diameter_branch
    )
    return TeeThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )

@register("angle_branch")
def build_angle_branch(params: Any) -> FittingCalculation:
    s = params.fitting_section
    component = AngleBranch(
        angle=s.angle,
        outside_diameter_main=s.outside_diameter_main,
        outside_diameter_branch=s.outside_diameter_branch
    )
    return AngleBranchThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )

@register("closed_valve")
def build_closed_valve(params: Any) -> FittingCalculation:
    s = params.fitting_section
    component = ClosedValve(
        outside_diameter=s.outside_diameter
    )
    return ClosedValveThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )

@register("line_stop")
def build_line_stop_valve(params: Any) -> FittingCalculation:
    s = params.fitting_section
    component = LineStop(
        outside_diameter=s.outside_diameter
    )
    return LineStopThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )


@register("blank_end")
def build_blank_end(params: Any) -> FittingCalculation:
    s = params.fitting_section
    component = BlankEnd(
        outside_diameter=s.outside_diameter
    )
    return BlankEndThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )

@register("taper_thrust")
def build_taper_thrust(params: Any) -> FittingCalculation:
    s = params.fitting_section
    component = TaperThrust(
        outside_diameter_large=s.outside_diameter_large,
        outside_diameter_small=s.outside_diameter_small
    )
    return TaperThrustThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )

@register("metallic_flange")
def build_metallic_flange(params: Any) -> FittingCalculation:
    s = params.pipe_section
    component = FlangedMetallicPipe(
        embedment_type=create_embedment(params)
    )
    return FlangedMetallicPipeThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )

@register("metallic_flange")
def build_line_stop_flange(params: Any) -> FittingCalculation:
    s = params.pipe_section
    component = FlangedMetallicPipe(
        embedment_type=create_embedment(params)
    )
    return FlangedMetallicPipeThrustBlock(
        component=component,
        maximum_design_pressure=s.maximum_design_pressure,
        crown_depth=s.crown_depth,
        soil_type=create_soil(params),
    )
#remove **kwargs
def fitting_from_params(params: Any, **kwargs) -> FittingCalculation:
    ui_fitting_label = str(params.fitting_section.fitting_type)

    try:
        fitting_key = fitting_list[ui_fitting_label]
    except KeyError as e:
        raise ValueError(
            f"Unkown fitting label '{ui_fitting_label}"
            F"Valid Options: {FITTING_LABELS}"
        ) from e
    
    try:
        builder = BUILDERS[fitting_key]
    except KeyError as e:
        raise ValueError(
            f"No builder registered for fitting key: {fitting_key}"
            f"Registered builders: {list(BUILDERS.keys())}"
        )
    return builder(params)
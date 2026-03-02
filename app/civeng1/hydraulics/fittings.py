import math
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Dict, Tuple, List, Union
from app.civeng1.soils.soil_mechanics import Soil, create_soil, UNIT_WEIGHT_WATER, CoarseSoil, FineSoil, CoarseEmbedment, FineEmbedment, Embedment, create_embedment
from app.civeng1.reporting.engres import EngRes
from .pipes import WeldedPePipe

#--- Utils and Types ---
fitting_list = {
    "Horizontal Bend": "horizontal_bend", 
    "Vertical Upturn Bend": "vertical_upturn_bend",
    "Vertical Downturn Bend": "vertical_downturn_bend",
    "Tee": "tee", 
    "Angle Branch": "angle_branch", 
    "Closed Valve": "closed_valve", 
    "Blank End": "blank_end", 
    "Taper Thrust": "taper_thrust",
}

FITTING_LABELS = list(fitting_list.keys())

ReportRow = Tuple[Any]
ThrustForce = Tuple[str, float]

# --- Abstract Base Class ---
@dataclass(frozen=True)
class Fitting(ABC):
    maximum_design_pressure: float
    crown_depth: float
    soil_type: Soil

    # @abstractmethod
    # def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
    #     ...

    @property
    def thrust_force_resultant(self) -> float:
        raise NotImplementedError("Subclass must implement this `thrust_force_resultant`")
        
    @property
    def area_disturbed_passive(self) -> float:
        raise NotImplementedError("Subclass must implement this `area_disturbed_passive`")
    
    @property
    def block_resistance(self) -> float:
        return self.soil_type.net_unit_area_soil_pressure * (self.soil_type.area_passive_face - self.area_disturbed_passive) \
            + (self.soil_type.sliding_resistance_base() * self.soil_type.area_base_sliding) \
            + (2 * self.soil_type.sliding_resistance_side * self.soil_type.area_side_sliding)
    
    @property
    def overturning_level_arm(self) -> float:
        """
        Calculates the overturning lever arm for the thrust block based on fitting geometry.
        Returns 0 if no matching diameter attribute is found.
        """
        raise NotImplementedError("Subclass must implement this `overturning_level_arm`")

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
        # if isinstance(self.fitting, VerticalBend) and self.fitting.turn_direction == "downturn":
        #     return self.effective_weight_thrust_block
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return (self.soil_type.unit_weight - (self.soil_type.buoyancy_coefficient * UNIT_WEIGHT_WATER)) * \
            self.soil_type.thrust_block.depth * self.soil_type.thrust_block.width * self.soil_type.thrust_block.length
    
    @property
    def block_restoring_moment(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return self.vertical_reaction_block * (self.soil_type.thrust_block.length / 2)
    
    @property
    def safety_factor_against_overturning(self) -> float:
        return self.block_restoring_moment / self.net_disturbing_moment
    
    @property
    def report_pipe_dimensions(self) -> List[EngRes]:
        raise NotImplementedError("Subclass must implement this `report_dimensions`")
    
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
            {
                "label": "Depth below ground to highest groundwater level",
                "output": self.soil_type.ground_water_level,
                "si_unit": "m",
                "formula_html": f"Z_GW = {self.soil_type.ground_water_level} m",
                "formula_xls": "Z_GW",
                "reference": " - "
            },
            {
                "label": "Depth to crown of larger pipe",
                "output": self.crown_depth,
                "si_unit": "m",
                "formula_html": f"Z_O = {self.crown_depth} m",
                "formula_xls": "Z_O",
                "reference": " - "
            },
            {
                "label": "Depth to base of block",
                "output": self.soil_type.thrust_block.depth,
                "si_unit": "m",
                "formula_html": f"Z_b = {self.soil_type.thrust_block.depth} m",
                "formula_xls": "Z_b",
                "reference": " - "
            },
            {
                "label": "Buoyancy coefficient",
                "output": self.soil_type.buoyancy_coefficient,
                "si_unit": "",
                "formula_html": f"C_GW = 1 − (Z_GW ÷ Z_b) = {self.soil_type.buoyancy_coefficient:.2f}",
                "formula_xls": "Z_O",
                "reference": "Section 3.5"
            },
            {
                "label": "Native soil type",
                "output": f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                "si_unit": "",
                "formula_html": f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                "formula_xls": f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                "reference": " - "
            },
            {
                "label": "Native soil unit weight",
                "output": self.soil_type.unit_weight,
                "si_unit": "kN/m3",
                "formula_html": f"γₛ = {self.soil_type.unit_weight} kN/m3",
                "formula_xls": "γ_s",
                "reference": "Table 3.5"
            },
            {
                "label": "Groundwater unit weight",
                "output": UNIT_WEIGHT_WATER,
                "si_unit": "kN/m3",
                "formula_html": f"γ<sub>W</sub> = {UNIT_WEIGHT_WATER} kN/m3",
                "formula_xls": "γ_W",
                "reference": "Table 3.5"
            },
        ]

    @property
    def thrust_block_over_turning_stability_check_workflow(self) -> List[EngRes]:

        return [
            {
                "label": "Overturning moment lever arm",
                "output": self.overturning_level_arm,
                "si_unit": "m",
                "formula_html": f"H_c = Z_b − (Z_O + D_O⁄2) = {self.overturning_level_arm:.2f} m",
                "formula_xls": "H_c = Z_b - (Z_O + D_O/2)",
                "reference": "Section 3.9"
            },
            {
                "label": "Overturning moment",
                "output": self.over_turning_moment,
                "si_unit": "kNm",
                "formula_html": f"M_O = T × H_c = {self.over_turning_moment:.2f} kNm",
                "formula_xls": "M_O = T x H_c",
                "reference": "Section 3.9"
            },
            {
                "label": "Passive face restoring moment",
                "output": self.passive_face_restoring_moment,
                "si_unit": "kNm",
                "formula_html": f"M_p = σ_pa × W × H²⁄3 = {self.passive_face_restoring_moment:.2f} kNm",
                "formula_xls": "M_p = σ_pa * W * (H^2)/3",
                "reference": "Section 3.9"
            },
            {
                "label": "Net disturbing moment",
                "output": self.net_disturbing_moment,
                "si_unit": "kNm",
                "formula_html": f"M_d = M_o − M_p = {self.net_disturbing_moment:.2f} kNm",
                "formula_xls": "M_d = M_o - M_P",
                "reference": "Section 3.9"
            },
            {
                "label": "Vertical reaction of block",
                "output": self.vertical_reaction_block,
                "si_unit": "kN",
                "formula_html": f"R_v = (γ_s − (C_GW × γ_W)) × Z_b × W × L = {self.vertical_reaction_block:.2f} kN",
                "formula_xls": "R_v = (γ_s - (C_GW * γ_w)) * Z_b * H * L",
                "reference": "Section 3.9"
            },
            {
                "label": "Concrete block restoring moment",
                "output": f"{self.block_restoring_moment}",
                "si_unit": "kNm",
                "formula_html": f"M_R = R_v × L⁄2 = {self.block_restoring_moment:.2f} kNm",
                "formula_xls": "M_R = R_v * L/2",
                "reference": "Section 3.9"
            },
            {
                "label": "Safety factor against overturning",
                "output": self.safety_factor_against_overturning,
                "si_unit": "m",
                "formula_html": f"SF_O = M_R ÷ M_d = {self.safety_factor_against_overturning:.2f}",
                "formula_xls": "SF_O = M_R / M_d",
                "reference": "Section 3.9"
            },
            {
                "label": "Overturning stability check",
                "output": self.overturning_check,
                "si_unit": " - ",
                "formula_html": f"{self.safety_factor_against_overturning:.2f} > 1.5, Pass" if self.overturning_check else f"1.5 > {self.safety_factor_against_overturning:.2f}, Fail",
                "formula_xls": "Pass overturning stability" if self.overturning_check else "Fail overturning stability",
                "reference": " - "
            }
        ]

    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        raise NotImplementedError("Subclass must implement this `fitting_workflow_res`")

# --- Fitting Dataclasses ---

@dataclass(frozen=True)
class HorizontalBend(Fitting):
    outside_diameter: float
    angle: float      # degrees
    radius: float = 0   # meters

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)
    
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
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter",
                "output": self.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D_O = {self.outside_diameter}",
                "formula_xls": "D_O",
                "reference": ""
            },
            {
                "label": "Bend Angle",
                "output": self.angle,
                "si_unit": "°",
                "formula_html": f"θ = {self.angle}°",
                "formula_xls": "θ",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R_s = (σ_pa × A_f) + (𝜏_b × A_b) = {self.block_resistance:.2f} kN",
                "formula_xls": "R_s",
                "reference": "Section 4.1.3"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = 2 × P × π⁄4 × (D_O)² × sin(θ⁄2) = {self.thrust_force_resultant:.2f} kN",
                "formula_xls": "T = 2 x P x π/4 x (D_O)2 x sin(θ/2)",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": self.thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "formula_xls": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "reference": ""
            }
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow

@dataclass(frozen=True)
class VerticalUpturnBend(Fitting):
    outside_diameter: float
    angle: float      # degrees
    radius: float     # meters

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)

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
        return f"{self.vertical_block_resistance_force} kN > {self.thrust_force_vertical:.2f} kN Pass vertical ground bearing resistance" if self.vertical_block_resistance_force > self.thrust_force_vertical \
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
    def fitting_workflow_res(self) -> List[EngRes]:
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter",
                "output": self.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D_O = {self.outside_diameter} m",
                "formula_xls": "D_O",
                "reference": ""
            },
            {
                "label": "Bend Angle",
                "output": self.angle,
                "si_unit": "°",
                "formula_html": f"θ = {self.angle}°",
                "formula_xls": "θ",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Horizontal block resistance force",
                "output": self.block_resistance,
                "si_unit": "kN",
                "formula_html": f"R_s = (σ_pa × A_f) + (𝜏_b × A_b) = {self.block_resistance:.2f} kN",
                "formula_xls": "R_s = (σ_pa * A_f) + (𝜏_b * A_b)",
                "reference": "Section 4.1.3"
            },
            {
                "label": "Thrust force (horizontal component)",
                "output": self.thrust_force_horizontal,
                "si_unit": "kN",
                "formula_html": f"T_x = P × π⁄4 × (D_O)² × (1 − cos(θ)) = {self.thrust_force_horizontal:.2f} kN",
                "formula_xls": "T_x = P * π/4 * D_O^2 * (1 - cos(θ))",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": self.thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{self.block_resistance:.2f} kN > {self.thrust_force_horizontal:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_horizontal:.2f} kN, Fail",
                "formula_xls": f"{self.block_resistance:.2f} kN > {self.thrust_force_horizontal:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_horizontal:.2f} kN, Fail",
                "reference": ""
            }
        ]
        
        vertical_ground_bearing_formula_html = "q_b = [0.5 × (γ_s − (C_GW × γ_w)) × B × N_γ] + [(γ_s − (C_GW × γ_w)) × (N_q − 1) × Z_b] ÷ DF_P"\
        if isinstance(self.soil_type, CoarseSoil) else "q_b = (6 × C_U) ÷ DF_P"
        vertical_ground_bearing_formula_xls = "q_b = (0.5 * (γ_s - (C_GW * γ_W)) * B * N_γ) + ((γ_S - (C_GW * γ_w) *(N_q - 1)* Z_b) ÷ DF_p" if isinstance(self.soil_type, CoarseSoil) \
        else "q_b = (6 * CU)  ÷ DF_p" 

        bearing_coefficients: list[EngRes] = [
            {
                "label": "Bearing capacity coefficient, Nq",
                "output": self.soil_type.bearing_capacity_coefficients.n_q,
                "si_unit": "",
                "formula_html": f"N_q =  {self.soil_type.bearing_capacity_coefficients.n_q}",
                "formula_xls": "N_q",
                "reference": "Table 3.10"
            },
            {
                "label": "Bearing capacity coefficient, Nc",
                "output": self.soil_type.bearing_capacity_coefficients.n_c,
                "si_unit": "",
                "formula_html": f"N_c =  {self.soil_type.bearing_capacity_coefficients.n_c}",
                "formula_xls": "N_c",
                "reference": "Table 3.10"
            },
            {
                "label": "Bearing capacity coefficient, Nγ",
                "output": self.soil_type.bearing_capacity_coefficients.n_y,
                "si_unit": "",
                "formula_html": f"N_γ =  {self.soil_type.bearing_capacity_coefficients.n_y}",
                "formula_xls": "N_γ",
                "reference": "Table 3.10"
            }
            ] if isinstance(self.soil_type, CoarseSoil) else [] 
        
        vertical_resistance_workflow: List[EngRes] = [
            {
                "label": "Thrust force (vertical component)",
                "output": self.thrust_force_vertical,
                "si_unit": "kN",
                "formula_html": f"T_z = 2 × P × π⁄4 × (D_O)² × sin(θ⁄2) = {self.thrust_force_vertical:.2f} kN",
                "formula_xls": "T = 2 * P * π/4 * (D_O)2 * sin(θ/2)",
                "reference": "Figure 2.3"
            },
            {
                "label": "Ultimate ground bearing resistance",
                "output": self.soil_type.ultimate_vertical_bearing_capacity,
                "si_unit": "kN/m2",
                "formula_html": f"{vertical_ground_bearing_formula_html} = {self.soil_type.ultimate_vertical_bearing_capacity:.2f} kN/m2",
                "formula_xls": vertical_ground_bearing_formula_xls,
                "reference": "Section 3.8.1"
            },
            {
                "label": "Vertical block resistance force",
                "output": self.vertical_block_resistance_force,
                "si_unit": "kN",
                "formula_html": f"Q_b = q_b × A_b = {self.vertical_block_resistance_force:.2f} kN",
                "formula_xls": "Q_b = q_b * A_b",
                "reference": "Section 4.1.4"
            },
            {
                "label": "vertical ground bearing resistance check",
                "output": self.vertical_bend_check,
                "si_unit": "",
                "formula_html": self.vertical_bend_check,
                "formula_xls": self.vertical_bend_check,
                "reference": ""
            }
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + bearing_coefficients + thrust_pass_through_res + vertical_resistance_workflow
    
@dataclass(frozen=True)
class VerticalDownturnBend(Fitting):
    outside_diameter: float
    angle: float      # degrees
    radius: float     # meters

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)

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
    def buoyancy_coefficient(self) -> float:
        """
        Returns buoyancy coefficient for a downturn bend
        """
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
        """
        Calculates the overturning lever arm for the thrust block based on fitting geometry.
        Returns 0 if no matching diameter attribute is found.
        """
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
            {
                "label": "Depth below ground to highest groundwater level",
                "output": self.soil_type.ground_water_level,
                "si_unit": "m",
                "formula_html": f"Z_GW = {self.soil_type.ground_water_level} m",
                "formula_xls": "Z_GW",
                "reference": " - "
            },
            {
                "label": "Depth to crown of larger pipe",
                "output": self.crown_depth,
                "si_unit": "m",
                "formula_html": f"Z_O = {self.crown_depth} m",
                "formula_xls": "Z_O",
                "reference": " - "
            },
            {
                "label": "Depth to base of block",
                "output": self.soil_type.thrust_block.depth,
                "si_unit": "m",
                "formula_html": f"Z_b = {self.soil_type.thrust_block.depth} m",
                "formula_xls": "Z_b",
                "reference": " - "
            },
            {
                "label": "Buoyancy coefficient",
                "output": self.soil_type.buoyancy_coefficient,
                "si_unit": "",
                "formula_html": f"C_GW = {self.buoyancy_coefficient:.2f} (groundwater level is at the base of the thrust block or above)",
                "formula_xls": "Z_O",
                "reference": "Section 3.5"
            },
            {
                "label": "Native soil type",
                "output": f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                "si_unit": "",
                "formula_html": f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                "formula_xls": f"{self.soil_type.soil_consistency.label} {self.soil_type.soil_type.label}",
                "reference": " - "
            },
            {
                "label": "Native soil unit weight",
                "output": self.soil_type.unit_weight,
                "si_unit": "kN/m3",
                "formula_html": f"γₛ = {self.soil_type.unit_weight} kN/m3",
                "formula_xls": "γ_s",
                "reference": "Table 3.5"
            },
                        {
                "label": "Reinforced concrete unit weight",
                "output": self.soil_type.thrust_block.reinforced_concrete_unit_weight,
                "si_unit": "kN/m3",
                "formula_html": f"γ_RC = {self.soil_type.thrust_block.reinforced_concrete_unit_weight} kN/m3",
                "formula_xls": "γ_RC",
                "reference": "Table 3.5"
            },
            {
                "label": "Groundwater unit weight",
                "output": UNIT_WEIGHT_WATER,
                "si_unit": "kN/m3",
                "formula_html": f"γ_W = {UNIT_WEIGHT_WATER} kN/m3",
                "formula_xls": "γ_W",
                "reference": "Table 3.5"
            },
        ]
    
    @property
    def thrust_block_over_turning_stability_check_workflow(self) -> List[EngRes]:

        overturning_stability_check = f"{self.safety_factor_against_overturning:.2f} > 1.5, Passes overturning stability check" \
        if self.safety_factor_against_overturning > 1.5 else \
        f"1.5 > {self.safety_factor_against_overturning:.2f}, Fails overturning stability check"     

        return [
            {
                "label": "Overturning moment lever arm",
                "output": self.overturning_level_arm,
                "si_unit": "m",
                "formula_html": f"H_c = Z_b − (Z_O + D_O⁄2) = {self.overturning_level_arm:.2f} m",
                "formula_xls": "H_c = Z_b - (Z_O + D_O/2)",
                "reference": "Section 3.9"
            },
            {
                "label": "Overturning moment",
                "output": self.over_turning_moment,
                "si_unit": "kNm",
                "formula_html": f"M_O = T_x × H_c = {self.over_turning_moment:.2f} kNm",
                "formula_xls": "M_O = T_x x H_c",
                "reference": "Section 3.9"
            },
            {
                "label": "Passive face restoring moment",
                "output": self.passive_face_restoring_moment,
                "si_unit": "kNm",
                "formula_html": f"M_p = σ_p × W × H²⁄3 = {self.passive_face_restoring_moment:.2f}kNm ",
                "formula_xls": "M_p = σ_pa * W * (H^2)/3",
                "reference": "Section 3.9"
            },
            {
                "label": "Net disturbing moment",
                "output": self.net_disturbing_moment,
                "si_unit": "kNm",
                "formula_html": f"M_d = M_o − M_p = {self.net_disturbing_moment:.2f} kNm",
                "formula_xls": "M_d = M_o - M_P",
                "reference": "Section 3.9"
            },
            {
                "label": "Vertical reaction of block",
                "output": self.vertical_reaction_block,
                "si_unit": "kNm",
                "formula_html": f"R_v = (γ_RC − (C_GW × γ_W)) × Z_b × W × L = {self.vertical_reaction_block:.2f} kN",
                "formula_xls": "R_v = (γ_s - (C_GW * γ_w)) * Z_b * H * L",
                "reference": "Section 3.9"
            },
            {
                "label": "Net vertical reaction of block",
                "output": self.net_vertical_reaction_block,
                "si_unit": "kNm",
                "formula_html": f"R_vₙₑₜ = R_v − T_z = {self.net_vertical_reaction_block:.2f} kN",
                "formula_xls": "R_v = T<sub>z</sub>R_v",
                "reference": "Section 4.1.5"
            },
            {
                "label": "Concrete block restoring moment",
                "output": f"{self.block_restoring_moment:.2f}",
                "si_unit": "kNm",
                "formula_html": f"M_R = R_vₙₑₜ × L⁄2 = {self.block_restoring_moment:.2f} kNm",
                "formula_xls": "M_R = R_v * L/2",
                "reference": "Section 3.9"
            },
            {
                "label": "Safety factor against overturning",
                "output": self.safety_factor_against_overturning,
                "si_unit": "m",
                "formula_html": f"SF_O = M_R ÷ M_d = {self.safety_factor_against_overturning:.2f}",
                "formula_xls": "SF_O = M_R / M_d",
                "reference": "Section 3.9"
            },
            {
                "label": "Overturning stability check",
                "output": overturning_stability_check,
                "si_unit": "",
                "formula_html": overturning_stability_check,
                "formula_xls": overturning_stability_check,
                "reference": " - "
            }
        ]

    @property
    def fitting_workflow_res(self) -> List[EngRes]:

        vertical_uplift_check = f"{self.uplift_factor_of_safety:.2f} > 1.5, Passes vertical uplift resistance" \
        if self.uplift_factor_of_safety > 1.5 else \
        f"1.5  > {self.uplift_factor_of_safety:.2f}, Fails vertical uplift resistance"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter",
                "output": self.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D_O = {self.outside_diameter}",
                "formula_xls": "D_O",
                "reference": ""
            },
            {
                "label": "Bend Angle",
                "output": self.angle,
                "si_unit": "°",
                "formula_html": f"θ = {self.angle}°",
                "formula_xls": "θ",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Disturbed passive area due to pipe trench",
                "output": self.area_disturbed_passive,
                "si_unit": "m",
                "formula_html": f"A_d = 1.5 × D_O × H = {self.area_disturbed_passive:.2f} m2",
                "formula_xls": "A_d",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Horizontal block resistance force",
                "output": self.block_resistance,
                "si_unit": "kN",
                "formula_html": f"R_s = (σ_pa × A_f) × (A_f − A_d) = {self.block_resistance:.2f} kN",
                "formula_xls": "R_s",
                "reference": "Figure 2.3"
            },
            {
                "label": "Thrust force (horizontal component)",
                "output": self.thrust_force_horizontal,
                "si_unit": "kN",
                "formula_html": f"T_x = P × π⁄4 × (D_O)² × (1 − cos(θ)) = {self.thrust_force_horizontal:.2f} kN",
                "formula_xls": "T_x = P * π/4 * D_O^2 * (1 - cos(θ))",
                "reference": "Section 4.1.5"
            },
            {
                "label": "Pass through resistance check",
                "output": self.thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{self.block_resistance:.2f} kN > {self.thrust_force_horizontal:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_horizontal:.2f} kN, Fail",
                "formula_xls": f"{self.block_resistance:.2f} kN > {self.thrust_force_horizontal:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_horizontal:.2f} kN, Fail",
                "reference": ""
            }
        ]

        vertical_uplift_workflow: List[EngRes] = [
            {
                "label": "Thrust force (vertical component)",
                "output": self.thrust_force_vertical,
                "si_unit": "kN",
                "formula_html": f" = {self.thrust_force_vertical:.2f} kN",
                "formula_xls": "T_Z = 2 * P * π/4 * (D_O)2 * sin(θ/2)",
                "reference": "Section 2.3"
            },
            {
                "label": "Effective weight of thrust block",
                "output": self.effective_weight_thrust_block,
                "si_unit": "m",
                "formula_html": f"T_z = 2 × P × π⁄4 × (D_O)² × sin(θ⁄2) = {self.effective_weight_thrust_block:.2f} kN/m2",
                "formula_xls": "W_T = H * W * L * (γ_RC - (C_GW - γ_W))",
                "reference": "Section 3.8.1"
            },
            {
                "label": "Uplift factor of safety",
                "output": self.uplift_factor_of_safety,
                "si_unit": "kN",
                "formula_html": f"F_s = W_T × T_z = {self.uplift_factor_of_safety:.2f}",
                "formula_xls": "Q_b = q_b * A_b",
                "reference": "Section 4.1.4"
            },
            {
                "label": "Uplift resistance check",
                "output": vertical_uplift_check,
                "si_unit": "",
                "formula_html": f"{vertical_uplift_check}",
                "formula_xls": f"{vertical_uplift_check}",
                "reference": ""
            }
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res + vertical_uplift_workflow + self.thrust_block_over_turning_stability_check_workflow

@dataclass(frozen=True)
class Tee(Fitting):
    outside_diameter_main: float
    outside_diameter_branch: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter_branch / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)

    @property
    def thrust_force_resultant(self) -> float:
        area_branch = (math.pi / 4) * self.outside_diameter_branch ** 2 
        return self.maximum_design_pressure * area_branch
    
    @property
    def area_disturbed_passive(self):
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
            {
                "label": "Ouside diameter of branch pipe",
                "output": self.outside_diameter_branch,
                "si_unit": "m",
                "formula_html": f"D_O_B = {self.outside_diameter_branch}",
                "formula_xls": "D_OB",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R_s = (σ_pa × A_f) + (𝜏_b × A_b) + [2 × 𝜏_s × A_S] = {self.block_resistance:.2f}",
                "formula_xls": "R_s = (σ_pa * A_f) + (𝜏_b * A_b) + [2 * 𝜏_s * A_S]",
                "reference": "Section 4.1.3"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P × π⁄4 × D_O_B² = {self.thrust_force_resultant:.2f} kN",
                "formula_xls": "T =  P * π/4 * (D_OB)^2",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "formula_xls": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "reference": ""
            }
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow

@dataclass(frozen=True)
class AngleBranch(Fitting):
    angle: float
    outside_diameter_main: float
    outside_diameter_branch: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter_branch / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)
    
    @property
    def over_turning_moment(self) -> float:
        # if isinstance(self.fitting, VerticalBend):
        #     return self.fitting.thrust_force_horizontal() * self.overturning_level_arm
        return self.thrust_force_resultant * self.overturning_level_arm
    
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
            {
                "label": "Ouside diameter of branch pipe",
                "output": self.outside_diameter_branch,
                "si_unit": "m",
                "formula_html": f"D_O_B = {self.outside_diameter_branch} m",
                "formula_xls": "D_OB",
                "reference": ""
            },
            {
                "label": "Ouside diameter of main pipe",
                "output": self.outside_diameter_main,
                "si_unit": "m",
                "formula_html": f"D_O_M = {self.outside_diameter_main} m",
                "formula_xls": "D_OM",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f" = {self.block_resistance:.2f} kN",
                "formula_xls": "R_s = (σ_pa * A_f) + (𝜏_b * A_b) + (2 * 𝜏_s)",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P x π/4 x D<sub>O_B</sub><sup>2</sup> = {self.thrust_force_resultant:.2f} kN",
                "formula_xls": "T = P * π/4 * D_OB^2",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": self.thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "formula_xls": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "reference": ""
            }
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow


@dataclass(frozen=True)
class ClosedValve(Fitting):
    outside_diameter: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)

    @property
    def thrust_force_resultant(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area
    
    @property
    def area_disturbed_passive(self) -> float:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth - self.soil_type.thrust_block.height > self.crown_depth:
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
        f"{self.thrust_force_resultant:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter",
                "output": f"{self.outside_diameter}",
                "si_unit": "m",
                "formula_html": f"D_O_B = {self.outside_diameter}",
                "formula_xls": "D_OB",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Disturbed passive area due to pipe trench",
                "output": self.area_disturbed_passive,
                "si_unit": "m",
                "formula_html": f"A_d = 1.5 × D_O × (H + D_O + Z_O − Z_b) = {self.area_disturbed_passive:.2f} m2",
                "formula_xls": "A_d",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R_s = σ_pa × (A_f − A_d) + (𝜏_b × A_b) + (2 × 𝜏_s × A_S) = {self.block_resistance:.2f} kN",
                "formula_xls": "R_s = σ_pa * (A_f - A_d) + (𝜏_b * A_b) + (2 * 𝜏_s * A_s)",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P × π⁄4 × D_O² = {self.thrust_force_resultant:.2f} kN",
                "formula_xls": "T = P * π/4 * (D_O)^2",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": self.thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "formula_xls": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "reference": ""
            }
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow


@dataclass(frozen=True)
class BlankEnd(Fitting):
    outside_diameter: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        area = math.pi * (self.outside_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)

    @property
    def thrust_force_resultant(self) -> float:
        area = math.pi * self.outside_diameter ** 2 / 4
        return self.maximum_design_pressure * area
    
    @property
    def area_disturbed_passive(self):
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth - self.soil_type.thrust_block.height > self.crown_depth:
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
            {
                "label": "Pipe outside diameter",
                "output": self.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D<sub>O</sub> = {self.outside_diameter} m",
                "formula_xls": "D_O = ",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Disturbed passive area due to pipe trench",
                "output": self.area_disturbed_passive,
                "si_unit": "m",
                "formula_html": f"A_d = 1.5 × D_O × (H + D_O + Z_O − Z_b) = {self.area_disturbed_passive:.2f} m2",
                "formula_xls": "A_d = ",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R_s = σ_pa × (A_f − A_d) + (𝜏_b × A_b) + (2 × 𝜏_s × A_S) = {self.block_resistance:.2f} kN",
                "formula_xls": "R_s = σ_pa * (A_f − A_d) + (𝜏_b * A_b) + (2 * 𝜏_s * A_S)",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P × π⁄4 × D_O² = {self.thrust_force_resultant:.2f} kN",
                "formula_xls": "T = P * π⁄4 * D_O^2 ",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": self.thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "formula_xls": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "reference": ""
            }
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow


@dataclass(frozen=True)
class TaperThrust(Fitting):
    outside_diameter_large: float
    outside_diameter_small: float

    def head_loss(self, flow_rate: float, k_factor: float = 0.5) -> float:
        average_diameter = (self.outside_diameter_large + self.outside_diameter_small) / 2
        area = math.pi * (average_diameter / 2) ** 2
        velocity = flow_rate / area
        return k_factor * (velocity ** 2) / (2 * 9.81)

    @property
    def thrust_force_resultant(self) -> float:
        area_large = math.pi * self.outside_diameter_large ** 2 / 4
        area_small = math.pi * self.outside_diameter_small ** 2 / 4
        return self.maximum_design_pressure * (area_large - area_small)
    
    @property
    def area_disturbed_passive(self):
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth - self.soil_type.thrust_block.height > self.crown_depth:
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
            {
                "label": "Pipe outside diameter – larger end",
                "output": self.outside_diameter_large,
                "si_unit": "m",
                "formula_html": f"D_O_A = {self.outside_diameter_large} m",
                "formula_xls": "D_OA = ",
                "reference": " - "
            },
            {
                "label": "Pipe outside diameter – smaller end",
                "output": self.outside_diameter_small,
                "si_unit": "m",
                "formula_html": f"DO_B = {self.outside_diameter_small} m",
                "formula_xls": "D_OB = ",
                "reference": " - "
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Disturbed passive area due to pipe trench",
                "output": self.area_disturbed_passive,
                "si_unit": "m",
                "formula_html": f"A_d = 1.5 × D_O_A × (H + D_O_A + Z_O − Z_b) = {self.area_disturbed_passive:.2f} m2",
                "formula_xls": "A_d = 1.5 * D_O_A * (H + D_O_A + Z_O − Z_b)",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R_s = σ_pa × (A_f − A_d) + (𝜏_b × A_b) + (2 × 𝜏_s × A_S) = {self.block_resistance:.2f} kN",
                "formula_xls": "R_s = σ_pa * (A_f − A_d) + (𝜏_b * A_b) + (2 * 𝜏_s * A_S)",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P × π⁄4 × ((D_O_A)² − (D_O_B)²) = {self.thrust_force_resultant:.2f} kN",
                "formula_xls": "T = P * π⁄4 * ((D_O_A)^2 − (D_O_B)^2) ",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": self.thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "formula_xls": f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Fail",
                "reference": " - "
            }
        ]
        return fitting_dims + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow
    
@dataclass(frozen=True)
class FlangedMetallicPipe(Fitting):
    embedment_type: Embedment

    @property
    def buoyancy_coefficient(self):
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return 1 - (self.soil_type.ground_water_level / self.soil_type.thrust_block.depth)
    
    @property
    def area_disturbed_passive(self):
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        if self.soil_type.thrust_block.depth - self.soil_type.thrust_block.height > self.crown_depth:
            return 0
        return 1.5 * self.embedment_type.pipe.outside_diameter \
            * (self.soil_type.thrust_block.height + self.embedment_type.pipe.outside_diameter + self.embedment_type.pipe.crown_depth - self.soil_type.thrust_block.depth)
    
    @property
    def block_resistance(self) -> float:
        return self.soil_type.net_unit_area_soil_pressure * (self.soil_type.area_passive_face - self.area_disturbed_passive) \
            + (self.soil_type.sliding_resistance_base() * self.soil_type.area_base_sliding) \
            + (2 * self.soil_type.sliding_resistance_side * self.soil_type.area_side_sliding)
    
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
            {
                "label": "Pipe outside diameter",
                "output": self.embedment_type.pipe.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D_O = {self.embedment_type.pipe.outside_diameter} m",
                "formula_xls": "D_O = ",
                "reference": " - "
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Disturbed passive area due to pipe trench",
                "output": self.area_disturbed_passive,
                "si_unit": "m",
                "formula_html": f"A_d = 1.5 × D_O_A × (H + D_O_A + Z_O − Z_b) = {self.area_disturbed_passive:.2f} m2",
                "formula_xls": "A_d = 1.5 * D_O_A * (H + D_O_A + Z_O − Z_b)",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R_s = σ_pa × (A_f − A_d) + (𝜏_b × A_b) + (2 × 𝜏_s × A_S) = {self.block_resistance:.2f} kN",
                "formula_xls": "R_s = ",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Design force",
                "output": self.embedment_type.contraction_design_force,
                "si_unit": "kN",
                "formula_html": f"F<sub>d</sub> = {self.embedment_type.contraction_design_force:.2f} kN",
                "formula_xls": "F_D",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": self.thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{self.block_resistance:.2f} kN > {self.embedment_type.contraction_design_force:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.embedment_type.contraction_design_force:.2f} kN, Fail",
                "formula_xls": f"{self.block_resistance:.2f} kN > {self.embedment_type.contraction_design_force:.2f} kN, Pass" if self.thrust_pass_through_check else f"{self.block_resistance:.2f} kN > {self.embedment_type.contraction_design_force:.2f} kN, Fail",
                "reference": " - "
            }
        ]
        return self.embedment_type.pipe.render_workflow_report + fitting_dims + self.embedment_type.render_workflow_report + self.thrust_block_standard_workflow + self.soil_type.soil_res + thrust_pass_through_res \
        + self.thrust_block_over_turning_stability_check_workflow
    
# --- Builder and Registry ---

BUILDERS: Dict[str, Callable[[Any], Fitting]] = {}

def register(fitting_key: str):
    """
    Decorator that registers a builder function for a fitting type.
    """
    def wrap(builder_fn: Callable[[Any], Fitting]):
        BUILDERS[fitting_key] = builder_fn
        return builder_fn
    return wrap

@register("horizontal_bend")
def build_horizontal_bend(params: Any) -> Fitting:
    s = params.fitting_section
    return HorizontalBend(
        maximum_design_pressure = s.maximum_design_pressure,
        crown_depth = s.crown_depth,
        soil_type=create_soil(params),
        outside_diameter = s.outside_diameter,
        angle = s.angle,
        radius = 0
    )

@register("vertical_upturn_bend")
def build_vertical_upturn_bend(params: Any) -> Fitting:
    s = params.fitting_section
    return VerticalUpturnBend(
        maximum_design_pressure = s.maximum_design_pressure,
        crown_depth = s.crown_depth,
        soil_type=create_soil(params),
        outside_diameter = s.outside_diameter,
        angle = s.angle,
        radius = 0,
    )

@register("vertical_downturn_bend")
def build_vertical_downturn_bend(params: Any) -> Fitting:
    s = params.fitting_section
    return VerticalDownturnBend(
        maximum_design_pressure = s.maximum_design_pressure,
        crown_depth = s.crown_depth,
        soil_type=create_soil(params),
        outside_diameter = s.outside_diameter,
        angle = s.angle,
        radius = 0,
    )

@register("tee")
def build_tee(params: Any) -> Fitting:
    s = params.fitting_section
    return Tee(
        maximum_design_pressure = s.maximum_design_pressure,
        crown_depth = s.crown_depth,
        soil_type=create_soil(params),
        outside_diameter_main = s.outside_diameter_main,
        outside_diameter_branch = s.outside_diameter_branch
    )

@register("angle_branch")
def build_angle_branch(params: Any) -> Fitting:
    s = params.fitting_section
    return AngleBranch(
        maximum_design_pressure = s.maximum_design_pressure,
        crown_depth = s.crown_depth,
        soil_type=create_soil(params),
        angle = s.angle,
        outside_diameter_main = s.outside_diameter_main,
        outside_diameter_branch = s.outside_diameter_branch
    )

@register("closed_valve")
def build_closed_valve(params: Any) -> Fitting:
    s = params.fitting_section
    return ClosedValve(
        maximum_design_pressure = s.maximum_design_pressure,
        crown_depth = s.crown_depth,
        soil_type=create_soil(params),
        outside_diameter = s.outside_diameter
    )

@register("blank_end")
def build_blank_end(params: Any) -> Fitting:
    s = params.fitting_section
    return BlankEnd(
        maximum_design_pressure = s.maximum_design_pressure,
        crown_depth = s.crown_depth,
        soil_type=create_soil(params),
        outside_diameter = s.outside_diameter
    )

@register("taper_thrust")
def build_taper_thrust(params: Any) -> Fitting:
    s = params.fitting_section
    return TaperThrust(
        maximum_design_pressure = s.maximum_design_pressure,
        crown_depth = s.crown_depth,
        soil_type=create_soil(params),
        outside_diameter_large = s.outside_diameter_large,
        outside_diameter_small = s.outside_diameter_small
    )

@register("metallic_flange")
def build_metallic_flange(params: Any) -> Fitting:
    s = params.pipe_section
    return FlangedMetallicPipe(
        maximum_design_pressure = s.maximum_design_pressure,
        crown_depth = s.crown_depth,
        soil_type=create_soil(params),
        embedment_type=create_embedment(params)
    )
#remove **kwargs
def fitting_from_params(params: Any, **kwargs) -> Fitting:
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
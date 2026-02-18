import math
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Dict, Tuple, List, Union
from app.civeng1.soils.soil_mechanics import Soil, EngRes, create_soil, UNIT_WEIGHT_WATER, CoarseSoil, FineSoil, CoarseEmbedment, FineEmbedment, Embedment, create_embedment
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

ReportRow = Tuple[str, str]
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
    def thrust_block_standard_workflow(self) -> List[EngRes]:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return [
            {
                "label": "Depth below ground to highest groundwater level",
                "output": self.soil_type.ground_water_level,
                "si_unit": "m",
                "formula_html": f"Z<sub>GW</sub> = {self.soil_type.ground_water_level} m",
                "formula_xls": "Z_GW",
                "reference": " - "
            },
            {
                "label": "Depth to crown of larger pipe",
                "output": self.crown_depth,
                "si_unit": "m",
                "formula_html": f"Z<sub>O</sub> = {self.crown_depth} m",
                "formula_xls": "Z_O",
                "reference": " - "
            },
            {
                "label": "Depth to base of block",
                "output": self.soil_type.thrust_block.depth,
                "si_unit": "m",
                "formula_html": f"Z<sub>b</sub> = {self.soil_type.thrust_block.depth} m",
                "formula_xls": "Z_b",
                "reference": " - "
            },
            {
                "label": "Buoyancy coefficient",
                "output": self.soil_type.buoyancy_coefficient,
                "si_unit": "",
                "formula_html": f"C<sub>GW</sub> = 1 - (Z<sub>GW</sub> ÷ Z<sub>b</sub>) = <b>{self.soil_type.buoyancy_coefficient:.2f}</b>",
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
                "formula_html": f"γ<sub>s</sub> = {self.soil_type.unit_weight} kN/m3",
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

        overturning_stability_check = f"<span style='color: green'><b>{self.safety_factor_against_overturning:.2f} > 1.5, Passes overturning stability check</b></span>" \
        if self.safety_factor_against_overturning > 1.5 else \
        f"<span style='color: red'><b>1.5 > {self.safety_factor_against_overturning:.2f} kN, Fails overturning stability check</b></span>"     

        return [
            {
                "label": "Overturning moment lever arm",
                "output": self.overturning_level_arm,
                "si_unit": "m",
                "formula_html": f"H<sub>c</sub> = Z<sub>b</sub> - (Z<sub>O</sub> + D<sub>O</sub>/2) = <b>{self.overturning_level_arm:.2f}</b> m",
                "formula_xls": "H_c = Z_b - (Z_O + D_O/2)",
                "reference": "Section 3.9"
            },
            {
                "label": "Overturning moment",
                "output": self.over_turning_moment,
                "si_unit": "kNm",
                "formula_html": f"M<sub>O</sub> = T x H<sub>c</sub> = <b>{self.over_turning_moment:.2f}</b> kNm",
                "formula_xls": "M_O = T x H_c",
                "reference": "Section 3.9"
            },
            {
                "label": "Passive face restoring moment",
                "output": self.passive_face_restoring_moment,
                "si_unit": "kNm",
                "formula_html": f"M<sub>p</sub> = σ<sub>pa</sub> x W x H<sup>2</sup>/3 = <b>{self.passive_face_restoring_moment:.2f}</b> kNm",
                "formula_xls": "M_p = σ_pa * W * (H^2)/3",
                "reference": "Section 3.9"
            },
            {
                "label": "Net disturbing moment",
                "output": self.block_resistance,
                "si_unit": "kNm",
                "formula_html": f"M<sub>d</sub> = M<sub>o</sub> – M<sub>p</sub> = <b>{self.block_resistance:.2f}</b> kNm",
                "formula_xls": "M_d = M_o - M_P",
                "reference": "Section 3.9"
            },
            {
                "label": "Vertical reaction of block",
                "output": self.vertical_reaction_block,
                "si_unit": "kN",
                "formula_html": f"R<sub>v</sub> = (γ<sub>s</sub> – (C<sub>GW</sub> x γ<sub>W</sub>)) x Z<sub>b</sub> x W x L = <b>{self.vertical_reaction_block:.2f}</b> kN",
                "formula_xls": "R_v = (γ_s - (C_GW * γ_w)) * Z_b * H * L",
                "reference": "Section 3.9"
            },
            {
                "label": "Concrete block restoring moment",
                "output": f"{self.block_restoring_moment}",
                "si_unit": "kNm",
                "formula_html": f"M<sub>R</sub> = R<sub>v</sub> x L/2 = <b>{self.block_restoring_moment:.2f}</b> kNm",
                "formula_xls": "M_R = R_v * L/2",
                "reference": "Section 3.9"
            },
            {
                "label": "Safety factor against overturning",
                "output": self.safety_factor_against_overturning,
                "si_unit": "m",
                "formula_html": f"SF<sub>O</sub> = M<sub>R</sub> ÷ M<sub>d</sub> = <b>{self.safety_factor_against_overturning:.2f}</b>",
                "formula_xls": "SF_O = M_R / M_d",
                "reference": "Section 3.9"
            },
            {
                "label": "Overturning stability check",
                "output": overturning_stability_check,
                "si_unit": " - ",
                "formula_html": overturning_stability_check,
                "formula_xls": "",
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
        thrust_pass_through_check = f"<span style='color: green'><b>{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance</b></span>" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"<span style='color: red'><b>{self.thrust_force_resultant:.2f} kN > {self.block_resistance:.2f} kN, Fails thrust resistance</b></span>"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter",
                "output": self.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D<sub>O</sub> = {self.outside_diameter}",
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
                "formula_html": f"R<sub>s</sub> = (σ<sub>pa</sub> x A<sub>f</sub>) + (𝜏<sub>b</sub> x A<sub>b</sub>) = <b>{self.block_resistance:.2f} kN</b>",
                "formula_xls": "R_s",
                "reference": "Section 4.1.3"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = 2 x P x π/4 x (D<sub>O</sub>)<sup>2</sup> x sin(θ/2) = <b>{self.thrust_force_resultant:.2f} kN</b>",
                "formula_xls": "T = 2 x P x π/4 x (D_O)2 x sin(θ/2)",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": thrust_pass_through_check,
                "formula_xls": "",
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
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"<span style='color: green'><b>{self.block_resistance:.2f} kN > {self.thrust_force_horizontal:.2f} kN, Passes thrust resistance</b></span>" \
        if self.block_resistance > self.thrust_force_horizontal else \
        f"<span style='color: red'><b>{self.thrust_force_resultant:.2f} kN > {self.block_resistance:.2f} kN, Fails thrust resistance</b></span></span>"

        vertical_ground_bearing_check = f"<span style='color: green'><b>{self.vertical_block_resistance_force:.2f} kN > {self.thrust_force_vertical:.2f} kN, Passes vertical ground bearing resistance</b></span>" \
        if self.vertical_block_resistance_force > self.thrust_force_vertical else \
        f"<span style='color: red'><b>{self.thrust_force_vertical:.2f} kN > {self.vertical_block_resistance_force:.2f} kN, Fails vertical ground bearing resistance</b></span>"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter",
                "output": self.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D<sub>O</sub> = {self.outside_diameter} m",
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
                "formula_html": f"R<sub>s</sub> = (σ<sub>pa</sub> x A<sub>f</sub>) + (𝜏<sub>b</sub> x A<sub>b</sub>) = <b>{self.block_resistance:.2f} kN</b>",
                "formula_xls": "R_s = (σ_pa * A_f) + (𝜏_b * A_b)",
                "reference": "Section 4.1.3"
            },
            {
                "label": "Thrust force (horizontal component)",
                "output": self.thrust_force_horizontal,
                "si_unit": "kN",
                "formula_html": f"T<sub>x</sub> = P x π/4 x (D<sub>O</sub>)<sup>2</sup> x (1 - cos(θ)) = <b>{self.thrust_force_horizontal:.2f} kN</b>",
                "formula_xls": "T_x = P * π/4 * D_O^2 * (1 - cos(θ))",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{thrust_pass_through_check}",
                "formula_xls": "",
                "reference": ""
            }
        ]
        
        vertical_ground_bearing_formula_html = "q<sub>b</sub> = (0.5 * (γ<sub>s</sub> - (C<sub>GW</sub> x γ<sub>w</sub>)) x B x N<sub>γ</sub>) + ((γ<sub>s</sub> - (C<sub>GW</sub> x γ<sub>w</sub>)) x (N<sub>q</sub> - 1) x Z<sub>b</sub>) ÷ DF<sub>P</sub>" \
        if isinstance(self.soil_type, CoarseSoil) else "q<sub>b</sub> = (6 x C<sub>U</sub>) ÷ DF<sub>P</sub>"
        vertical_ground_bearing_formula_xls = "q_b = (0.5 * (γ_s - (C_GW * γ_W)) * B * N_γ) + ((γ_S - (C_GW * γ_w) *(N_q - 1)* Z_b) ÷ DF_p" if isinstance(self.soil_type, CoarseSoil) \
        else "q_b = (6 * CU)  ÷ DF_p" 

        bearing_coefficients: list[EngRes] = [
            {
                "label": "Bearing capacity coefficient, Nq",
                "output": self.soil_type.bearing_capacity_coefficients.n_q,
                "si_unit": "",
                "formula_html": f"N<sub>q</sub> =  {self.soil_type.bearing_capacity_coefficients.n_q}",
                "formula_xls": "N_q",
                "reference": "Table 3.10"
            },
            {
                "label": "Bearing capacity coefficient, Nc",
                "output": self.soil_type.bearing_capacity_coefficients.n_c,
                "si_unit": "",
                "formula_html": f"N<sub>c</sub> =  {self.soil_type.bearing_capacity_coefficients.n_c}",
                "formula_xls": "N_c",
                "reference": "Table 3.10"
            },
            {
                "label": "Bearing capacity coefficient, Nγ",
                "output": self.soil_type.bearing_capacity_coefficients.n_y,
                "si_unit": "",
                "formula_html": f"N<sub>γ</sub> =  {self.soil_type.bearing_capacity_coefficients.n_y}",
                "formula_xls": "N_γ",
                "reference": "Table 3.10"
            }
            ] if isinstance(self.soil_type, CoarseSoil) else [] 
        
        vertical_resistance_workflow: List[EngRes] = [
            {
                "label": "Thrust force (vertical component)",
                "output": self.thrust_force_vertical,
                "si_unit": "kN",
                "formula_html": f"T<sub>z</sub> = 2 x P x π/4 x (D<sub>O</sub>)<sup>2</sup> x sin(θ/2) = <b>{self.thrust_force_vertical:.2f}</b> kN",
                "formula_xls": "T = 2 * P * π/4 * (D_O)2 * sin(θ/2)",
                "reference": "Figure 2.3"
            },
            {
                "label": "Ultimate ground bearing resistance",
                "output": self.soil_type.ultimate_vertical_bearing_capacity,
                "si_unit": "kN/m2",
                "formula_html": f"{vertical_ground_bearing_formula_html} = <b>{self.soil_type.ultimate_vertical_bearing_capacity:.2f} kN/m2</b>",
                "formula_xls": vertical_ground_bearing_formula_xls,
                "reference": "Section 3.8.1"
            },
            {
                "label": "Vertical block resistance force",
                "output": self.vertical_block_resistance_force,
                "si_unit": "kN",
                "formula_html": f"Q<sub>b</sub> = q<sub>b</sub> x A<sub>b</sub> = <b>{self.vertical_block_resistance_force:.2f} kN</b>",
                "formula_xls": "Q_b = q_b * A_b",
                "reference": "Section 4.1.4"
            },
            {
                "label": "vertical ground bearing resistance check",
                "output": vertical_ground_bearing_check,
                "si_unit": "",
                "formula_html": vertical_ground_bearing_check,
                "formula_xls": vertical_ground_bearing_check,
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
    def thrust_block_standard_workflow(self) -> List[EngRes]:
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
        return [
            {
                "label": "Depth below ground to highest groundwater level",
                "output": self.soil_type.ground_water_level,
                "si_unit": "m",
                "formula_html": f"Z<sub>GW</sub> = {self.soil_type.ground_water_level} m",
                "formula_xls": "Z_GW",
                "reference": " - "
            },
            {
                "label": "Depth to crown of larger pipe",
                "output": self.crown_depth,
                "si_unit": "m",
                "formula_html": f"Z<sub>O</sub> = {self.crown_depth} m",
                "formula_xls": "Z_O",
                "reference": " - "
            },
            {
                "label": "Depth to base of block",
                "output": self.soil_type.thrust_block.depth,
                "si_unit": "m",
                "formula_html": f"Z<sub>b</sub> = {self.soil_type.thrust_block.depth} m",
                "formula_xls": "Z_b",
                "reference": " - "
            },
            {
                "label": "Buoyancy coefficient",
                "output": self.soil_type.buoyancy_coefficient,
                "si_unit": "",
                "formula_html": f"C<sub>GW</sub> = {self.buoyancy_coefficient:.2f} (groundwater level is at the base of the thrust block or above)",
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
                "formula_html": f"γ<sub>s</sub> = {self.soil_type.unit_weight} kN/m3",
                "formula_xls": "γ_s",
                "reference": "Table 3.5"
            },
                        {
                "label": "Reinforced concrete unit weight",
                "output": self.soil_type.thrust_block.reinforced_concrete_unit_weight,
                "si_unit": "kN/m3",
                "formula_html": f"γ<sub>RC</sub> = {self.soil_type.thrust_block.reinforced_concrete_unit_weight} kN/m3",
                "formula_xls": "γ_RC",
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

        overturning_stability_check = f"<span style='color: green'><b>{self.safety_factor_against_overturning:.2f} > 1.5, Passes overturning stability check</b></span>" \
        if self.safety_factor_against_overturning > 1.5 else \
        f"<span style='color: red'><b>1.5 > {self.safety_factor_against_overturning:.2f} kN, Fails overturning stability check</b></span>"     

        return [
            {
                "label": "Overturning moment lever arm",
                "output": self.overturning_level_arm,
                "si_unit": "m",
                "formula_html": f"H<sub>c</sub> = Z<sub>b</sub> - (Z<sub>O</sub> + D<sub>O</sub>/2) = <b>{self.overturning_level_arm:.2f} m</b>",
                "formula_xls": "H_c = Z_b - (Z_O + D_O/2)",
                "reference": "Section 3.9"
            },
            {
                "label": "Overturning moment",
                "output": self.over_turning_moment,
                "si_unit": "kNm",
                "formula_html": f"M<sub>O</sub> = T<sub>x</sub> x H<sub>c</sub> = <b>{self.over_turning_moment:.2f} kNm</b>",
                "formula_xls": "M_O = T_x x H_c",
                "reference": "Section 3.9"
            },
            {
                "label": "Passive face restoring moment",
                "output": self.passive_face_restoring_moment,
                "si_unit": "kNm",
                "formula_html": f"M<sub>p</sub> = σ<sub>p</sub> x W x H<sup>2</sup>/3 = <b>{self.passive_face_restoring_moment:.2f}kNm</b> ",
                "formula_xls": "M_p = σ_pa * W * (H^2)/3",
                "reference": "Section 3.9"
            },
            {
                "label": "Net disturbing moment",
                "output": self.net_disturbing_moment,
                "si_unit": "kNm",
                "formula_html": f"M<sub>d</sub> = M<sub>o</sub> – M<sub>p</sub> = <b>{self.net_disturbing_moment:.2f} kNm</b>",
                "formula_xls": "M_d = M_o - M_P",
                "reference": "Section 3.9"
            },
            {
                "label": "Vertical reaction of block",
                "output": self.vertical_reaction_block,
                "si_unit": "kNm",
                "formula_html": f"R<sub>v</sub> = (γ<sub>RC</sub> – (C<sub>GW</sub> x γ<sub>W</sub>)) x Z<sub>b</sub> x W x L = <b>{self.vertical_reaction_block:.2f} kN</b>",
                "formula_xls": "R_v = (γ_s - (C_GW * γ_w)) * Z_b * H * L",
                "reference": "Section 3.9"
            },
                        {
                "label": "Net vertical reaction of block",
                "output": self.net_vertical_reaction_block,
                "si_unit": "kNm",
                "formula_html": f"R<sub>v_net</sub> = R<sub>v</sub> - T<sub>z</sub>= <b>{self.net_vertical_reaction_block:.2f} kN</b>",
                "formula_xls": "R_v = T<sub>z</sub>R_v",
                "reference": "Section 4.1.5"
            },
            {
                "label": "Concrete block restoring moment",
                "output": f"{self.block_restoring_moment:.2f}",
                "si_unit": "kNm",
                "formula_html": f"M<sub>R</sub> = R<sub>v_net</sub> x L/2 = <b>{self.block_restoring_moment:.2f} kNm</b>",
                "formula_xls": "M_R = R_v * L/2",
                "reference": "Section 3.9"
            },
            {
                "label": "Safety factor against overturning",
                "output": self.safety_factor_against_overturning,
                "si_unit": "m",
                "formula_html": f"SF<sub>O</sub> = M<sub>R</sub> ÷ M<sub>d</sub> = <b>{self.safety_factor_against_overturning:.2f}</b>",
                "formula_xls": "SF_O = M_R / M_d",
                "reference": "Section 3.9"
            },
            {
                "label": "Overturning stability check",
                "output": overturning_stability_check,
                "si_unit": "",
                "formula_html": f"{overturning_stability_check}",
                "formula_xls": "",
                "reference": " - "
            }
        ]

    @property
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"<span style='color: green'><b>{self.block_resistance:.2f} > {self.thrust_force_horizontal:.2f}, Passes thrust resistance</b></span>" \
        if self.block_resistance > self.thrust_force_horizontal else \
        f"<span style='color: red'><b>{self.thrust_force_horizontal:.2f} > {self.block_resistance:.2f}, Fails thrust resistance</b></span>"

        vertical_uplift_check = f"<span style='color: green'><b>{self.uplift_factor_of_safety:.2f} > 1.5, Passes vertical uplift resistance</b></span>" \
        if self.uplift_factor_of_safety > 1.5 else \
        f"<span style='color: red'><b>1.5  > {self.uplift_factor_of_safety:.2f}, Fails vertical uplift resistance</b></span>"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter",
                "output": self.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D<sub>O</sub> = {self.outside_diameter}",
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
                "formula_html": f"A<sub>d</sub> = 1.5 x D<sub>O</sub> x H = <b>{self.area_disturbed_passive:.2f} m2</b>",
                "formula_xls": "A_d",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Horizontal block resistance force",
                "output": self.block_resistance,
                "si_unit": "kN",
                "formula_html": f"R<sub>s</sub> = (σ<sub>pa</sub> x A<sub>f</sub>) x (A<sub>f</sub> - A<sub>d</sub>) = <b>{self.block_resistance:.2f} kN</b>",
                "formula_xls": "R_s",
                "reference": "Figure 2.3"
            },
            {
                "label": "Thrust force (horizontal component)",
                "output": self.thrust_force_horizontal,
                "si_unit": "kN",
                "formula_html": f"T<sub>x</sub> = P x π/4 x (D<sub>O</sub>)<sup>2</sup> x (1 - cos(θ)) = <b>{self.thrust_force_horizontal:.2f} kN</b>",
                "formula_xls": "T_x = P * π/4 * D_O^2 * (1 - cos(θ))",
                "reference": "Section 4.1.5"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{thrust_pass_through_check}",
                "formula_xls": "",
                "reference": ""
            }
        ]

        vertical_uplift_workflow: List[EngRes] = [
            {
                "label": "Thrust force (vertical component)",
                "output": self.thrust_force_vertical,
                "si_unit": "kN",
                "formula_html": f"T<sub>z</sub> = 2 x P x π/4 x (D<sub>O</sub>)<sup>2</sup> x sin(θ/2) = <b>{self.thrust_force_vertical:.2f} kN</b>",
                "formula_xls": "T_Z = 2 * P * π/4 * (D_O)2 * sin(θ/2)",
                "reference": "Section 2.3"
            },
            {
                "label": "Effective weight of thrust block",
                "output": self.effective_weight_thrust_block,
                "si_unit": "m",
                "formula_html": f"W<sub>T</sub> = H x W x L x (γ<sub>RC</sub> – (C<sub>GW</sub> x γ<sub>W</sub>)) = <b>{self.effective_weight_thrust_block:.2f} kN/m2</b>",
                "formula_xls": "W_T = H * W * L * (γ_RC - (C_GW - γ_W))",
                "reference": "Section 3.8.1"
            },
            {
                "label": "Uplift factor of safety",
                "output": self.uplift_factor_of_safety,
                "si_unit": "kN",
                "formula_html": f"F<sub>s</sub> = W<sub>T</sub> x T<sub>z</sub> = {self.uplift_factor_of_safety:.2f}",
                "formula_xls": "Q_b = q_b * A_b",
                "reference": "Section 4.1.4"
            },
            {
                "label": "Uplift resistance check",
                "output": vertical_uplift_check,
                "si_unit": "",
                "formula_html": f"<b>{vertical_uplift_check}</b>",
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
        area_branch = math.pi * self.outside_diameter_branch ** 2 / 4
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
        thrust_pass_through_check = f"<span style='color: green'><b>{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance</b></span>" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"<span style='color: red'><b>{self.thrust_force_resultant:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance</b></span>"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Ouside diameter of branch pipe",
                "output": self.outside_diameter_branch,
                "si_unit": "m",
                "formula_html": f"D<sub>O_B</sub> = {self.outside_diameter_branch}",
                "formula_xls": "D_OB",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R<sub>s</sub> = (σ<sub>pa</sub> x A<sub>f</sub>) + (𝜏<sub>b</sub> x A<sub>b</sub>) + (2 x 𝜏<sub>s</sub> x A<sub>S</sub>) = {self.block_resistance:.2f}",
                "formula_xls": "R_s",
                "reference": "Section 4.1.3"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P x π/4 x D<sub>O_B</sub><sup>2</sup> = <b>{self.thrust_force_resultant:.2f} kN</b>",
                "formula_xls": "T =  P * π/4 * (D_OB)^2",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{thrust_pass_through_check}",
                "formula_xls": "",
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
        thrust_pass_through_check = f"<span style='color: green'><b>{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance</b></span>" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"<span style='color: red'><b>{self.thrust_force_resultant:.2f} kN > {self.block_resistance:.2f} kN, Fails thrust resistance</b></span>"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Ouside diameter of branch pipe",
                "output": self.outside_diameter_branch,
                "si_unit": "m",
                "formula_html": f"D<sub>O_B</sub> = {self.outside_diameter_branch} m",
                "formula_xls": "D_OB",
                "reference": ""
            },
            {
                "label": "Ouside diameter of main pipe",
                "output": self.outside_diameter_main,
                "si_unit": "m",
                "formula_html": f"D<sub>O_B</sub> = {self.outside_diameter_main} m",
                "formula_xls": "D_OM",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R<sub>s</sub> = (σ<sub>pa</sub> x A<sub>f</sub>) + (𝜏<sub>b</sub> x A<sub>b</sub>) + (2 x 𝜏<sub>s</sub> x A<sub>S</sub>) = <b>{self.block_resistance:.2f} kN</b>",
                "formula_xls": "R_s = (σ_pa * A_f) + (𝜏_b * A_b) + (2 * 𝜏_s)",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P x π/4 x D<sub>O_B</sub><sup>2</sup> = <b>{self.thrust_force_resultant:.2f} kN</b>",
                "formula_xls": "T = P * π/4 * D_OB^2",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{thrust_pass_through_check}",
                "formula_xls": "",
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
    def area_disturbed_passive(self):
        if self.soil_type.thrust_block is None:
            raise ValueError("Thrust Block not implemented")
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
        thrust_pass_through_check = f"<span style='color: green'><b>{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance</b></span>" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"<span style='color: red'><b>{self.thrust_force_resultant:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance</b></span>"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter",
                "output": f"{self.outside_diameter}",
                "si_unit": "m",
                "formula_html": "D<sub>O_B</sub> = ",
                "formula_xls": "D_OB",
                "reference": ""
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Disturbed passive area due to pipe trench",
                "output": self.area_disturbed_passive,
                "si_unit": "m",
                "formula_html": f"A<sub>d</sub> = 1.5 x D<sub>O</sub> x (H + D<sub>O</sub> + Z<sub>O</sub> - Z<sub>b</sub>) = <b>{self.area_disturbed_passive:.2f} m2</b>",
                "formula_xls": "A_d",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R<sub>s</sub> = σ<sub>pa</sub> x (A<sub>f</sub> – A<sub>d</sub>) + (𝜏<sub>b</sub> x A<sub>b</sub>) + (2 x 𝜏<sub>s</sub> x A<sub>S</sub>) = <b>{self.block_resistance:.2f} kN</b>",
                "formula_xls": "R_s = σ_pa * (A_f - A_d) + (𝜏_b * A_b) + (2 * 𝜏_s * A_s)",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P x π/4 x D<sub>O</sub><sup>2</sup> = <b>{self.thrust_force_resultant:.2f} kN</b>",
                "formula_xls": "T = P * π/4 * (D_O)^2",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{thrust_pass_through_check}",
                "formula_xls": "",
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
        thrust_pass_through_check = f"<span style='color: green'><b>{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance</b></span>" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"<span style='color: red'><b>{self.thrust_force_resultant:.2f} kN > {self.block_resistance:.2f} kN, Fails thrust resistance</b></span></span>"
        
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
                "formula_html": f"A<sub>d</sub> = 1.5 x D<sub>O</sub> x (H + D<sub>O</sub> + Z<sub>O</sub> - Z<sub>b</sub>) = <b>{self.area_disturbed_passive:.2f} m2</b>",
                "formula_xls": "A_d = ",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R<sub>s</sub> = σ<sub>pa</sub> x (A<sub>f</sub> – A<sub>d</sub>) + (𝜏<sub>b</sub> x A<sub>b</sub>) + (2 x 𝜏<sub>s</sub> x A<sub>S</sub>) = <b>{self.block_resistance:.2f} kN</b>",
                "formula_xls": "R_s = ",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P x π/4 x D<sub>O</sub><sup>2</sup> = <b>{self.thrust_force_resultant:.2f} kN</b>",
                "formula_xls": "T = P * A ",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{thrust_pass_through_check}",
                "formula_xls": "",
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
        thrust_pass_through_check = f"<span style='color: green'><b>{self.block_resistance:.2f} kN > {self.thrust_force_resultant:.2f} kN, Passes thrust resistance</b></span>" \
        if self.block_resistance > self.thrust_force_resultant else \
        f"<span style='color: red'><b>{self.thrust_force_resultant:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance</b></span>"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter – larger end",
                "output": self.outside_diameter_large,
                "si_unit": "m",
                "formula_html": f"D<sub>O_A</sub> = {self.outside_diameter_large} m",
                "formula_xls": "D_OA = ",
                "reference": " - "
            },
            {
                "label": "Pipe outside diameter – smaller end",
                "output": self.outside_diameter_small,
                "si_unit": "m",
                "formula_html": f"D<sub>O_B</sub> = {self.outside_diameter_small} m",
                "formula_xls": "D_OB = ",
                "reference": " - "
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Disturbed passive area due to pipe trench",
                "output": self.area_disturbed_passive,
                "si_unit": "m",
                "formula_html": f"A<sub>d</sub> = 1.5 x D<sub>O_A</sub> x (H + D<sub>O_A</sub> + Z<sub>O</sub> - Z<sub>b</sub>) = <b>{self.area_disturbed_passive:.2f} m2</b>",
                "formula_xls": "A_d = ",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R<sub>s</sub> = σ<sub>pa</sub> x (A<sub>f</sub> – A<sub>d</sub>) + (𝜏<sub>b</sub> x A<sub>b</sub>) + (2 x 𝜏<sub>s</sub> x A<sub>S</sub>) = <b>{self.block_resistance:.2f} kN</b>",
                "formula_xls": "R_s = ",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Thrust force",
                "output": self.thrust_force_resultant,
                "si_unit": "m",
                "formula_html": f"T = P x π/4 x ((D<sub>O_A</sub>)<sup>2</sup> - (D<sub>O_B</sub>)<sup>2</sup>) = <b>{self.thrust_force_resultant:.2f} kN</b>",
                "formula_xls": "T = 2 x P x π/4 x (D_O)2 x sin(θ/2) ",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{thrust_pass_through_check}",
                "formula_xls": "",
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
    def fitting_workflow_res(self) -> List[EngRes]:
        thrust_pass_through_check = f"<span style='color: green'><b>{self.block_resistance:.2f} kN > {self.embedment_type.contraction_design_force:.2f} kN, Passes thrust resistance</b></span>" \
        if self.block_resistance > self.embedment_type.contraction_design_force else \
        f"<span style='color: red'><b>{self.embedment_type.contraction_design_force:.2f} kN> {self.block_resistance:.2f} kN, Fails thrust resistance</b></span>"
        
        fitting_dims: List[EngRes] = [
            {
                "label": "Pipe outside diameter",
                "output": self.embedment_type.pipe.outside_diameter,
                "si_unit": "m",
                "formula_html": f"D<sub>O</sub> = {self.embedment_type.pipe.outside_diameter} m",
                "formula_xls": "D_OB = ",
                "reference": " - "
            },
        ]
        thrust_pass_through_res: List[EngRes] = [
            {
                "label": "Disturbed passive area due to pipe trench",
                "output": self.area_disturbed_passive,
                "si_unit": "m",
                "formula_html": f"A<sub>d</sub> = 1.5 x D<sub>O_A</sub> x (H + D<sub>O_A</sub> + Z<sub>O</sub> - Z<sub>b</sub>) = <b>{self.area_disturbed_passive:.2f} m2</b>",
                "formula_xls": "A_d = ",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Block resistance force",
                "output": self.block_resistance,
                "si_unit": "m",
                "formula_html": f"R<sub>s</sub> = σ<sub>pa</sub> x (A<sub>f</sub> – A<sub>d</sub>) + (𝜏<sub>b</sub> x A<sub>b</sub>) + (2 x 𝜏<sub>s</sub> x A<sub>S</sub>) = <b>{self.block_resistance:.2f} kN</b>",
                "formula_xls": "R_s = ",
                "reference": "Section 4.1.1"
            },
            {
                "label": "Design force",
                "output": self.embedment_type.contraction_design_force,
                "si_unit": "kN",
                "formula_html": f"F<sub>d</sub> = <b>{self.embedment_type.contraction_design_force:.2f} kN</b>",
                "formula_xls": "F_D",
                "reference": "Figure 2.3"
            },
            {
                "label": "Pass through resistance check",
                "output": thrust_pass_through_check,
                "si_unit": "",
                "formula_html": f"{thrust_pass_through_check}",
                "formula_xls": "",
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
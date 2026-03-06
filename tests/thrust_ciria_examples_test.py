import pytest
import unittest
from app.civeng1.soils.soil_mechanics import CoarseEmbedment, FineEmbedment, CoarseSoil, FineSoil, UNIT_WEIGHT_WATER
from app.civeng1.soils.soil_enum import SoilCategory, SoilConsistency, SoilType, WaterCondition, EmbedmentCategory, EmbedmentClass
from app.civeng1.hydraulics.fittings import HorizontalBend, VerticalDownturnBend, VerticalUpturnBend, TaperThrust, FlangedMetallicPipe
from app.civeng1.hydraulics.pipes import WeldedPePipe, PipeMaterial
from app.civeng1.structures.concrete import ThrustBlock
from app.civeng1.calculations.thrust_block_calculation import (
    HorizontalBendThrustBlock,
    VerticalDownturnBendThrustBlock,
    VerticalUpturnBendThrustBlock,
    TaperThrustThrustBlock,
    FlangedMetallicPipeThrustBlock
)

#--- Factory method for thrust block creation


def create_thrust_block(
        height,
        width,
        length,
        depth,
        user_effective_depth,
        user_effective_height
    ):
        return ThrustBlock(
            height=height,
            width=width,
            length=length,
            depth=depth,
            user_effective_depth=user_effective_depth,
            user_effective_height=user_effective_height
        )


#--- Test for  Ciria C816, Example 8.1.1

MediumDenseGravel = CoarseSoil(
            soil_type=SoilType.GRAVEL,
            soil_consistency=SoilConsistency.MEDIUM_DENSE,
            water_condition=WaterCondition.BELOW_WATER,
            ground_water_level=0.8,
            soil_passive_factor=3,
            soil_sliding_factor=2.25,
            soil_category=SoilCategory.COARSE,
            thrust_block=create_thrust_block(height=1.8, width=3.5, length=2.5, depth=2.3, user_effective_depth=None, user_effective_height=None),
            friction_angle=33
        )

taper_component = TaperThrust(
            outside_diameter_large=0.63,
            outside_diameter_small=0.43
        )

taper_thrust_example = TaperThrustThrustBlock(
            maximum_design_pressure=1200,
            crown_depth=1,
            soil_type=MediumDenseGravel,
            component=taper_component
        )
        
def test_taper_example():
    soil = taper_thrust_example.soil_type
    assert soil.buoyancy_coefficient == pytest.approx(0.65, rel=1e-2)
    assert soil.unit_weight == pytest.approx(20.5, rel=1e-1)
    if isinstance(soil, CoarseSoil):
        assert soil.friction_angle == pytest.approx(33, rel=1e-1)
        assert soil.coefficient_passive_earth_pressure == pytest.approx(3.392, rel=1e-3)
        assert soil.coefficient_active_earth_pressure == pytest.approx(0.295, rel=1e-3)
        assert soil.net_unit_area_soil_pressure == pytest.approx(20.2, rel=1e-1)
        assert soil.sliding_resistance_base() == pytest.approx(9.3, rel=1e-1)
        assert soil.sliding_resistance_side == pytest.approx(1.7, rel=1e-1)
        assert soil.area_passive_face == pytest.approx(6.3, rel=1e-1)
        assert soil.area_base_sliding == pytest.approx(8.8, rel=1e-1)
        assert soil.area_side_sliding == pytest.approx(4.5, rel=1e-1)
    assert taper_thrust_example.area_disturbed_passive == pytest.approx(1.1, rel=1e-1)
    assert taper_thrust_example.block_resistance == pytest.approx(201.9, rel=1e-1)
    assert taper_thrust_example.thrust_force_resultant == pytest.approx(199.8, rel=1e-1)
    assert taper_thrust_example.overturning_level_arm == pytest.approx(1, rel=1e-1)
    assert taper_thrust_example.over_turning_moment == pytest.approx(196.8, rel=1e-1)
    assert taper_thrust_example.passive_face_restoring_moment == pytest.approx(76.4, rel=1e-1)
    assert taper_thrust_example.vertical_reaction_block == pytest.approx(281.3, rel=1e-1)
    assert taper_thrust_example.block_restoring_moment == pytest.approx(351.6, rel=1e-1)
    assert taper_thrust_example.safety_factor_against_overturning == pytest.approx(2.9,  rel=1e-1)

# --- Test for  Ciria C816, Example 8.1.2

FirmClay = FineSoil(
            soil_type=SoilType.CLAY,
            soil_consistency=SoilConsistency.FIRM,
            water_condition=WaterCondition.BELOW_WATER,
            ground_water_level=0.8,
            soil_passive_factor=3,
            soil_sliding_factor=2.25,
            soil_category=SoilCategory.FINE,
            thrust_block=create_thrust_block(height=1.6, width=2.5, length=2.8, depth=2.1, user_effective_depth=None, user_effective_height=None),
            undrained_shear_strength=50
        )

horizontal_bend_component = HorizontalBend(
            outside_diameter=0.63,
            angle=45
        )

horizontal_bend_example = HorizontalBendThrustBlock(
            maximum_design_pressure=1200,
            crown_depth=1,
            soil_type=FirmClay,
            component=horizontal_bend_component
        )

def test_horizontal_bend():
    soil = horizontal_bend_example.soil_type
    assert soil.buoyancy_coefficient == pytest.approx(0.62, rel=1e-2)
    assert soil.unit_weight == pytest.approx(18.5, rel=1e-1)
    if isinstance(soil, FineSoil):
        assert soil.undrained_shear_strength == pytest.approx(50, rel=1e-1)
        assert soil.net_unit_area_soil_pressure == pytest.approx(33.3, rel=1e-1)
        assert soil.sliding_resistance_base() == pytest.approx(22.2, rel=1e-1)
        assert soil.sliding_resistance_side == pytest.approx(0, rel=1e-1)
        assert soil.area_passive_face == pytest.approx(4, rel=1e-1)
        assert soil.area_base_sliding == pytest.approx(7, rel=1e-1)
        assert soil.area_side_sliding == pytest.approx(0, rel=1e-1)
    assert horizontal_bend_example.area_disturbed_passive == pytest.approx(0, rel=1e-1)
    assert horizontal_bend_example.block_resistance == pytest.approx(288.9, rel=1e-1)
    assert horizontal_bend_example.thrust_force_resultant == pytest.approx(286.3, rel=1e-1)
    assert horizontal_bend_example.overturning_level_arm == pytest.approx(0.8, rel=1e-1)
    assert horizontal_bend_example.over_turning_moment == pytest.approx(224.7, rel=1e-1)
    assert horizontal_bend_example.passive_face_restoring_moment == pytest.approx(71.1, rel=1e-1)
    assert horizontal_bend_example.vertical_reaction_block == pytest.approx(181.0, rel=1e-1)
    assert horizontal_bend_example.block_restoring_moment == pytest.approx(253.3, rel=1e-1)
    assert horizontal_bend_example.safety_factor_against_overturning == pytest.approx(1.6,  rel=1e-1)

# --- Test for Ciria C816, Example 8.1.3

FirmClay = FineSoil(
            soil_type=SoilType.CLAY,
            soil_consistency=SoilConsistency.FIRM,
            water_condition=WaterCondition.BELOW_WATER,
            ground_water_level=0.8,
            soil_passive_factor=3,
            soil_sliding_factor=2.25,
            soil_category=SoilCategory.FINE,
            thrust_block=create_thrust_block(height=1.2, width=1.6, length=1.7, depth=2.2, user_effective_depth=None, user_effective_height=None),
            undrained_shear_strength=50
        )

vertical_upturn_bend_component = VerticalUpturnBend(
            outside_diameter=0.63,
            angle=45,
            radius=0
        )

vertical_upturn_bend_example = VerticalUpturnBendThrustBlock(
            maximum_design_pressure=1200,
            crown_depth=1,
            soil_type=FirmClay,
            component=vertical_upturn_bend_component
        )

def test_vertical_upturn_bend():
    soil = vertical_upturn_bend_example.soil_type
    assert soil.buoyancy_coefficient == pytest.approx(0.64, rel=1e-2)
    assert soil.unit_weight == pytest.approx(18.5, rel=1e-1)
    if isinstance(soil, FineSoil):
        assert soil.undrained_shear_strength == pytest.approx(50, rel=1e-1)
        assert soil.net_unit_area_soil_pressure == pytest.approx(33.3, rel=1e-1)
        assert soil.sliding_resistance_base() == pytest.approx(22.2, rel=1e-1)
        assert soil.sliding_resistance_side == pytest.approx(0, rel=1e-1)
        assert soil.area_passive_face == pytest.approx(1.9, rel=1e-1)
        assert soil.area_base_sliding == pytest.approx(2.7, rel=1e-1)
        assert soil.area_side_sliding == pytest.approx(0, rel=1e-1)
    assert vertical_upturn_bend_example.area_disturbed_passive == pytest.approx(0, rel=1e-1)
    assert vertical_upturn_bend_example.block_resistance == pytest.approx(124.4, rel=1e-1)
    assert vertical_upturn_bend_example.thrust_force_horizontal == pytest.approx(109.6, rel=1e-1)
    assert vertical_upturn_bend_example.thrust_force_vertical == pytest.approx(264.5, rel=1e-1)
    assert soil.ultimate_vertical_bearing_capacity == pytest.approx(100, rel=1e-1)
    assert vertical_upturn_bend_example.vertical_block_resistance_force == pytest.approx(272, rel=1e-1)

# --- Test for Ciria C816, Example 8.1.4

FirmClay = FineSoil(
            soil_type=SoilType.CLAY,
            soil_consistency=SoilConsistency.FIRM,
            water_condition=WaterCondition.BELOW_WATER,
            ground_water_level=0.8,
            soil_passive_factor=3,
            soil_sliding_factor=2.25,
            soil_category=SoilCategory.FINE,
            thrust_block=create_thrust_block(height=2, width=3, length=4.5, depth=2.5, user_effective_depth=None, user_effective_height=None),
            undrained_shear_strength=40
        )

vertical_downturn_bend_component = VerticalDownturnBend(
            outside_diameter=0.63,
            angle=45,
            radius=0
        )

vertical_downturn_bend_example = VerticalDownturnBendThrustBlock(
            maximum_design_pressure=1200,
            crown_depth=1,
            soil_type=FirmClay,
            component=vertical_downturn_bend_component
        )

def test_vertical_downturn_bend():
    soil = vertical_downturn_bend_example.soil_type
    assert vertical_downturn_bend_example.buoyancy_coefficient == pytest.approx(1, rel=1e-2)
    assert soil.unit_weight == pytest.approx(18.5, rel=1e-1)
    if isinstance(soil, FineSoil):
        assert soil.undrained_shear_strength == pytest.approx(40, rel=1e-1)
        assert soil.net_unit_area_soil_pressure == pytest.approx(26.7, rel=1e-1)
        assert soil.sliding_resistance_base(True) == pytest.approx(0, rel=1e-1)
        assert soil.sliding_resistance_side == pytest.approx(0, rel=1e-1)
        assert soil.area_passive_face == pytest.approx(6, rel=1e-1)
        assert soil.area_base_sliding == pytest.approx(13.5, rel=1e-1)
        assert soil.area_side_sliding == pytest.approx(0, rel=1e-1)
    assert vertical_downturn_bend_example.area_disturbed_passive == pytest.approx(1.9, rel=1e-1)
    assert vertical_downturn_bend_example.block_resistance == pytest.approx(109.6, rel=1e-1)
    assert vertical_downturn_bend_example.thrust_force_horizontal == pytest.approx(109.6, rel=1e-1)
    assert vertical_downturn_bend_example.thrust_force_vertical == pytest.approx(264.5, rel=1e-1)
    assert vertical_downturn_bend_example.effective_weight_thrust_block == pytest.approx(405, rel=1e-1)
    assert vertical_downturn_bend_example.uplift_factor_of_safety == pytest.approx(1.53, rel=1e-1)
    assert vertical_downturn_bend_example.overturning_level_arm == pytest.approx(1.2, rel=1e-1)
    assert vertical_downturn_bend_example.over_turning_moment == pytest.approx(129.8, rel=1e-1)
    assert vertical_downturn_bend_example.passive_face_restoring_moment == pytest.approx(106.7, rel=1e-1)
    assert vertical_downturn_bend_example.net_disturbing_moment == pytest.approx(23.2, rel=1e-1)
    assert vertical_downturn_bend_example.vertical_reaction_block == pytest.approx(405, rel=1e-1)
    assert vertical_downturn_bend_example.net_vertical_reaction_block == pytest.approx(140.5, rel=1e-1)
    assert vertical_downturn_bend_example.block_restoring_moment == pytest.approx(316.1, rel=1e-1)
    assert vertical_downturn_bend_example.safety_factor_against_overturning == pytest.approx(13.6, rel=1e-1)

# --- Test for Ciria C816, Example 8.1.8

pe_pipe = WeldedPePipe(
    maximum_design_pressure=1200,
    outside_diameter=0.71,
    crown_depth=1,
    length=200,
    pipe_material=PipeMaterial.PE_PIPE,
    standard_dimension_ratio=17,
    poisson_ratio=0.38,
    thermal_coefficient=0.00013,
    temperature_reduction=10,
    elastic_modulus=712000,
    allowable_contraction_movement=0.005,
)

coarse_embedment = CoarseEmbedment(
    ground_water_level=0.8,
    pipe=pe_pipe,
    backfill_soil=MediumDenseGravel,
    compaction_class="Compacted sands and gravels (85%)",
    embedment_class=EmbedmentClass.S_THREE
)

native_medium_dense_gravel = CoarseSoil(
            soil_type=SoilType.GRAVEL,
            soil_consistency=SoilConsistency.MEDIUM_DENSE,
            water_condition=WaterCondition.BELOW_WATER,
            ground_water_level=0.8,
            soil_passive_factor=3,
            soil_sliding_factor=2.25,
            soil_category=SoilCategory.COARSE,
            thrust_block=create_thrust_block(height=2.35, width=4, length=3, depth=2.85, user_effective_depth=None, user_effective_height=None),
            friction_angle=33
        )

flanged_metallic_pipe_component = FlangedMetallicPipe(
            embedment_type=coarse_embedment
        )

flanged_metallic_pipe_example = FlangedMetallicPipeThrustBlock(
            maximum_design_pressure=1200,
            crown_depth=1,
            soil_type=native_medium_dense_gravel,
            component=flanged_metallic_pipe_component
        )

def test_metallic_flange_bend():
    soil = flanged_metallic_pipe_example.soil_type
    assert flanged_metallic_pipe_example.embedment_type.pipe.hoop_stress == pytest.approx(9600, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.liquid_pressure_longitudinal_stress == pytest.approx(3648, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.liquid_pressure_long_longitudinal_force == pytest.approx(319.8, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.temperature_longitudinal_strain == pytest.approx(0.00130, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.temperature_longitudinal_stress == pytest.approx(925.6, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.temperature_longitudinal_force == pytest.approx(81.2, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.fixed_end_contraction_force == pytest.approx(401, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.allowable_contraction_movement == pytest.approx(0.005, rel=1e-2)
    if isinstance(flanged_metallic_pipe_example.embedment_type, CoarseEmbedment):
        assert flanged_metallic_pipe_example.embedment_type.effective_angle_shearing_resistance == pytest.approx(36, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.friction_reduction_factor == pytest.approx(0.8, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.backfill_soil.unit_weight == pytest.approx(20.5, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.pipe.pipe_material_factor == pytest.approx(0.8, rel=1e-1)
        assert flanged_metallic_pipe_example.embedment_type.embedment_sliding_resistance_factor == pytest.approx(2, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.buoyancy_coefficient == pytest.approx(0.41, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.sliding_resistance_force == pytest.approx(6.6, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.long_short_pipe_transition_length == pytest.approx(19.45, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.contraction_design_force == pytest.approx(336.8, rel=1e-2)
        assert flanged_metallic_pipe_example.buoyancy_coefficient == pytest.approx(0.72, rel=1e-2)
    if isinstance(flanged_metallic_pipe_example.soil_type, CoarseSoil):
        assert flanged_metallic_pipe_example.soil_type.net_unit_area_soil_pressure == pytest.approx(23, rel=1e-2)
        assert flanged_metallic_pipe_example.soil_type.sliding_resistance_base() == pytest.approx(10.9, rel=1e-2)
        assert flanged_metallic_pipe_example.soil_type.sliding_resistance_side == pytest.approx(1.9, rel=1e-2)
        assert flanged_metallic_pipe_example.soil_type.area_passive_face == pytest.approx(9.4, rel=1e-2)
        assert flanged_metallic_pipe_example.soil_type.area_base_sliding == pytest.approx(12, rel=1e-2)
        assert flanged_metallic_pipe_example.soil_type.area_side_sliding == pytest.approx(7.1, rel=1e-2)
        assert flanged_metallic_pipe_example.area_disturbed_passive == pytest.approx(1.3, rel=1e-2)
    assert flanged_metallic_pipe_example.block_resistance == pytest.approx(344.8, rel=1e-2)
    assert flanged_metallic_pipe_example.overturning_level_arm == pytest.approx(1.5, rel=1e-2)
    assert flanged_metallic_pipe_example.over_turning_moment == pytest.approx(503.5, rel=1e-2)
    assert flanged_metallic_pipe_example.passive_face_restoring_moment == pytest.approx(169.4, rel=1e-2)
    assert flanged_metallic_pipe_example.net_disturbing_moment == pytest.approx(334.1, rel=1e-2)
    assert flanged_metallic_pipe_example.vertical_reaction_block == pytest.approx(455.1, rel=1e-2)
    assert flanged_metallic_pipe_example.block_restoring_moment == pytest.approx(682.7, rel=1e-2)
    assert flanged_metallic_pipe_example.safety_factor_against_overturning == pytest.approx(2, rel=1e-1)



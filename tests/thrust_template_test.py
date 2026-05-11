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

# --- Factory method for creating Thrust Blocks
def create_thrust_block(
        height,
        width,
        length,
        depth,
        key_height,
        key_length
    ):
        return ThrustBlock(
            height=height,
            width=width,
            length=length,
            depth=depth,
            key_height=key_height,
            key_length=key_length
        )



# --- Test for Arcadis Template - Detail 1 TB1 contraction

pe_pipe = WeldedPePipe(
    maximum_design_pressure=1320,
    outside_diameter=0.3572,
    crown_depth=0.8,
    length=120,
    pipe_material=PipeMaterial.PE_PIPE,
    standard_dimension_ratio=11,
    poisson_ratio=0.48,
    thermal_coefficient=0.00013,
    temperature_reduction=10,
    elastic_modulus=1100000,
    allowable_contraction_movement=0.005,
)

native_medium_dense_gravel = CoarseSoil(
            soil_type=SoilType.SAND,
            soil_consistency=SoilConsistency.LOOSE,
            ground_water_level=0.8,
            soil_passive_factor=5,
            soil_sliding_factor=3,
            soil_category=SoilCategory.COARSE,
            soil_unit_weight=None,
            thrust_block=create_thrust_block(height=1.4, width=4, length=5, depth=1.6786, key_height=None, key_length=None),
            friction_angle=28
        )

coarse_embedment = CoarseEmbedment(
    ground_water_level=0.8,
    pipe=pe_pipe,
    backfill_soil=native_medium_dense_gravel,
    compaction_class="Uncompacted processed gravels",
    embedment_class=EmbedmentClass.S_ONE
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
    assert flanged_metallic_pipe_example.embedment_type.pipe.hoop_stress == pytest.approx(6600, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.liquid_pressure_longitudinal_stress == pytest.approx(3168, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.liquid_pressure_long_longitudinal_force == pytest.approx(104.948, rel=1e-3)
    assert flanged_metallic_pipe_example.embedment_type.pipe.temperature_longitudinal_strain == pytest.approx(0.00130, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.temperature_longitudinal_stress == pytest.approx(1430, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.temperature_longitudinal_force == pytest.approx(47.372, rel=1e-2)
    assert flanged_metallic_pipe_example.embedment_type.pipe.allowable_contraction_movement == pytest.approx(0.005, rel=1e-2)
    if isinstance(flanged_metallic_pipe_example.embedment_type, CoarseEmbedment):
        assert flanged_metallic_pipe_example.embedment_type.effective_angle_shearing_resistance == pytest.approx(32, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.friction_reduction_factor == pytest.approx(0.8, rel=1e-1)
        assert flanged_metallic_pipe_example.embedment_type.backfill_soil.unit_weight == pytest.approx(19, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.pipe.pipe_material_factor == pytest.approx(0.85, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.embedment_sliding_resistance_factor == pytest.approx(2.5, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.buoyancy_coefficient == pytest.approx(0.1825, rel=1e-3)
        assert flanged_metallic_pipe_example.embedment_type.sliding_resistance_force == pytest.approx(1.813, rel=1e-3)
        assert flanged_metallic_pipe_example.embedment_type.long_short_pipe_transition_length == pytest.approx(28.35, rel=1e-2)
        assert flanged_metallic_pipe_example.embedment_type.contraction_design_force == pytest.approx(125.943, rel=1e-2)
        assert flanged_metallic_pipe_example.buoyancy_coefficient == pytest.approx(0.523, rel=1e-2)
    if isinstance(flanged_metallic_pipe_example.soil_type, CoarseSoil):
        assert flanged_metallic_pipe_example.soil_type.net_unit_area_soil_pressure == pytest.approx(6.48991, rel=1e-3)
        assert flanged_metallic_pipe_example.soil_type.sliding_resistance_base() == pytest.approx(4.095, rel=1e-3)
        assert flanged_metallic_pipe_example.soil_type.sliding_resistance_side() == pytest.approx(0.862, rel=1e-2)
        assert flanged_metallic_pipe_example.soil_type.area_passive_face == pytest.approx(5.6, rel=1e-2)
        assert flanged_metallic_pipe_example.soil_type.area_base_sliding == pytest.approx(20, rel=1e-2)
        assert flanged_metallic_pipe_example.soil_type.area_side_sliding == pytest.approx(7, rel=1e-2)
        assert flanged_metallic_pipe_example.area_disturbed_passive == pytest.approx(0.47, rel=1e-2)
    assert flanged_metallic_pipe_example.block_resistance == pytest.approx(127.266, rel=1e-2)
    assert flanged_metallic_pipe_example.overturning_level_arm == pytest.approx(0.7, rel=1e-2)
    assert flanged_metallic_pipe_example.over_turning_moment == pytest.approx(88.16, rel=1e-2)
    assert flanged_metallic_pipe_example.passive_face_restoring_moment == pytest.approx(16.96, rel=1e-2)
    assert flanged_metallic_pipe_example.net_disturbing_moment == pytest.approx(71.2, rel=1e-2)
    assert flanged_metallic_pipe_example.vertical_reaction_block == pytest.approx(462.15, rel=1e-2)
    assert flanged_metallic_pipe_example.block_restoring_moment == pytest.approx(1155.37, rel=1e-2)
    assert flanged_metallic_pipe_example.safety_factor_against_overturning == pytest.approx(16.23, rel=1e-1)

#--- --- Test for Arcadis Template - Detail 2 TB1 Taper

taper_medium_dense_gravel = CoarseSoil(
            soil_type=SoilType.SAND,
            soil_consistency=SoilConsistency.LOOSE,
            ground_water_level=0.8,
            soil_passive_factor=5,
            soil_sliding_factor=3,
            soil_category=SoilCategory.COARSE,
            soil_unit_weight=None,
            thrust_block=create_thrust_block(height=2, width=3.5, length=2.2, depth=1.98, key_height=None, key_length=None),
            friction_angle=28
        )

taper_component = TaperThrust(
            outside_diameter_large=0.3572,
            outside_diameter_small=0.222
        )

taper_thrust_example = TaperThrustThrustBlock(
            maximum_design_pressure=1320,
            crown_depth=0.8,
            soil_type=taper_medium_dense_gravel,
            component=taper_component
        )
        
def test_taper_example():
    soil = taper_thrust_example.soil_type
    assert soil.buoyancy_coefficient == pytest.approx(0.6, rel=1e-2)
    assert soil.unit_weight == pytest.approx(19, rel=1e-1)
    if isinstance(soil, CoarseSoil):
        assert soil.friction_angle == pytest.approx(28, rel=1e-1)
        assert soil.coefficient_passive_earth_pressure == pytest.approx(2.77, rel=1e-3)
        assert soil.coefficient_active_earth_pressure == pytest.approx(0.361, rel=1e-3)
        assert soil.net_unit_area_soil_pressure == pytest.approx(6.15, rel=1e-1)
        assert soil.sliding_resistance_base() == pytest.approx(4.57, rel=1e-1)
        assert soil.sliding_resistance_side() == pytest.approx(0.82, rel=1e-1)
        assert soil.area_passive_face == pytest.approx(7, rel=1e-1)
        assert soil.area_base_sliding == pytest.approx(7.7, rel=1e-1)
        assert soil.area_side_sliding == pytest.approx(4.4, rel=1e-1)
    assert taper_thrust_example.area_disturbed_passive == pytest.approx(0.63, rel=1e-1)
    assert taper_thrust_example.block_resistance == pytest.approx(81.57, rel=1e-1)
    assert taper_thrust_example.thrust_force_resultant == pytest.approx(81.18, rel=1e-1)
    assert taper_thrust_example.overturning_level_arm == pytest.approx(1, rel=1e-1)
    assert taper_thrust_example.over_turning_moment == pytest.approx(81.18, rel=1e-1)
    assert taper_thrust_example.passive_face_restoring_moment == pytest.approx(28.7, rel=1e-1)
    assert taper_thrust_example.vertical_reaction_block == pytest.approx(198.72, rel=1e-1)
    assert taper_thrust_example.block_restoring_moment == pytest.approx(218.59, rel=1e-1)
    assert taper_thrust_example.safety_factor_against_overturning == pytest.approx(4.16,  rel=1e-1)

    # --- Test for  Ciria C816, Example 8.1.2

horizontal_bend_medium_dense_gravel = CoarseSoil(
            soil_type=SoilType.SAND,
            soil_consistency=SoilConsistency.LOOSE,
            ground_water_level=0.8,
            soil_passive_factor=5,
            soil_sliding_factor=3,
            soil_category=SoilCategory.COARSE,
            soil_unit_weight=None,
            thrust_block=create_thrust_block(height=1.8, width=1.9, length=1.8, depth=1.811, key_height=None, key_length=None),
            friction_angle=28
        )

horizontal_bend_component = HorizontalBend(
            outside_diameter=0.222,
            angle=45
        )

horizontal_bend_example = HorizontalBendThrustBlock(
            maximum_design_pressure=1320,
            crown_depth=0.8,
            soil_type=horizontal_bend_medium_dense_gravel,
            component=horizontal_bend_component
        )

def test_horizontal_bend():
    soil = horizontal_bend_example.soil_type
    assert soil.buoyancy_coefficient == pytest.approx(0.56, rel=1e-2)
    assert soil.unit_weight == pytest.approx(19, rel=1e-1)
    if isinstance(soil, CoarseSoil):
        assert soil.friction_angle == pytest.approx(28, rel=1e-1)
        assert soil.coefficient_passive_earth_pressure == pytest.approx(2.77, rel=1e-3)
        assert soil.coefficient_active_earth_pressure == pytest.approx(0.361, rel=1e-3)
        assert soil.net_unit_area_soil_pressure == pytest.approx(5.889, rel=1e-1)
        assert soil.sliding_resistance_base() == pytest.approx(4.307, rel=1e-1)
        assert soil.sliding_resistance_side() == pytest.approx(0.725, rel=1e-1)
        assert soil.area_passive_face == pytest.approx(3.42, rel=1e-1)
        assert soil.area_base_sliding == pytest.approx(3.42, rel=1e-1)
        assert soil.area_side_sliding == pytest.approx(3.24, rel=1e-1)
    assert horizontal_bend_example.area_disturbed_passive == pytest.approx(0, rel=1e-1)
    assert horizontal_bend_example.block_resistance == pytest.approx(39.94, rel=1e-1)
    assert horizontal_bend_example.thrust_force_resultant == pytest.approx(39.11, rel=1e-1)
    assert horizontal_bend_example.overturning_level_arm == pytest.approx(0.9, rel=1e-1)
    assert horizontal_bend_example.over_turning_moment == pytest.approx(35.2, rel=1e-1)
    assert horizontal_bend_example.passive_face_restoring_moment == pytest.approx(12.08, rel=1e-1)
    assert horizontal_bend_example.vertical_reaction_block == pytest.approx(83.10, rel=1e-1)
    assert horizontal_bend_example.block_restoring_moment == pytest.approx(74.79, rel=1e-1)
    assert horizontal_bend_example.safety_factor_against_overturning == pytest.approx(3.24,  rel=1e-1)
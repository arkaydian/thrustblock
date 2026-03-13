import math
from types import SimpleNamespace

import pytest

from app.civeng1.hydraulics.pipes import PipeMaterial, WeldedPePipe
from app.civeng1.soils.soil_enum import EmbedmentClass, SoilConsistency, SoilType, WaterCondition
from app.civeng1.soils.soil_mechanics import (
    CoarseEmbedment,
    CoarseSoil,
    FineEmbedment,
    FineSoil,
    create_embedment,
    create_soil,
    get_embedment_key,
    interpolate_bearing_coefficients,
)
from app.civeng1.structures.concrete import ThrustBlock


def _make_thrust_block(
    *,
    height: float = 1.2,
    width: float = 1.5,
    length: float = 1.7,
    depth: float = 2.0,
    key_height: float | None = None,
    key_length: float | None = None,
) -> ThrustBlock:
    return ThrustBlock(
        height=height,
        width=width,
        length=length,
        depth=depth,
        key_height=key_height,
        key_length=key_length,
    )


def _make_pipe() -> WeldedPePipe:
    return WeldedPePipe(
        maximum_design_pressure=1200,
        outside_diameter=0.315,
        crown_depth=1.0,
        length=100.0,
        standard_dimension_ratio=11,
        poisson_ratio=0.45,
        thermal_coefficient=0.00013,
        temperature_reduction=10,
        elastic_modulus=1_100_000,
        pipe_material=PipeMaterial.PE_PIPE,
        allowable_contraction_movement=0.005,
    )


def _make_common_section(
    *,
    soil_type: str,
    coarse_consistency: str,
    fine_consistency: str,
    friction_angle: float | None,
    undrained_shear_strength: float | None,
):
    return SimpleNamespace(
        soil_type=soil_type,
        coarse_soil_consistency=coarse_consistency,
        fine_soil_consistency=fine_consistency,
        ground_condition="Below Water",
        groundwater_level=0.8,
        soil_passive_factor=3.0,
        soil_sliding_factor=2.25,
        friction_angle=friction_angle,
        undrained_shear_strength=undrained_shear_strength,
    )


def test_interpolate_bearing_coefficients_exact_and_linear_interpolation() -> None:
    exact = interpolate_bearing_coefficients(30)
    assert exact.n_c == pytest.approx(30.0)
    assert exact.n_y == pytest.approx(16.0)
    assert exact.n_q == pytest.approx(18.0)

    interpolated = interpolate_bearing_coefficients(27.5)
    assert interpolated.n_c == pytest.approx(25.5)
    assert interpolated.n_y == pytest.approx(11.5)
    assert interpolated.n_q == pytest.approx(14.5)


def test_get_embedment_key_raises_for_unknown_label() -> None:
    with pytest.raises(ValueError, match="Unknown compaction class"):
        get_embedment_key("Not a valid option")


def test_coarse_soil_uses_effective_depth_and_height_in_calculations() -> None:
    soil = CoarseSoil(
        soil_type=SoilType.SAND,
        soil_consistency=SoilConsistency.LOOSE,
        water_condition=WaterCondition.BELOW_WATER,
        ground_water_level=0.5,
        soil_passive_factor=3.0,
        soil_sliding_factor=2.0,
        soil_category=SoilType.SAND.category,
        thrust_block=_make_thrust_block(
            depth=2.0,
            key_height=1.6,
            height=1.2,
            key_length=1.0,
        ),
        friction_angle=30,
    )

    expected_base = (soil.effective_unit_weight * 1.6 * math.tan(math.radians(30))) / 2.0
    assert soil.sliding_resistance_base() == pytest.approx(expected_base)

    expected_net_pressure = (
        soil.effective_unit_weight
        * (1.6 - (1.0 / 2))
        * (soil.coefficient_passive_earth_pressure - soil.coefficient_active_earth_pressure)
    ) / soil.soil_passive_factor
    assert soil.net_unit_area_soil_pressure == pytest.approx(expected_net_pressure)


def test_create_soil_builds_coarse_soil_from_params() -> None:
    params = SimpleNamespace(
        soil_section=_make_common_section(
            soil_type="Sand",
            coarse_consistency="Loose",
            fine_consistency="Firm",
            friction_angle=30,
            undrained_shear_strength=None,
        ),
        block_section=SimpleNamespace(height=1.2, width=1.0, length=1.8, depth=2.0),
    )

    soil = create_soil(params)
    assert isinstance(soil, CoarseSoil)
    assert soil.soil_type == SoilType.SAND
    assert soil.soil_consistency == SoilConsistency.LOOSE


def test_create_soil_builds_fine_soil_from_params() -> None:
    params = SimpleNamespace(
        soil_section=_make_common_section(
            soil_type="Clay",
            coarse_consistency="Loose",
            fine_consistency="Firm",
            friction_angle=None,
            undrained_shear_strength=60,
        ),
        block_section=SimpleNamespace(height=1.2, width=1.0, length=1.8, depth=2.0),
    )

    soil = create_soil(params)
    assert isinstance(soil, FineSoil)
    assert soil.soil_type == SoilType.CLAY
    assert soil.soil_consistency == SoilConsistency.FIRM
    assert soil.undrained_shear_strength == pytest.approx(60)


def test_coarse_embedment_invalid_class_compaction_combination_raises() -> None:
    backfill = CoarseSoil(
        soil_type=SoilType.SAND,
        soil_consistency=SoilConsistency.LOOSE,
        water_condition=WaterCondition.BELOW_WATER,
        ground_water_level=0.8,
        soil_passive_factor=3.0,
        soil_sliding_factor=2.25,
        soil_category=SoilType.SAND.category,
        thrust_block=_make_thrust_block(),
        friction_angle=30,
    )
    embedment = CoarseEmbedment(
        ground_water_level=0.8,
        pipe=_make_pipe(),
        backfill_soil=backfill,
        compaction_class="Compacted sands and gravels (85%)",
        embedment_class=EmbedmentClass.S_ONE,
    )

    with pytest.raises(ValueError, match="Invalid combination"):
        _ = embedment.effective_angle_shearing_resistance


def test_fine_embedment_adhesion_mapping_and_sliding_factor() -> None:
    backfill = FineSoil(
        soil_type=SoilType.CLAY,
        soil_consistency=SoilConsistency.FIRM,
        water_condition=WaterCondition.BELOW_WATER,
        ground_water_level=0.8,
        soil_passive_factor=3.0,
        soil_sliding_factor=2.25,
        soil_category=SoilType.CLAY.category,
        thrust_block=_make_thrust_block(),
        undrained_shear_strength=60,
    )
    embedment = FineEmbedment(
        ground_water_level=0.8,
        pipe=_make_pipe(),
        backfill_soil=backfill,
        adhesion="Firm or Stiff Clay",
        compaction_class="Compacted clays (90%)",
    )

    assert embedment.representative_adhesion == pytest.approx(30.0)
    assert embedment.embedment_sliding_resistance_factor == pytest.approx(3.5)


def test_create_embedment_builds_coarse_embedment_from_params() -> None:
    params = SimpleNamespace(
        pipe_section=SimpleNamespace(
            maximum_design_pressure=1200,
            outside_diameter=0.315,
            crown_depth=1.0,
            length=120.0,
            standard_dimension_ratio=11,
            poisson_ratio=0.45,
            thermal_coefficient=0.00013,
            temperature_reduction=10,
            elastic_modulus=1100,
            pipe_material="PE Pipe",
            allowable_contraction_movement=0.005,
        ),
        block_section=SimpleNamespace(height=1.2, width=1.0, length=1.8, depth=2.0),
        backfill_section=_make_common_section(
            soil_type="Sand",
            coarse_consistency="Loose",
            fine_consistency="Firm",
            friction_angle=30,
            undrained_shear_strength=None,
        ),
        embedment_section=SimpleNamespace(
            ground_water_level=0.8,
            embedment_class="s2",
            s_one_compaction_class="Uncompacted processed gravels",
            coarse_compaction_class="Compacted sands and gravels (85%)",
            fine_compaction_class="Compacted clays (90%)",
            adhesion="Soft Clay",
        ),
    )

    embedment = create_embedment(params)
    assert isinstance(embedment, CoarseEmbedment)
    assert embedment.embedment_class == EmbedmentClass.S_TWO
    assert embedment.embedment_sliding_resistance_factor == pytest.approx(2.0)

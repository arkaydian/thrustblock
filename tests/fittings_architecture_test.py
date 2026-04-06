from types import SimpleNamespace

from app.civeng1.hydraulics.fittings import HorizontalBend, TaperThrust
from app.civeng1.calculations.thrust_block_calculation import (
    HorizontalBendThrustBlock,
    build_horizontal_bend,
    TaperThrustThrustBlock,
    build_taper_thrust
)
from app.civeng1.soils.soil_mechanics import create_soil

# --- Test for  Ciria C816, Example 8.1.1

def _taper_params() -> SimpleNamespace:
    return SimpleNamespace(
        fitting_section=SimpleNamespace(
            maximum_design_pressure=1200,
            crown_depth=1,
            outside_diameter_large=0.63,
            outside_diameter_small=0.43
        ),
        soil_section=SimpleNamespace(
            soil_type="Gravel",
            coarse_soil_consistency="Medium Dense",
            fine_soil_consistency="Firm",
            ground_condition="Below Water",
            groundwater_level=0.8,
            soil_passive_factor=3.0,
            soil_sliding_factor=2.25,
            friction_angle=30,
            undrained_shear_strength=None,
        ),
        block_section=SimpleNamespace(
            height=1.8,
            width=3.5,
            length=2.5,
            depth=2.3,
            is_key = "No"
        ),
    )

# --- Test for  Ciria C816, Example 8.1.2

def test_taper_thrust_component_can_convert_to_thrust_block_model() -> None:
    params = _taper_params()
    component = TaperThrust(
        outside_diameter_large=params.fitting_section.outside_diameter_large,
        outside_diameter_small=params.fitting_section.outside_diameter_small
    )

    calc_model = TaperThrustThrustBlock(
        component=component,
        maximum_design_pressure=params.fitting_section.maximum_design_pressure,
        crown_depth=params.fitting_section.crown_depth,
        soil_type=create_soil(params),
    )
    assert isinstance(calc_model, TaperThrustThrustBlock)
    assert calc_model.thrust_force_resultant > 0
    # Component attributes are accessible via __getattr__ delegation
    assert calc_model.outside_diameter_large == component.outside_diameter_large
    assert calc_model.outside_diameter_small == component.outside_diameter_small


def test_taper_thrust_builder_returns_thrust_block_model() -> None:
    fitting = build_taper_thrust(_taper_params())
    assert isinstance(fitting, TaperThrustThrustBlock)
    assert fitting.fitting_workflow_res


def _horizontal_bend_params() -> SimpleNamespace:
    return SimpleNamespace(
        fitting_section=SimpleNamespace(
            maximum_design_pressure=1200,
            crown_depth=1.0,
            outside_diameter=0.315,
            angle=45,
        ),
        soil_section=SimpleNamespace(
            soil_type="Sand",
            coarse_soil_consistency="Loose",
            fine_soil_consistency="Firm",
            ground_condition="Below Water",
            groundwater_level=0.8,
            soil_passive_factor=3.0,
            soil_sliding_factor=2.25,
            friction_angle=30,
            undrained_shear_strength=None,
        ),
        block_section=SimpleNamespace(
            height=1.2,
            width=1.0,
            length=1.8,
            depth=2.0,
            is_key = "No"
        ),
    )


def test_horizontal_bend_component_can_convert_to_thrust_block_model() -> None:
    params = _horizontal_bend_params()
    component = HorizontalBend(
        outside_diameter=params.fitting_section.outside_diameter,
        angle=params.fitting_section.angle,
        radius=0,
    )

    calc_model = HorizontalBendThrustBlock(
        component=component,
        maximum_design_pressure=params.fitting_section.maximum_design_pressure,
        crown_depth=params.fitting_section.crown_depth,
        soil_type=create_soil(params),
    )
    assert isinstance(calc_model, HorizontalBendThrustBlock)
    assert calc_model.thrust_force_resultant > 0
    # Component attributes are accessible via __getattr__ delegation
    assert calc_model.outside_diameter == component.outside_diameter
    assert calc_model.angle == component.angle


def test_horizontal_bend_builder_returns_thrust_block_model() -> None:
    fitting = build_horizontal_bend(_horizontal_bend_params())
    assert isinstance(fitting, HorizontalBendThrustBlock)
    assert fitting.fitting_workflow_res

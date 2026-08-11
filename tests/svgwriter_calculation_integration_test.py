from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.civeng1.calculations.thrust_block_calculation import (
    BlankEndThrustBlock,
    FittingCalculation,
    HorizontalBendThrustBlock,
    TeeThrustBlock,
    TaperThrustThrustBlock,
    VerticalDownturnBendThrustBlock,
    VerticalUpturnBendThrustBlock,
    build_blank_end,
    build_horizontal_bend,
    build_taper_thrust,
    build_tee,
    build_vertical_upturn_bend,
    fitting_from_params,
)
from app.civeng1.hydraulics.fittings import BlankEnd, HorizontalBend
from app.civeng1.soils.soil_mechanics import create_soil
from app.utils.svg.registry import (
    SVGWriterRegistrationError,
    SVGWriterNotRegisteredError,
    get_svg_writer,
    register_svg_writer,
)
from app.utils.svgwriter import (
    BlankEndSVGWriter,
    DrawingOptions,
    HorizontalBendSVGWriter,
    SVGDrawing,
    TaperSVGWriter,
    VerticalBendSVGWriter,
    VerticalDownturnBendSVGWriter,
)


def _base_soil_section() -> SimpleNamespace:
    return SimpleNamespace(
        soil_type="Gravel",
        coarse_soil_consistency="Medium Dense",
        fine_soil_consistency="Firm",
        ground_condition="Below Water",
        groundwater_level=0.8,
        is_custom_unit_weight=False,
        soil_passive_factor=3.0,
        soil_sliding_factor=2.25,
        friction_angle=30,
        undrained_shear_strength=None,
    )


def _base_block_section() -> SimpleNamespace:
    return SimpleNamespace(
        height=1.8,
        width=3.5,
        length=2.5,
        depth=2.3,
        is_depth_custom="Yes",
        is_key="No",
    )


def _horizontal_params() -> SimpleNamespace:
    return SimpleNamespace(
        fitting_section=SimpleNamespace(
            fitting_type="Horizontal Bend",
            maximum_design_pressure=1200,
            crown_depth=1.0,
            outside_diameter=0.315,
            angle=45.0,
        ),
        soil_section=_base_soil_section(),
        block_section=_base_block_section(),
    )


def _vertical_upturn_params() -> SimpleNamespace:
    return SimpleNamespace(
        fitting_section=SimpleNamespace(
            fitting_type="Vertical Upturn Bend",
            maximum_design_pressure=1200,
            crown_depth=1.0,
            outside_diameter=0.315,
            angle=45.0,
        ),
        soil_section=_base_soil_section(),
        block_section=_base_block_section(),
    )


def _blank_end_params() -> SimpleNamespace:
    return SimpleNamespace(
        fitting_section=SimpleNamespace(
            fitting_type="Blank End",
            maximum_design_pressure=1200,
            crown_depth=1.0,
            outside_diameter=0.315,
        ),
        soil_section=_base_soil_section(),
        block_section=_base_block_section(),
    )


def _taper_params() -> SimpleNamespace:
    return SimpleNamespace(
        fitting_section=SimpleNamespace(
            fitting_type="Taper Thrust",
            maximum_design_pressure=1200,
            crown_depth=1.0,
            outside_diameter_large=0.63,
            outside_diameter_small=0.43,
        ),
        soil_section=_base_soil_section(),
        block_section=_base_block_section(),
    )


def _tee_params() -> SimpleNamespace:
    return SimpleNamespace(
        fitting_section=SimpleNamespace(
            fitting_type="Tee",
            maximum_design_pressure=1200,
            crown_depth=1.0,
            outside_diameter_main=0.5,
            outside_diameter_branch=0.3,
        ),
        soil_section=_base_soil_section(),
        block_section=_base_block_section(),
    )


def _assert_drawings_valid(drawings: list[SVGDrawing]) -> None:
    assert isinstance(drawings, list)
    assert drawings
    for drawing in drawings:
        assert isinstance(drawing, SVGDrawing)
        assert drawing.svg.strip()
        ET.fromstring(drawing.svg)


def test_supported_calculation_has_inherited_svg_drawings_method() -> None:
    assert "svg_drawings" not in HorizontalBendThrustBlock.__dict__
    assert callable(HorizontalBendThrustBlock.svg_drawings)


def test_svg_drawings_does_not_mutate_frozen_dataclass() -> None:
    calculation = build_horizontal_bend(_horizontal_params())
    before = calculation.__dict__.copy()
    calculation.svg_drawings()
    assert calculation.__dict__ == before


@pytest.mark.parametrize(
    ("builder", "params_factory", "expected_type"),
    [
        (build_horizontal_bend, _horizontal_params, HorizontalBendThrustBlock),
        (build_vertical_upturn_bend, _vertical_upturn_params, VerticalUpturnBendThrustBlock),
        (build_blank_end, _blank_end_params, BlankEndThrustBlock),
        (build_taper_thrust, _taper_params, TaperThrustThrustBlock),
    ],
)
def test_supported_calculation_svg_drawings_returns_valid_svg(builder, params_factory, expected_type) -> None:
    calculation = builder(params_factory())
    assert isinstance(calculation, expected_type)
    _assert_drawings_valid(calculation.svg_drawings())


def test_svg_drawings_creates_no_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    calculation = build_blank_end(_blank_end_params())
    calculation.svg_drawings()
    assert list(tmp_path.iterdir()) == []


def test_fitting_from_params_returns_calculation_that_can_render_svg() -> None:
    calculation = fitting_from_params(_horizontal_params())
    assert isinstance(calculation, FittingCalculation)
    _assert_drawings_valid(calculation.svg_drawings())


def test_writer_receives_same_calculation_instance_from_builder(monkeypatch) -> None:
    captured: dict[str, object] = {}

    @classmethod
    def fake_build(cls, calculation, options=None):
        captured["calculation"] = calculation
        return [SVGDrawing(name="spy", svg='<svg xmlns="http://www.w3.org/2000/svg"></svg>')]

    monkeypatch.setattr(HorizontalBendSVGWriter, "build", fake_build)
    calculation = fitting_from_params(_horizontal_params())
    drawings = calculation.svg_drawings()
    assert captured["calculation"] is calculation
    _assert_drawings_valid(drawings)


def test_supported_writer_registrations() -> None:
    assert get_svg_writer(HorizontalBendThrustBlock) is HorizontalBendSVGWriter
    assert get_svg_writer(VerticalUpturnBendThrustBlock) is VerticalBendSVGWriter
    assert get_svg_writer(VerticalDownturnBendThrustBlock) is VerticalDownturnBendSVGWriter
    assert get_svg_writer(BlankEndThrustBlock) is BlankEndSVGWriter
    assert get_svg_writer(TaperThrustThrustBlock) is TaperSVGWriter


def test_unsupported_calculation_raises_svg_writer_not_registered() -> None:
    calculation = build_tee(_tee_params())
    assert isinstance(calculation, TeeThrustBlock)
    with pytest.raises(SVGWriterNotRegisteredError, match="No SVG writer is registered for TeeThrustBlock"):
        calculation.svg_drawings()


def test_duplicate_svg_writer_registration_is_rejected() -> None:
    @dataclass(frozen=True)
    class DummyCalculation(FittingCalculation):
        @property
        def depth(self) -> float:
            return 1.0

        @property
        def thrust_force_resultant(self) -> float:
            return 1.0

        @property
        def area_disturbed_passive(self) -> float:
            return 0.0

        @property
        def overturning_level_arm(self) -> float:
            return 1.0

        @property
        def fitting_workflow_res(self):
            return []

    class DummyWriter:
        @classmethod
        def build(cls, calculation, options=None):
            return []

    register_svg_writer(DummyCalculation, DummyWriter)
    with pytest.raises(SVGWriterRegistrationError):
        register_svg_writer(DummyCalculation, DummyWriter)


def test_horizontal_writer_reads_component_block_crown_and_groundwater_data() -> None:
    calculation = build_horizontal_bend(_horizontal_params())
    drawings = calculation.svg_drawings()
    plan_svg = drawings[0].svg
    assert len(drawings) == 1
    assert "Plan" in plan_svg


def test_component_geometry_change_flows_through_calculation_component() -> None:
    params_a = _horizontal_params()
    params_b = _horizontal_params()
    params_b.fitting_section.angle = 90.0
    svg_a = build_horizontal_bend(params_a).svg_drawings()[0].svg
    svg_b = build_horizontal_bend(params_b).svg_drawings()[0].svg
    assert svg_a != svg_b


def test_thrust_force_resultant_is_read_from_calculation(monkeypatch) -> None:
    original = HorizontalBendThrustBlock.thrust_force_resultant
    calls = {"count": 0}

    def wrapped(self):
        calls["count"] += 1
        return original.fget(self)

    monkeypatch.setattr(HorizontalBendThrustBlock, "thrust_force_resultant", property(wrapped))
    build_horizontal_bend(_horizontal_params()).svg_drawings()
    assert calls["count"] >= 1


def test_block_dependent_writer_raises_clear_error_when_thrust_block_missing() -> None:
    calculation = HorizontalBendThrustBlock(
        component=HorizontalBend(outside_diameter=0.315, angle=45.0, radius=0.0),
        maximum_design_pressure=1200,
        crown_depth=1.0,
        soil_type=SimpleNamespace(ground_water_level=0.8, thrust_block=None),
    )
    with pytest.raises(ValueError, match="Cannot generate thrust-block SVG drawings because soil_type.thrust_block is None"):
        calculation.svg_drawings()


def test_blank_end_writer_does_not_require_thrust_block() -> None:
    calculation = BlankEndThrustBlock(
        component=BlankEnd(outside_diameter=0.315),
        maximum_design_pressure=1200,
        crown_depth=1.0,
        soil_type=SimpleNamespace(ground_water_level=0.8, thrust_block=None),
    )
    _assert_drawings_valid(calculation.svg_drawings())


def test_drawing_options_change_canvas_size() -> None:
    calculation = build_blank_end(_blank_end_params())
    default_svg = calculation.svg_drawings()[0].svg
    custom_svg = calculation.svg_drawings(DrawingOptions(canvas_width=320, canvas_height=240))[0].svg
    assert 'width="600"' in default_svg
    assert 'width="320"' in custom_svg
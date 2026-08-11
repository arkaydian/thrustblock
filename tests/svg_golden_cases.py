from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from app.civeng1.calculations.thrust_block_calculation import fitting_from_params
from app.utils.svgwriter import DrawingKind, DrawingOptions, SVGDrawing, build_vertical_downturn_bend_section_svg


GOLDEN_DIR = Path(__file__).resolve().parent / "golden_svg"


@dataclass(frozen=True, slots=True)
class GoldenSVGCase:
    name: str
    build_calculation: Callable[[], object]
    drawing_name: str | None = None
    drawing_kind: DrawingKind | None = None
    options: DrawingOptions | None = None

    @property
    def fixture_path(self) -> Path:
        return GOLDEN_DIR / f"{self.name}.svg"

    def select(self, drawings: list[SVGDrawing]) -> SVGDrawing:
        if self.drawing_kind is not None:
            for drawing in drawings:
                if drawing.kind == self.drawing_kind:
                    return drawing
            available = ", ".join(f"{drawing.name}:{drawing.kind}" for drawing in drawings)
            raise AssertionError(
                f"Drawing kind '{self.drawing_kind}' was not returned for case '{self.name}'. "
                f"Available drawings: {available}"
            )

        if self.drawing_name is not None:
            for drawing in drawings:
                if drawing.name == self.drawing_name:
                    return drawing
            available = ", ".join(drawing.name for drawing in drawings)
            raise AssertionError(
                f"Drawing view '{self.drawing_name}' was not returned for case '{self.name}'. "
                f"Available views: {available}"
            )

        raise AssertionError(f"Case '{self.name}' must define drawing_name or drawing_kind")

    def render(self) -> SVGDrawing:
        calculation = self.build_calculation()
        drawings = calculation.svg_drawings(self.options)
        return self.select(drawings)


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


def _horizontal_params(angle: float = 45.0) -> SimpleNamespace:
    return SimpleNamespace(
        fitting_section=SimpleNamespace(
            fitting_type="Horizontal Bend",
            maximum_design_pressure=1200,
            crown_depth=1.0,
            outside_diameter=0.315,
            angle=angle,
        ),
        soil_section=_base_soil_section(),
        block_section=_base_block_section(),
    )


def _vertical_upturn_params(angle: float = 45.0) -> SimpleNamespace:
    return SimpleNamespace(
        fitting_section=SimpleNamespace(
            fitting_type="Vertical Upturn Bend",
            maximum_design_pressure=1200,
            crown_depth=1.0,
            outside_diameter=0.315,
            angle=angle,
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


def _calc_for(params: SimpleNamespace):
    return fitting_from_params(params)


class _StandaloneDrawingCalculation:
    def __init__(self, drawing_builder: Callable[[DrawingOptions | None], SVGDrawing]) -> None:
        self._drawing_builder = drawing_builder

    def svg_drawings(self, options: DrawingOptions | None = None) -> list[SVGDrawing]:
        return [self._drawing_builder(options)]


def _vertical_downturn_case(angle: float) -> _StandaloneDrawingCalculation:
    def _build(_: DrawingOptions | None = None) -> SVGDrawing:
        svg = build_vertical_downturn_bend_section_svg(
            block_height=2.0,
            block_width=2.5,
            block_length=4.5,
            block_depth=2.5,
            gw_level=0.8,
            od=0.6,
            depth_crown=1.0,
            angle=angle,
            canvas_w=800,
            canvas_h=500,
        )
        return SVGDrawing(
            name="section_downturn",
            svg=svg,
            view=None,
            kind=DrawingKind.VERTICAL_DOWNTURN_LONGITUDINAL,
        )

    return _StandaloneDrawingCalculation(_build)


def iter_golden_cases() -> list[GoldenSVGCase]:
    return [
        GoldenSVGCase(
            name="blank_end_default_elevation",
            build_calculation=lambda: _calc_for(_blank_end_params()),
            drawing_name="elevation",
        ),
        GoldenSVGCase(
            name="taper_thrust_default_plan",
            build_calculation=lambda: _calc_for(_taper_params()),
            drawing_name="plan",
        ),
        GoldenSVGCase(
            name="taper_thrust_default_section",
            build_calculation=lambda: _calc_for(_taper_params()),
            drawing_name="section",
        ),
        GoldenSVGCase(
            name="horizontal_bend_default_plan",
            build_calculation=lambda: _calc_for(_horizontal_params(45.0)),
            drawing_name="plan",
        ),
        GoldenSVGCase(
            name="vertical_upturn_longitudinal_section",
            build_calculation=lambda: _calc_for(_vertical_upturn_params(45.0)),
            drawing_kind=DrawingKind.VERTICAL_UPTURN_LONGITUDINAL,
        ),
        GoldenSVGCase(
            name="horizontal_bend_angle_11_25_plan",
            build_calculation=lambda: _calc_for(_horizontal_params(11.25)),
            drawing_name="plan",
        ),
        GoldenSVGCase(
            name="horizontal_bend_angle_22_5_plan",
            build_calculation=lambda: _calc_for(_horizontal_params(22.5)),
            drawing_name="plan",
        ),
        GoldenSVGCase(
            name="horizontal_bend_angle_45_plan",
            build_calculation=lambda: _calc_for(_horizontal_params(45.0)),
            drawing_name="plan",
        ),
        GoldenSVGCase(
            name="horizontal_bend_angle_90_plan",
            build_calculation=lambda: _calc_for(_horizontal_params(90.0)),
            drawing_name="plan",
        ),
        GoldenSVGCase(
            name="vertical_upturn_angle_11_25_longitudinal_section",
            build_calculation=lambda: _calc_for(_vertical_upturn_params(11.25)),
            drawing_kind=DrawingKind.VERTICAL_UPTURN_LONGITUDINAL,
        ),
        GoldenSVGCase(
            name="vertical_upturn_angle_22_5_longitudinal_section",
            build_calculation=lambda: _calc_for(_vertical_upturn_params(22.5)),
            drawing_kind=DrawingKind.VERTICAL_UPTURN_LONGITUDINAL,
        ),
        GoldenSVGCase(
            name="vertical_upturn_angle_45_longitudinal_section",
            build_calculation=lambda: _calc_for(_vertical_upturn_params(45.0)),
            drawing_kind=DrawingKind.VERTICAL_UPTURN_LONGITUDINAL,
        ),
        GoldenSVGCase(
            name="vertical_upturn_angle_90_longitudinal_section",
            build_calculation=lambda: _calc_for(_vertical_upturn_params(90.0)),
            drawing_kind=DrawingKind.VERTICAL_UPTURN_LONGITUDINAL,
        ),
        GoldenSVGCase(
            name="vertical_downturn_angle_11_25_section",
            build_calculation=lambda: _vertical_downturn_case(11.25),
            drawing_kind=DrawingKind.VERTICAL_DOWNTURN_LONGITUDINAL,
        ),
        GoldenSVGCase(
            name="vertical_downturn_angle_22_5_section",
            build_calculation=lambda: _vertical_downturn_case(22.5),
            drawing_kind=DrawingKind.VERTICAL_DOWNTURN_LONGITUDINAL,
        ),
        GoldenSVGCase(
            name="vertical_downturn_angle_45_section",
            build_calculation=lambda: _vertical_downturn_case(45.0),
            drawing_kind=DrawingKind.VERTICAL_DOWNTURN_LONGITUDINAL,
        ),
        GoldenSVGCase(
            name="vertical_downturn_angle_90_section",
            build_calculation=lambda: _vertical_downturn_case(90.0),
            drawing_kind=DrawingKind.VERTICAL_DOWNTURN_LONGITUDINAL,
        ),
    ]


def supported_calculation_cases() -> list[GoldenSVGCase]:
    return [
        case
        for case in iter_golden_cases()
        if case.name
        in {
            "blank_end_default_elevation",
            "taper_thrust_default_plan",
            "taper_thrust_default_section",
            "horizontal_bend_default_plan",
            "vertical_upturn_longitudinal_section",
        }
    ]
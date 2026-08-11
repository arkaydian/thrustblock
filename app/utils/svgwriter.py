from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace
from typing import TYPE_CHECKING, Callable, List, NewType, Protocol

if __name__ not in sys.modules:
    _self_module = ModuleType(__name__)
    _self_module.__dict__.update(globals())
    sys.modules[__name__] = _self_module

if TYPE_CHECKING:
    from app.utils.svg.canvas import CanvasLayout as CanvasLayoutType
    from app.utils.svg.canvas import Point as PointType
    from app.utils.svg.canvas import Port as PortType
    from app.utils.svg.canvas import SVGCanvas as SVGCanvasType
    from app.utils.svg.canvas import Vector as VectorType
    from app.utils.svg.geometry import AnchorGeometry as AnchorGeometryType
    from app.utils.svg.geometry import BendGeometry as BendGeometryType
    from app.utils.svg.geometry import FittingPlacement as FittingPlacementType

try:
    from app.utils.svg.canvas import CanvasLayout, Point, Port, SVGCanvas, Vector
    from app.utils.svg.geometry import AnchorGeometry, BendGeometry, FittingPlacement, add_vector, rotate_point, rotate_vector, scale_vector
except ModuleNotFoundError:
    _canvas_spec = spec_from_file_location(
        "svgwriter_canvas_module",
        Path(__file__).resolve().parent / "svg" / "canvas.py",
    )
    assert _canvas_spec is not None
    _canvas_module = module_from_spec(_canvas_spec)
    assert _canvas_spec.loader is not None
    sys.modules[_canvas_spec.name] = _canvas_module
    _canvas_spec.loader.exec_module(_canvas_module)
    CanvasLayout = _canvas_module.CanvasLayout
    Point = _canvas_module.Point
    Port = _canvas_module.Port
    SVGCanvas = _canvas_module.SVGCanvas
    Vector = _canvas_module.Vector

    _geometry_spec = spec_from_file_location(
        "svgwriter_geometry_module",
        Path(__file__).resolve().parent / "svg" / "geometry.py",
    )
    assert _geometry_spec is not None
    _geometry_module = module_from_spec(_geometry_spec)
    assert _geometry_spec.loader is not None
    sys.modules[_geometry_spec.name] = _geometry_module
    _geometry_spec.loader.exec_module(_geometry_module)
    AnchorGeometry = _geometry_module.AnchorGeometry
    BendGeometry = _geometry_module.BendGeometry
    FittingPlacement = _geometry_module.FittingPlacement
    add_vector = _geometry_module.add_vector
    rotate_point = _geometry_module.rotate_point
    rotate_vector = _geometry_module.rotate_vector
    scale_vector = _geometry_module.scale_vector


class _CompatStrEnum(str, Enum):
    pass


class DrawingView(_CompatStrEnum):
    ELEVATION = "elevation"
    PLAN = "plan"
    SECTION = "section"


class DrawingKind(_CompatStrEnum):
    ELEVATION = "elevation"
    PLAN = "plan"
    SECTION = "section"
    VERTICAL_UPTURN_LONGITUDINAL = "vertical_upturn_longitudinal"
    VERTICAL_DOWNTURN_LONGITUDINAL = "vertical_downturn_longitudinal"
    THRUST_BLOCK_SECTION_A_A = "thrust_block_section_a_a"


@dataclass(frozen=True, slots=True)
class SVGDrawing:
    name: str
    svg: str
    view: DrawingView | None = None
    kind: DrawingKind | None = None

    def __post_init__(self) -> None:
        resolved_view = self.view
        if resolved_view is None:
            try:
                resolved_view = DrawingView(self.name)
            except ValueError:
                resolved_view = None

        resolved_kind = self.kind
        if resolved_kind is None and resolved_view is not None:
            if resolved_view == DrawingView.ELEVATION:
                resolved_kind = DrawingKind.ELEVATION
            elif resolved_view == DrawingView.PLAN:
                resolved_kind = DrawingKind.PLAN
            elif resolved_view == DrawingView.SECTION:
                resolved_kind = DrawingKind.SECTION

        object.__setattr__(self, "view", resolved_view)
        object.__setattr__(self, "kind", resolved_kind)


@dataclass(frozen=True, slots=True)
class DrawingOptions:
    canvas_width: int = 600
    canvas_height: int = 400
    start_angle_deg: float | None = None
    bend_orientation_deg: float | None = None


class BlankEndLike(Protocol):
    @property
    def outside_diameter(self) -> float:
        ...


class TaperLike(Protocol):
    @property
    def outside_diameter_large(self) -> float:
        ...

    @property
    def outside_diameter_small(self) -> float:
        ...


class BendLike(Protocol):
    @property
    def outside_diameter(self) -> float:
        ...

    @property
    def angle(self) -> float:
        ...

    @property
    def radius(self) -> float:
        ...


class ThrustBlockLike(Protocol):
    @property
    def height(self) -> float:
        ...

    @property
    def width(self) -> float:
        ...

    @property
    def length(self) -> float:
        ...

    @property
    def depth(self) -> float:
        ...


class SoilDrawingLike(Protocol):
    @property
    def ground_water_level(self) -> float:
        ...

    @property
    def thrust_block(self) -> ThrustBlockLike | None:
        ...


class BlankEndCalculationLike(Protocol):
    @property
    def component(self) -> BlankEndLike:
        ...

    @property
    def thrust_force_resultant(self) -> float:
        ...


class TaperCalculationLike(Protocol):
    @property
    def component(self) -> TaperLike:
        ...

    @property
    def soil_type(self) -> SoilDrawingLike:
        ...

    @property
    def crown_depth(self) -> float:
        ...

    @property
    def thrust_force_resultant(self) -> float:
        ...


class HorizontalBendCalculationLike(Protocol):
    @property
    def component(self) -> BendLike:
        ...

    @property
    def soil_type(self) -> SoilDrawingLike:
        ...

    @property
    def crown_depth(self) -> float:
        ...

    @property
    def thrust_force_resultant(self) -> float:
        ...


class VerticalBendCalculationLike(Protocol):
    @property
    def component(self) -> BendLike:
        ...

    @property
    def soil_type(self) -> SoilDrawingLike:
        ...

    @property
    def crown_depth(self) -> float:
        ...

    @property
    def thrust_force_resultant(self) -> float:
        ...


@dataclass(frozen=True, slots=True)
class BlankEndInput:
    outside_diameter: float


@dataclass(frozen=True, slots=True)
class TaperInput:
    outside_diameter_large: float
    outside_diameter_small: float


@dataclass(frozen=True, slots=True)
class BendInput:
    outside_diameter: float
    angle: float
    radius: float = 0.0


@dataclass(frozen=True, slots=True)
class ThrustBlockInput:
    height: float
    width: float
    length: float
    depth: float


def _canvas_svg_string(canvas: SVGCanvasType) -> str:
    """Serialize a canvas to a standalone SVG document string."""
    return canvas.to_svg()


def _drawing_from_canvas(
    name: str,
    canvas: SVGCanvasType,
    *,
    view: DrawingView | None = None,
    kind: DrawingKind | None = None,
) -> SVGDrawing:
    return SVGDrawing(name=name, svg=canvas.to_svg(), view=view, kind=kind)


def _require_thrust_block(soil: SoilDrawingLike) -> ThrustBlockLike:
    thrust_block = soil.thrust_block
    if thrust_block is None:
        raise ValueError("Cannot generate thrust-block SVG drawings because soil_type.thrust_block is None")
    return thrust_block


class BlankEndSVGWriter:
    @classmethod
    def build(
        cls,
        calculation: BlankEndCalculationLike,
        options: DrawingOptions | None = None,
    ) -> list[SVGDrawing]:
        options = options or DrawingOptions()
        _ = calculation.thrust_force_resultant
        return cls(
            fitting=calculation.component,
            canvas_w=options.canvas_width,
            canvas_h=options.canvas_height,
        ).drawings()

    def __init__(self, fitting: BlankEndLike, canvas_w: int, canvas_h: int) -> None:
        self._fitting = fitting
        self._canvas_w = canvas_w
        self._canvas_h = canvas_h

    def drawings(self) -> list[SVGDrawing]:
        return [self._build_elevation()]

    def _build_elevation(self) -> SVGDrawing:
        canvas = SVGCanvas(scale=1.0, width=self._canvas_w, height=self._canvas_h)
        centre_y = self._canvas_h / 2
        pipe_len = 260.0
        socket_len = 55.0
        pipe_half = self._fitting.outside_diameter / 2
        canvas.rect(120.0, centre_y - pipe_half, pipe_len, self._fitting.outside_diameter, fill="white", stroke="black", stroke_w=2)
        canvas.rect(120.0 - socket_len, centre_y - pipe_half * 1.12, socket_len, self._fitting.outside_diameter * 1.12, fill="#efefef", stroke="black", stroke_w=1.8)
        canvas.line(60.0, centre_y, 380.0, centre_y, stroke="#999999", stroke_w=1, dasharray="6,6", stroke_opacity=0.5)
        canvas.text(self._canvas_w / 2, centre_y + 42.0, "Blank End", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
        return _drawing_from_canvas("elevation", canvas, view=DrawingView.ELEVATION, kind=DrawingKind.ELEVATION)


class TaperSVGWriter:
    @classmethod
    def build(
        cls,
        calculation: TaperCalculationLike,
        options: DrawingOptions | None = None,
    ) -> list[SVGDrawing]:
        options = options or DrawingOptions()
        thrust_block = _require_thrust_block(calculation.soil_type)
        _ = calculation.thrust_force_resultant
        return cls(
            thrust_block=thrust_block,
            taper=calculation.component,
            canvas_w=options.canvas_width,
            canvas_h=options.canvas_height,
            depth_crown=calculation.crown_depth,
            gw_level=calculation.soil_type.ground_water_level,
        ).drawings()

    def __init__(
        self,
        thrust_block: ThrustBlockLike,
        taper: TaperLike,
        canvas_w: int,
        canvas_h: int,
        depth_crown: float = 1.0,
        gw_level: float = 0.8,
    ) -> None:
        self._block = thrust_block
        self._taper = taper
        self._canvas_w = canvas_w
        self._canvas_h = canvas_h
        self._depth_crown = depth_crown
        self._gw_level = gw_level

    def drawings(self) -> list[SVGDrawing]:
        return [self._build_plan(), self._build_section()]

    def _draw_excavation_lines(
        self,
        canvas: SVGCanvasType,
        *,
        cy: float,
        block_left: float,
        block_right: float,
        x_min: float,
        x_max: float,
        trench_half_width: float,
    ) -> None:
        trench_stroke = "#333333"
        edge_stroke_w = 1.6
        hatch_stroke_w = 2.0

        left_end = min(block_left - 2.0, x_max)
        right_start = max(block_right + 2.0, x_min)
        if left_end <= x_min or x_max <= right_start:
            return

        upper_y = cy - trench_half_width
        lower_y = cy + trench_half_width

        def _edge_points(x0: float, x1: float, y0: float, offsets: list[float]) -> list[tuple[float, float]]:
            span = x1 - x0
            fractions = [0.0, 0.20, 0.39, 0.58, 0.79, 1.0]
            return [(x0 + span * fx, y0 + dy) for fx, dy in zip(fractions, offsets)]

        def _draw_edge(points: list[tuple[float, float]]) -> None:
            d = " ".join(
                [f"M {points[0][0]:.2f},{points[0][1]:.2f}"]
                + [f"L {x:.2f},{y:.2f}" for x, y in points[1:]]
            )
            canvas.path(d=d, stroke=trench_stroke, stroke_w=edge_stroke_w, fill="none")

        left_upper = _edge_points(x_min, left_end, upper_y, [0.0, 1.2, -0.9, 0.8, -0.5, 0.0])
        left_lower = _edge_points(x_min, left_end, lower_y, [0.0, -1.1, 0.8, -0.7, 0.4, 0.0])
        right_upper = _edge_points(right_start, x_max, upper_y, [0.0, -1.0, 0.9, -0.7, 0.5, 0.0])
        right_lower = _edge_points(right_start, x_max, lower_y, [0.0, 1.1, -0.9, 0.7, -0.4, 0.0])

        _draw_edge(left_upper)
        _draw_edge(left_lower)
        _draw_edge(right_upper)
        _draw_edge(right_lower)

        def _draw_hatch_group(x_anchor: float, y_anchor: float, above: bool, count: int = 4) -> None:
            spacing = 8.0
            dx = 7.0
            dy = 7.0
            y0 = y_anchor - 8.0 if above else y_anchor + 8.0
            for idx in range(count):
                x1 = x_anchor + idx * spacing
                if above:
                    y1 = y0
                    x2 = x1 + dx
                    y2 = y1 - dy
                else:
                    y1 = y0
                    x2 = x1 + dx
                    y2 = y1 + dy
                canvas.line(x1, y1, x2, y2, stroke=trench_stroke, stroke_w=hatch_stroke_w)

        left_span = left_end - x_min
        right_span = x_max - right_start
        _draw_hatch_group(x_min + left_span * 0.18, upper_y, above=True)
        _draw_hatch_group(x_min + left_span * 0.16, lower_y, above=False)
        _draw_hatch_group(right_start + right_span * 0.55, upper_y, above=True)
        _draw_hatch_group(right_start + right_span * 0.56, lower_y, above=False)

    def _build_plan(self) -> SVGDrawing:
        canvas = SVGCanvas(scale=1.0, width=self._canvas_w, height=self._canvas_h)
        m_to_px = 46.0
        cx = self._canvas_w / 2
        cy = self._canvas_h / 2
        block_len_px = self._block.length * m_to_px
        block_w = block_len_px
        block_h = self._block.width * m_to_px
        left = cx - block_w / 2
        top = cy - block_h / 2

        # Compose the taper assembly in plan using local fittings chained by ports.
        pipe_large = self._taper.outside_diameter_large * m_to_px
        pipe_small = self._taper.outside_diameter_small * m_to_px
        taper_len = max(block_len_px * 0.2608695652173913, 1.2 * max(pipe_large, pipe_small))
        flange_t = max(4.0, 0.12 * pipe_large)
        flange_gap = max(3.0, 0.08 * pipe_small)
        flange_pair_w = 2 * flange_t + flange_gap
        socket_large_w = max(8.0, 0.40 * pipe_large)
        socket_small_w = max(8.0, 0.40 * pipe_small)
        pipe_overhang = max(block_len_px * 0.35, 2.0 * max(pipe_large, pipe_small))

        taper_start_x = cx - taper_len / 2
        taper_end_x = cx + taper_len / 2
        left_outer_target = left - pipe_overhang
        right_outer_target = left + block_w + pipe_overhang

        upstream_len = max(
            1.5 * pipe_large,
            (taper_start_x - flange_pair_w - socket_large_w) - left_outer_target,
        )
        downstream_len = max(
            1.5 * pipe_small,
            right_outer_target - (taper_end_x + flange_pair_w + socket_small_w),
        )

        left_socket_start = taper_start_x - flange_pair_w - socket_large_w - upstream_len
        left_pipe_start = left_socket_start + socket_large_w
        left_flange_start = left_pipe_start + upstream_len
        right_flange_start = taper_end_x
        right_pipe_start = right_flange_start + flange_pair_w
        right_socket_start = right_pipe_start + downstream_len

        # Draw excavation edges/hatching outside the block before block and pipe geometry.
        trench_half_width = min(block_h * 0.34, max(28.0, 1.55 * max(pipe_large, pipe_small)))
        self._draw_excavation_lines(
            canvas,
            cy=cy,
            block_left=left,
            block_right=left + block_w,
            x_min=left_outer_target,
            x_max=right_outer_target,
            trench_half_width=trench_half_width,
        )

        canvas.rect(left, top, block_w, block_h, fill="#d9d9d9", stroke="black", stroke_w=2)

        # Draw the continuous upstream/downstream pipe runs first.
        canvas.place_fitting_local(
            canvas.make_port(left_pipe_start, cy, 1, 0),
            lambda: draw_plan_pipe_segment(canvas, length_px=upstream_len, diameter_px=pipe_large),
        )
        canvas.place_fitting_local(
            canvas.make_port(right_pipe_start, cy, 1, 0),
            lambda: draw_plan_pipe_segment(canvas, length_px=downstream_len, diameter_px=pipe_small),
        )

        # Centre lines for the straight side-pipe runs on either side of taper.
        canvas.line(left_pipe_start, cy, left_pipe_start + upstream_len, cy, stroke="#999999", stroke_w=1, dasharray="6,6", stroke_opacity=0.5)
        canvas.line(right_pipe_start, cy, right_pipe_start + downstream_len, cy, stroke="#999999", stroke_w=1, dasharray="6,6", stroke_opacity=0.5)

        # Draw the reducer body on top of the pipe runs.
        canvas.place_fitting_local(
            canvas.make_port(taper_start_x, cy, 1, 0),
            lambda: taper_local(canvas, taper_len, pipe_large, pipe_small, wall=1.0),
        )

        # Draw joints/flanges last so they remain visually legible over the pipe.
        canvas.place_fitting_local(
            canvas.make_port(left_socket_start, cy, 1, 0),
            lambda: draw_plan_single_socket(
                canvas,
                diameter_px=pipe_large,
                socket_w_px=socket_large_w,
                height_factor=1.12,
            ),
        )
        canvas.place_fitting_local(
            canvas.make_port(left_flange_start, cy, 1, 0),
            lambda: draw_plan_double_flange(
                canvas,
                diameter_px=pipe_large,
                flange_t_px=flange_t,
                flange_gap_px=flange_gap,
                height_factor=1.25,
            ),
        )
        canvas.place_fitting_local(
            canvas.make_port(right_flange_start, cy, 1, 0),
            lambda: draw_plan_double_flange(
                canvas,
                diameter_px=pipe_small,
                flange_t_px=flange_t,
                flange_gap_px=flange_gap,
                height_factor=1.25,
            ),
        )
        canvas.place_fitting_local(
            canvas.make_port(right_socket_start, cy, 1, 0),
            lambda: draw_plan_single_socket(
                canvas,
                diameter_px=pipe_small,
                socket_w_px=socket_small_w,
                height_factor=1.12,
            ),
        )

        draw_horizontal_dim(canvas, left, left + block_w, top + block_h + 34.0, f'L = {self._block.length:.1f} m')
        w_dim_x = min(self._canvas_w - 12.0, max(left + block_w + 34.0, self._canvas_w - 26.0))
        draw_vertical_dim(
            canvas,
            w_dim_x,
            top,
            top + block_h,
            f'W = {self._block.width:.1f}m',
            text_dx=-8.0,
            text_anchor="end",
        )
        canvas.text(cx, self._canvas_h - 16, "Plan", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
        return _drawing_from_canvas("plan", canvas, view=DrawingView.PLAN, kind=DrawingKind.PLAN)

    def _build_section(self) -> SVGDrawing:
        canvas = SVGCanvas(scale=1.0, width=self._canvas_w, height=self._canvas_h)
        m_to_px = 46.0
        cx = self._canvas_w / 2
        cy = self._canvas_h / 2
        sec_w = self._block.width * m_to_px
        sec_h = self._block.height * m_to_px
        left = cx - sec_w / 2
        top = cy - sec_h / 2
        right = left + sec_w
        bottom = top + sec_h
        pipe_r = self._taper.outside_diameter_large * m_to_px / 2
        crown_y = cy - pipe_r
        ground_y = crown_y - self._depth_crown * m_to_px
        gw_y = ground_y + self._gw_level * m_to_px
        canvas.rect(left, top, sec_w, sec_h, fill="#d9d9d9", stroke="black", stroke_w=2)
        canvas.line(20.0, ground_y, self._canvas_w - 20.0, ground_y, stroke="black", stroke_w=2)
        canvas.line(20.0, gw_y, self._canvas_w - 20.0, gw_y, stroke="#42a5f5", stroke_w=1, dasharray="8,6")
        canvas.circle(cx, cy, pipe_r, fill="white", stroke="black", stroke_w=2)
        draw_vertical_dim(canvas, left - 56.0, ground_y, gw_y, f'Z_GW = {self._gw_level:.1f}m', color="#42a5f5", text_dx=-8.0, text_anchor="end")
        draw_vertical_dim(canvas, cx + 28.0, ground_y, crown_y, f'Z_0 = {self._depth_crown:.1f}m')
        draw_vertical_dim(canvas, right + 32.0, top, bottom, f'H = {self._block.height:.1f}m')
        draw_vertical_dim(canvas, right + 98.0, ground_y, bottom, f'Z_b = {self._block.depth:.1f}m')
        draw_horizontal_dim(canvas, left, right, bottom + 16.0, f'W = {self._block.width:.1f}m')
        canvas.text(left + sec_w / 2, bottom + 64, "Section A-A", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
        return _drawing_from_canvas("section", canvas, view=DrawingView.SECTION, kind=DrawingKind.SECTION)


class HorizontalBendSVGWriter:
    @classmethod
    def build(
        cls,
        calculation: HorizontalBendCalculationLike,
        options: DrawingOptions | None = None,
    ) -> list[SVGDrawing]:
        options = options or DrawingOptions()
        thrust_block = _require_thrust_block(calculation.soil_type)
        _ = calculation.thrust_force_resultant
        start_angle = options.start_angle_deg if options.start_angle_deg is not None else -(calculation.component.angle / 2)
        return cls(
            thrust_block=thrust_block,
            bend=calculation.component,
            canvas_w=options.canvas_width,
            canvas_h=options.canvas_height,
            depth_crown=calculation.crown_depth,
            gw_level=calculation.soil_type.ground_water_level,
            start_angle=start_angle,
        ).drawings()

    def __init__(
        self,
        thrust_block: ThrustBlockLike,
        bend: BendLike,
        canvas_w: int,
        canvas_h: int,
        depth_crown: float,
        gw_level: float,
        start_angle: float,
    ) -> None:
        self._block = thrust_block
        self._bend = bend
        self._canvas_w = canvas_w
        self._canvas_h = canvas_h
        self._depth_crown = depth_crown
        self._gw_level = gw_level
        self._start_angle = start_angle

    def drawings(self) -> list[SVGDrawing]:
        return [self._build_plan()]

    def _build_plan(self) -> SVGDrawing:
        canvas = SVGCanvas(scale=1.0, width=self._canvas_w, height=self._canvas_h)
        m_to_px = 46.0
        bend_diameter = self._bend.outside_diameter * m_to_px
        bend_radius = max(bend_diameter * 1.35, 62.0)
        bend_geometry = BendGeometry.from_params(radius_px=bend_radius, angle_deg=self._bend.angle)
        plan_target = Point(canvas.centre.x, canvas.centre.y - 10.0)
        thrust_angle_deg = math.degrees(math.atan2(bend_geometry.normalized_resultant_thrust_vector.y, bend_geometry.normalized_resultant_thrust_vector.x))
        placement = FittingPlacement.anchor_at(
            local_anchor=bend_geometry.arc_midpoint,
            target=plan_target,
            orientation_deg=-thrust_angle_deg,
        )
        bend_ports = self._draw_plan_bend_and_sockets(canvas, m_to_px, bend_diameter, bend_radius, bend_geometry, placement)
        self._draw_plan_restraint(canvas, m_to_px, bend_diameter, bend_geometry, placement)
        canvas.text(canvas.centre.x, self._canvas_h - 16.0, "Plan", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
        return _drawing_from_canvas("plan", canvas, view=DrawingView.PLAN, kind=DrawingKind.PLAN)

    def _draw_plan_bend_and_sockets(
        self,
        canvas: SVGCanvasType,
        m_to_px: float,
        bend_diameter: float,
        bend_radius: float,
        bend_geometry: BendGeometryType,
        placement: FittingPlacementType,
    ) -> list[PortType]:
        with canvas.group(placement.svg_transform()):
            bend_local(canvas, radius_px=bend_radius, diameter_px=bend_diameter, angle_deg=self._bend.angle)
        bend_ports = [placement.transform_port(bend_geometry.inlet_port), placement.transform_port(bend_geometry.outlet_port)]
        inlet_port = bend_ports[0]
        upstream_socket_length_px = 1.5 * m_to_px
        canvas.place_fitting_local(
            inlet_port,
            lambda: socket_pipe_local(canvas, length=upstream_socket_length_px, diameter=bend_diameter, socket_length=upstream_socket_length_px * 0.15, socket_od=bend_diameter * 1.12, is_inlet=True),
        )[0]
        downstream_socket_length_px = 1.5 * m_to_px
        downstream_socket_ports = canvas.place_fitting_local(
            bend_ports[1],
            lambda: socket_pipe_local(canvas, length=downstream_socket_length_px, diameter=bend_diameter, socket_length=downstream_socket_length_px * 0.15, socket_od=bend_diameter * 1.12, is_inlet=False, draw_barrel=False),
        )
        canvas.pipe_from_port(downstream_socket_ports[1], length=1.5 * m_to_px, diameter=bend_diameter)
        return bend_ports

    def _draw_plan_restraint(
        self,
        canvas: SVGCanvasType,
        m_to_px: float,
        bend_diameter: float,
        bend_geometry: BendGeometryType,
        placement: FittingPlacementType,
    ) -> None:
        contact_point = placement.transform_point(bend_geometry.arc_midpoint)
        thrust_ux, thrust_uy = (1.0, 0.0)
        wall_x = contact_point.x + thrust_ux * (bend_diameter / 2)
        wall_y = contact_point.y + thrust_uy * (bend_diameter / 2)
        block_length_px = self._block.length * m_to_px
        block_width_px = self._block.width * m_to_px
        block_cx = wall_x + thrust_ux * (block_length_px / 2)
        block_cy = wall_y + thrust_uy * (block_length_px / 2)
        block_vx = -thrust_uy
        block_vy = thrust_ux
        canvas.polygon(self._plan_block_points(block_cx, block_cy, block_vx, block_vy, thrust_ux, thrust_uy, block_width_px, block_length_px), fill="#d9d9d9", stroke="black", stroke_w=2)
        self._draw_plan_arrow(canvas, wall_x, wall_y, thrust_ux, thrust_uy)

    def _plan_block_points(self, block_cx: float, block_cy: float, block_vx: float, block_vy: float, thrust_ux: float, thrust_uy: float, block_width_px: float, block_length_px: float) -> list[tuple[float, float]]:
        return [
            (block_cx - block_vx * (block_width_px / 2) - thrust_ux * (block_length_px / 2), block_cy - block_vy * (block_width_px / 2) - thrust_uy * (block_length_px / 2)),
            (block_cx + block_vx * (block_width_px / 2) - thrust_ux * (block_length_px / 2), block_cy + block_vy * (block_width_px / 2) - thrust_uy * (block_length_px / 2)),
            (block_cx + block_vx * (block_width_px / 2) + thrust_ux * (block_length_px / 2), block_cy + block_vy * (block_width_px / 2) + thrust_uy * (block_length_px / 2)),
            (block_cx - block_vx * (block_width_px / 2) + thrust_ux * (block_length_px / 2), block_cy - block_vy * (block_width_px / 2) + thrust_uy * (block_length_px / 2)),
        ]

    def _draw_plan_arrow(self, canvas: SVGCanvasType, wall_x: float, wall_y: float, thrust_ux: float, thrust_uy: float) -> None:
        arrow_len = 92.0
        head_len = 14.0
        head_base_x = wall_x - thrust_ux * head_len
        head_base_y = wall_y - thrust_uy * head_len
        shaft_start_x = wall_x - thrust_ux * arrow_len
        shaft_start_y = wall_y - thrust_uy * arrow_len
        canvas.line(shaft_start_x, shaft_start_y, head_base_x, head_base_y, stroke="#d32f2f", stroke_w=2.3)
        canvas.polygon([(wall_x, wall_y), (head_base_x - thrust_uy * 7.0, head_base_y + thrust_ux * 7.0), (head_base_x + thrust_uy * 7.0, head_base_y - thrust_ux * 7.0)], fill="#d32f2f", stroke="#d32f2f", stroke_w=1)
        canvas.text(shaft_start_x - 16.0, (shaft_start_y + head_base_y) / 2, "T", fill="#d32f2f", font_size=18, font_family="Arial, sans-serif", text_anchor="middle", dominant_baseline="middle")

    def _build_section(self) -> SVGDrawing:
        canvas = SVGCanvas(scale=1.0, width=self._canvas_w, height=self._canvas_h)
        m_to_px = 46.0
        cx = self._canvas_w / 2
        cy = self._canvas_h / 2
        sec_w = self._block.width * m_to_px
        sec_h = self._block.height * m_to_px
        left = cx - sec_w / 2
        top = cy - sec_h / 2
        right = left + sec_w
        bottom = top + sec_h
        pipe_r = self._bend.outside_diameter * m_to_px / 2
        crown_y = cy - pipe_r
        ground_y = crown_y - self._depth_crown * m_to_px
        gw_y = ground_y + self._gw_level * m_to_px
        canvas.rect(left, top, sec_w, sec_h, fill="#d9d9d9", stroke="black", stroke_w=2)
        canvas.line(20.0, ground_y, self._canvas_w - 20.0, ground_y, stroke="black", stroke_w=2)
        canvas.line(20.0, gw_y, self._canvas_w - 20.0, gw_y, stroke="#42a5f5", stroke_w=1, dasharray="8,6")
        canvas.circle(cx, cy, pipe_r, fill="white", stroke="black", stroke_w=2)
        draw_vertical_dim(canvas, left - 56.0, ground_y, gw_y, f'Z_GW = {self._gw_level:.1f}m', color="#42a5f5", text_dx=-8.0, text_anchor="end")
        draw_vertical_dim(canvas, cx + 28.0, ground_y, crown_y, f'Z_0 = {self._depth_crown:.1f}m')
        draw_vertical_dim(canvas, right + 32.0, top, bottom, f'H = {self._block.height:.1f}m')
        draw_vertical_dim(canvas, right + 98.0, ground_y, bottom, f'Z_b = {(bottom - ground_y) / m_to_px:.1f}m')
        draw_horizontal_dim(canvas, left, right, bottom + 16.0, f'W = {self._block.width:.1f}m')
        canvas.text(left + sec_w / 2, bottom + 64, "Section A-A", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
        return _drawing_from_canvas("section", canvas, view=DrawingView.SECTION, kind=DrawingKind.SECTION)

    def _normalized_components(self, x: float, y: float) -> tuple[float, float]:
        length = math.hypot(x, y)
        if length == 0:
            return (1.0, 0.0)
        return (x / length, y / length)


class VerticalBendSVGWriter:
    @classmethod
    def build(
        cls,
        calculation: VerticalBendCalculationLike,
        options: DrawingOptions | None = None,
    ) -> list[SVGDrawing]:
        options = options or DrawingOptions()
        thrust_block = _require_thrust_block(calculation.soil_type)
        _ = calculation.thrust_force_resultant
        bend_orientation = options.bend_orientation_deg if options.bend_orientation_deg is not None else 90.0
        return cls(
            thrust_block=thrust_block,
            bend=calculation.component,
            canvas_w=options.canvas_width,
            canvas_h=options.canvas_height,
            depth_crown=calculation.crown_depth,
            gw_level=calculation.soil_type.ground_water_level,
            bend_orientation=bend_orientation,
        ).drawings()

    def __init__(
        self,
        thrust_block: ThrustBlockLike,
        bend: BendLike,
        canvas_w: int,
        canvas_h: int,
        depth_crown: float,
        gw_level: float,
        bend_orientation: float = 90.0,
    ) -> None:
        self._block = thrust_block
        self._bend = bend
        self._canvas_w = canvas_w
        self._canvas_h = canvas_h
        self._depth_crown = depth_crown
        self._gw_level = gw_level
        self._bend_orientation = bend_orientation

    def drawings(self) -> list[SVGDrawing]:
        return [self._build_longitudinal_section()]

    def downturn_drawings(self) -> list[SVGDrawing]:
        return [self._build_downturn_longitudinal_section()]

    def _build_longitudinal_section(self) -> SVGDrawing:
        canvas = SVGCanvas(scale=1.0, width=self._canvas_w, height=self._canvas_h)
        m_to_px = 46.0
        # Keep the thrust-block arrangement fixed to the approved template,
        # while letting the bend itself follow the requested angle.
        block_template_angle_deg = 45.0
        bend_diameter = self._bend.outside_diameter * m_to_px
        bend_radius = max(bend_diameter * 1.35, 62.0)
        bend_geometry = BendGeometry.from_params(radius_px=bend_radius, angle_deg=self._bend.angle)
        bend_contact_x = bend_geometry.arc_midpoint.x + bend_geometry.outside_radial_direction.x * (bend_diameter / 2)
        bend_contact_y = bend_geometry.arc_midpoint.y + bend_geometry.outside_radial_direction.y * (bend_diameter / 2)
        placement = FittingPlacement.anchor_at(
            local_anchor=bend_geometry.arc_midpoint,
            target=canvas.centre,
            orientation_deg=self._bend_orientation - 90.0,
        )

        inlet_wall_point_a = placement.transform_point(Point(bend_geometry.inlet_point.x, bend_geometry.inlet_point.y - (bend_diameter / 2)))
        inlet_wall_point_b = placement.transform_point(Point(bend_geometry.inlet_point.x, bend_geometry.inlet_point.y + (bend_diameter / 2)))
        # Z0 must terminate at the *upper* inlet crown point in global section coordinates.
        inlet_crown_global = inlet_wall_point_a if inlet_wall_point_a.y <= inlet_wall_point_b.y else inlet_wall_point_b
        z0_dim_x = inlet_crown_global.x
        crown_y = inlet_crown_global.y
        ground_y = crown_y - self._depth_crown * m_to_px
        gw_y = ground_y + self._gw_level * m_to_px
        canvas.line(20.0, ground_y, self._canvas_w - 20.0, ground_y, stroke="black", stroke_w=2)
        canvas.line(20.0, gw_y, self._canvas_w - 20.0, gw_y, stroke="#42a5f5", stroke_w=1, dasharray="8,6")

        ground_marker_x = 56.0
        ground_marker_half_w = 6.0
        ground_marker_h = 8.0
        canvas.polygon(
            [
                (ground_marker_x - ground_marker_half_w, ground_y - ground_marker_h),
                (ground_marker_x + ground_marker_half_w, ground_y - ground_marker_h),
                (ground_marker_x, ground_y),
            ],
            fill="black",
            stroke="black",
            stroke_w=1,
        )
        canvas.text(
            ground_marker_x + 12.0,
            ground_y - 10.0,
            "Ground Level",
            fill="black",
            font_size=12,
            font_family="Arial, sans-serif",
            text_anchor="start",
            dominant_baseline="middle",
        )

        # Keep T anchored at the bend contact and place the thrust block so the
        # diagonal-cut midpoint matches that fixed anchor for each bend angle.
        thrust_anchor_x = bend_contact_x
        thrust_anchor_y = bend_contact_y
        _, _, thrust_dir_x, thrust_dir_y = _upturn_cut_and_thrust_unit_vectors(self._bend.angle)

        with canvas.group(placement.svg_transform()):
            contact_x, contact_y, block_left, block_right, block_top, block_bottom = thrust_block_for_upturn_bend_local(
                canvas,
                radius_px=bend_radius,
                diameter_px=bend_diameter,
                angle_deg=block_template_angle_deg,
                block_width_px=self._block.length * m_to_px,
                block_height_px=self._block.height * m_to_px,
                cut_midpoint=(thrust_anchor_x, thrust_anchor_y),
                cut_angle_deg=self._bend.angle,
            )
            bend_ports = bend_local(
                canvas,
                radius_px=bend_radius,
                diameter_px=bend_diameter,
                angle_deg=self._bend.angle,
            )
            inlet_socket_length_px = 1.25 * m_to_px
            canvas.place_fitting_local(
                bend_ports[0],
                lambda: socket_pipe_local(
                    canvas,
                    length=inlet_socket_length_px,
                    diameter=bend_diameter,
                    socket_length=inlet_socket_length_px * 0.18,
                    socket_od=bend_diameter * 1.12,
                    is_inlet=True,
                ),
            )
            outlet_socket_length_px = 1.25 * m_to_px
            outlet_socket_ports = canvas.place_fitting_local(
                bend_ports[1],
                lambda: socket_pipe_local(
                    canvas,
                    length=outlet_socket_length_px,
                    diameter=bend_diameter,
                    socket_length=outlet_socket_length_px * 0.18,
                    socket_od=bend_diameter * 1.12,
                    is_inlet=False,
                    draw_barrel=False,
                ),
            )
            canvas.pipe_from_port(outlet_socket_ports[1], length=1.1 * m_to_px, diameter=bend_diameter)
            thrust_component_arrows_for_bend_local(
                canvas,
                origin_x=thrust_anchor_x,
                origin_y=thrust_anchor_y,
                tx_len_px=56.0,
                tz_len_px=56.0,
                t_len_px=82.0,
                t_direction_x=thrust_dir_x,
                t_direction_y=thrust_dir_y,
                component_dasharray="6,4",
            )

        block_points = [
            placement.transform_point(Point(block_left, block_top)),
            placement.transform_point(Point(block_right, block_top)),
            placement.transform_point(Point(block_right, block_bottom)),
            placement.transform_point(Point(block_left, block_bottom)),
        ]
        block_global_left = min(point.x for point in block_points)
        block_global_right = max(point.x for point in block_points)
        block_global_top = min(point.y for point in block_points)
        block_global_bottom = max(point.y for point in block_points)

        # Keep the longitudinal L-dimension line below the thrust-arrow envelope.
        t_tip_local = Point(thrust_anchor_x + (82.0 * thrust_dir_x), thrust_anchor_y + (82.0 * thrust_dir_y))
        tz_label_len = math.hypot(4.0, 14.0)
        tz_tip_local = Point(thrust_anchor_x, thrust_anchor_y + 56.0)
        tz_label_anchor_local = Point(
            tz_tip_local.x + (4.0 / tz_label_len) * 12.0,
            tz_tip_local.y + (14.0 / tz_label_len) * 12.0,
        )
        t_label_len = math.hypot(thrust_dir_x, thrust_dir_y)
        t_label_anchor_local = Point(
            t_tip_local.x + (thrust_dir_x / t_label_len) * 12.0,
            t_tip_local.y + (thrust_dir_y / t_label_len) * 12.0,
        )
        arrow_envelope_points = [
            placement.transform_point(Point(thrust_anchor_x + 56.0, thrust_anchor_y)),
            placement.transform_point(Point(thrust_anchor_x, thrust_anchor_y + 56.0)),
            placement.transform_point(t_tip_local),
            placement.transform_point(tz_label_anchor_local),
            placement.transform_point(t_label_anchor_local),
        ]
        arrow_envelope_max_y = max(point.y for point in arrow_envelope_points) + 10.0
        l_dim_y = max(block_global_bottom + 16.0, arrow_envelope_max_y + 20.0)

        draw_vertical_dim(canvas, block_global_left - 50.0, ground_y, gw_y, f'Z_GW = {self._gw_level:.1f}m', color="#42a5f5", text_dx=-8.0, text_anchor="end")
        draw_vertical_dim(canvas, z0_dim_x, ground_y, crown_y, f'Z_0 = {self._depth_crown:.1f}m')
        draw_vertical_dim(canvas, block_global_right + 30.0, block_global_top, block_global_bottom, f'H = {self._block.height:.1f}m')
        draw_vertical_dim(canvas, block_global_right + 96.0, ground_y, block_global_bottom, f'Z_b = {self._block.depth:.1f}m')
        draw_horizontal_dim(
            canvas,
            block_global_left,
            block_global_right,
            l_dim_y,
            f'L = {self._block.length:.1f}m',
            label_padding_px=18.0,
        )
        canvas.text(
            canvas.centre.x,
            self._canvas_h - 16.0,
            "Vertical Upturn Bend",
            fill="black",
            font_size=13,
            font_family="Arial, sans-serif",
            text_anchor="middle",
        )

        return _drawing_from_canvas(
            "section",
            canvas,
            view=DrawingView.SECTION,
            kind=DrawingKind.VERTICAL_UPTURN_LONGITUDINAL,
        )

    def _build_section_a_a(self) -> SVGDrawing:
        canvas = SVGCanvas(scale=1.0, width=self._canvas_w, height=self._canvas_h)
        m_to_px = 46.0
        cx = self._canvas_w / 2
        cy = self._canvas_h / 2
        sec_w = self._block.width * m_to_px
        sec_h = self._block.height * m_to_px
        left = cx - sec_w / 2
        top = cy - sec_h / 2
        right = left + sec_w
        bottom = top + sec_h
        pipe_r = self._bend.outside_diameter * m_to_px / 2
        crown_y = cy - pipe_r
        ground_y = crown_y - self._depth_crown * m_to_px
        gw_y = ground_y + self._gw_level * m_to_px
        canvas.rect(left, top, sec_w, sec_h, fill="#d9d9d9", stroke="black", stroke_w=2)
        canvas.line(20.0, ground_y, self._canvas_w - 20.0, ground_y, stroke="black", stroke_w=2)
        canvas.line(20.0, gw_y, self._canvas_w - 20.0, gw_y, stroke="#42a5f5", stroke_w=1, dasharray="8,6")
        canvas.circle(cx, cy, pipe_r, fill="white", stroke="black", stroke_w=2)
        draw_vertical_dim(canvas, left - 56.0, ground_y, gw_y, f'Z_GW = {self._gw_level:.1f}m', color="#42a5f5", text_dx=-8.0, text_anchor="end")
        draw_vertical_dim(canvas, cx + 28.0, ground_y, crown_y, f'Z_0 = {self._depth_crown:.1f}m')
        draw_vertical_dim(canvas, right + 32.0, top, bottom, f'H = {self._block.height:.1f}m')
        draw_vertical_dim(canvas, right + 98.0, ground_y, bottom, f'Z_b = {(bottom - ground_y) / m_to_px:.1f}m')
        draw_horizontal_dim(canvas, left, right, bottom + 16.0, f'W = {self._block.width:.1f}m')
        canvas.text(left + sec_w / 2, bottom + 64, "Section A-A", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
        return _drawing_from_canvas(
            "section_a_a",
            canvas,
            view=DrawingView.SECTION,
            kind=DrawingKind.THRUST_BLOCK_SECTION_A_A,
        )

    def _build_downturn_longitudinal_section(self) -> SVGDrawing:
        canvas = SVGCanvas(scale=1.0, width=self._canvas_w, height=self._canvas_h)
        m_to_px = 46.0
        bend_diameter = self._bend.outside_diameter * m_to_px
        bend_radius = max(bend_diameter * 1.35, 62.0)
        bend_geometry = BendGeometry.from_params(radius_px=bend_radius, angle_deg=self._bend.angle)

        # Rotate the local upturn bend geometry into a downturn profile and keep
        # the bend midpoint anchored at canvas centre.
        placement = FittingPlacement.anchor_at(
            local_anchor=bend_geometry.arc_midpoint,
            target=canvas.centre,
            orientation_deg=-180.0,
        )

        inlet_center_global = placement.transform_point(bend_geometry.inlet_point)
        inlet_wall_point_a = placement.transform_point(Point(bend_geometry.inlet_point.x, bend_geometry.inlet_point.y - (bend_diameter / 2)))
        inlet_wall_point_b = placement.transform_point(Point(bend_geometry.inlet_point.x, bend_geometry.inlet_point.y + (bend_diameter / 2)))
        z0_dim_x = inlet_center_global.x + max(14.0, 0.30 * m_to_px)
        crown_y = min(inlet_wall_point_a.y, inlet_wall_point_b.y)
        ground_y = crown_y - self._depth_crown * m_to_px
        gw_y = ground_y + self._gw_level * m_to_px

        canvas.line(20.0, ground_y, self._canvas_w - 20.0, ground_y, stroke="black", stroke_w=2)
        canvas.line(20.0, gw_y, self._canvas_w - 20.0, gw_y, stroke="#42a5f5", stroke_w=1, dasharray="8,6")

        ground_marker_x = 56.0
        ground_marker_half_w = 6.0
        ground_marker_h = 8.0
        canvas.polygon(
            [
                (ground_marker_x - ground_marker_half_w, ground_y - ground_marker_h),
                (ground_marker_x + ground_marker_half_w, ground_y - ground_marker_h),
                (ground_marker_x, ground_y),
            ],
            fill="black",
            stroke="black",
            stroke_w=1,
        )
        canvas.text(
            ground_marker_x + 12.0,
            ground_y - 10.0,
            "Ground level",
            fill="black",
            font_size=12,
            font_family="Arial, sans-serif",
            text_anchor="start",
            dominant_baseline="middle",
        )

        block_len_px = self._block.length * m_to_px
        block_h_px = self._block.height * m_to_px
        block_local_left = bend_geometry.arc_midpoint.x - (block_len_px / 2)
        block_local_right = bend_geometry.arc_midpoint.x + (block_len_px / 2)
        block_local_top = bend_geometry.arc_midpoint.y - (block_h_px / 2)
        block_local_bottom = bend_geometry.arc_midpoint.y + (block_h_px / 2)

        with canvas.group(placement.svg_transform()):
            # Draw concrete as an enclosing block around the fitting footprint,
            # matching the taper-thrust style arrangement.
            canvas.rect(
                block_local_left,
                block_local_top,
                block_local_right - block_local_left,
                block_local_bottom - block_local_top,
                fill="#d9d9d9",
                stroke="black",
                stroke_w=2,
            )

            bend_ports = bend_local(
                canvas,
                radius_px=bend_radius,
                diameter_px=bend_diameter,
                angle_deg=self._bend.angle,
            )

            flange_projection_px = max(7.0, 0.18 * m_to_px)
            flange_thickness_px = max(6.0, 0.14 * m_to_px)

            inlet_flange_ports = canvas.place_fitting_local(
                bend_ports[0],
                lambda: flange_local(
                    canvas,
                    diameter_px=bend_diameter,
                    projection_px=flange_projection_px,
                    thickness_px=flange_thickness_px,
                    flange_width_ratio=1.2,
                ),
            )
            canvas.pipe_from_port(inlet_flange_ports[0], length=1.0 * m_to_px, diameter=bend_diameter)

            outlet_flange_ports = canvas.place_fitting_local(
                bend_ports[1],
                lambda: flange_local(
                    canvas,
                    diameter_px=bend_diameter,
                    projection_px=flange_projection_px,
                    thickness_px=flange_thickness_px,
                    flange_width_ratio=1.2,
                ),
            )
            canvas.pipe_from_port(outlet_flange_ports[1], length=1.0 * m_to_px, diameter=bend_diameter)

            reinforcement_margin_x = min(24.0, max(10.0, block_len_px * 0.10))
            reinforcement_margin_y = min(20.0, max(8.0, block_h_px * 0.10))
            inner_left = block_local_left + reinforcement_margin_x
            inner_right = block_local_right - reinforcement_margin_x
            inner_top = block_local_top + reinforcement_margin_y
            inner_bottom = block_local_bottom - reinforcement_margin_y

            if inner_right > inner_left and inner_bottom > inner_top:
                canvas.rect(
                    inner_left,
                    inner_top,
                    inner_right - inner_left,
                    inner_bottom - inner_top,
                    fill="none",
                    stroke="#4d4d4d",
                    stroke_w=1.2,
                    dasharray="6,5",
                )

            contact_x = bend_geometry.arc_midpoint.x
            contact_y = bend_geometry.arc_midpoint.y
            thrust_component_arrows_for_bend_local(
                canvas,
                origin_x=contact_x,
                origin_y=contact_y,
                tx_len_px=56.0,
                tz_len_px=56.0,
                t_len_px=82.0,
                t_direction_x=bend_geometry.normalized_resultant_thrust_vector.x,
                t_direction_y=bend_geometry.normalized_resultant_thrust_vector.y,
                label_rotation_deg=180.0,
            )

        block_global_left = canvas.centre.x - (block_len_px / 2)
        block_global_right = canvas.centre.x + (block_len_px / 2)
        block_global_top = canvas.centre.y - (block_h_px / 2)
        block_global_bottom = canvas.centre.y + (block_h_px / 2)

        t_direction_len = math.hypot(1.0, 1.0)
        t_tip_local = Point(contact_x + (82.0 / t_direction_len), contact_y + (82.0 / t_direction_len))
        tz_label_len = math.hypot(4.0, 14.0)
        tz_tip_local = Point(contact_x, contact_y + 56.0)
        tz_label_anchor_local = Point(
            tz_tip_local.x + (4.0 / tz_label_len) * 12.0,
            tz_tip_local.y + (14.0 / tz_label_len) * 12.0,
        )
        t_label_len = math.hypot(8.0, 12.0)
        t_label_anchor_local = Point(
            t_tip_local.x + (8.0 / t_label_len) * 12.0,
            t_tip_local.y + (12.0 / t_label_len) * 12.0,
        )
        arrow_envelope_points = [
            placement.transform_point(Point(contact_x + 56.0, contact_y)),
            placement.transform_point(Point(contact_x, contact_y + 56.0)),
            placement.transform_point(t_tip_local),
            placement.transform_point(tz_label_anchor_local),
            placement.transform_point(t_label_anchor_local),
        ]
        arrow_envelope_max_y = max(point.y for point in arrow_envelope_points) + 10.0
        l_dim_y = max(block_global_bottom + 16.0, arrow_envelope_max_y + 20.0)

        draw_vertical_dim(canvas, block_global_left - 50.0, ground_y, gw_y, f'Z_GW = {self._gw_level:.1f}m', color="#42a5f5", text_dx=-8.0, text_anchor="end")
        draw_vertical_dim(canvas, z0_dim_x, ground_y, crown_y, f'Z_0 = {self._depth_crown:.1f}m')
        draw_vertical_dim(canvas, block_global_right + 30.0, block_global_top, block_global_bottom, f'H = {self._block.height:.1f}m')
        z_b_drawn_m = (block_global_bottom - ground_y) / m_to_px
        draw_vertical_dim(canvas, block_global_right + 96.0, ground_y, block_global_bottom, f'Z_b = {z_b_drawn_m:.1f}m')
        draw_horizontal_dim(
            canvas,
            block_global_left,
            block_global_right,
            l_dim_y,
            f'L = {self._block.length:.1f}m',
            label_padding_px=18.0,
        )
        canvas.text(
            canvas.centre.x,
            self._canvas_h - 16.0,
            "Vertical Downturn Bend",
            fill="black",
            font_size=13,
            font_family="Arial, sans-serif",
            text_anchor="middle",
        )

        return _drawing_from_canvas(
            "section_downturn",
            canvas,
            view=DrawingView.SECTION,
            kind=DrawingKind.VERTICAL_DOWNTURN_LONGITUDINAL,
        )


class VerticalDownturnBendSVGWriter(VerticalBendSVGWriter):
    @classmethod
    def build(
        cls,
        calculation: VerticalBendCalculationLike,
        options: DrawingOptions | None = None,
    ) -> list[SVGDrawing]:
        options = options or DrawingOptions()
        thrust_block = _require_thrust_block(calculation.soil_type)
        _ = calculation.thrust_force_resultant
        bend_orientation = options.bend_orientation_deg if options.bend_orientation_deg is not None else 90.0
        return cls(
            thrust_block=thrust_block,
            bend=calculation.component,
            canvas_w=options.canvas_width,
            canvas_h=options.canvas_height,
            depth_crown=calculation.crown_depth,
            gw_level=calculation.soil_type.ground_water_level,
            bend_orientation=bend_orientation,
        ).downturn_drawings()


def socket_pipe_local(
    canvas: SVGCanvasType,
    length: float,
    diameter: float,
    socket_length: float,
    socket_od: float,
    is_inlet: bool = True,
    draw_barrel: bool = True,
) -> list[PortType]:
    """
    Socketed pipe section in local coordinates.

    Returns
    -------
    list[Port]
        [inlet_port, outlet_port]
    """

    if is_inlet:
        # Inlet socket is anchored at bend port (x=0) and drawn upstream (negative x).
        barrel_x = -length
        barrel_w = length
        points = (
            f'0,{-diameter/2:.2f} '
            f'-{socket_length:.2f},{-socket_od/2:.2f} '
            f'-{socket_length:.2f},{socket_od/2:.2f} '
            f'0,{diameter/2:.2f}'
        )
        centreline_x1 = -length
        centreline_x2 = 0
        ports = [
            canvas.make_port(-length, 0, -1, 0),
            canvas.make_port(0, 0, 1, 0),
        ]
    else:
        # Outlet socket is anchored at bend port (x=0) and drawn downstream (positive x).
        barrel_x = 0
        barrel_w = length
        points = (
            f'0,{-diameter/2:.2f} '
            f'{socket_length:.2f},{-socket_od/2:.2f} '
            f'{socket_length:.2f},{socket_od/2:.2f} '
            f'0,{diameter/2:.2f}'
        )
        centreline_x1 = 0
        centreline_x2 = socket_length
        ports = [
            canvas.make_port(0, 0, -1, 0),
            canvas.make_port(socket_length, 0, 1, 0),
        ]

    if draw_barrel:
        canvas.rect(
            x=barrel_x,
            y=-diameter / 2,
            w=barrel_w,
            h=diameter,
            fill=canvas.pipe_fill,
            stroke=canvas.pipe_stroke,
            stroke_w=2,
        )

    # Bellmouth
    canvas.polygon(
        points=points,
        fill=canvas.pipe_fill,
        stroke=canvas.pipe_stroke,
        stroke_w=2,
    )

    # Centreline
    canvas.line(
        centreline_x1,
        0,
        centreline_x2,
        0,
        stroke="#999999",
        stroke_w=1,
        dasharray="6,6",
        stroke_opacity=0.5,
    )

    return ports


def bend_local(
    canvas: SVGCanvasType,
    radius_px: float,
    diameter_px: float,
    angle_deg: float,
) -> list[PortType]:
    """
    Upturn bend in LOCAL coordinates.

    Inlet:
        (0,0) tangent +X

    Positive angle bends upward in screen space (negative SVG Y).
    """
    geometry = BendGeometry.from_params(radius_px=radius_px, angle_deg=angle_deg)

    outline_width = 2

    # Bend outline
    canvas.path(
        geometry.path_d,
        stroke="black",
        stroke_w=diameter_px + outline_width,
        fill="none",
        stroke_linecap="butt",
    )

    # Bend body
    canvas.path(
        geometry.path_d,
        stroke="white",
        stroke_w=diameter_px - outline_width,
        fill="none",
        stroke_linecap="butt",
    )

    # Centreline
    canvas.path(
        geometry.path_d,
        stroke="#999999",
        stroke_w=1,
        dasharray="6,6",
        stroke_opacity=0.5,
        fill="none",
    )

    return [
        canvas.make_port(geometry.inlet_point.x, geometry.inlet_point.y, geometry.inlet_tangent.x, geometry.inlet_tangent.y),
        canvas.make_port(geometry.outlet_point.x, geometry.outlet_point.y, geometry.outlet_tangent.x, geometry.outlet_tangent.y),
    ]


def thrust_component_arrows_for_bend_local(
    canvas: SVGCanvasType,
    origin_x: float,
    origin_y: float,
    tx_len_px: float,
    tz_len_px: float,
    t_len_px: float,
    t_direction_x: float = 1,
    t_direction_y: float = 1,
    stroke: str = "#d32f2f",
    stroke_width: float = 1.5,
    label_rotation_deg: float | None = None,
    component_dasharray: str | None = None,
) -> None:
    """Draw Tx, Tz and resultant T arrows in red schematic style."""

    def _draw_arrow(
        x1: float,
        y1: float,
        ux: float,
        uy: float,
        length: float,
        label: str,
        label_dx: float,
        label_dy: float,
        label_padding_px: float = 12,
        head_length_px: float = 14,
        head_width_px: float = 10,
        line_dasharray: str | None = None,
    ) -> None:
        d = math.hypot(ux, uy)
        if d == 0:
            return

        ux = ux / d
        uy = uy / d
        vx = -uy
        vy = ux

        x2 = x1 + ux * length
        y2 = y1 + uy * length

        base_x = x2 - ux * head_length_px
        base_y = y2 - uy * head_length_px

        left_x = base_x + vx * (head_width_px / 2)
        left_y = base_y + vy * (head_width_px / 2)
        right_x = base_x - vx * (head_width_px / 2)
        right_y = base_y - vy * (head_width_px / 2)

        line_dash_attr = f' stroke-dasharray="{line_dasharray}"' if line_dasharray else ""

        canvas.line(
            x1,
            y1,
            base_x,
            base_y,
            stroke=stroke,
            stroke_w=stroke_width,
            dasharray=line_dasharray,
        )
        canvas.polygon(
            [(x2, y2), (left_x, left_y), (right_x, right_y)],
            fill=stroke,
            stroke=stroke,
            stroke_w=1,
        )

        # Keep a fixed gap between arrow tip and label while preserving label direction.
        label_dir_len = math.hypot(label_dx, label_dy)
        if label_dir_len == 0:
            label_ux, label_uy = vx, vy
        else:
            label_ux = label_dx / label_dir_len
            label_uy = label_dy / label_dir_len

        label_x = x2 + label_ux * label_padding_px
        label_y = y2 + label_uy * label_padding_px

        canvas.text(
            label_x,
            label_y,
            label,
            fill=stroke,
            font_size=11,
            font_family="Arial, sans-serif",
            text_anchor="middle",
            dominant_baseline="middle",
            transform=(f"rotate({label_rotation_deg:.1f} {label_x:.2f} {label_y:.2f})" if label_rotation_deg is not None else None),
        )

    _draw_arrow(origin_x, origin_y, 1, 0, tx_len_px, "T_x", 1, 0, line_dasharray=component_dasharray)
    _draw_arrow(origin_x, origin_y, 0, 1, tz_len_px, "T_z", 4, 14, line_dasharray=component_dasharray)
    _draw_arrow(origin_x, origin_y, t_direction_x, t_direction_y, t_len_px, "T", 8, 12)


def _upturn_cut_and_thrust_unit_vectors(theta_deg: float) -> tuple[float, float, float, float]:
    """Return cut-face and thrust unit vectors for a vertical upturn bend.

    For bend angle theta, the diagonal cut uses theta/2 and T is taken from the
    cut normal so T is always perpendicular to the cut face.
    """

    theta = math.radians(theta_deg)
    half_theta = theta / 2.0

    # SVG local axes: +x right, +y down.
    cut_ux = -math.cos(half_theta)
    cut_uy = math.sin(half_theta)

    normal_a = (-cut_uy, cut_ux)
    normal_b = (cut_uy, -cut_ux)

    # Align the selected normal with the bend resultant direction.
    resultant_x = 1.0 - math.cos(theta)
    resultant_y = math.sin(theta)
    resultant_len = math.hypot(resultant_x, resultant_y)
    if resultant_len > 0.0:
        resultant_x /= resultant_len
        resultant_y /= resultant_len

    dot_a = (normal_a[0] * resultant_x) + (normal_a[1] * resultant_y)
    dot_b = (normal_b[0] * resultant_x) + (normal_b[1] * resultant_y)
    thrust_ux, thrust_uy = normal_a if dot_a >= dot_b else normal_b

    return cut_ux, cut_uy, thrust_ux, thrust_uy


def thrust_block_for_upturn_bend_local(
    canvas: SVGCanvasType,
    radius_px: float,
    diameter_px: float,
    angle_deg: float,
    block_width_px: float,
    block_height_px: float,
    cut_midpoint: tuple[float, float] | None = None,
    cut_angle_deg: float | None = None,
) -> tuple[float, float, float, float, float, float]:
    """Draw an angle-dependent support block under an upturn bend.

    The bend midpoint on the outside wall is used as the thrust contact location.
    A single straight diagonal cut is used on the top-left corner.
    """

    theta = math.radians(angle_deg)

    # Use bend centreline midpoint first, then shift to the outside wall.
    mid_theta = theta / 2
    mid_x = radius_px * math.sin(mid_theta)
    mid_y = -radius_px * (1 - math.cos(mid_theta))

    # Arc centre for the upturn bend.
    cx = 0.0
    cy = -radius_px

    # Radial outward unit vector at arc midpoint.
    rx = mid_x - cx
    ry = mid_y - cy
    r_len = math.hypot(rx, ry)
    if r_len == 0:
        return (
            mid_x,
            mid_y,
            mid_x,
            mid_x + block_width_px,
            mid_y,
            mid_y + block_height_px,
        )

    ux = rx / r_len
    uy = ry / r_len

    # Outside wall contact point (centreline + OD/2).
    contact_x = mid_x + ux * (diameter_px / 2)
    contact_y = mid_y + uy * (diameter_px / 2)

    # `angle_deg` controls the template block arrangement, while `cut_angle_deg`
    # can override the diagonal-cut orientation to match the actual bend.
    cut_angle = cut_angle_deg if cut_angle_deg is not None else angle_deg

    # Diagonal cut orientation from theta/2.
    cut_ux, cut_uy, _, _ = _upturn_cut_and_thrust_unit_vectors(cut_angle)

    # Allow the diagonal-cut midpoint to be anchored to an external target
    # (e.g. actual bend contact for the current bend angle).
    diagonal_mid_x = contact_x if cut_midpoint is None else cut_midpoint[0]
    diagonal_mid_y = contact_y if cut_midpoint is None else cut_midpoint[1]

    # Build the diagonal so the chosen anchor lies on the face where T acts.
    # Keep the top edge anchored and let height changes extend the block bottom.
    min_cut_depth_px = max(12.0, diameter_px * 0.8)

    if abs(cut_uy) < 1e-9:
        # Fallback for near-horizontal cut directions.
        top = diagonal_mid_y - (block_height_px / 2.0)
        bottom = top + block_height_px
        left = diagonal_mid_x - (block_width_px / 2.0)
        right = left + block_width_px
        top_cut_x = diagonal_mid_x
        top_cut_y = top
        left_cut_x = left
        left_cut_y = diagonal_mid_y
    else:
        # d is the vertical distance from the anchor to the top cut endpoint.
        # Keep d independent of block height so the top stays fixed as height
        # changes, and only constrain by available width.
        max_d_from_width = (block_width_px / 2.0) * (abs(cut_uy) / abs(cut_ux)) if abs(cut_ux) >= 1e-9 else float("inf")

        max_d = max_d_from_width
        target_d = max(min_cut_depth_px / 2.0, 1.0)
        d = max(1e-6, min(target_d, max_d)) if max_d > 1e-6 else 1e-6

        top = diagonal_mid_y - d
        bottom = top + block_height_px

        top_param = (top - diagonal_mid_y) / cut_uy
        top_cut_x = diagonal_mid_x + top_param * cut_ux
        top_cut_y = top

        # Mirror the top-cut endpoint through the anchor to place the left-cut
        # endpoint so, in normal geometry ranges, the cut midpoint is the
        # thrust anchor itself.
        left = (2.0 * diagonal_mid_x) - top_cut_x
        right = left + block_width_px
        left_cut_x = left
        left_cut_y = (2.0 * diagonal_mid_y) - top

        if left_cut_y > bottom:
            # For unusually short blocks, keep the top fixed and clip the
            # left-cut endpoint at the block base along the same cut line.
            left_cut_y = bottom
            left_param = (left_cut_y - diagonal_mid_y) / cut_uy
            left_cut_x = diagonal_mid_x + left_param * cut_ux
            left = left_cut_x
            right = left + block_width_px

        # Numerical guardrails.
        left_cut_y = min(max(left_cut_y, top - 1e-9), bottom + 1e-9)

    # Simple block with one straight diagonal cut from left edge to top edge.
    p1 = (left, bottom)
    p2 = (right, bottom)
    p3 = (right, top)
    p4 = (top_cut_x, top_cut_y)
    p5 = (left_cut_x, left_cut_y)

    canvas.polygon([p1, p2, p3, p4, p5], fill="#d9d9d9", stroke="black", stroke_w=2)

    # Return thrust contact and block bounds for external annotation drawing.
    return (diagonal_mid_x, diagonal_mid_y, left, right, top, bottom)


def thrust_arrow_for_bend_local(
    canvas: SVGCanvasType,
    radius_px: float,
    angle_deg: float,
    offset_px: float = 0,
    length_px: float = 80,
    head_length_px: float = 18,
    head_width_px: float = 12,
    stroke: str = "#d32f2f",
    stroke_width: float = 2,
    label: str | None = "T",
) -> None:
    """
    Draw a thrust arrow for a bend in LOCAL coordinates.

    The arrow starts at the bend centreline midpoint and points in the
    resultant thrust direction (inlet tangent minus outlet tangent).
    """

    geometry = BendGeometry.from_params(radius_px=radius_px, angle_deg=angle_deg)
    thrust = geometry.normalized_resultant_thrust_vector
    if thrust.x == 0 and thrust.y == 0:
        return

    ux = thrust.x
    uy = thrust.y

    # Perpendicular vector for arrow head and optional label offset
    vx = -uy
    vy = ux

    start_x = geometry.arc_midpoint.x + ux * offset_px
    start_y = geometry.arc_midpoint.y + uy * offset_px
    end_x = start_x + ux * length_px
    end_y = start_y + uy * length_px

    base_x = end_x - ux * head_length_px
    base_y = end_y - uy * head_length_px

    left_x = base_x + vx * (head_width_px / 2)
    left_y = base_y + vy * (head_width_px / 2)
    right_x = base_x - vx * (head_width_px / 2)
    right_y = base_y - vy * (head_width_px / 2)

    canvas.line(start_x, start_y, base_x, base_y, stroke=stroke, stroke_w=stroke_width)

    canvas.polygon(
        [(end_x, end_y), (left_x, left_y), (right_x, right_y)],
        fill=stroke,
        stroke=stroke,
        stroke_w=1,
    )

    if label:
        label_x = end_x + vx * 10
        label_y = end_y + vy * 10
        canvas.text(
            label_x,
            label_y,
            label,
            fill=stroke,
            font_size=14,
            font_family="Arial, sans-serif",
            text_anchor="middle",
            dominant_baseline="middle",
        )

def taper_local(
    canvas: SVGCanvasType,
    length: float,
    od1: float,
    od2: float,
    wall: float = 2.0,
) -> list[PortType]:
    """
    Draw a taper (reducer) using OD only.
    
    Parameters
    ----------
    canvas : SVGCanvas
    length : float
        Length of taper (px)
    od1 : float
        Upstream outside diameter (px)
    od2 : float
        Downstream outside diameter (px)
    wall : float
        Constant wall thickness (px)
    
    Returns
    -------
    list[Port]
    """

    # --- derive inner diameters ---
    id1 = od1 - 2 * wall
    id2 = od2 - 2 * wall

    if id1 <= 0 or id2 <= 0:
        raise ValueError("Wall thickness too large for given diameters")

    # --- outer half heights ---
    y1o = od1 / 2
    y2o = od2 / 2

    # --- inner half heights ---
    y1i = id1 / 2
    y2i = id2 / 2

    # =========================
    # 1. OUTER SHAPE
    # =========================
    canvas._lines.append(
        f'<polygon points="'
        f'0,{y1o:.2f} '
        f'{length:.2f},{y2o:.2f} '
        f'{length:.2f},{-y2o:.2f} '
        f'0,{-y1o:.2f}" '
        f'fill="{canvas.pipe_fill}" '
        f'stroke="{canvas.pipe_stroke}" '
        f'stroke-width="2"/>'
    )

    # =========================
    # 2. INNER VOID
    # =========================
    canvas._lines.append(
        f'<polygon points="'
        f'0,{y1i:.2f} '
        f'{length:.2f},{y2i:.2f} '
        f'{length:.2f},{-y2i:.2f} '
        f'0,{-y1i:.2f}" '
        f'fill="white" '
        f'stroke="none"/>'
    )

    # =========================
    # 3. CENTRELINE
    # =========================
    canvas._lines.append(
        f'<line x1="0" y1="0" x2="{length:.2f}" y2="0" '
        f'stroke="#999999" '
        f'stroke-width="1" '
        f'stroke-dasharray="6,6" '
        f'stroke-opacity="0.5"/>'
    )

    # =========================
    # OUTPUT PORT
    # =========================
    return [canvas.make_port(length, 0, 1, 0)]


def flange_local(
    canvas: SVGCanvasType,
    diameter_px: float,
    projection_px: float = 40,
    thickness_px: float = 15,
    flange_width_ratio: float = 1.15,
) -> list[PortType]:
    """
    Draw a flange connection in LOCAL coordinates.

    Parameters
    ----------
    canvas : SVGCanvas
    diameter_px : float
        Pipe diameter
    projection_px : float
        Flange axial projection (thickness)
    thickness_px : float
        Flange radial thickness
    flange_width_ratio : float
        Flange outer diameter as ratio of pipe diameter (default 1.15 = 15% wider)

    Returns
    -------
    list[Port]
        [inlet_port, outlet_port]
    """

    pipe_half_d = diameter_px / 2
    flange_half_d = diameter_px * flange_width_ratio / 2
    half_p = projection_px / 2

    # Flange body (rectangular projection, wider than pipe)
    canvas.rect(
        x=-half_p,
        y=-flange_half_d,
        w=projection_px,
        h=diameter_px * flange_width_ratio,
        fill=canvas.pipe_fill,
        stroke=canvas.pipe_stroke,
        stroke_w=2,
    )

    # Centreline
    canvas.line(
        -half_p,
        0,
        half_p,
        0,
        stroke="#999999",
        stroke_w=1,
        dasharray="6,6",
        stroke_opacity=0.5,
    )

    return [
        canvas.make_port(-half_p, 0, -1, 0),
        canvas.make_port(half_p, 0, 1, 0),
    ]


def thrust_block_for_bend_local(
    canvas: SVGCanvasType,
    radius_px: float,
    diameter_px: float,
    angle_deg: float,
    block_width_px: float,
    block_depth_px: float,
    offset_px: float = 0,
) -> None:
    """
    Draw a thrust block behind a bend in local coordinates.

    The block is placed on the resultant thrust direction of the bend.
    """

    geometry = BendGeometry.from_params(radius_px=radius_px, angle_deg=angle_deg)
    thrust = geometry.normalized_resultant_thrust_vector
    if thrust.x == 0 and thrust.y == 0:
        return

    ux = thrust.x
    uy = thrust.y

    # Perpendicular direction to thrust
    vx = -uy
    vy = ux

    # Position block outside the pipe body
    centre_x = geometry.arc_midpoint.x + ux * (diameter_px / 2 + block_depth_px / 2 + offset_px)
    centre_y = geometry.arc_midpoint.y + uy * (diameter_px / 2 + block_depth_px / 2 + offset_px)

    half_w = block_width_px / 2
    half_d = block_depth_px / 2

    # Four corners of rotated rectangle
    p1 = (
        centre_x - vx * half_w - ux * half_d,
        centre_y - vy * half_w - uy * half_d,
    )

    p2 = (
        centre_x + vx * half_w - ux * half_d,
        centre_y + vy * half_w - uy * half_d,
    )

    p3 = (
        centre_x + vx * half_w + ux * half_d,
        centre_y + vy * half_w + uy * half_d,
    )

    p4 = (
        centre_x - vx * half_w + ux * half_d,
        centre_y - vy * half_w + uy * half_d,
    )

    points = " ".join(
        f"{x:.2f},{y:.2f}"
        for x, y in [p1, p2, p3, p4]
    )

    canvas.polygon(points, fill="#d9d9d9", stroke="black", stroke_w=2)


def thrust_block_restraint_for_bend_local(
    canvas: SVGCanvasType,
    radius_px: float,
    diameter_px: float,
    angle_deg: float,
    block_width_px: float,
    block_depth_px: float,
    offset_px: float = 0,
    label: str | None = "Restraint Block",
) -> None:
    """
    Draw a thrust block as a restraint element for bend thrust forces.

    This helper composes the bend block geometry with a short force-path line
    and optional label so the restraint intent is clear on the SVG.

    By default, the near face of the block touches the bend outside wall at the
    arc midpoint. Use positive ``offset_px`` to move the block further away.
    """

    thrust_block_for_bend_local(
        canvas=canvas,
        radius_px=radius_px,
        diameter_px=diameter_px,
        angle_deg=angle_deg,
        block_width_px=block_width_px,
        block_depth_px=block_depth_px,
        offset_px=offset_px,
    )

    geometry = BendGeometry.from_params(radius_px=radius_px, angle_deg=angle_deg)
    thrust = geometry.normalized_resultant_thrust_vector
    if thrust.x == 0 and thrust.y == 0:
        return

    ux = thrust.x
    uy = thrust.y
    vx = -uy
    vy = ux

    # Show transfer from bend outside wall midpoint into the restraint block.
    force_start_x = geometry.arc_midpoint.x + ux * (diameter_px / 2)
    force_start_y = geometry.arc_midpoint.y + uy * (diameter_px / 2)
    force_end_x = force_start_x + ux * (block_depth_px + offset_px)
    force_end_y = force_start_y + uy * (block_depth_px + offset_px)

    canvas.line(
        force_start_x,
        force_start_y,
        force_end_x,
        force_end_y,
        stroke="#666666",
        stroke_w=1.5,
        dasharray="5,4",
    )

    if label:
        label_x = force_end_x + vx * 12
        label_y = force_end_y + vy * 12
        canvas.text(
            label_x,
            label_y,
            label,
            fill="#333333",
            font_size=12,
            font_family="Arial, sans-serif",
        )


def create_canvas(
    total_len: float,
    max_height: float,
    canvas_w: int,
    canvas_h: int,
    margin_x: int = 110,
    margin_y: int = 90,
) -> CanvasLayoutType:
    """Build a reusable canvas/scale context for any fitting SVG.

    Args:
        total_len:  Total axial length of the fitting in mm — used to compute horizontal scale.
        max_height: Tallest element height in mm (e.g. flange OD) — used to compute vertical scale.
        canvas_w:   SVG canvas width in pixels (user-controlled).
        canvas_h:   SVG canvas height in pixels (user-controlled).
        margin_x:   Left/right pixel margin reserved for dimension arrows and labels.
        margin_y:   Top/bottom pixel margin reserved for dimension lines and title.

    Returns:
        A dict containing:
          - 'scale'    : float — mm-to-pixel conversion factor
          - 'cx'       : float — horizontal centre of the canvas in pixels
          - 'cy'       : float — vertical centre of the canvas in pixels (shifted up slightly)
          - 'canvas_w' : int   — canvas width (passed through for SVG header)
          - 'canvas_h' : int   — canvas height (passed through for SVG header)
    """
    # Usable drawing area after subtracting margins on both sides
    if total_len <= 0:
        raise ValueError("total_len must be positive")
    if max_height <= 0:
        raise ValueError("max_height must be positive")
    if canvas_w <= 0:
        raise ValueError("canvas_w must be positive")
    if canvas_h <= 0:
        raise ValueError("canvas_h must be positive")
    if margin_x < 0:
        raise ValueError("margin_x must be non-negative")
    if margin_y < 0:
        raise ValueError("margin_y must be non-negative")

    draw_w = canvas_w - 2 * margin_x  # Available horizontal space for the pipe geometry
    draw_h = canvas_h - 2 * margin_y  # Available vertical space for the pipe geometry
    if draw_w <= 0:
        raise ValueError("canvas_w must exceed horizontal margins")
    if draw_h <= 0:
        raise ValueError("canvas_h must exceed vertical margins")

    # Scale factor: converts mm → SVG pixels.
    # min() picks the tighter constraint so the drawing never overflows in either direction.
    scale = min(draw_w / total_len, draw_h / (max_height * 1.1))

    cx = canvas_w / 2  # Horizontal centre of the canvas in pixels
    cy = canvas_h / 2 - 20  # Vertical centre, shifted up 20px to leave room for the dim line

    return CanvasLayout(
        scale=scale,
        cx=cx,
        cy=cy,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )


def vertical_upturn_bend_section(
    thrust_block: "ThrustBlock | SimpleNamespace",
    vertical_bend: "VerticalUpturnBend | SimpleNamespace",
    z0_m: float = 1.0,
    z_gw_m: float = 0.8,
) -> list[SVGDrawing]:

    block_input = ThrustBlockInput(
        height=thrust_block.height,
        width=thrust_block.width,
        length=thrust_block.length,
        depth=thrust_block.depth,
    )
    bend_input = BendInput(
        outside_diameter=vertical_bend.outside_diameter,
        angle=vertical_bend.angle,
        radius=vertical_bend.radius,
    )
    return VerticalBendSVGWriter(
        thrust_block=block_input,
        bend=bend_input,
        canvas_w=600,
        canvas_h=400,
        depth_crown=z0_m,
        gw_level=z_gw_m,
    ).drawings()

def thrust_arrow_for_taper_axial(
    canvas: SVGCanvasType,
    start_x: float,
    start_y: float,
    direction_x: float,
    direction_y: float,
    length_px: float = 80,
    head_length_px: float = 18,
    head_width_px: float = 12,
    stroke: str = "#d32f2f",
    stroke_width: float = 2,
    label: str | None = "Thrust",
) -> None:
    """
    Draw a thrust arrow for a taper in axial (pipe) direction.

    Parameters
    ----------
    start_x, start_y : float
        Arrow start point on the taper
    direction_x, direction_y : float
        Unit direction vector (tx, ty)
    length_px : float
        Shaft length
    head_length_px, head_width_px : float
        Arrowhead dimensions
    stroke : str
        Arrow colour
    stroke_width : float
        Line width
    label : str or None
        Optional text label
    """

    # Normalize direction
    dlen = math.hypot(direction_x, direction_y)
    if dlen == 0:
        return

    ux = direction_x / dlen
    uy = direction_y / dlen

    # Perpendicular for arrowhead width
    vx = -uy
    vy = ux

    end_x = start_x + ux * length_px
    end_y = start_y + uy * length_px

    base_x = end_x - ux * head_length_px
    base_y = end_y - uy * head_length_px

    left_x = base_x + vx * (head_width_px / 2)
    left_y = base_y + vy * (head_width_px / 2)
    right_x = base_x - vx * (head_width_px / 2)
    right_y = base_y - vy * (head_width_px / 2)

    # Shaft
    canvas.line(start_x, start_y, base_x, base_y, stroke=stroke, stroke_w=stroke_width)

    # Arrowhead
    canvas.polygon(
        [(end_x, end_y), (left_x, left_y), (right_x, right_y)],
        fill=stroke,
        stroke=stroke,
        stroke_w=1,
    )

    if label:
        label_x = end_x + vx * 10
        label_y = end_y + vy * 10
        canvas.text(
            label_x,
            label_y,
            label,
            fill=stroke,
            font_size=14,
            font_family="Arial, sans-serif",
            text_anchor="middle",
            dominant_baseline="middle",
        )


def thrust_block_restraint_for_taper_axial(
    canvas: SVGCanvasType,
    contact_x: float,
    contact_y: float,
    direction_x: float,
    direction_y: float,
    block_width_px: float,
    block_depth_px: float,
    offset_px: float = 0,
    label: str | None = "Restraint Block",
) -> None:
    """
    Draw a restraint block for taper thrust in axial direction.

    Parameters
    ----------
    contact_x, contact_y : float
        Contact point on the taper
    direction_x, direction_y : float
        Unit direction vector (thrust direction)
    block_width_px : float
        Block width perpendicular to thrust
    block_depth_px : float
        Block depth along thrust direction
    offset_px : float
        Gap between taper and block (0 = touching)
    label : str or None
        Optional text label
    """

    # Normalize direction
    dlen = math.hypot(direction_x, direction_y)
    if dlen == 0:
        return

    ux = direction_x / dlen
    uy = direction_y / dlen

    # Perpendicular
    vx = -uy
    vy = ux

    # Block centre position aligned with contact point (taper thrust midpoint)
    centre_x = contact_x + ux * offset_px
    centre_y = contact_y + uy * offset_px

    half_w = block_width_px / 2
    half_d = block_depth_px / 2

    # Four corners of rotated rectangle
    p1 = (centre_x - vx * half_w - ux * half_d, centre_y - vy * half_w - uy * half_d)
    p2 = (centre_x + vx * half_w - ux * half_d, centre_y + vy * half_w - uy * half_d)
    p3 = (centre_x + vx * half_w + ux * half_d, centre_y + vy * half_w + uy * half_d)
    p4 = (centre_x - vx * half_w + ux * half_d, centre_y - vy * half_w + uy * half_d)

    points = " ".join(f"{x:.2f},{y:.2f}" for x, y in [p1, p2, p3, p4])
    canvas.polygon(points, fill="#d9d9d9", stroke="black", stroke_w=2)

    # Force transfer line from contact to far edge of block
    force_end_x = contact_x + ux * (block_depth_px / 2 + offset_px)
    force_end_y = contact_y + uy * (block_depth_px / 2 + offset_px)

    canvas.line(
        contact_x,
        contact_y,
        force_end_x,
        force_end_y,
        stroke="#666666",
        stroke_w=1.5,
        dasharray="5,4",
    )

    if label:
        label_x = force_end_x + vx * 12
        label_y = force_end_y + vy * 12
        canvas.text(
            label_x,
            label_y,
            label,
            fill="#333333",
            font_size=12,
            font_family="Arial, sans-serif",
        )


def draw_vertical_dim(
    canvas: SVGCanvasType,
    x: float,
    y_top: float,
    y_bottom: float,
    label: str,
    color: str = "black",
    text_dx: float = 8.0,
    text_anchor: str = "start",
) -> None:
    """Draw a vertical two-headed dimension with a label."""
    head_len = 8.0
    head_half_w = 4.0
    shaft_top = y_top + head_len
    shaft_bottom = y_bottom - head_len
    if shaft_bottom > shaft_top:
        canvas.line(x, shaft_top, x, shaft_bottom, stroke=color, stroke_w=1.6)

    canvas.polygon(
        [(x - head_half_w, y_top + head_len), (x + head_half_w, y_top + head_len), (x, y_top)],
        fill=color,
        stroke=color,
        stroke_w=1,
    )
    canvas.polygon(
        [(x - head_half_w, y_bottom - head_len), (x + head_half_w, y_bottom - head_len), (x, y_bottom)],
        fill=color,
        stroke=color,
        stroke_w=1,
    )

    canvas.text(
        x + text_dx,
        (y_top + y_bottom) / 2,
        label,
        fill=color,
        font_size=13,
        font_family="Arial, sans-serif",
        dominant_baseline="middle",
        text_anchor=text_anchor,
    )


def draw_horizontal_dim(
    canvas: SVGCanvasType,
    x_left: float,
    x_right: float,
    y: float,
    label: str,
    color: str = "black",
    label_padding_px: float = 16.0,
) -> None:
    """Draw a horizontal two-headed dimension with a centered label."""
    head_len = 10.0
    head_half_h = 4.5
    shaft_left = x_left + head_len
    shaft_right = x_right - head_len
    if shaft_right > shaft_left:
        canvas.line(shaft_left, y, shaft_right, y, stroke=color, stroke_w=1.6)

    canvas.polygon(
        [(x_left + head_len, y - head_half_h), (x_left + head_len, y + head_half_h), (x_left, y)],
        fill=color,
        stroke=color,
        stroke_w=1,
    )
    canvas.polygon(
        [(x_right - head_len, y - head_half_h), (x_right - head_len, y + head_half_h), (x_right, y)],
        fill=color,
        stroke=color,
        stroke_w=1,
    )

    canvas.text(
        (x_left + x_right) / 2,
        y + label_padding_px,
        label,
        fill=color,
        font_size=13,
        font_family="Arial, sans-serif",
        text_anchor="middle",
    )


def draw_plan_bellmouth(
    canvas: SVGCanvasType,
    length_px: float,
    connected_diameter_px: float,
    opening_scale: float = 1.6,
) -> list[PortType]:
    """Draw a local bellmouth with connection at x=0 and opening at x=length."""
    pipe_half_h = connected_diameter_px / 2
    opening_half_h = pipe_half_h * opening_scale

    canvas.polygon(
        [(0, -pipe_half_h), (length_px, -opening_half_h), (length_px, opening_half_h), (0, pipe_half_h)],
        fill="white",
        stroke="black",
        stroke_w=2,
    )

    return [
        canvas.make_port(0, 0, -1, 0),
        canvas.make_port(length_px, 0, 1, 0),
    ]


def draw_plan_double_flange(
    canvas: SVGCanvasType,
    diameter_px: float,
    flange_t_px: float,
    flange_gap_px: float,
    height_factor: float,
) -> list[PortType]:
    """Draw a local double-flange pair and return inlet/outlet ports."""
    pair_w = 2 * flange_t_px + flange_gap_px
    flange_h = diameter_px * height_factor
    flange_a_x = 0.0
    flange_b_x = flange_t_px + flange_gap_px

    canvas.rect(0, -diameter_px / 2, pair_w, diameter_px, fill="white", stroke="black", stroke_w=2)
    canvas.rect(flange_a_x, -flange_h / 2, flange_t_px, flange_h, fill="#efefef", stroke="black", stroke_w=1.6)
    canvas.rect(flange_b_x, -flange_h / 2, flange_t_px, flange_h, fill="#efefef", stroke="black", stroke_w=1.6)

    return [
        canvas.make_port(0, 0, -1, 0),
        canvas.make_port(pair_w, 0, 1, 0),
    ]


def draw_plan_single_socket(
    canvas: SVGCanvasType,
    diameter_px: float,
    socket_w_px: float,
    height_factor: float,
) -> list[PortType]:
    """Draw a local single socket collar and return inlet/outlet ports."""
    socket_h = diameter_px * height_factor
    canvas.rect(0, -socket_h / 2, socket_w_px, socket_h, fill="#efefef", stroke="black", stroke_w=1.8)

    return [
        canvas.make_port(0, 0, -1, 0),
        canvas.make_port(socket_w_px, 0, 1, 0),
    ]


def draw_plan_pipe_segment(
    canvas: SVGCanvasType,
    length_px: float,
    diameter_px: float,
) -> list[PortType]:
    """Draw a local straight pipe segment and return inlet/outlet ports."""
    canvas.rect(0, -diameter_px / 2, length_px, diameter_px, fill="white", stroke="black", stroke_w=2)

    return [
        canvas.make_port(0, 0, -1, 0),
        canvas.make_port(length_px, 0, 1, 0),
    ]


def taper_thrust_section(
    thrust_block: "ThrustBlock | SimpleNamespace",
    taper_thrust: "TaperThrust | SimpleNamespace",
    z0_m: float = 1.0,
    z_gw_m: float = 0.8,
) -> list[SVGDrawing]:
    block_input = ThrustBlockInput(
        height=thrust_block.height,
        width=thrust_block.width,
        length=thrust_block.length,
        depth=thrust_block.depth,
    )
    taper_input = TaperInput(
        outside_diameter_large=taper_thrust.outside_diameter_large,
        outside_diameter_small=taper_thrust.outside_diameter_small,
    )
    return TaperSVGWriter(
        thrust_block=block_input,
        taper=taper_input,
        canvas_w=600,
        canvas_h=400,
        depth_crown=z0_m,
        gw_level=z_gw_m,
    ).drawings()


def build_socket_pipe_svg(od: float, canvas_w: int, canvas_h: int) -> str:
    """Draw a simple socketed pipe elevation for the blank-end case."""
    return BlankEndSVGWriter(BlankEndInput(outside_diameter=od), canvas_w, canvas_h).drawings()[0].svg


def build_taper_thrust_svg(
    block_height: float,
    block_width: float,
    block_length: float,
    od_large: float,
    od_small: float,
    canvas_w: int,
    canvas_h: int,
) -> str:
    """Draw the taper thrust plan view as a standalone SVG string."""
    return TaperSVGWriter(
        thrust_block=ThrustBlockInput(height=block_height, width=block_width, length=block_length, depth=0.0),
        taper=TaperInput(outside_diameter_large=od_large, outside_diameter_small=od_small),
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    ).drawings()[0].svg


def build_taper_thrust_section_svg(
    block_height: float,
    block_width: float,
    block_length: float,
    block_depth: float,
    gw_level: float,
    od_large: float,
    depth_crown: float,
    canvas_w: int,
    canvas_h: int,
) -> str:
    """Draw the taper thrust section as a standalone SVG string."""
    return TaperSVGWriter(
        thrust_block=ThrustBlockInput(height=block_height, width=block_width, length=block_length, depth=block_depth),
        taper=TaperInput(outside_diameter_large=od_large, outside_diameter_small=od_large),
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        depth_crown=depth_crown,
        gw_level=gw_level,
    ).drawings()[1].svg


def build_horizontal_bend(
    block_height: float,
    block_width: float,
    block_length: float,
    block_depth: float,
    gw_level: float,
    od: float,
    depth_crown: float,
    start_angle: float,
    angle: float,
    canvas_w: int,
    canvas_h: int,
) -> str:
    """Draw the horizontal bend plan view as a standalone SVG string."""
    return HorizontalBendSVGWriter(
        thrust_block=ThrustBlockInput(height=block_height, width=block_width, length=block_length, depth=block_depth),
        bend=BendInput(outside_diameter=od, angle=angle, radius=0.0),
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        depth_crown=depth_crown,
        gw_level=gw_level,
        start_angle=start_angle,
    ).drawings()[0].svg


def build_horizontal_bend_section_svg(
    block_height: float,
    block_width: float,
    block_length: float,
    block_depth: float,
    gw_level: float,
    od: float,
    depth_crown: float,
    canvas_w: int,
    canvas_h: int,
) -> str:
    """Backward-compatible helper that returns the horizontal bend plan SVG string."""
    return HorizontalBendSVGWriter(
        thrust_block=ThrustBlockInput(height=block_height, width=block_width, length=block_length, depth=block_depth),
        bend=BendInput(outside_diameter=od, angle=0.0, radius=0.0),
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        depth_crown=depth_crown,
        gw_level=gw_level,
        start_angle=0.0,
    ).drawings()[0].svg


def build_vertical_upturn_bend_section_svg(
    block_height: float,
    block_width: float,
    block_length: float,
    block_depth: float,
    gw_level: float,
    od: float,
    depth_crown: float,
    bend_orientation: float,
    angle: float,
    canvas_w: int,
    canvas_h: int,
) -> str:
    """Draw the vertical upturn bend section as a standalone SVG string."""
    return VerticalBendSVGWriter(
        thrust_block=ThrustBlockInput(height=block_height, width=block_width, length=block_length, depth=block_depth),
        bend=BendInput(outside_diameter=od, angle=angle, radius=0.0),
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        depth_crown=depth_crown,
        gw_level=gw_level,
        bend_orientation=bend_orientation,
    ).drawings()[0].svg


def build_vertical_downturn_bend_section_svg(
    block_height: float,
    block_width: float,
    block_length: float,
    block_depth: float,
    gw_level: float,
    od: float,
    depth_crown: float,
    angle: float,
    canvas_w: int,
    canvas_h: int,
) -> str:
    """Draw the vertical downturn bend longitudinal section as a standalone SVG string."""
    writer = VerticalBendSVGWriter(
        thrust_block=ThrustBlockInput(height=block_height, width=block_width, length=block_length, depth=block_depth),
        bend=BendInput(outside_diameter=od, angle=angle, radius=0.0),
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        depth_crown=depth_crown,
        gw_level=gw_level,
        bend_orientation=-90.0,
    )
    return writer.downturn_drawings()[0].svg


if __name__ == "__main__":
    try:
        from app.civeng1.hydraulics.fittings import HorizontalBend, TaperThrust, VerticalUpturnBend
        from app.civeng1.structures.concrete import ThrustBlock

        vertical_bend = VerticalUpturnBend(
            outside_diameter=0.60,
            angle=45.0,
            radius=0.90,
        )
        thrust_block = ThrustBlock(
            height=1.20,
            width=1.70,
            length=1.70,
            depth=1.00,
            key_height=None,
            key_length=None,
        )
        taper_thrust_block = ThrustBlock(
            height=1.80,
            width=3.50,
            length=2.50,
            depth=1.00,
            key_height=None,
            key_length=None,
        )
        taper_thrust = TaperThrust(
            outside_diameter_large=0.60,
            outside_diameter_small=0.40,
        )
        horizontal_bend = HorizontalBend(
            outside_diameter=0.60,
            angle=45.0,
            radius=0.90,
        )
        horizontal_bend_block = ThrustBlock(
            height=1.60,
            width=2.50,
            length=2.80,
            depth=2.10,
            key_height=None,
            key_length=None,
        )
    except Exception:
        # Fallback keeps this local utility runnable without full app dependencies.
        vertical_bend = SimpleNamespace(
            outside_diameter=0.60,
            angle=45.0,
            radius=0.90,
        )
        thrust_block = SimpleNamespace(
            height=1.20,
            width=1.70,
            length=1.70,
            depth=1.00,
        )
        taper_thrust_block = SimpleNamespace(
            height=1.80,
            width=3.50,
            length=2.50,
            depth=1.00,
        )
        taper_thrust = SimpleNamespace(
            outside_diameter_large=0.60,
            outside_diameter_small=0.40,
        )
        horizontal_bend = SimpleNamespace(
            outside_diameter=0.60,
            angle=45.0,
            radius=0.90,
        )
        horizontal_bend_block = SimpleNamespace(
            height=1.60,
            width=2.50,
            length=2.80,
            depth=2.10,
        )

    horizontal_bend_plan_svg = build_horizontal_bend(
        horizontal_bend_block.height,
        horizontal_bend_block.width,
        horizontal_bend_block.length,
        horizontal_bend_block.depth,
        0.8,
        horizontal_bend.outside_diameter,
        1.0,
        0.0,
        horizontal_bend.angle,
        600,
        400,
    )
    horizontal_bend_section_svg = build_horizontal_bend_section_svg(
        horizontal_bend_block.height,
        horizontal_bend_block.width,
        horizontal_bend_block.length,
        horizontal_bend_block.depth,
        0.8,
        horizontal_bend.outside_diameter,
        1.0,
        600,
        400,
    )

    with open("./test_horizontal_bend_plan.svg", "w", encoding="utf-8") as f:
        f.write(horizontal_bend_plan_svg)

    with open("./test_horizontal_bend_section.svg", "w", encoding="utf-8") as f:
        f.write(horizontal_bend_section_svg)

    vertical_upturn_bend_section(
        thrust_block=thrust_block,
        vertical_bend=vertical_bend,
    )
    taper_thrust_section(
        thrust_block=taper_thrust_block,
        taper_thrust=taper_thrust,
    )
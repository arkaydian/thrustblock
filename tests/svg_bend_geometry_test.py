from __future__ import annotations

import math
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SVGWRITER_PATH = ROOT / "app" / "utils" / "svgwriter.py"


def _load_svgwriter_module():
    spec = spec_from_file_location("svgwriter_bend_module", SVGWRITER_PATH)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


svgwriter = _load_svgwriter_module()


def _assert_point(point, expected: tuple[float, float]) -> None:
    assert tuple(point) == pytest.approx(expected)


@pytest.mark.parametrize("angle_deg", [11.25, 22.5, 45.0, 90.0])
def test_bend_geometry_local_arc_midpoint(angle_deg: float) -> None:
    geometry = svgwriter.BendGeometry.from_params(radius_px=100.0, angle_deg=angle_deg)
    theta = math.radians(angle_deg / 2.0)
    expected = (100.0 * math.sin(theta), -100.0 * (1.0 - math.cos(theta)))
    _assert_point(geometry.arc_midpoint, expected)
    _assert_point(geometry.anchor_point, expected)


@pytest.mark.parametrize("orientation_deg", [0.0, 30.0, 90.0, 180.0, 270.0])
def test_bend_anchor_is_placed_at_canvas_centre_for_any_orientation(orientation_deg: float) -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=640, height=360)
    geometry = svgwriter.BendGeometry.from_params(radius_px=62.0, angle_deg=45.0)
    placement = svgwriter.FittingPlacement.anchor_at(
        local_anchor=geometry.anchor_point,
        target=canvas.centre,
        orientation_deg=orientation_deg,
    )

    _assert_point(placement.transform_point(geometry.arc_midpoint), tuple(canvas.centre))


def test_bend_points_rotate_about_anchor_and_tangents_only_rotate() -> None:
    geometry = svgwriter.BendGeometry.from_params(radius_px=80.0, angle_deg=45.0)
    target = svgwriter.Point(250.0, 180.0)
    placement = svgwriter.FittingPlacement.anchor_at(geometry.anchor_point, target, 90.0)

    inlet = placement.transform_point(geometry.inlet_point)
    outlet = placement.transform_point(geometry.outlet_point)
    inlet_tangent = placement.transform_vector(geometry.inlet_tangent)
    outlet_tangent = placement.transform_vector(geometry.outlet_tangent)

    inlet_local = svgwriter.Vector(
        geometry.inlet_point.x - geometry.anchor_point.x,
        geometry.inlet_point.y - geometry.anchor_point.y,
    )
    outlet_local = svgwriter.Vector(
        geometry.outlet_point.x - geometry.anchor_point.x,
        geometry.outlet_point.y - geometry.anchor_point.y,
    )
    inlet_expected = placement.transform_vector(inlet_local)
    outlet_expected = placement.transform_vector(outlet_local)

    _assert_point(inlet, (target.x + inlet_expected.x, target.y + inlet_expected.y))
    _assert_point(outlet, (target.x + outlet_expected.x, target.y + outlet_expected.y))
    _assert_point(inlet_tangent, (0.0, 1.0))
    _assert_point(outlet_tangent, tuple(svgwriter.rotate_vector(geometry.outlet_tangent, 90.0)))


def test_distances_from_anchor_are_preserved_after_transformation() -> None:
    geometry = svgwriter.BendGeometry.from_params(radius_px=62.0, angle_deg=90.0)
    placement = svgwriter.FittingPlacement.anchor_at(geometry.anchor_point, svgwriter.Point(320.0, 200.0), 30.0)

    local_points = [geometry.inlet_point, geometry.outlet_point, geometry.arc_center]
    transformed_points = [placement.transform_point(point) for point in local_points]

    for local_point, transformed_point in zip(local_points, transformed_points):
        local_distance = math.hypot(local_point.x - geometry.anchor_point.x, local_point.y - geometry.anchor_point.y)
        global_distance = math.hypot(transformed_point.x - 320.0, transformed_point.y - 200.0)
        assert global_distance == pytest.approx(local_distance)


def test_thrust_direction_matches_outside_radial_direction() -> None:
    geometry = svgwriter.BendGeometry.from_params(radius_px=62.0, angle_deg=45.0)
    assert tuple(geometry.normalized_resultant_thrust_vector) == pytest.approx(tuple(geometry.outside_radial_direction))


def test_canvas_size_changes_target_centre_not_local_bend_geometry() -> None:
    geometry = svgwriter.BendGeometry.from_params(radius_px=62.0, angle_deg=45.0)
    small_canvas = svgwriter.SVGCanvas(scale=1.0, width=400, height=300)
    large_canvas = svgwriter.SVGCanvas(scale=1.0, width=800, height=500)

    small_placement = svgwriter.FittingPlacement.anchor_at(geometry.anchor_point, small_canvas.centre, 0.0)
    large_placement = svgwriter.FittingPlacement.anchor_at(geometry.anchor_point, large_canvas.centre, 0.0)

    _assert_point(geometry.arc_midpoint, (62.0 * math.sin(math.radians(22.5)), -62.0 * (1 - math.cos(math.radians(22.5)))))
    _assert_point(small_placement.transform_point(geometry.arc_midpoint), tuple(small_canvas.centre))
    _assert_point(large_placement.transform_point(geometry.arc_midpoint), tuple(large_canvas.centre))


def test_taper_anchor_can_be_placed_at_canvas_centre_with_same_placement_abstraction() -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=500, height=300)
    local_anchor = svgwriter.Point(15.0, 0.0)
    placement = svgwriter.FittingPlacement.anchor_at(local_anchor=local_anchor, target=canvas.centre, orientation_deg=0.0)
    _assert_point(placement.transform_point(local_anchor), tuple(canvas.centre))


def test_build_horizontal_bend_keeps_anchor_at_canvas_centre_without_manual_offset() -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=600, height=400)
    geometry = svgwriter.BendGeometry.from_params(radius_px=max(0.6 * 46.0 * 1.35, 62.0), angle_deg=45.0)
    placement = svgwriter.FittingPlacement.anchor_at(
        local_anchor=geometry.anchor_point,
        target=canvas.centre,
        orientation_deg=-90.0,
    )

    _assert_point(placement.transform_point(geometry.arc_midpoint), tuple(canvas.centre))
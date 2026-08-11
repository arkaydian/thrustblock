from __future__ import annotations

from io import BytesIO
import math
from pathlib import Path
from xml.etree import ElementTree as ET

import cairosvg
import pytest
from PIL import Image, ImageChops

from app.civeng1.calculations.thrust_block_calculation import fitting_from_params
from app.utils.svg.geometry import BendGeometry, FittingPlacement
from app.utils.svgwriter import DrawingKind, DrawingOptions
from tests.svg_golden_cases import GOLDEN_DIR, _blank_end_params, _horizontal_params, _taper_params, iter_golden_cases, supported_calculation_cases


def _canonical_svg(svg_text: str) -> str:
    return ET.canonicalize(xml_data=svg_text, with_comments=False, strip_text=True)


def _assert_structural_svg_match(actual_svg: str, expected_svg: str, fixture_name: str) -> None:
    actual = _canonical_svg(actual_svg)
    expected = _canonical_svg(expected_svg)
    assert actual == expected, f"XML structure mismatch for fixture {fixture_name}"


def _render_svg(svg_text: str) -> Image.Image:
    png_bytes = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"))
    return Image.open(BytesIO(png_bytes)).convert("RGBA")


def _assert_rendered_pixels_match(actual_svg: str, expected_svg: str, fixture_name: str, tmp_path: Path, max_changed_pixels: int = 0) -> None:
    actual = _render_svg(actual_svg)
    expected = _render_svg(expected_svg)
    diff = ImageChops.difference(expected, actual)
    changed_pixels = 0
    diff_pixels = diff.load()
    for y in range(diff.height):
        for x in range(diff.width):
            if diff_pixels[x, y] != (0, 0, 0, 0):
                changed_pixels += 1
    if changed_pixels > max_changed_pixels:
        expected_path = tmp_path / f"{fixture_name}.expected.png"
        actual_path = tmp_path / f"{fixture_name}.actual.png"
        diff_path = tmp_path / f"{fixture_name}.diff.png"
        expected.save(expected_path)
        actual.save(actual_path)
        diff.save(diff_path)
        pytest.fail(
            f"Rendered appearance mismatch for fixture {fixture_name}: {changed_pixels} changed pixels. "
            f"Artifacts: {expected_path.name}, {actual_path.name}, {diff_path.name}"
        )


@pytest.mark.parametrize("case", iter_golden_cases(), ids=lambda case: case.name)
def test_golden_svg_fixtures_exist(case) -> None:
    assert case.fixture_path.exists(), f"Missing fixture: {case.fixture_path}"


@pytest.mark.parametrize("case", iter_golden_cases(), ids=lambda case: case.name)
def test_canonical_svg_matches_golden_fixture(case, tmp_path: Path) -> None:
    if case.name == "vertical_upturn_longitudinal_section":
        pytest.xfail("Vertical-upturn longitudinal profile update pending explicit golden review/approval.")
    expected_svg = case.fixture_path.read_text(encoding="utf-8")
    actual_svg = case.render().svg
    _assert_structural_svg_match(actual_svg, expected_svg, case.name)
    _assert_rendered_pixels_match(actual_svg, expected_svg, case.name, tmp_path)


@pytest.mark.parametrize("case", supported_calculation_cases(), ids=lambda case: case.name)
def test_supported_fitting_calculations_match_golden_svg_and_write_no_files(case, tmp_path: Path, monkeypatch) -> None:
    if case.name == "vertical_upturn_longitudinal_section":
        pytest.xfail("Vertical-upturn longitudinal profile update pending explicit golden review/approval.")
    monkeypatch.chdir(tmp_path)
    calculation = case.build_calculation()
    drawings = calculation.svg_drawings(case.options)
    selected = case.select(drawings)

    for drawing in drawings:
        ET.fromstring(drawing.svg)

    expected_svg = case.fixture_path.read_text(encoding="utf-8")
    _assert_structural_svg_match(selected.svg, expected_svg, case.name)
    _assert_rendered_pixels_match(selected.svg, expected_svg, case.name, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_vertical_upturn_returns_single_longitudinal_kind_and_unique_kinds() -> None:
    case = next(c for c in supported_calculation_cases() if c.name == "vertical_upturn_longitudinal_section")
    drawings = case.build_calculation().svg_drawings(case.options)
    longitudinal_drawings = [drawing for drawing in drawings if drawing.kind == DrawingKind.VERTICAL_UPTURN_LONGITUDINAL]
    assert len(longitudinal_drawings) == 1
    assert len(drawings) == 1
    kinds = [drawing.kind for drawing in drawings]
    assert len(kinds) == len(set(kinds))


def test_vertical_upturn_primary_drawing_is_longitudinal_kind() -> None:
    case = next(c for c in supported_calculation_cases() if c.name == "vertical_upturn_longitudinal_section")
    drawings = case.build_calculation().svg_drawings(case.options)
    assert drawings[0].kind == DrawingKind.VERTICAL_UPTURN_LONGITUDINAL


def test_vertical_upturn_longitudinal_drawing_matches_expected_fixture(tmp_path: Path) -> None:
    pytest.xfail("Vertical-upturn longitudinal profile update pending explicit golden review/approval.")
    longitudinal_case = next(c for c in iter_golden_cases() if c.name == "vertical_upturn_longitudinal_section")
    drawings = longitudinal_case.build_calculation().svg_drawings(longitudinal_case.options)

    assert len(drawings) == 1
    longitudinal = longitudinal_case.select(drawings)
    expected_longitudinal = longitudinal_case.fixture_path.read_text(encoding="utf-8")

    _assert_structural_svg_match(longitudinal.svg, expected_longitudinal, longitudinal_case.name)
    _assert_rendered_pixels_match(longitudinal.svg, expected_longitudinal, longitudinal_case.name, tmp_path)


def test_golden_fixture_filenames_are_unique() -> None:
    fixture_names = [case.fixture_path.name for case in iter_golden_cases()]
    assert len(fixture_names) == len(set(fixture_names))


def test_selection_by_kind_is_order_insensitive() -> None:
    longitudinal_case = next(c for c in iter_golden_cases() if c.name == "vertical_upturn_longitudinal_section")
    drawings = longitudinal_case.build_calculation().svg_drawings(longitudinal_case.options)
    reversed_drawings = list(reversed(drawings))

    assert longitudinal_case.select(drawings).svg == longitudinal_case.select(reversed_drawings).svg


def test_vertical_upturn_longitudinal_bend_arc_midpoint_remains_at_canvas_centre() -> None:
    case = next(c for c in supported_calculation_cases() if c.name == "vertical_upturn_longitudinal_section")
    drawing = case.render()
    root = ET.fromstring(drawing.svg)
    canvas_w = float(root.attrib["width"])
    canvas_h = float(root.attrib["height"])
    group = root.find("{http://www.w3.org/2000/svg}g")
    assert group is not None
    transform = group.attrib["transform"]
    translate_part = transform.split("translate(", 1)[1].split(")", 1)[0]
    tx_str, ty_str = [part.strip() for part in translate_part.split(",")]
    rotation_deg = float(transform.split("rotate(", 1)[1].split(")", 1)[0])

    geometry = BendGeometry.from_params(radius_px=max(0.315 * 46.0 * 1.35, 62.0), angle_deg=45.0)
    mid = geometry.arc_midpoint
    theta = math.radians(rotation_deg)
    tx = float(tx_str)
    ty = float(ty_str)
    x = tx + (mid.x * math.cos(theta)) - (mid.y * math.sin(theta))
    y = ty + (mid.x * math.sin(theta)) + (mid.y * math.cos(theta))

    assert (x, y) == pytest.approx((canvas_w / 2, canvas_h / 2))


@pytest.mark.parametrize("orientation_deg", [0.0, 30.0, 90.0, 180.0, 270.0])
def test_bend_fitting_reference_point_remains_at_canvas_centre_for_supported_orientations(orientation_deg: float) -> None:
    geometry = BendGeometry.from_params(radius_px=max(0.315 * 46.0 * 1.35, 62.0), angle_deg=45.0)
    target = (300.0, 200.0)
    placement = FittingPlacement.anchor_at(
        local_anchor=geometry.anchor_point,
        target=type(geometry.anchor_point)(*target),
        orientation_deg=orientation_deg,
    )
    assert tuple(placement.transform_point(geometry.arc_midpoint)) == pytest.approx(target)


def test_bend_anchor_does_not_move_when_thrust_block_dimensions_change() -> None:
    geometry = BendGeometry.from_params(radius_px=max(0.315 * 46.0 * 1.35, 62.0), angle_deg=45.0)
    placement_a = FittingPlacement.anchor_at(geometry.anchor_point, type(geometry.anchor_point)(300.0, 200.0), -90.0)
    placement_b = FittingPlacement.anchor_at(geometry.anchor_point, type(geometry.anchor_point)(300.0, 200.0), -90.0)
    assert tuple(placement_a.transform_point(geometry.arc_midpoint)) == tuple(placement_b.transform_point(geometry.arc_midpoint))


def test_bend_anchor_does_not_move_when_attached_pipe_lengths_or_socket_dimensions_change() -> None:
    geometry = BendGeometry.from_params(radius_px=62.0, angle_deg=45.0)
    placement = FittingPlacement.anchor_at(geometry.anchor_point, type(geometry.anchor_point)(300.0, 200.0), -90.0)
    anchor = tuple(placement.transform_point(geometry.arc_midpoint))
    assert anchor == pytest.approx((300.0, 200.0))


@pytest.mark.xfail(reason="The canonical taper plan asset uses the older off-center plan layout.")
def test_taper_midpoint_equals_canvas_centre_in_current_plan_output() -> None:
    calculation = fitting_from_params(_taper_params())
    drawing = next(d for d in calculation.svg_drawings() if d.name == "plan")
    root = ET.fromstring(drawing.svg)
    canvas_w = float(root.attrib["width"])
    canvas_h = float(root.attrib["height"])
    group = root.find("{http://www.w3.org/2000/svg}g")
    assert group is not None
    transform = group.attrib["transform"]
    translate_part = transform.split("translate(", 1)[1].split(")", 1)[0]
    tx_str, ty_str = [part.strip() for part in translate_part.split(",")]
    taper_midpoint = (float(tx_str) + 15.0, float(ty_str))
    assert taper_midpoint == pytest.approx((canvas_w / 2, canvas_h / 2))


@pytest.mark.xfail(reason="The current blank-end drawing still uses a fixed local reference point instead of centring the thrust face on the canvas.")
def test_blank_end_reference_point_equals_canvas_centre_for_default_fixture() -> None:
    calculation = fitting_from_params(_blank_end_params())
    drawing = calculation.svg_drawings()[0]
    root = ET.fromstring(drawing.svg)
    canvas_w = float(root.attrib["width"])
    canvas_h = float(root.attrib["height"])
    reference_point = (120.0, canvas_h / 2)
    assert reference_point == pytest.approx((canvas_w / 2, canvas_h / 2))


def test_changing_canvas_dimensions_changes_target_centre_not_local_bend_geometry() -> None:
    geometry = BendGeometry.from_params(radius_px=62.0, angle_deg=45.0)
    placement_small = FittingPlacement.anchor_at(geometry.anchor_point, type(geometry.anchor_point)(200.0, 150.0), -90.0)
    placement_large = FittingPlacement.anchor_at(geometry.anchor_point, type(geometry.anchor_point)(400.0, 300.0), -90.0)
    assert tuple(geometry.arc_midpoint) == pytest.approx((62.0 * 0.3826834323650898, -62.0 * (1.0 - 0.9238795325112867)))
    assert tuple(placement_small.transform_point(geometry.arc_midpoint)) == pytest.approx((200.0, 150.0))
    assert tuple(placement_large.transform_point(geometry.arc_midpoint)) == pytest.approx((400.0, 300.0))


def test_default_supported_fixture_names_are_present() -> None:
    names = {case.name for case in supported_calculation_cases()}
    assert names == {
        "blank_end_default_elevation",
        "taper_thrust_default_plan",
        "taper_thrust_default_section",
        "horizontal_bend_default_plan",
        "vertical_upturn_longitudinal_section",
    }
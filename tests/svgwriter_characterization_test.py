from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SVGWRITER_PATH = ROOT / "app" / "utils" / "svgwriter.py"
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "svgwriter"
SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
INVALID_FLOAT_PATTERN = re.compile(r"(?<![A-Za-z0-9_])-?inf(?![A-Za-z0-9_])|(?<![A-Za-z0-9_])nan(?![A-Za-z0-9_])", re.IGNORECASE)


def _load_svgwriter_module():
    spec = spec_from_file_location("svgwriter_module", SVGWRITER_PATH)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


svgwriter = _load_svgwriter_module()


def _assert_svg_is_well_formed(svg: str) -> ET.Element:
    assert isinstance(svg, str)
    assert svg.strip()
    assert INVALID_FLOAT_PATTERN.search(svg) is None
    return ET.fromstring(svg)


def _assert_unit_vector(port: dict[str, tuple[float, float]]) -> None:
    tx, ty = port["tangent"]
    assert math.hypot(tx, ty) == pytest.approx(1.0)


def _assert_port_matches(port, center: tuple[float, float], tangent: tuple[float, float]) -> None:
    assert tuple(port["center"]) == pytest.approx(center)
    assert tuple(port["tangent"]) == pytest.approx(tangent)


def _parse_points(points_attr: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for pair in points_attr.split():
        x_str, y_str = pair.split(",")
        points.append((float(x_str), float(y_str)))
    return points


def _rendered_x_extent(lines: list[str]) -> tuple[float, float]:
    wrapper = "<svg xmlns=\"http://www.w3.org/2000/svg\">" + "".join(lines) + "</svg>"
    root = ET.fromstring(wrapper)
    xs: list[float] = []

    for rect in root.findall("svg:rect", SVG_NS):
        x = float(rect.attrib["x"])
        width = float(rect.attrib["width"])
        xs.extend([x, x + width])

    for polygon in root.findall("svg:polygon", SVG_NS):
        xs.extend(x for x, _ in _parse_points(polygon.attrib["points"]))

    for line in root.findall("svg:line", SVG_NS):
        xs.extend([float(line.attrib["x1"]), float(line.attrib["x2"])])

    assert xs
    return min(xs), max(xs)


def _extract_first_path_end(svg_fragment: str) -> tuple[float, float]:
    root = ET.fromstring(f"<svg xmlns=\"http://www.w3.org/2000/svg\">{svg_fragment}</svg>")
    path = root.find("svg:path", SVG_NS)
    assert path is not None
    match = re.search(r"([\-0-9.]+)\s+([\-0-9.]+)$", path.attrib["d"])
    assert match is not None
    return float(match.group(1)), float(match.group(2))


def _parse_translate(transform: str) -> tuple[float, float]:
    match = re.search(r"translate\(([-0-9.]+),\s*([-0-9.]+)\)", transform)
    assert match is not None
    return float(match.group(1)), float(match.group(2))


def _group_x_extent(group: ET.Element, tx: float) -> tuple[float, float]:
    xs: list[float] = []
    for rect in group.findall("svg:rect", SVG_NS):
        x = float(rect.attrib["x"])
        width = float(rect.attrib["width"])
        xs.extend([tx + x, tx + x + width])

    for polygon in group.findall("svg:polygon", SVG_NS):
        for x, _ in _parse_points(polygon.attrib["points"]):
            xs.append(tx + x)

    for line in group.findall("svg:line", SVG_NS):
        xs.extend([tx + float(line.attrib["x1"]), tx + float(line.attrib["x2"])])

    assert xs
    return min(xs), max(xs)


def _find_taper_group(root: ET.Element) -> tuple[ET.Element, float, float]:
    for group in root.findall("svg:g", SVG_NS):
        transform = group.attrib.get("transform", "")
        if "translate(" not in transform:
            continue
        if group.find("svg:line[@stroke-dasharray='6,6']", SVG_NS) is None:
            continue
        polygon = group.find("svg:polygon", SVG_NS)
        if polygon is None:
            continue
        tx, ty = _parse_translate(transform)
        return group, tx, ty
    raise AssertionError("Could not find taper group in plan SVG")


def _find_block_rect(root: ET.Element) -> ET.Element:
    for rect in root.findall("svg:rect", SVG_NS):
        if rect.attrib.get("fill") == "#d9d9d9":
            return rect
    raise AssertionError("Could not find thrust block rectangle")


def _taper_outer_diameters(group: ET.Element) -> tuple[float, float]:
    polygon = group.find("svg:polygon", SVG_NS)
    assert polygon is not None
    points = _parse_points(polygon.attrib["points"])
    assert len(points) == 4
    upstream_d = abs(points[0][1] - points[3][1])
    downstream_d = abs(points[1][1] - points[2][1])
    return upstream_d, downstream_d


def _parse_path_points(path_d: str) -> list[tuple[float, float]]:
    values = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", path_d)]
    assert len(values) % 2 == 0
    return [(values[i], values[i + 1]) for i in range(0, len(values), 2)]


def _find_trench_paths(root: ET.Element) -> list[ET.Element]:
    return [
        path
        for path in root.findall("svg:path", SVG_NS)
        if path.attrib.get("stroke") == "#333333" and path.attrib.get("fill") == "none"
    ]


def _find_trench_hatch_lines(root: ET.Element) -> list[ET.Element]:
    return [
        line
        for line in root.findall("svg:line", SVG_NS)
        if line.attrib.get("stroke") == "#333333"
    ]


def _build_cases() -> dict[str, tuple[callable, Path]]:
    return {
        "blank_end": (
            lambda: svgwriter.build_socket_pipe_svg(od=22.0, canvas_w=240, canvas_h=180),
            FIXTURES_DIR / "blank_end.svg",
        ),
        "taper_plan": (
            lambda: svgwriter.build_taper_thrust_svg(
                block_height=1.8,
                block_width=3.5,
                block_length=2.5,
                od_large=0.6,
                od_small=0.4,
                canvas_w=600,
                canvas_h=400,
            ),
            FIXTURES_DIR / "taper_plan.svg",
        ),
        "taper_section": (
            lambda: svgwriter.build_taper_thrust_section_svg(
                block_height=1.8,
                block_width=3.5,
                block_length=2.5,
                block_depth=2.3,
                gw_level=0.8,
                od_large=0.6,
                depth_crown=1.0,
                canvas_w=600,
                canvas_h=400,
            ),
            FIXTURES_DIR / "taper_section.svg",
        ),
        "horizontal_bend_plan": (
            lambda: svgwriter.build_horizontal_bend(
                block_height=1.6,
                block_width=2.5,
                block_length=2.8,
                block_depth=2.1,
                gw_level=0.8,
                od=0.6,
                depth_crown=1.0,
                start_angle=0.0,
                angle=45.0,
                canvas_w=600,
                canvas_h=400,
            ),
            FIXTURES_DIR / "horizontal_bend_plan.svg",
        ),
        "vertical_upturn_section": (
            lambda: svgwriter.build_vertical_upturn_bend_section_svg(
                block_height=1.2,
                block_width=1.7,
                block_length=1.7,
                block_depth=1.0,
                gw_level=0.8,
                od=0.6,
                depth_crown=1.0,
                bend_orientation=90.0,
                angle=45.0,
                canvas_w=600,
                canvas_h=400,
            ),
            FIXTURES_DIR / "vertical_upturn_section.svg",
        ),
    }


@pytest.mark.parametrize("name", sorted(_build_cases()))
def test_public_builders_return_non_empty_parseable_svg_without_invalid_floats(name: str) -> None:
    build_svg, _ = _build_cases()[name]
    svg = build_svg()
    root = _assert_svg_is_well_formed(svg)
    assert root.tag.endswith("svg")


@pytest.mark.parametrize("name", sorted(_build_cases()))
def test_public_builders_match_golden_svg_fixtures(name: str) -> None:
    if name == "vertical_upturn_section":
        pytest.xfail("Vertical-upturn longitudinal profile update pending explicit golden review/approval.")
    build_svg, fixture_path = _build_cases()[name]
    actual_svg = build_svg()
    expected_svg = fixture_path.read_text(encoding="utf-8")
    assert actual_svg == expected_svg

def test_taper_plan_scales_with_block_length() -> None:
    short_svg = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.6,
        od_small=0.4,
        canvas_w=600,
        canvas_h=400,
    )
    long_svg = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=3.5,
        od_large=0.6,
        od_small=0.4,
        canvas_w=600,
        canvas_h=400,
    )

    assert short_svg != long_svg
    assert 'L = 2.5 m' in short_svg
    assert 'L = 3.5 m' in long_svg


def test_taper_plan_pipeline_crosses_block_and_reducer_is_centered() -> None:
    svg = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.6,
        od_small=0.4,
        canvas_w=600,
        canvas_h=400,
    )
    root = _assert_svg_is_well_formed(svg)

    block = _find_block_rect(root)
    block_left = float(block.attrib["x"])
    block_top = float(block.attrib["y"])
    block_w = float(block.attrib["width"])
    block_h = float(block.attrib["height"])
    block_right = block_left + block_w
    block_cy = block_top + block_h / 2

    taper_group, taper_tx, taper_ty = _find_taper_group(root)
    assert taper_ty == pytest.approx(block_cy)

    taper_polygon = taper_group.find("svg:polygon", SVG_NS)
    assert taper_polygon is not None
    taper_points = _parse_points(taper_polygon.attrib["points"])
    taper_start_x = taper_tx + min(x for x, _ in taper_points)
    taper_end_x = taper_tx + max(x for x, _ in taper_points)
    assert block_left <= taper_start_x <= block_right
    assert block_left <= taper_end_x <= block_right

    centreline_groups: list[tuple[ET.Element, float]] = []
    for group in root.findall("svg:g", SVG_NS):
        transform = group.attrib.get("transform", "")
        if "translate(" not in transform:
            continue
        tx, ty = _parse_translate(transform)
        if abs(ty - block_cy) < 1e-6:
            centreline_groups.append((group, tx))

    assert centreline_groups
    min_x = min(_group_x_extent(group, tx)[0] for group, tx in centreline_groups)
    max_x = max(_group_x_extent(group, tx)[1] for group, tx in centreline_groups)
    assert min_x < block_left
    assert max_x > block_right


def test_taper_plan_dimensions_orientation_and_values_remain_block_based() -> None:
    svg = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.6,
        od_small=0.4,
        canvas_w=600,
        canvas_h=400,
    )
    root = _assert_svg_is_well_formed(svg)

    texts = [text.text or "" for text in root.findall("svg:text", SVG_NS)]
    assert "L = 2.5 m" in texts
    assert "W = 3.5m" in texts

    block = _find_block_rect(root)
    block_bottom = float(block.attrib["y"]) + float(block.attrib["height"])
    block_right = float(block.attrib["x"]) + float(block.attrib["width"])

    horizontal_lines = []
    vertical_lines = []
    for line in root.findall("svg:line", SVG_NS):
        x1 = float(line.attrib["x1"])
        y1 = float(line.attrib["y1"])
        x2 = float(line.attrib["x2"])
        y2 = float(line.attrib["y2"])
        if abs(y1 - y2) < 1e-6 and y1 > block_bottom:
            horizontal_lines.append((x1, y1, x2, y2))
        if abs(x1 - x2) < 1e-6 and x1 > block_right:
            vertical_lines.append((x1, y1, x2, y2))

    assert horizontal_lines
    assert vertical_lines


def test_taper_plan_reflects_upstream_and_downstream_diameter_changes() -> None:
    reducing_svg = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.6,
        od_small=0.4,
        canvas_w=600,
        canvas_h=400,
    )
    increasing_svg = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.4,
        od_small=0.6,
        canvas_w=600,
        canvas_h=400,
    )
    narrower_svg = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.6,
        od_small=0.3,
        canvas_w=600,
        canvas_h=400,
    )

    reducing_group, _, _ = _find_taper_group(_assert_svg_is_well_formed(reducing_svg))
    increasing_group, _, _ = _find_taper_group(_assert_svg_is_well_formed(increasing_svg))
    narrower_group, _, _ = _find_taper_group(_assert_svg_is_well_formed(narrower_svg))

    reducing_up_d, reducing_down_d = _taper_outer_diameters(reducing_group)
    increasing_up_d, increasing_down_d = _taper_outer_diameters(increasing_group)
    _, narrower_down_d = _taper_outer_diameters(narrower_group)

    assert reducing_up_d != pytest.approx(reducing_down_d)
    assert increasing_up_d == pytest.approx(reducing_down_d)
    assert increasing_down_d == pytest.approx(reducing_up_d)
    assert narrower_down_d < reducing_down_d


def test_taper_plan_trench_segments_are_split_around_block_and_centered() -> None:
    svg = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.6,
        od_small=0.4,
        canvas_w=600,
        canvas_h=400,
    )
    root = _assert_svg_is_well_formed(svg)
    block = _find_block_rect(root)
    block_left = float(block.attrib["x"])
    block_right = block_left + float(block.attrib["width"])
    cy = float(block.attrib["y"]) + float(block.attrib["height"]) / 2

    trench_paths = _find_trench_paths(root)
    assert len(trench_paths) == 4

    path_points = [_parse_path_points(path.attrib["d"]) for path in trench_paths]
    left_segments = [pts for pts in path_points if max(x for x, _ in pts) <= block_left]
    right_segments = [pts for pts in path_points if min(x for x, _ in pts) >= block_right]

    assert len(left_segments) == 2
    assert len(right_segments) == 2

    for pts in left_segments:
        assert max(x for x, _ in pts) <= block_left
    for pts in right_segments:
        assert min(x for x, _ in pts) >= block_right

    upper_segments = [pts for pts in path_points if sum(y for _, y in pts) / len(pts) < cy]
    lower_segments = [pts for pts in path_points if sum(y for _, y in pts) / len(pts) > cy]
    assert len(upper_segments) == 2
    assert len(lower_segments) == 2


def test_taper_plan_trench_hatching_is_on_soil_side_and_outside_block() -> None:
    svg = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.6,
        od_small=0.4,
        canvas_w=600,
        canvas_h=400,
    )
    root = _assert_svg_is_well_formed(svg)
    block = _find_block_rect(root)
    block_left = float(block.attrib["x"])
    block_right = block_left + float(block.attrib["width"])
    cy = float(block.attrib["y"]) + float(block.attrib["height"]) / 2

    trench_paths = _find_trench_paths(root)
    path_points = [_parse_path_points(path.attrib["d"]) for path in trench_paths]
    upper_y_max = max(y for pts in path_points for _, y in pts if sum(py for _, py in pts) / len(pts) < cy)
    lower_y_min = min(y for pts in path_points for _, y in pts if sum(py for _, py in pts) / len(pts) > cy)

    hatch_lines = _find_trench_hatch_lines(root)
    assert len(hatch_lines) >= 12

    hatch_midpoints = []
    for line in hatch_lines:
        x1 = float(line.attrib["x1"])
        y1 = float(line.attrib["y1"])
        x2 = float(line.attrib["x2"])
        y2 = float(line.attrib["y2"])
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        assert mx <= block_left or mx >= block_right
        hatch_midpoints.append(my)

    assert any(my < upper_y_max for my in hatch_midpoints)
    assert any(my > lower_y_min for my in hatch_midpoints)


def test_taper_plan_trench_geometry_is_deterministic_and_dimensions_unchanged() -> None:
    svg_a = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.6,
        od_small=0.4,
        canvas_w=600,
        canvas_h=400,
    )
    svg_b = svgwriter.build_taper_thrust_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        od_large=0.6,
        od_small=0.4,
        canvas_w=600,
        canvas_h=400,
    )

    root_a = _assert_svg_is_well_formed(svg_a)
    root_b = _assert_svg_is_well_formed(svg_b)

    trench_paths_a = [p.attrib["d"] for p in _find_trench_paths(root_a)]
    trench_paths_b = [p.attrib["d"] for p in _find_trench_paths(root_b)]
    assert trench_paths_a == trench_paths_b

    hatch_a = [
        (line.attrib["x1"], line.attrib["y1"], line.attrib["x2"], line.attrib["y2"])
        for line in _find_trench_hatch_lines(root_a)
    ]
    hatch_b = [
        (line.attrib["x1"], line.attrib["y1"], line.attrib["x2"], line.attrib["y2"])
        for line in _find_trench_hatch_lines(root_b)
    ]
    assert hatch_a == hatch_b

    texts = [text.text or "" for text in root_a.findall("svg:text", SVG_NS)]
    assert "L = 2.5 m" in texts
    assert "W = 3.5m" in texts


def test_taper_section_svg_remains_unchanged_when_plan_geometry_changes() -> None:
    actual = svgwriter.build_taper_thrust_section_svg(
        block_height=1.8,
        block_width=3.5,
        block_length=2.5,
        block_depth=2.3,
        gw_level=0.8,
        od_large=0.6,
        depth_crown=1.0,
        canvas_w=600,
        canvas_h=400,
    )
    expected = (FIXTURES_DIR / "taper_section.svg").read_text(encoding="utf-8")
    assert actual == expected


def test_port_tangents_are_unit_vectors() -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=400, height=300)

    port_collections = [
        [canvas.make_port(0, 0, 3, 4)],
        [canvas.pipe_from_port(canvas.make_port(5, 10, 2, 0), 15.0, 6.0)],
        svgwriter.socket_pipe_local(canvas, length=40.0, diameter=20.0, socket_length=10.0, socket_od=24.0),
        svgwriter.bend_local(canvas, radius_px=100.0, diameter_px=20.0, angle_deg=45.0),
        svgwriter.taper_local(canvas, length=30.0, od1=24.0, od2=18.0, wall=2.0),
        svgwriter.flange_local(canvas, diameter_px=20.0),
        svgwriter.draw_plan_bellmouth(canvas, length_px=12.0, connected_diameter_px=20.0),
        svgwriter.draw_plan_double_flange(canvas, diameter_px=20.0, flange_t_px=4.0, flange_gap_px=2.0, height_factor=1.25),
        svgwriter.draw_plan_single_socket(canvas, diameter_px=20.0, socket_w_px=8.0, height_factor=1.1),
        svgwriter.draw_plan_pipe_segment(canvas, length_px=18.0, diameter_px=20.0),
    ]

    for ports in port_collections:
        for port in ports:
            _assert_unit_vector(port)


def test_place_fitting_local_translates_and_rotates_positions_and_tangents() -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=400, height=300)
    base_port = canvas.make_port(100.0, 200.0, 0.0, 1.0)

    def draw_func():
        return [
            canvas.make_port(10.0, 5.0, 1.0, 0.0),
            canvas.make_port(-5.0, 8.0, 0.0, -2.0),
        ]

    global_ports = canvas.place_fitting_local(base_port, draw_func)

    _assert_port_matches(global_ports[0], (95.0, 210.0), (0.0, 1.0))
    _assert_port_matches(global_ports[1], (92.0, 195.0), (1.0, 0.0))
    assert canvas._lines[0] == '<g transform="translate(100.0,200.0) rotate(90.0)">'
    assert canvas._lines[-1] == "</g>"


def test_socket_pipe_local_opening_only_ports_match_rendered_extents() -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=200, height=200)
    ports = svgwriter.socket_pipe_local(
        canvas,
        length=40.0,
        diameter=20.0,
        socket_length=10.0,
        socket_od=24.0,
        is_inlet=False,
        draw_barrel=False,
    )

    min_x, max_x = _rendered_x_extent(canvas._lines)
    assert min_x == pytest.approx(0.0)
    assert max_x == pytest.approx(10.0)
    assert ports[0]["center"][0] == pytest.approx(min_x)
    assert ports[1]["center"][0] == pytest.approx(max_x)


def test_socket_pipe_local_inlet_ports_match_rendered_extents() -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=200, height=200)
    ports = svgwriter.socket_pipe_local(
        canvas,
        length=40.0,
        diameter=20.0,
        socket_length=10.0,
        socket_od=24.0,
        is_inlet=True,
        draw_barrel=True,
    )

    min_x, max_x = _rendered_x_extent(canvas._lines)
    assert ports[0]["center"][0] == pytest.approx(min_x)
    assert ports[1]["center"][0] == pytest.approx(max_x)


@pytest.mark.xfail(reason="When draw_barrel=True and socket_length differs from length, the outlet port follows socket_length rather than the full rendered barrel extent.")
def test_socket_pipe_local_outlet_port_matches_barrel_extent_when_barrel_drawn() -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=200, height=200)
    ports = svgwriter.socket_pipe_local(
        canvas,
        length=40.0,
        diameter=20.0,
        socket_length=10.0,
        socket_od=24.0,
        is_inlet=False,
        draw_barrel=True,
    )

    _, max_x = _rendered_x_extent(canvas._lines)
    assert ports[1]["center"][0] == pytest.approx(max_x)


@pytest.mark.parametrize("angle_deg", [11.25, 22.5, 45.0, 90.0])
def test_bend_local_cases_match_endpoint_and_tangent_geometry(angle_deg: float) -> None:
    radius_px = 100.0
    diameter_px = 20.0
    canvas = svgwriter.SVGCanvas(scale=1.0, width=300, height=300)
    ports = svgwriter.bend_local(canvas, radius_px=radius_px, diameter_px=diameter_px, angle_deg=angle_deg)

    theta = math.radians(angle_deg)
    expected_end = (radius_px * math.sin(theta), -radius_px * (1.0 - math.cos(theta)))
    expected_tangent = (math.cos(theta), -math.sin(theta))

    assert len(ports) == 2
    _assert_port_matches(ports[0], (0.0, 0.0), (1.0, 0.0))
    _assert_port_matches(ports[1], expected_end, expected_tangent)
    _assert_unit_vector(ports[0])
    _assert_unit_vector(ports[1])


def test_upturn_bend_block_contact_and_diagonal_cut_profile() -> None:
    radius_px = 100.0
    diameter_px = 20.0
    angle_deg = 45.0
    canvas = svgwriter.SVGCanvas(scale=1.0, width=300, height=300)

    contact_x, contact_y, *_ = svgwriter.thrust_block_for_upturn_bend_local(
        canvas,
        radius_px=radius_px,
        diameter_px=diameter_px,
        angle_deg=angle_deg,
        block_width_px=80.0,
        block_height_px=60.0,
    )

    theta = math.radians(angle_deg)
    mid_theta = theta / 2.0
    mid_x = radius_px * math.sin(mid_theta)
    mid_y = -radius_px * (1.0 - math.cos(mid_theta))
    radial_x = math.sin(mid_theta)
    radial_y = math.cos(mid_theta)
    assert (contact_x, contact_y) == pytest.approx((mid_x + radial_x * (diameter_px / 2), mid_y + radial_y * (diameter_px / 2)))

    root = ET.fromstring(f"<svg xmlns=\"http://www.w3.org/2000/svg\">{''.join(canvas._lines)}</svg>")
    polygon = root.find("svg:polygon", SVG_NS)
    assert polygon is not None
    points = _parse_points(polygon.attrib["points"])

    # Restored upturn profile: 5-vertex polygon with a single straight diagonal cut.
    # p0=bottom-left, p1=bottom-right, p2=top-right, p3=top-cut, p4=left-cut.
    assert len(points) == 5
    assert points[0][1] == pytest.approx(points[1][1])  # base is horizontal
    assert points[1][0] == pytest.approx(points[2][0])  # right face is vertical
    assert points[2][1] == pytest.approx(points[3][1])  # top-right to top-cut is horizontal
    assert points[0][0] == pytest.approx(points[4][0])  # left face x aligns with left-cut
    assert points[3][0] > points[4][0]  # diagonal cut runs from top toward left edge


def test_upturn_bend_block_offsets_diagonal_midpoint_when_steep_cut_would_spike_above_top() -> None:
    radius_px = 100.0
    diameter_px = 20.0
    angle_deg = 90.0
    canvas = svgwriter.SVGCanvas(scale=1.0, width=300, height=300)

    contact_x, contact_y, *_ = svgwriter.thrust_block_for_upturn_bend_local(
        canvas,
        radius_px=radius_px,
        diameter_px=diameter_px,
        angle_deg=angle_deg,
        block_width_px=80.0,
        block_height_px=60.0,
    )

    root = ET.fromstring(f"<svg xmlns=\"http://www.w3.org/2000/svg\">{''.join(canvas._lines)}</svg>")
    polygon = root.find("svg:polygon", SVG_NS)
    assert polygon is not None
    points = _parse_points(polygon.attrib["points"])

    theta = math.radians(angle_deg)
    mid_theta = theta / 2.0
    actual_mid_x = radius_px * math.sin(mid_theta)
    actual_mid_y = -radius_px * (1.0 - math.cos(mid_theta))
    actual_contact_y = actual_mid_y + math.cos(mid_theta) * (diameter_px / 2)

    assert len(points) == 5
    assert contact_y == pytest.approx(actual_contact_y)
    # p3 (top-cut) and p4 (left-cut) should be symmetric around the anchor.
    diag_mid_x = (points[3][0] + points[4][0]) / 2.0
    diag_mid_y = (points[3][1] + points[4][1]) / 2.0
    assert (diag_mid_x, diag_mid_y) == pytest.approx((contact_x, contact_y), abs=0.02)


@pytest.mark.parametrize("angle_deg", [30.0, 45.0, 60.0, 90.0])
def test_upturn_bend_diagonal_cut_angle_follows_half_bend_angle(angle_deg: float) -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=300, height=300)
    svgwriter.thrust_block_for_upturn_bend_local(
        canvas,
        radius_px=100.0,
        diameter_px=20.0,
        angle_deg=angle_deg,
        block_width_px=80.0,
        block_height_px=60.0,
    )

    root = ET.fromstring(f"<svg xmlns=\"http://www.w3.org/2000/svg\">{''.join(canvas._lines)}</svg>")
    polygon = root.find("svg:polygon", SVG_NS)
    assert polygon is not None
    points = _parse_points(polygon.attrib["points"])

    # p3 -> p4 is the diagonal cut segment.
    top_cut = points[3]
    left_cut = points[4]
    dx = left_cut[0] - top_cut[0]
    dy = left_cut[1] - top_cut[1]
    assert dx < 0.0
    assert dy > 0.0

    observed = abs(math.degrees(math.atan2(dy, abs(dx))))
    expected = angle_deg / 2.0
    assert observed == pytest.approx(expected, abs=0.15)


@pytest.mark.parametrize("angle_deg", [30.0, 45.0, 60.0, 90.0])
def test_upturn_bend_cut_and_thrust_vectors_are_perpendicular(angle_deg: float) -> None:
    cut_dx, cut_dy, thrust_dx, thrust_dy = svgwriter._upturn_cut_and_thrust_unit_vectors(angle_deg)

    observed_cut_angle = abs(math.degrees(math.atan2(cut_dy, abs(cut_dx))))
    assert observed_cut_angle == pytest.approx(angle_deg / 2.0, abs=1e-9)

    dot = (cut_dx * thrust_dx) + (cut_dy * thrust_dy)
    assert dot == pytest.approx(0.0, abs=1e-9)


def test_upturn_bend_height_change_keeps_top_fixed_and_extends_bottom() -> None:
    common_kwargs = dict(
        radius_px=100.0,
        diameter_px=20.0,
        angle_deg=45.0,
        block_width_px=80.0,
        cut_midpoint=(30.0, -15.0),
        cut_angle_deg=45.0,
    )

    canvas_small = svgwriter.SVGCanvas(scale=1.0, width=300, height=300)
    _, _, _, _, top_small, bottom_small = svgwriter.thrust_block_for_upturn_bend_local(
        canvas_small,
        block_height_px=40.0,
        **common_kwargs,
    )

    canvas_tall = svgwriter.SVGCanvas(scale=1.0, width=300, height=300)
    _, _, _, _, top_tall, bottom_tall = svgwriter.thrust_block_for_upturn_bend_local(
        canvas_tall,
        block_height_px=80.0,
        **common_kwargs,
    )

    assert top_tall == pytest.approx(top_small)
    assert (bottom_tall - bottom_small) == pytest.approx(40.0)


def test_thrust_arrow_for_bend_local_starts_at_bend_midpoint_in_same_frame_as_bend_local() -> None:
    radius_px = 100.0
    angle_deg = 45.0
    canvas = svgwriter.SVGCanvas(scale=1.0, width=300, height=300)
    svgwriter.thrust_arrow_for_bend_local(canvas, radius_px=radius_px, angle_deg=angle_deg, offset_px=0.0, length_px=40.0, label=None)

    root = ET.fromstring(f"<svg xmlns=\"http://www.w3.org/2000/svg\">{''.join(canvas._lines)}</svg>")
    line = root.find("svg:line", SVG_NS)
    assert line is not None

    theta = math.radians(angle_deg)
    mid_theta = theta / 2.0
    expected_midpoint = (radius_px * math.sin(mid_theta), -radius_px * (1.0 - math.cos(mid_theta)))
    assert (float(line.attrib["x1"]), float(line.attrib["y1"])) == pytest.approx(expected_midpoint, abs=2.5e-3)


@pytest.mark.parametrize("angle_deg", [11.25, 22.5, 45.0, 90.0])
def test_horizontal_bend_plan_thrust_arrow_points_right_for_supported_angles(angle_deg: float) -> None:
    svg = svgwriter.build_horizontal_bend(
        block_height=1.6,
        block_width=2.5,
        block_length=2.8,
        block_depth=2.1,
        gw_level=0.8,
        od=0.6,
        depth_crown=1.0,
        start_angle=0.0,
        angle=angle_deg,
        canvas_w=600,
        canvas_h=400,
    )

    root = ET.fromstring(svg)
    arrow_line = next(
        line
        for line in root.findall("svg:line", SVG_NS)
        if line.attrib.get("stroke") == "#d32f2f"
    )
    assert float(arrow_line.attrib["x2"]) > float(arrow_line.attrib["x1"])


@pytest.mark.parametrize("od1, od2", [(24.0, 18.0), (18.0, 24.0)])
def test_taper_local_handles_reducing_and_increasing_diameters(od1: float, od2: float) -> None:
    canvas = svgwriter.SVGCanvas(scale=1.0, width=300, height=300)
    ports = svgwriter.taper_local(canvas, length=30.0, od1=od1, od2=od2, wall=2.0)

    assert len(ports) == 1
    _assert_port_matches(ports[0], (30.0, 0.0), (1.0, 0.0))
    svg = "<svg xmlns=\"http://www.w3.org/2000/svg\">" + "".join(canvas._lines) + "</svg>"
    _assert_svg_is_well_formed(svg)


@pytest.mark.xfail(reason="build_vertical_upturn_bend_section_svg currently ignores bend_orientation and angle, so distinct bend inputs yield identical SVG output.")
def test_vertical_upturn_section_builder_changes_when_bend_inputs_change() -> None:
    baseline = svgwriter.build_vertical_upturn_bend_section_svg(
        block_height=1.2,
        block_width=1.7,
        block_length=1.7,
        block_depth=1.0,
        gw_level=0.8,
        od=0.6,
        depth_crown=1.0,
        bend_orientation=90.0,
        angle=45.0,
        canvas_w=600,
        canvas_h=400,
    )
    changed = svgwriter.build_vertical_upturn_bend_section_svg(
        block_height=1.2,
        block_width=1.7,
        block_length=1.7,
        block_depth=1.0,
        gw_level=0.8,
        od=0.6,
        depth_crown=1.0,
        bend_orientation=15.0,
        angle=11.25,
        canvas_w=600,
        canvas_h=400,
    )
    assert baseline != changed
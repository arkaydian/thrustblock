from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


module_path = Path(__file__).resolve().parents[1] / "app" / "utils" / "svgwriter.py"
spec = spec_from_file_location("svgwriter_module", module_path)
svgwriter = module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(svgwriter)

SVGCanvas = svgwriter.SVGCanvas
build_vertical_downturn_bend_section_svg = svgwriter.build_vertical_downturn_bend_section_svg
build_horizontal_bend = svgwriter.build_horizontal_bend
socket_pipe_local = svgwriter.socket_pipe_local


def test_horizontal_bend_plan_draws_inlet_bellmouth_aligned_with_flow() -> None:
    svg = build_horizontal_bend(
        block_height=1.0,
        block_width=1.0,
        block_length=1.0,
        block_depth=0.5,
        gw_level=0.2,
        od=0.222,
        depth_crown=0.8,
        start_angle=0.0,
        angle=45.0,
        canvas_w=400,
        canvas_h=300,
    )

    assert "<polygon" in svg
    assert "Plan" in svg


def test_socket_pipe_local_can_draw_opening_only_for_outlet() -> None:
    canvas = SVGCanvas(scale=1.0, width=200, height=200)

    socket_pipe_local(
        canvas,
        length=40.0,
        diameter=20.0,
        socket_length=10.0,
        socket_od=24.0,
        is_inlet=False,
        draw_barrel=False,
    )

    svg = "\n".join(canvas._lines)
    assert "<polygon" in svg
    assert "<rect" not in svg
    assert 'points="0,-10.00' in svg


def test_socket_pipe_local_outlet_port_is_at_bellmouth_edge_when_opening_only() -> None:
    canvas = SVGCanvas(scale=1.0, width=200, height=200)

    ports = socket_pipe_local(
        canvas,
        length=40.0,
        diameter=20.0,
        socket_length=10.0,
        socket_od=24.0,
        is_inlet=False,
        draw_barrel=False,
    )

    assert ports[1]["center"][0] == 10.0


def test_horizontal_bend_plan_uses_opening_only_outlet_socket() -> None:
    svg = build_horizontal_bend(
        block_height=1.0,
        block_width=1.0,
        block_length=1.0,
        block_depth=0.5,
        gw_level=0.2,
        od=0.222,
        depth_crown=0.8,
        start_angle=0.0,
        angle=45.0,
        canvas_w=400,
        canvas_h=300,
    )

    assert svg.count("<polygon") >= 5
    assert "<rect" in svg


def test_vertical_downturn_section_builder_returns_svg() -> None:
    svg = build_vertical_downturn_bend_section_svg(
        block_height=2.0,
        block_width=2.5,
        block_length=4.5,
        block_depth=2.5,
        gw_level=0.8,
        od=0.6,
        depth_crown=1.0,
        angle=45.0,
        canvas_w=800,
        canvas_h=500,
    )

    assert "Vertical Downturn Bend" in svg
    assert "Ground level" in svg
    assert "stroke-dasharray=\"8,6\"" in svg


def test_vertical_downturn_section_includes_double_flanges_and_reinforcement() -> None:
    svg = build_vertical_downturn_bend_section_svg(
        block_height=2.0,
        block_width=2.5,
        block_length=4.5,
        block_depth=2.5,
        gw_level=0.8,
        od=0.6,
        depth_crown=1.0,
        angle=45.0,
        canvas_w=800,
        canvas_h=500,
    )

    # Keep only the dashed reinforcement perimeter (no internal grid lines).
    assert svg.count("stroke-dasharray=\"5,4\"") == 0
    assert svg.count("stroke-dasharray=\"6,5\"") >= 1
    assert svg.count("<rect") >= 3

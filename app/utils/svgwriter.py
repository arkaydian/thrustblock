import math
from types import SimpleNamespace
from typing import TYPE_CHECKING, Callable, List, NewType, Tuple, TypedDict

if TYPE_CHECKING:
    from app.civeng1.hydraulics.fittings import HorizontalBend
    from app.civeng1.hydraulics.fittings import TaperThrust
    from app.civeng1.hydraulics.fittings import VerticalUpturnBend
    from app.civeng1.structures.concrete import ThrustBlock

Mm = NewType("Mm", float)
Px = NewType("Px", float)

BEND_ANGLES = {
    "11.25°": 11.25,
    "22.5°": 22.5,
    "45°": 45.0,
    "90°": 90.0,
}

# =========================================================
# PORT DEFINITION
# =========================================================

class Port(TypedDict):
    """
    Represents a connection point on a pipe or fitting.

    center : (float, float)
        Centreline point (x, y) in SVG coordinates

    tangent : (float, float)
        Unit direction vector (tx, ty)
    """
    center: Tuple[float, float]
    tangent: Tuple[float, float]


# =========================================================
# SVG CANVAS
# =========================================================

class SVGCanvas:

    def __init__(
        self,
        scale: float = 1.0,
        width: int = 5000,
        height: int = 5000,
        pipe_stroke: str = "black",
    ) -> None:
        """
        Initialise the SVG canvas.

        Parameters
        ----------
        scale : float
            Scale factor applied to all dimensions

        width : float
            Canvas width (px)

        height : float
            Canvas height (px)

        pipe_stroke : str
            Default pipe stroke colour
        """
        self.scale = scale
        self.width = width
        self.height = height

        self._lines: list[str] = []  # stores SVG elements

        # Default styles
        self.pipe_fill = "white"
        self.pipe_stroke = pipe_stroke
        self.sw: float = 3 * scale
        self.dsw: float = 1.5 * scale


    # =========================================================
    # BASIC UTILITIES
    # =========================================================

    def mm_to_px(self, v: float) -> float:
        """
        Scale a value.

        Parameters
        ----------
        v : float

        Returns
        -------
        float
        """
        return v * self.scale


    def _unit(self, vx: float, vy: float) -> Tuple[float, float]:
        """
        Normalise a vector.

        Returns unit vector (vx, vy)
        """
        length = math.hypot(vx, vy)
        if length == 0:
            raise ValueError("Zero-length vector")
        return (vx / length, vy / length)


    def make_port(self, x: float, y: float, tx: float, ty: float) -> Port:
        """
        Create a port with a normalised tangent.

        Parameters
        ----------
        x, y : float
            Centreline location

        tx, ty : float
            Direction vector

        Returns
        -------
        Port
        """
        tx, ty = self._unit(tx, ty)
        return {"center": (x, y), "tangent": (tx, ty)}


    # =========================================================
    # GROUPING (REQUIRED FOR SNAPPING)
    # =========================================================

    def begin_group(self, transform: str) -> None:
        """
        Start a transformed SVG group.

        Parameters
        ----------
        transform : str
            SVG transform string
            e.g. "translate(x, y)", "rotate(angle)", "matrix(...)"
        """
        self._lines.append(f'<g transform="{transform}">')


    def end_group(self) -> None:
        """
        Close the current group.
        """
        self._lines.append("</g>")


    # =========================
    # PIPE / FITTING METHODS
    # =========================


    def pipe_from_port(self, port: Port, length: Px, diameter: Px) -> Port:
        """
        Draw a pipe with diameter (rectangle) from a port.

        Parameters
        ----------
        port : Port
            Starting point + direction

        length : Px
            Pipe length

        diameter : Px
            Pipe diameter (width)

        Returns
        -------
        Port
            New port at pipe end
        """

        # unpack port
        x, y = port["center"]
        tx, ty = port["tangent"]

        # end point
        x2 = x + tx * length
        y2 = y + ty * length

        # half width
        r = diameter / 2

        # normal vector (perpendicular)
        nx = -ty
        ny = tx

        # offset points (4 corners of rectangle)
        x1_top = x + nx * r
        y1_top = y + ny * r

        x1_bot = x - nx * r
        y1_bot = y - ny * r

        x2_top = x2 + nx * r
        y2_top = y2 + ny * r

        x2_bot = x2 - nx * r
        y2_bot = y2 - ny * r

        # draw pipe body
        self._lines.append(
            f'<polygon points="'
            f'{x1_top:.2f},{y1_top:.2f} '
            f'{x2_top:.2f},{y2_top:.2f} '
            f'{x2_bot:.2f},{y2_bot:.2f} '
            f'{x1_bot:.2f},{y1_bot:.2f}" '
            f'fill="{self.pipe_fill}" stroke="{self.pipe_stroke}" stroke-width="2"/>'
        )

        
        
        # draw centreline (grey + semi-transparent)
        self._lines.append(
            f'<line x1="{x:.2f}" y1="{y:.2f}" '
            f'x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="grey" '
            f'stroke-width="1" '
            f'stroke-dasharray="6,6" '
            f'stroke-opacity="0.5"/>'
        )
        return self.make_port(x2, y2, tx, ty)

    def place_fitting_local(self, port: Port, draw_func: Callable[[], List[Port]]) -> List[Port]:
        """
        Place a fitting defined in local coordinates (0,0) at a given port.

        Parameters
        ----------
        port : Port
            Target placement location and direction

        draw_func : Callable[[], List[Port]]
            Function that draws the fitting at (0,0) in local coordinates.
            Must return a list of output ports in LOCAL coordinates.

        Returns
        -------
        List[Port]
            Output ports transformed into global coordinates
        """
        # unpack reference port
        x, y = port["center"]
        tx, ty = port["tangent"]

        # determine rotation angle from direction vector
        angle = math.degrees(math.atan2(ty, tx))

        # apply transform (move + rotate)
        self.begin_group(f"translate({x},{y}) rotate({angle})")

        # draw fitting in local space
        local_ports = draw_func()

        # close transform group
        self.end_group()

        # prepare transformation
        cos_a = math.cos(math.radians(angle))
        sin_a = math.sin(math.radians(angle))

        global_ports: List[Port] = []

        # convert local ports → global ports
        for p in local_ports:
            lx, ly = p["center"]
            ltx, lty = p["tangent"]

            # rotate + translate position
            gx = x + lx * cos_a - ly * sin_a
            gy = y + lx * sin_a + ly * cos_a

            # rotate direction (no translation)
            gtx = ltx * cos_a - lty * sin_a
            gty = ltx * sin_a + lty * cos_a

            global_ports.append(self.make_port(gx, gy, gtx, gty))

        return global_ports

    # =========================================================
    # DRAWING PRIMITIVES
    # =========================================================

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str | None = None,
        stroke: str | None = None,
        stroke_w: float | None = None,
        dasharray: str | None = None,
    ) -> None:
        """
        Draw rectangle.

        Parameters
        ----------
        x, y : float
            Top-left corner

        w, h : float
            Width and height
        """
        fill = fill if fill is not None else "none"
        stroke = stroke if stroke is not None else "#000"
        stroke_w = stroke_w if stroke_w is not None else self.sw
        dash_attr = f' stroke-dasharray="{dasharray}"' if dasharray is not None else ""

        self._lines.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"{dash_attr}/>'
        )


    def circle(
        self,
        cx: float,
        cy: float,
        r: float,
        fill: str | None = None,
        stroke: str | None = None,
        stroke_w: float | None = None,
    ) -> None:
        """
        Draw circle.

        Parameters
        ----------
        cx, cy : float
            Centre point

        r : float
            Radius
        """
        fill = fill if fill is not None else "none"
        stroke = stroke if stroke is not None else "#000"
        stroke_w = stroke_w if stroke_w is not None else self.sw

        self._lines.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"/>'
        )


    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stroke: str = "#000",
        stroke_w: float | None = None,
        dasharray: str | None = None,
        stroke_opacity: float | None = None,
    ) -> None:
        """Draw a line segment."""
        stroke_w = stroke_w if stroke_w is not None else self.sw
        attrs = [
            f'x1="{x1:.2f}"',
            f'y1="{y1:.2f}"',
            f'x2="{x2:.2f}"',
            f'y2="{y2:.2f}"',
            f'stroke="{stroke}"',
            f'stroke-width="{stroke_w:.2f}"',
        ]
        if dasharray is not None:
            attrs.append(f'stroke-dasharray="{dasharray}"')
        if stroke_opacity is not None:
            attrs.append(f'stroke-opacity="{stroke_opacity:.2f}"')
        self._lines.append(f"<line {' '.join(attrs)}/>")


    def polygon(
        self,
        points: list[tuple[float, float]] | str,
        fill: str | None = None,
        stroke: str | None = None,
        stroke_w: float | None = None,
    ) -> None:
        """Draw a polygon from point tuples or a preformatted points string."""
        fill = fill if fill is not None else "none"
        stroke = stroke if stroke is not None else "#000"
        stroke_w = stroke_w if stroke_w is not None else self.sw

        if isinstance(points, str):
            points_str = points
        else:
            points_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)

        self._lines.append(
            f'<polygon points="{points_str}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"/>'
        )


    def text(
        self,
        x: float,
        y: float,
        content: str,
        fill: str = "#000",
        font_size: float = 12,
        font_family: str = "Arial, sans-serif",
        text_anchor: str | None = None,
        dominant_baseline: str | None = None,
    ) -> None:
        """Draw a text label."""
        attrs = [
            f'x="{x:.2f}"',
            f'y="{y:.2f}"',
            f'fill="{fill}"',
            f'font-size="{font_size:.2f}"',
            f'font-family="{font_family}"',
        ]
        if text_anchor is not None:
            attrs.append(f'text-anchor="{text_anchor}"')
        if dominant_baseline is not None:
            attrs.append(f'dominant-baseline="{dominant_baseline}"')

        self._lines.append(f"<text {' '.join(attrs)}>{content}</text>")


    def draw_ground_level(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        spacing: float = 20,
    ) -> None:
        """
        Draw ground level hatch line.
        """
        self._lines.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#000" stroke-width="{self.dsw:.2f}"/>'
        )

        dx = x2 - x1
        dy = y2 - y1
        length = (dx**2 + dy**2)**0.5
        if length == 0:
            return

        ux = dx / length
        uy = dy / length

        for i in range(int(length // spacing) + 1):
            px = x1 + ux * i * spacing
            py = y1 + uy * i * spacing

            ang = math.radians(120)
            dx_tick = math.cos(ang) * ux - math.sin(ang) * uy
            dy_tick = math.sin(ang) * ux + math.cos(ang) * uy

            tick_length = spacing * 0.4
            x_end = px + dx_tick * tick_length
            y_end = py + dy_tick * tick_length

            self._lines.append(
                f'<line x1="{px:.2f}" y1="{py:.2f}" x2="{x_end:.2f}" y2="{y_end:.2f}" '
                f'stroke="#000" stroke-width="{self.dsw:.2f}"/>'
            )


    def draw_trench(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """
        Draw trench box with dashed centreline.
        """
        self._lines.append(
            f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{(x2-x1):.2f}" height="{(y2-y1):.2f}" '
            f'fill="none" stroke="#000" stroke-width="{self.dsw:.2f}"/>'
        )

        cx = (x1 + x2) / 2
        self._lines.append(
            f'<line x1="{cx:.2f}" y1="{y1:.2f}" x2="{cx:.2f}" y2="{y2:.2f}" '
            f'stroke="#000" stroke-dasharray="5,5" stroke-width="{self.dsw:.2f}"/>'
        )

    # =========================================================
    # OUTPUT
    # =========================================================

    def save(self, filename: str = "output.svg") -> None:
        """
        Write SVG file.
        """
        with open(filename, "w", encoding="utf-8") as f:
            f.write(
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}">\n'
            )
            f.write("\n".join(self._lines))
            f.write("\n</svg>")


def _canvas_svg_string(canvas: SVGCanvas) -> str:
    """Serialize a canvas to a standalone SVG document string."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{canvas.width}" height="{canvas.height}" '
        f'viewBox="0 0 {canvas.width} {canvas.height}">\n'
        + "\n".join(canvas._lines)
        + "\n</svg>"
    )


def socket_pipe_local(
    canvas: SVGCanvas,
    length: float,
    diameter: float,
    socket_length: float,
    socket_od: float,
    is_inlet: bool = True,
    draw_barrel: bool = True,
) -> list[Port]:
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
    canvas: SVGCanvas,
    radius_px: float,
    diameter_px: float,
    angle_deg: float,
) -> list[Port]:
    """
    Upturn bend in LOCAL coordinates.

    Inlet:
        (0,0) tangent +X

    Positive angle bends upward in screen space (negative SVG Y).
    """

    theta = math.radians(angle_deg)

    end_x = radius_px * math.sin(theta)
    end_y = -radius_px * (1 - math.cos(theta))

    path = (
        f"M 0 0 "
        f"A {radius_px:.2f} {radius_px:.2f} "
        f"0 0 0 "
        f"{end_x:.2f} {end_y:.2f}"
    )

    outline_width = 2

    # Bend outline
    canvas._lines.append(
        f'<path d="{path}" '
        f'stroke="black" '
        f'stroke-width="{diameter_px + outline_width:.2f}" '
        f'fill="none" '
        f'stroke-linecap="butt"/>'
    )

    # Bend body
    canvas._lines.append(
        f'<path d="{path}" '
        f'stroke="white" '
        f'stroke-width="{diameter_px - outline_width:.2f}" '
        f'fill="none" '
        f'stroke-linecap="butt"/>'
    )

    # Centreline
    canvas._lines.append(
        f'<path d="{path}" '
        f'stroke="#999999" '
        f'stroke-width="1" '
        f'stroke-dasharray="6,6" '
        f'stroke-opacity="0.5" '
        f'fill="none"/>'
    )

    return [
        canvas.make_port(0, 0, 1, 0),
        canvas.make_port(
            end_x,
            end_y,
            math.cos(theta),
            -math.sin(theta),
        ),
    ]


def thrust_component_arrows_for_bend_local(
    canvas: SVGCanvas,
    origin_x: float,
    origin_y: float,
    tx_len_px: float,
    tz_len_px: float,
    t_len_px: float,
    t_direction_x: float = 1,
    t_direction_y: float = 1,
    stroke: str = "#d32f2f",
    stroke_width: float = 1.5,
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

        canvas._lines.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" '
            f'x2="{base_x:.2f}" y2="{base_y:.2f}" '
            f'stroke="{stroke}" stroke-width="{stroke_width:.2f}"{line_dash_attr}/>'
        )
        canvas._lines.append(
            f'<polygon points="{x2:.2f},{y2:.2f} '
            f'{left_x:.2f},{left_y:.2f} '
            f'{right_x:.2f},{right_y:.2f}" '
            f'fill="{stroke}" stroke="{stroke}" stroke-width="1"/>'
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

        canvas._lines.append(
            f'<text x="{label_x:.2f}" y="{label_y:.2f}" '
            f'fill="{stroke}" font-size="11" font-family="Arial, sans-serif" '
            f'text-anchor="middle" dominant-baseline="middle">{label}</text>'
        )

    _draw_arrow(origin_x, origin_y, 1, 0, tx_len_px, "T_x", 1, 0, line_dasharray="6,4")
    _draw_arrow(origin_x, origin_y, 0, 1, tz_len_px, "T_z", 4, 14, line_dasharray="6,4")
    _draw_arrow(origin_x, origin_y, t_direction_x, t_direction_y, t_len_px, "T", 8, 12)


def thrust_block_for_upturn_bend_local(
    canvas: SVGCanvas,
    radius_px: float,
    diameter_px: float,
    angle_deg: float,
    block_width_px: float,
    block_height_px: float,
) -> tuple[float, float, float, float, float, float]:
    """Draw an angle-dependent support block under an upturn bend.

    The bend midpoint on the outside wall is used as the thrust contact location.
    A single straight diagonal cut is used on the top-left corner, aligned
    with the bend angle, so the resultant thrust has a clear flush support face.
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

    # Resultant thrust direction from inlet and outlet tangents.
    thrust_x = 1 - math.cos(theta)
    thrust_y = math.sin(theta)
    thrust_len = math.hypot(thrust_x, thrust_y)
    if thrust_len == 0:
        return (
            contact_x,
            contact_y,
            contact_x,
            contact_x + block_width_px,
            contact_y,
            contact_y + block_height_px,
        )

    thrust_ux = thrust_x / thrust_len
    thrust_uy = thrust_y / thrust_len

    # Diagonal cut must be perpendicular to thrust so T acts normal to the face.
    cut_ux = -thrust_uy
    cut_uy = thrust_ux

    # Force block top to match inlet pipe crown in local coordinates.
    top = -diameter_px / 2

    # Put the top diagonal point where the thrust-normal line intersects the block top.
    if abs(cut_uy) < 1e-9:
        top_cut_x = contact_x
    else:
        top_param = (top - contact_y) / cut_uy
        top_cut_x = contact_x + top_param * cut_ux
    top_cut_y = top

    # Keep the second diagonal point on the same thrust-normal line at the left edge.
    # This preserves one straight cut that stays perpendicular to T.
    left_cut_y = top + max(12.0, min(block_height_px * 0.58, block_height_px - 12.0))
    if abs(cut_uy) < 1e-9:
        left_cut_x = top_cut_x - max(diameter_px * 0.5, 24.0)
    else:
        left_param = (left_cut_y - contact_y) / cut_uy
        left_cut_x = contact_x + left_param * cut_ux

    left = left_cut_x
    right = left + block_width_px
    bottom = top + block_height_px

    # Simple block with one straight diagonal cut from left edge to top edge.
    p1 = (left, bottom)
    p2 = (right, bottom)
    p3 = (right, top)
    p4 = (top_cut_x, top_cut_y)
    p5 = (left_cut_x, left_cut_y)

    points = " ".join(f"{x:.2f},{y:.2f}" for x, y in [p1, p2, p3, p4, p5])
    canvas._lines.append(
        f'<polygon points="{points}" '
        f'fill="#d9d9d9" stroke="black" stroke-width="2"/>'
    )

    # Return thrust contact and block bounds for external annotation drawing.
    return (contact_x, contact_y, left, right, top, bottom)


def thrust_arrow_for_bend_local(
    canvas: SVGCanvas,
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

    theta = math.radians(angle_deg)

    # Midpoint of bend centreline arc
    mid_theta = theta / 2
    mid_x = radius_px * math.sin(mid_theta)
    mid_y = radius_px * (1 - math.cos(mid_theta))

    # Resultant thrust vector from inlet and outlet tangents
    thrust_x = 1 - math.cos(theta)
    thrust_y = 0 - math.sin(theta)

    thrust_len = math.hypot(thrust_x, thrust_y)
    if thrust_len == 0:
        return

    ux = thrust_x / thrust_len
    uy = thrust_y / thrust_len

    # Perpendicular vector for arrow head and optional label offset
    vx = -uy
    vy = ux

    start_x = mid_x + ux * offset_px
    start_y = mid_y + uy * offset_px
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
    canvas: SVGCanvas,
    length: float,
    od1: float,
    od2: float,
    wall: float = 2.0,
) -> list[Port]:
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
    canvas: SVGCanvas,
    diameter_px: float,
    projection_px: float = 40,
    thickness_px: float = 15,
    flange_width_ratio: float = 1.15,
) -> list[Port]:
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
    canvas._lines.append(
        f'<rect x="{-half_p:.2f}" y="{-flange_half_d:.2f}" '
        f'width="{projection_px:.2f}" height="{diameter_px * flange_width_ratio:.2f}" '
        f'fill="{canvas.pipe_fill}" '
        f'stroke="{canvas.pipe_stroke}" '
        f'stroke-width="2"/>'
    )

    # Centreline
    canvas._lines.append(
        f'<line x1="{-half_p:.2f}" y1="0" x2="{half_p:.2f}" y2="0" '
        f'stroke="#999999" '
        f'stroke-width="1" '
        f'stroke-dasharray="6,6" '
        f'stroke-opacity="0.5"/>'
    )

    return [
        canvas.make_port(-half_p, 0, -1, 0),
        canvas.make_port(half_p, 0, 1, 0),
    ]


def thrust_block_for_bend_local(
    canvas: SVGCanvas,
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

    theta = math.radians(angle_deg)

    # Midpoint of the bend centreline
    mid_theta = theta / 2

    mid_x = radius_px * math.sin(mid_theta)
    mid_y = radius_px * (1 - math.cos(mid_theta))

    # Inlet tangent
    in_tx = 1
    in_ty = 0

    # Outlet tangent
    out_tx = math.cos(theta)
    out_ty = math.sin(theta)

    # Resultant thrust direction
    thrust_x = in_tx - out_tx
    thrust_y = in_ty - out_ty

    # Normalise thrust direction
    thrust_len = math.hypot(thrust_x, thrust_y)

    if thrust_len == 0:
        return

    ux = thrust_x / thrust_len
    uy = thrust_y / thrust_len

    # Perpendicular direction to thrust
    vx = -uy
    vy = ux

    # Position block outside the pipe body
    centre_x = mid_x + ux * (diameter_px / 2 + block_depth_px / 2 + offset_px)
    centre_y = mid_y + uy * (diameter_px / 2 + block_depth_px / 2 + offset_px)

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
    canvas: SVGCanvas,
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

    theta = math.radians(angle_deg)
    mid_theta = theta / 2

    mid_x = radius_px * math.sin(mid_theta)
    mid_y = radius_px * (1 - math.cos(mid_theta))

    thrust_x = 1 - math.cos(theta)
    thrust_y = -math.sin(theta)
    thrust_len = math.hypot(thrust_x, thrust_y)
    if thrust_len == 0:
        return

    ux = thrust_x / thrust_len
    uy = thrust_y / thrust_len
    vx = -uy
    vy = ux

    # Show transfer from bend outside wall midpoint into the restraint block.
    force_start_x = mid_x + ux * (diameter_px / 2)
    force_start_y = mid_y + uy * (diameter_px / 2)
    force_end_x = force_start_x + ux * (block_depth_px + offset_px)
    force_end_y = force_start_y + uy * (block_depth_px + offset_px)

    canvas._lines.append(
        f'<line x1="{force_start_x:.2f}" y1="{force_start_y:.2f}" '
        f'x2="{force_end_x:.2f}" y2="{force_end_y:.2f}" '
        f'stroke="#666666" stroke-width="1.5" stroke-dasharray="5,4"/>'
    )

    if label:
        label_x = force_end_x + vx * 12
        label_y = force_end_y + vy * 12
        canvas._lines.append(
            f'<text x="{label_x:.2f}" y="{label_y:.2f}" '
            f'fill="#333333" font-size="12" '
            f'font-family="Arial, sans-serif">{label}</text>'
        )


def create_canvas(
    total_len: float,
    max_height: float,
    canvas_w: int,
    canvas_h: int,
    margin_x: int = 110,
    margin_y: int = 90,
) -> dict[str, float | int]:
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
    draw_w = canvas_w - 2 * margin_x  # Available horizontal space for the pipe geometry
    draw_h = canvas_h - 2 * margin_y  # Available vertical space for the pipe geometry

    # Scale factor: converts mm → SVG pixels.
    # min() picks the tighter constraint so the drawing never overflows in either direction.
    scale = min(draw_w / total_len, draw_h / (max_height * 1.1))

    cx = canvas_w / 2  # Horizontal centre of the canvas in pixels
    cy = canvas_h / 2 - 20  # Vertical centre, shifted up 20px to leave room for the dim line

    return {
        "scale": scale,
        "cx": cx,
        "cy": cy,
        "canvas_w": canvas_w,
        "canvas_h": canvas_h,
    }


def vertical_upturn_bend_section(
    thrust_block: "ThrustBlock | SimpleNamespace",
    vertical_bend: "VerticalUpturnBend | SimpleNamespace",
    z0_m: float = 1.0,
    z_gw_m: float = 0.8,
) -> None:

    # =========================
    # CREATE CANVAS
    # =========================
    outside_diameter_mm = vertical_bend.outside_diameter * 1000
    bend_angle_deg = vertical_bend.angle
    bend_radius_mm = (
        vertical_bend.radius * 1000
        if vertical_bend.radius > 0
        else 1.5 * outside_diameter_mm
    )

    block_height_mm = thrust_block.height * 1000
    block_length_mm = thrust_block.length * 1000

    # Fit the geometry to canvas with sensible dynamic bounds.
    total_len_mm = max(4000.0, 2 * 1000 + 2 * 150 + bend_radius_mm)
    max_height_mm = max(3000.0, block_height_mm * 1.8)

    ctx = create_canvas(total_len_mm, max_height_mm, 600, 400)

    canvas = SVGCanvas(
        ctx["scale"],
        int(ctx["canvas_w"]),
        int(ctx["canvas_h"]),
    )

    cx = ctx["cx"]
    cy = ctx["cy"]

    # =========================
    # BEND (CENTRE FEATURE)
    # =========================
    bend_diameter = canvas.mm_to_px(outside_diameter_mm)
    bend_radius = canvas.mm_to_px(bend_radius_mm)

    bend_ports = canvas.place_fitting_local(
        canvas.make_port(cx, cy, 1, 0),
        lambda: bend_local(
            canvas,
            radius_px=bend_radius,
            diameter_px=bend_diameter,
            angle_deg=bend_angle_deg,
        )
    )

    bend_inlet = bend_ports[0]
    bend_outlet = bend_ports[1]

    # =========================
    # SOCKET ON INLET SIDE
    # =========================
    socket_od = canvas.mm_to_px(1.15 * outside_diameter_mm)

    socket_ports = canvas.place_fitting_local(
        bend_inlet,
        lambda: socket_pipe_local(
            canvas,
            length=canvas.mm_to_px(150),
            diameter=bend_diameter,
            socket_length=canvas.mm_to_px(150),
            socket_od=socket_od,
        ),
    )

    socket_inlet = socket_ports[0]

    # =========================
    # INLET PIPE
    # =========================
    inlet_pipe_port = canvas.make_port(
        socket_inlet["center"][0],
        socket_inlet["center"][1],
        socket_inlet["tangent"][0],
        socket_inlet["tangent"][1],
    )

    inlet_pipe_end_port = canvas.pipe_from_port(
        inlet_pipe_port,
        Px(canvas.mm_to_px(1000)),
        Px(bend_diameter),
    )

    # =========================
    # Outlet Socket
    # =========================

    socket_length = canvas.mm_to_px(140)
    socket_od = canvas.mm_to_px(1.15 * outside_diameter_mm)

    socket_ports = canvas.place_fitting_local(
        bend_outlet,
        lambda: socket_pipe_local(
            canvas,
            length=socket_length,
            diameter=bend_diameter,
            socket_length=canvas.mm_to_px(150),
            socket_od=socket_od,
            is_inlet=False,
        ),
    )

    socket_outlet = socket_ports[1]

    # =========================
    # OUTLET PIPE
    # =========================
    canvas.pipe_from_port(
        socket_outlet,
        Px(canvas.mm_to_px(1000)),
        Px(bend_diameter),
    )

    # =========================
    # THRUST BLOCK (angle dependent, supports bend midpoint)
    # =========================
    canvas.begin_group(f"translate({cx},{cy}) rotate(0)")
    contact_x, contact_y, block_left, block_right, block_top, block_bottom = thrust_block_for_upturn_bend_local(
        canvas,
        radius_px=bend_radius,
        diameter_px=bend_diameter,
        angle_deg=bend_angle_deg,
        block_width_px=canvas.mm_to_px(block_length_mm),
        block_height_px=canvas.mm_to_px(block_height_mm),
    )

    # THRUST COMPONENT ARROWS (Tx, Tz and resultant T)
    theta = math.radians(bend_angle_deg)
    t_direction_x = 1 - math.cos(theta)
    t_direction_y = math.sin(theta)

    thrust_component_arrows_for_bend_local(
        canvas,
        origin_x=contact_x,
        origin_y=contact_y,
        tx_len_px=canvas.mm_to_px(620),
        tz_len_px=canvas.mm_to_px(500),
        t_len_px=canvas.mm_to_px(670),
        t_direction_x=t_direction_x,
        t_direction_y=t_direction_y,
    )
    canvas.end_group()

    # Convert block bounds from local bend coordinates to global canvas coordinates.
    block_left_g = block_left + cx
    block_right_g = block_right + cx
    block_top_g = block_top + cy
    block_bottom_g = block_bottom + cy

    # =========================
    # GROUND LEVEL (REFERENCE Z0 FROM PIPE CROWN)
    # =========================
    inlet_top_wall_center_x = (
        inlet_pipe_port["center"][0] + inlet_pipe_end_port["center"][0]
    ) / 2
    crown_y = inlet_pipe_port["center"][1] - (bend_diameter / 2)
    z0_px = canvas.mm_to_px(z0_m * 1000)
    ground_y = max(20.0, crown_y - z0_px)

    ground_x1 = 10.0
    ground_x2 = float(ctx["canvas_w"]) - 10.0
    canvas._lines.append(
        f'<line x1="{ground_x1:.2f}" y1="{ground_y:.2f}" '
        f'x2="{ground_x2:.2f}" y2="{ground_y:.2f}" '
        f'stroke="black" stroke-width="2"/>'
    )

    # Groundwater level placeholder (depth below ground level).
    z_gw_px = canvas.mm_to_px(z_gw_m * 1000)
    gw_y = min(float(ctx["canvas_h"]) - 10.0, ground_y + z_gw_px)
    canvas._lines.append(
        f'<line x1="{ground_x1:.2f}" y1="{gw_y:.2f}" '
        f'x2="{ground_x2:.2f}" y2="{gw_y:.2f}" '
        f'stroke="#42a5f5" stroke-width="1" stroke-dasharray="8,6"/>'
    )

    label_x = float(ctx["canvas_w"]) * 0.52
    label_y = ground_y - 16
    triangle_half_w = 6.0
    triangle_h = 10.0
    tri_top_y = ground_y - triangle_h

    canvas._lines.append(
        f'<text x="{label_x:.2f}" y="{label_y:.2f}" '
        f'fill="black" font-size="12" '
        f'font-family="Arial, sans-serif" '
        f'text-anchor="middle">Ground level</text>'
    )

    # Downward triangle marker beneath the label.
    canvas._lines.append(
        f'<polygon points="'
        f'{label_x - triangle_half_w:.2f},{tri_top_y:.2f} '
        f'{label_x + triangle_half_w:.2f},{tri_top_y:.2f} '
        f'{label_x:.2f},{tri_top_y + triangle_h:.2f}'
        f'" fill="none" stroke="black" stroke-width="1.5"/>'
    )

    # Vertical Z0 dimension arrow between inlet crown and ground level.
    z0_arrow_x = inlet_top_wall_center_x
    z0_top_y = min(ground_y, crown_y)
    z0_bottom_y = max(ground_y, crown_y)
    z0_head_len = 8.0
    z0_head_half_w = 4.0

    shaft_top_y = z0_top_y + z0_head_len
    shaft_bottom_y = z0_bottom_y - z0_head_len
    if shaft_bottom_y > shaft_top_y:
        canvas._lines.append(
            f'<line x1="{z0_arrow_x:.2f}" y1="{shaft_top_y:.2f}" '
            f'x2="{z0_arrow_x:.2f}" y2="{shaft_bottom_y:.2f}" '
            f'stroke="black" stroke-width="1.6"/>'
        )

    canvas._lines.append(
        f'<polygon points="'
        f'{z0_arrow_x - z0_head_half_w:.2f},{z0_top_y + z0_head_len:.2f} '
        f'{z0_arrow_x + z0_head_half_w:.2f},{z0_top_y + z0_head_len:.2f} '
        f'{z0_arrow_x:.2f},{z0_top_y:.2f}'
        f'" fill="black" stroke="black" stroke-width="1"/>'
    )
    canvas._lines.append(
        f'<polygon points="'
        f'{z0_arrow_x - z0_head_half_w:.2f},{z0_bottom_y - z0_head_len:.2f} '
        f'{z0_arrow_x + z0_head_half_w:.2f},{z0_bottom_y - z0_head_len:.2f} '
        f'{z0_arrow_x:.2f},{z0_bottom_y:.2f}'
        f'" fill="black" stroke="black" stroke-width="1"/>'
    )

    z0_text_x = z0_arrow_x + 10.0
    z0_text_y = (z0_top_y + z0_bottom_y) / 2
    canvas._lines.append(
        f'<text x="{z0_text_x:.2f}" y="{z0_text_y:.2f}" '
        f'fill="black" font-size="13" '
        f'font-family="Arial, sans-serif" dominant-baseline="middle">'
        f'Z_0 = {z0_m:.1f}m</text>'
    )

    # Vertical Z_GW dimension arrow between ground level and groundwater level.
    z_gw_arrow_x = ground_x1 + 22.0
    z_gw_top_y = min(ground_y, gw_y)
    z_gw_bottom_y = max(ground_y, gw_y)
    z_gw_head_len = 8.0
    z_gw_head_half_w = 4.0

    z_gw_shaft_top_y = z_gw_top_y + z_gw_head_len
    z_gw_shaft_bottom_y = z_gw_bottom_y - z_gw_head_len
    if z_gw_shaft_bottom_y > z_gw_shaft_top_y:
        canvas._lines.append(
            f'<line x1="{z_gw_arrow_x:.2f}" y1="{z_gw_shaft_top_y:.2f}" '
            f'x2="{z_gw_arrow_x:.2f}" y2="{z_gw_shaft_bottom_y:.2f}" '
            f'stroke="#42a5f5" stroke-width="1.6"/>'
        )

    canvas._lines.append(
        f'<polygon points="'
        f'{z_gw_arrow_x - z_gw_head_half_w:.2f},{z_gw_top_y + z_gw_head_len:.2f} '
        f'{z_gw_arrow_x + z_gw_head_half_w:.2f},{z_gw_top_y + z_gw_head_len:.2f} '
        f'{z_gw_arrow_x:.2f},{z_gw_top_y:.2f}'
        f'" fill="#42a5f5" stroke="#42a5f5" stroke-width="1"/>'
    )
    canvas._lines.append(
        f'<polygon points="'
        f'{z_gw_arrow_x - z_gw_head_half_w:.2f},{z_gw_bottom_y - z_gw_head_len:.2f} '
        f'{z_gw_arrow_x + z_gw_head_half_w:.2f},{z_gw_bottom_y - z_gw_head_len:.2f} '
        f'{z_gw_arrow_x:.2f},{z_gw_bottom_y:.2f}'
        f'" fill="#42a5f5" stroke="#42a5f5" stroke-width="1"/>'
    )

    z_gw_text_x = z_gw_arrow_x + 10.0
    z_gw_text_y = (z_gw_top_y + z_gw_bottom_y) / 2
    canvas._lines.append(
        f'<text x="{z_gw_text_x:.2f}" y="{z_gw_text_y:.2f}" '
        f'fill="#42a5f5" font-size="13" '
        f'font-family="Arial, sans-serif" dominant-baseline="middle" '
        f'text-anchor="start">'
        f'Z_GW = {z_gw_m:.1f}m</text>'
    )

    # =========================
    # BLOCK DIMENSIONS (Z_b, H, L)
    # =========================
    dim_color = "black"
    dim_dash = "8,6"
    head_len = 8.0
    head_half_w = 4.0

    # Horizontal dashed references at block top and bottom.
    h_arrow_x = block_right_g + 28.0
    z_b_arrow_x = h_arrow_x + 86.0
    canvas._lines.append(
        f'<line x1="{block_right_g:.2f}" y1="{block_top_g:.2f}" '
        f'x2="{h_arrow_x:.2f}" y2="{block_top_g:.2f}" '
        f'stroke="{dim_color}" stroke-width="1.5" stroke-dasharray="{dim_dash}"/>'
    )
    canvas._lines.append(
        f'<line x1="{block_right_g:.2f}" y1="{block_bottom_g:.2f}" '
        f'x2="{z_b_arrow_x:.2f}" y2="{block_bottom_g:.2f}" '
        f'stroke="{dim_color}" stroke-width="1.5" stroke-dasharray="{dim_dash}"/>'
    )

    # H (block height): vertical two-sided arrow at right of block.
    h_top = block_top_g
    h_bottom = block_bottom_g
    h_shaft_top = h_top + head_len
    h_shaft_bottom = h_bottom - head_len
    if h_shaft_bottom > h_shaft_top:
        canvas._lines.append(
            f'<line x1="{h_arrow_x:.2f}" y1="{h_shaft_top:.2f}" '
            f'x2="{h_arrow_x:.2f}" y2="{h_shaft_bottom:.2f}" '
            f'stroke="{dim_color}" stroke-width="1.8"/>'
        )

    canvas._lines.append(
        f'<polygon points="'
        f'{h_arrow_x - head_half_w:.2f},{h_top + head_len:.2f} '
        f'{h_arrow_x + head_half_w:.2f},{h_top + head_len:.2f} '
        f'{h_arrow_x:.2f},{h_top:.2f}'
        f'" fill="{dim_color}" stroke="{dim_color}" stroke-width="1"/>'
    )
    canvas._lines.append(
        f'<polygon points="'
        f'{h_arrow_x - head_half_w:.2f},{h_bottom - head_len:.2f} '
        f'{h_arrow_x + head_half_w:.2f},{h_bottom - head_len:.2f} '
        f'{h_arrow_x:.2f},{h_bottom:.2f}'
        f'" fill="{dim_color}" stroke="{dim_color}" stroke-width="1"/>'
    )

    canvas._lines.append(
        f'<text x="{(h_arrow_x + 10.0):.2f}" y="{((h_top + h_bottom) / 2):.2f}" '
        f'fill="{dim_color}" font-size="13" '
        f'font-family="Arial, sans-serif" dominant-baseline="middle">'
        f'H = {thrust_block.height:.1f}m</text>'
    )

    # Z_b (depth from ground to block base): vertical two-sided arrow farther right.
    z_b_top = ground_y
    z_b_bottom = block_bottom_g
    z_b_shaft_top = z_b_top + head_len
    z_b_shaft_bottom = z_b_bottom - head_len
    if z_b_shaft_bottom > z_b_shaft_top:
        canvas._lines.append(
            f'<line x1="{z_b_arrow_x:.2f}" y1="{z_b_shaft_top:.2f}" '
            f'x2="{z_b_arrow_x:.2f}" y2="{z_b_shaft_bottom:.2f}" '
            f'stroke="{dim_color}" stroke-width="1.8"/>'
        )

    canvas._lines.append(
        f'<polygon points="'
        f'{z_b_arrow_x - head_half_w:.2f},{z_b_top + head_len:.2f} '
        f'{z_b_arrow_x + head_half_w:.2f},{z_b_top + head_len:.2f} '
        f'{z_b_arrow_x:.2f},{z_b_top:.2f}'
        f'" fill="{dim_color}" stroke="{dim_color}" stroke-width="1"/>'
    )
    canvas._lines.append(
        f'<polygon points="'
        f'{z_b_arrow_x - head_half_w:.2f},{z_b_bottom - head_len:.2f} '
        f'{z_b_arrow_x + head_half_w:.2f},{z_b_bottom - head_len:.2f} '
        f'{z_b_arrow_x:.2f},{z_b_bottom:.2f}'
        f'" fill="{dim_color}" stroke="{dim_color}" stroke-width="1"/>'
    )

    z_b_m = (z_b_bottom - z_b_top) / (canvas.scale * 1000)
    canvas._lines.append(
        f'<text x="{(z_b_arrow_x + 10.0):.2f}" y="{((z_b_top + z_b_bottom) / 2):.2f}" '
        f'fill="{dim_color}" font-size="13" '
        f'font-family="Arial, sans-serif" dominant-baseline="middle">'
        f'Z_b = {z_b_m:.1f}m</text>'
    )

    # L (block length): horizontal two-sided arrow under the block.
    l_arrow_y = block_bottom_g + 58.0
    l_head_len = 10.0
    l_head_half_h = 4.5
    l_shaft_left = block_left_g + l_head_len
    l_shaft_right = block_right_g - l_head_len

    canvas._lines.append(
        f'<line x1="{block_left_g:.2f}" y1="{block_bottom_g:.2f}" '
        f'x2="{block_left_g:.2f}" y2="{l_arrow_y:.2f}" '
        f'stroke="{dim_color}" stroke-width="1.5" stroke-dasharray="{dim_dash}"/>'
    )
    canvas._lines.append(
        f'<line x1="{block_right_g:.2f}" y1="{block_bottom_g:.2f}" '
        f'x2="{block_right_g:.2f}" y2="{l_arrow_y:.2f}" '
        f'stroke="{dim_color}" stroke-width="1.5" stroke-dasharray="{dim_dash}"/>'
    )

    if l_shaft_right > l_shaft_left:
        canvas._lines.append(
            f'<line x1="{l_shaft_left:.2f}" y1="{l_arrow_y:.2f}" '
            f'x2="{l_shaft_right:.2f}" y2="{l_arrow_y:.2f}" '
            f'stroke="{dim_color}" stroke-width="1.8"/>'
        )

    canvas._lines.append(
        f'<polygon points="'
        f'{block_left_g + l_head_len:.2f},{l_arrow_y - l_head_half_h:.2f} '
        f'{block_left_g + l_head_len:.2f},{l_arrow_y + l_head_half_h:.2f} '
        f'{block_left_g:.2f},{l_arrow_y:.2f}'
        f'" fill="{dim_color}" stroke="{dim_color}" stroke-width="1"/>'
    )
    canvas._lines.append(
        f'<polygon points="'
        f'{block_right_g - l_head_len:.2f},{l_arrow_y - l_head_half_h:.2f} '
        f'{block_right_g - l_head_len:.2f},{l_arrow_y + l_head_half_h:.2f} '
        f'{block_right_g:.2f},{l_arrow_y:.2f}'
        f'" fill="{dim_color}" stroke="{dim_color}" stroke-width="1"/>'
    )

    canvas._lines.append(
        f'<text x="{((block_left_g + block_right_g) / 2):.2f}" y="{(l_arrow_y + 14.0):.2f}" '
        f'fill="{dim_color}" font-size="13" '
        f'font-family="Arial, sans-serif" text-anchor="middle">'
        f'L = {thrust_block.length:.1f}m</text>'
    )

    # =========================
    # SAVE SVG
    # =========================
    canvas.save("./test_pipe.svg")

def thrust_arrow_for_taper_axial(
    canvas: SVGCanvas,
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
    canvas: SVGCanvas,
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
    canvas: SVGCanvas,
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
    canvas: SVGCanvas,
    x_left: float,
    x_right: float,
    y: float,
    label: str,
    color: str = "black",
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
        y + 16,
        label,
        fill=color,
        font_size=13,
        font_family="Arial, sans-serif",
        text_anchor="middle",
    )


def draw_plan_bellmouth(
    canvas: SVGCanvas,
    length_px: float,
    connected_diameter_px: float,
    opening_scale: float = 1.6,
) -> list[Port]:
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
    canvas: SVGCanvas,
    diameter_px: float,
    flange_t_px: float,
    flange_gap_px: float,
    height_factor: float,
) -> list[Port]:
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
    canvas: SVGCanvas,
    diameter_px: float,
    socket_w_px: float,
    height_factor: float,
) -> list[Port]:
    """Draw a local single socket collar and return inlet/outlet ports."""
    socket_h = diameter_px * height_factor
    canvas.rect(0, -socket_h / 2, socket_w_px, socket_h, fill="#efefef", stroke="black", stroke_w=1.8)

    return [
        canvas.make_port(0, 0, -1, 0),
        canvas.make_port(socket_w_px, 0, 1, 0),
    ]


def draw_plan_pipe_segment(
    canvas: SVGCanvas,
    length_px: float,
    diameter_px: float,
) -> list[Port]:
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
) -> None:
    """Draw taper thrust plan and section views using model inputs."""

    # Same canvas size as bend-section drawing.
    canvas_w = 600
    canvas_h = 400

    # Drawing scale for both taper drawings (px per metre).
    m_to_px = 46.0

    # Inputs from domain models.
    length_m = thrust_block.length
    block_width_m = thrust_block.width
    block_height_m = thrust_block.height
    pipe_od_large_m = taper_thrust.outside_diameter_large
    pipe_od_small_m = taper_thrust.outside_diameter_small

    # =========================
    # PLAN DRAWING
    # =========================
    plan_canvas = SVGCanvas(scale=1.0, width=canvas_w, height=canvas_h)

    plan_x1 = 20.0
    plan_x2 = 580.0
    plan_y1 = 20.0
    plan_y2 = 350.0
    plan_cx = (plan_x1 + plan_x2) / 2
    plan_cy = (plan_y1 + plan_y2) / 2
    plan_block_w = length_m * m_to_px
    plan_block_h = block_width_m * m_to_px

    plan_left = plan_cx - (plan_block_w / 2)
    plan_right = plan_cx + (plan_block_w / 2)
    plan_top = plan_cy - (plan_block_h / 2)
    plan_bottom = plan_cy + (plan_block_h / 2)
    # Keep W-dimension near right canvas edge with margin, but clear of the block.
    w_dim_x = max(plan_right + 12.0, plan_x2 - 16.0)

    plan_canvas.rect(plan_left, plan_top, plan_block_w, plan_block_h, fill="#d9d9d9", stroke="black", stroke_w=2)

    def _draw_wavy_horizontal_line(x1: float, x2: float, y: float, amp: float = 2.2, wave_len: float = 28.0) -> None:
        """Draw a hand-sketched style wavy horizontal line segment."""
        n_segments = max(10, int((x2 - x1) / 8.0))
        prev_x = x1
        prev_y = y
        for i in range(1, n_segments + 1):
            t = i / n_segments
            x = x1 + (x2 - x1) * t
            dx = x - x1
            # Blend multiple frequencies for a less uniform, sketch-like waviness.
            wave_y = y + amp * (
                0.65 * math.sin((2 * math.pi * dx / wave_len))
                + 0.25 * math.sin((2 * math.pi * dx / (wave_len * 0.57)) + 1.1)
                + 0.10 * math.sin((2 * math.pi * dx / (wave_len * 1.9)) + 2.3)
            )
            plan_canvas.line(prev_x, prev_y, x, wave_y, stroke="black", stroke_w=1.6)
            prev_x = x
            prev_y = wave_y

    def _draw_hatch_cluster(x_start: float, y: float, count: int = 4, up: bool = True) -> None:
        """Draw a small cluster of diagonal hatch strokes near a trench line."""
        for i in range(count):
            x1 = x_start + i * 8.0
            y1 = y
            x2 = x1 + 7.0
            y2 = y1 - 7.0 if up else y1 + 7.0
            plan_canvas.line(x1, y1, x2, y2, stroke="black", stroke_w=2.0)

    # Trench/ground indication lines: top and bottom, left and right of block.
    trench_top_y = plan_top + plan_block_h * 0.22
    trench_bottom_y = plan_bottom - plan_block_h * 0.22
    trench_right_x2 = max(plan_right + 20.0, w_dim_x - 36.0)
    _draw_wavy_horizontal_line(plan_x1 + 8.0, plan_left, trench_top_y)
    _draw_wavy_horizontal_line(plan_x1 + 8.0, plan_left, trench_bottom_y)
    _draw_wavy_horizontal_line(plan_right, trench_right_x2, trench_top_y)
    _draw_wavy_horizontal_line(plan_right, trench_right_x2, trench_bottom_y)

    # Diagonal hatching similar to trench sketch notation.
    _draw_hatch_cluster(plan_x1 + 18.0, trench_top_y, count=4, up=True)
    _draw_hatch_cluster(plan_x1 + 14.0, trench_bottom_y, count=3, up=False)
    _draw_hatch_cluster(plan_right + 42.0, trench_top_y, count=3, up=True)
    _draw_hatch_cluster(plan_right + 38.0, trench_bottom_y, count=3, up=False)

    # Use true diameters in plan so sizing matches Section A-A scale.
    pipe_h_large = pipe_od_large_m * m_to_px
    pipe_h_small = pipe_od_small_m * m_to_px

    taper_len = 28.0
    bell_len = 9.0
    dn600_len = 100.0
    outlet_pipe_len = 100.0
    tail_pipe_len = 55.0
    flange_t = 4.0
    flange_gap = 0.0

    taper_inlet_x = plan_cx - (taper_len / 2)
    taper_inlet_port = plan_canvas.make_port(taper_inlet_x, plan_cy, 1, 0)
    taper_outlet_port = plan_canvas.place_fitting_local(
        taper_inlet_port,
        lambda: taper_local(
            plan_canvas,
            taper_len,
            pipe_h_large,
            pipe_h_small,
            wall=1.0,
        ),
    )[0]

    downstream_port = plan_canvas.place_fitting_local(
        taper_outlet_port,
        lambda: draw_plan_double_flange(
            plan_canvas,
            diameter_px=pipe_h_small,
            flange_t_px=flange_t,
            flange_gap_px=flange_gap,
            height_factor=1.35,
        ),
    )[1]
    downstream_port = plan_canvas.place_fitting_local(
        downstream_port,
        lambda: draw_plan_pipe_segment(plan_canvas, outlet_pipe_len, pipe_h_small),
    )[1]
    downstream_port = plan_canvas.place_fitting_local(
        downstream_port,
        lambda: draw_plan_bellmouth(plan_canvas, bell_len, pipe_h_small, opening_scale=1.6),
    )[1]
    downstream_end_port = plan_canvas.place_fitting_local(
        downstream_port,
        lambda: draw_plan_pipe_segment(plan_canvas, tail_pipe_len, pipe_h_small),
    )[1]

    upstream_start = plan_canvas.make_port(taper_inlet_x, plan_cy, -1, 0)
    upstream_port = plan_canvas.place_fitting_local(
        upstream_start,
        lambda: draw_plan_double_flange(
            plan_canvas,
            diameter_px=pipe_h_large,
            flange_t_px=flange_t,
            flange_gap_px=flange_gap,
            height_factor=1.25,
        ),
    )[1]
    upstream_port = plan_canvas.place_fitting_local(
        upstream_port,
        lambda: draw_plan_pipe_segment(plan_canvas, dn600_len, pipe_h_large),
    )[1]
    upstream_end_port = plan_canvas.place_fitting_local(
        upstream_port,
        lambda: draw_plan_bellmouth(plan_canvas, bell_len, pipe_h_large, opening_scale=1.6),
    )[1]

    socket_w = 12.0
    socket_gap = 2.0
    inlet_socket_x = plan_left - socket_gap - socket_w
    inlet_socket_port = plan_canvas.make_port(inlet_socket_x, plan_cy, 1, 0)
    plan_canvas.place_fitting_local(
        inlet_socket_port,
        lambda: draw_plan_single_socket(
            plan_canvas,
            diameter_px=pipe_h_large,
            socket_w_px=socket_w,
            height_factor=1.2,
        ),
    )

    outlet_socket_x = plan_right + socket_gap
    outlet_socket_port = plan_canvas.make_port(outlet_socket_x, plan_cy, 1, 0)
    plan_canvas.place_fitting_local(
        outlet_socket_port,
        lambda: draw_plan_single_socket(
            plan_canvas,
            diameter_px=pipe_h_small,
            socket_w_px=socket_w,
            height_factor=1.25,
        ),
    )

    plan_canvas.line(
        upstream_end_port["center"][0],
        plan_cy,
        downstream_end_port["center"][0],
        plan_cy,
        stroke="#999999",
        stroke_w=1,
        dasharray="6,6",
        stroke_opacity=0.6,
    )

    draw_horizontal_dim(plan_canvas, plan_left, plan_right, plan_bottom + 36.0, f'L = {length_m:.1f} m')
    draw_vertical_dim(
        plan_canvas,
        w_dim_x,
        plan_top,
        plan_bottom,
        f'W = {block_width_m:.1f}m',
        text_dx=-8.0,
        text_anchor="end",
    )

    # Keep Plan label near the bottom canvas edge while respecting margin.
    plan_label_y = canvas_h - 16.0
    plan_canvas.text(
        plan_cx,
        plan_label_y,
        "Plan",
        fill="black",
        font_size=13,
        font_family="Arial, sans-serif",
        text_anchor="middle",
    )

    # Single A-A section cut through the large side of the taper, just after the upstream flanges.
    section_cut_x = taper_inlet_x + 2.0
    section_top_y = plan_top - 20.0
    section_bottom_y = plan_bottom + 20.0
    plan_canvas.line(section_cut_x, section_top_y, section_cut_x, section_bottom_y, stroke="black", stroke_w=1.6)

    # Top and bottom right-pointing arrows with A labels.
    top_arrow_y = section_top_y
    bottom_arrow_y = section_bottom_y
    arrow_len = 52.0
    head_len = 10.0
    head_half_h = 5.0

    # Top arrow shaft + head
    top_shaft_end_x = section_cut_x + arrow_len - head_len
    plan_canvas.line(section_cut_x, top_arrow_y, top_shaft_end_x, top_arrow_y, stroke="black", stroke_w=1.4)
    plan_canvas.polygon(
        [
            (section_cut_x + arrow_len, top_arrow_y),
            (top_shaft_end_x, top_arrow_y - head_half_h),
            (top_shaft_end_x, top_arrow_y + head_half_h),
        ],
        fill="black",
        stroke="black",
        stroke_w=1,
    )
    plan_canvas.text(
        section_cut_x + arrow_len + 8.0,
        top_arrow_y,
        "A",
        fill="black",
        font_size=12,
        font_family="Arial, sans-serif",
        dominant_baseline="middle",
        text_anchor="start",
    )

    # Bottom arrow shaft + head
    bottom_shaft_end_x = section_cut_x + arrow_len - head_len
    plan_canvas.line(section_cut_x, bottom_arrow_y, bottom_shaft_end_x, bottom_arrow_y, stroke="black", stroke_w=1.4)
    plan_canvas.polygon(
        [
            (section_cut_x + arrow_len, bottom_arrow_y),
            (bottom_shaft_end_x, bottom_arrow_y - head_half_h),
            (bottom_shaft_end_x, bottom_arrow_y + head_half_h),
        ],
        fill="black",
        stroke="black",
        stroke_w=1,
    )
    plan_canvas.text(
        section_cut_x + arrow_len + 8.0,
        bottom_arrow_y,
        "A",
        fill="black",
        font_size=12,
        font_family="Arial, sans-serif",
        dominant_baseline="middle",
        text_anchor="start",
    )

    plan_canvas.save("./test_taper_plan.svg")

    # =========================
    # SECTION A-A DRAWING
    # =========================
    section_canvas = SVGCanvas(scale=1.0, width=canvas_w, height=canvas_h)

    section_x1 = 20.0
    section_x2 = 580.0
    section_y1 = 20.0
    section_y2 = 350.0
    section_cx = (section_x1 + section_x2) / 2
    section_cy = (section_y1 + section_y2) / 2

    sec_w = block_width_m * m_to_px
    sec_h = block_height_m * m_to_px
    sec_left = section_cx - (sec_w / 2)
    sec_right = sec_left + sec_w

    pipe_r = (pipe_od_large_m * m_to_px) / 2
    pipe_cx = section_cx
    pipe_cy = section_cy
    sec_top = pipe_cy - (sec_h / 2)
    sec_bottom = sec_top + sec_h

    section_canvas.rect(sec_left, sec_top, sec_w, sec_h, fill="#d9d9d9", stroke="black", stroke_w=2)

    crown_y = pipe_cy - pipe_r
    ground_y = crown_y - z0_m * m_to_px
    gw_y = ground_y + z_gw_m * m_to_px
    z_b_section_m = (sec_bottom - ground_y) / m_to_px

    section_canvas.line(section_x1, ground_y, section_x2, ground_y, stroke="black", stroke_w=2)
    section_canvas.line(section_x1, gw_y, section_x2, gw_y, stroke="#42a5f5", stroke_w=1, dasharray="8,6")

    gl_label_x = section_cx + 65.0
    gl_label_y = ground_y - 12.0
    tri_h = 9.0
    tri_w = 6.0
    tri_top_y = ground_y - tri_h
    section_canvas.text(
        gl_label_x,
        gl_label_y,
        "Ground level",
        fill="black",
        font_size=12,
        font_family="Arial, sans-serif",
        text_anchor="middle",
    )
    section_canvas.polygon(
        [(gl_label_x - tri_w, tri_top_y), (gl_label_x + tri_w, tri_top_y), (gl_label_x, ground_y)],
        fill="none",
        stroke="black",
        stroke_w=1.5,
    )

    section_canvas.circle(pipe_cx, pipe_cy, pipe_r, fill="white", stroke="black", stroke_w=2)

    pocket_pad = 18.0
    section_canvas.rect(
        pipe_cx - pipe_r - pocket_pad,
        pipe_cy - pipe_r - pocket_pad,
        2 * (pipe_r + pocket_pad),
        2 * (pipe_r + pocket_pad),
        fill="none",
        stroke="#777777",
        stroke_w=1.2,
        dasharray="5,4",
    )

    draw_vertical_dim(
        section_canvas,
        sec_left - 56.0,
        ground_y,
        gw_y,
        f'Z_GW = {z_gw_m:.1f}m',
        color="#42a5f5",
        text_dx=-8.0,
        text_anchor="end",
    )
    draw_vertical_dim(section_canvas, pipe_cx + 28.0, ground_y, crown_y, f'Z_0 = {z0_m:.1f}m')
    draw_vertical_dim(section_canvas, sec_right + 32.0, sec_top, sec_bottom, f'H = {block_height_m:.1f}m')
    draw_vertical_dim(section_canvas, sec_right + 98.0, ground_y, sec_bottom, f'Z_b = {z_b_section_m:.1f}m')

    section_canvas.line(
        sec_right,
        sec_bottom,
        sec_right + 120,
        sec_bottom,
        stroke="black",
        stroke_w=1.3,
        dasharray="8,6",
    )

    draw_horizontal_dim(section_canvas, sec_left, sec_right, sec_bottom + 16.0, f'W = {block_width_m:.1f}m')

    section_canvas.text(
        sec_left + sec_w / 2,
        sec_bottom + 64,
        "Section A-A",
        fill="black",
        font_size=13,
        font_family="Arial, sans-serif",
        text_anchor="middle",
    )

    section_canvas.save("./test_taper_section.svg")


def build_socket_pipe_svg(od: float, canvas_w: int, canvas_h: int) -> str:
    """Draw a simple socketed pipe elevation for the blank-end case."""
    canvas = SVGCanvas(scale=1.0, width=canvas_w, height=canvas_h)
    centre_y = canvas_h / 2
    pipe_len = 260.0
    socket_len = 55.0
    pipe_half = od / 2
    canvas.rect(120.0, centre_y - pipe_half, pipe_len, od, fill="white", stroke="black", stroke_w=2)
    canvas.rect(120.0 - socket_len, centre_y - pipe_half * 1.12, socket_len, od * 1.12, fill="#efefef", stroke="black", stroke_w=1.8)
    canvas.line(60.0, centre_y, 380.0, centre_y, stroke="#999999", stroke_w=1, dasharray="6,6", stroke_opacity=0.5)
    canvas.text(canvas_w / 2, centre_y + 42.0, "Blank End", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
    return _canvas_svg_string(canvas)


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
    canvas = SVGCanvas(scale=1.0, width=canvas_w, height=canvas_h)
    m_to_px = 46.0
    cx = canvas_w / 2
    cy = canvas_h / 2 - 10
    block_w = block_length * m_to_px
    block_h = block_width * m_to_px
    left = cx - block_w / 2
    top = cy - block_h / 2
    canvas.rect(left, top, block_w, block_h, fill="#d9d9d9", stroke="black", stroke_w=2)
    taper_len = 30.0
    pipe_large = od_large * m_to_px
    pipe_small = od_small * m_to_px
    taper_x = cx - taper_len / 2
    inlet_port = canvas.make_port(taper_x, cy, 1, 0)
    outlet_port = canvas.place_fitting_local(inlet_port, lambda: taper_local(canvas, taper_len, pipe_large, pipe_small, wall=1.0))[0]
    canvas.text(cx, canvas_h - 16, "Plan", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
    draw_horizontal_dim(canvas, left, left + block_w, top + block_h + 34.0, f'L = {block_length:.1f} m')
    draw_vertical_dim(canvas, left + block_w + 34.0, top, top + block_h, f'W = {block_width:.1f}m')
    return _canvas_svg_string(canvas)


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
    canvas = SVGCanvas(scale=1.0, width=canvas_w, height=canvas_h)
    m_to_px = 46.0
    cx = canvas_w / 2
    cy = canvas_h / 2
    sec_w = block_width * m_to_px
    sec_h = block_height * m_to_px
    left = cx - sec_w / 2
    top = cy - sec_h / 2
    right = left + sec_w
    bottom = top + sec_h
    pipe_r = od_large * m_to_px / 2
    crown_y = cy - pipe_r
    ground_y = crown_y - depth_crown * m_to_px
    gw_y = ground_y + gw_level * m_to_px
    canvas.rect(left, top, sec_w, sec_h, fill="#d9d9d9", stroke="black", stroke_w=2)
    canvas.line(20.0, ground_y, canvas_w - 20.0, ground_y, stroke="black", stroke_w=2)
    canvas.line(20.0, gw_y, canvas_w - 20.0, gw_y, stroke="#42a5f5", stroke_w=1, dasharray="8,6")
    canvas.circle(cx, cy, pipe_r, fill="white", stroke="black", stroke_w=2)
    draw_vertical_dim(canvas, left - 56.0, ground_y, gw_y, f'Z_GW = {gw_level:.1f}m', color="#42a5f5", text_dx=-8.0, text_anchor="end")
    draw_vertical_dim(canvas, cx + 28.0, ground_y, crown_y, f'Z_0 = {depth_crown:.1f}m')
    draw_vertical_dim(canvas, right + 32.0, top, bottom, f'H = {block_height:.1f}m')
    draw_vertical_dim(canvas, right + 98.0, ground_y, bottom, f'Z_b = {block_depth:.1f}m')
    draw_horizontal_dim(canvas, left, right, bottom + 16.0, f'W = {block_width:.1f}m')
    canvas.text(left + sec_w / 2, bottom + 64, "Section A-A", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
    return _canvas_svg_string(canvas)


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
    canvas = SVGCanvas(scale=1.0, width=canvas_w, height=canvas_h)
    m_to_px = 46.0
    cx = canvas_w / 2
    cy = canvas_h / 2 - 10.0
    bend_diameter = od * m_to_px
    bend_radius = max(bend_diameter * 1.35, 62.0)
    theta = math.radians(angle)
    mid_theta = theta / 2.0
    rotation_deg = start_angle + math.degrees(mid_theta) - 90.0
    rotation_rad = math.radians(rotation_deg)
    cos_r = math.cos(rotation_rad)
    sin_r = math.sin(rotation_rad)

    def _rotate_local_point(x: float, y: float) -> tuple[float, float]:
        return (
            bend_cx + x * cos_r - y * sin_r,
            bend_cy + x * sin_r + y * cos_r,
        )

    def _rotate_local_vector(x: float, y: float) -> tuple[float, float]:
        return (
            x * cos_r - y * sin_r,
            x * sin_r + y * cos_r,
        )

    # Place the bend so the rotated arc midpoint sits at the canvas centre.
    mid_x_local = bend_radius * math.sin(mid_theta)
    mid_y_local = -bend_radius * (1.0 - math.cos(mid_theta))
    mid_x_rot, mid_y_rot = _rotate_local_vector(mid_x_local, mid_y_local)
    bend_cx = cx - mid_x_rot
    bend_cy = cy - mid_y_rot

    inlet_port = canvas.make_port(bend_cx, bend_cy, math.cos(rotation_rad), math.sin(rotation_rad))
    bend_ports = canvas.place_fitting_local(
        inlet_port,
        lambda: bend_local(
            canvas,
            radius_px=bend_radius,
            diameter_px=bend_diameter,
            angle_deg=angle,
        ),
    )

    upstream_socket_length_px = 1.5 * m_to_px
    upstream_socket_port = canvas.place_fitting_local(
        inlet_port,
        lambda: socket_pipe_local(
            canvas,
            length=upstream_socket_length_px,
            diameter=bend_diameter,
            socket_length=upstream_socket_length_px * 0.15,
            socket_od=bend_diameter * 1.12,
            is_inlet=True,
        ),
    )[0]

    downstream_socket_length_px = 1.5 * m_to_px
    downstream_socket_ports = canvas.place_fitting_local(
        bend_ports[1],
        lambda: socket_pipe_local(
            canvas,
            length=downstream_socket_length_px,
            diameter=bend_diameter,
            socket_length=downstream_socket_length_px * 0.15,
            socket_od=bend_diameter * 1.12,
            is_inlet=False,
            draw_barrel=False,
        ),
    )
    downstream_pipe_length_px = 1.5 * m_to_px
    canvas.pipe_from_port(
        downstream_socket_ports[1],
        length=downstream_pipe_length_px,
        diameter=bend_diameter,
    )

    # Thrust line is drawn through the midpoint of the bend arc and is normal to the centreline there.
    normal_x_local = math.sin(mid_theta)
    normal_y_local = math.cos(mid_theta)

    contact_x, contact_y = _rotate_local_point(mid_x_local, mid_y_local)

    thrust_ux, thrust_uy = _rotate_local_vector(normal_x_local, normal_y_local)
    thrust_len = math.hypot(thrust_ux, thrust_uy)
    if thrust_len == 0:
        thrust_ux, thrust_uy = 1.0, 0.0
    else:
        thrust_ux /= thrust_len
        thrust_uy /= thrust_len

    arrow_len = 92.0
    head_len = 14.0
    wall_x = contact_x + thrust_ux * (bend_diameter / 2)
    wall_y = contact_y + thrust_uy * (bend_diameter / 2)
    block_length_px = block_length * m_to_px
    block_width_px = block_width * m_to_px
    block_cx = wall_x + thrust_ux * (block_length_px / 2)
    block_cy = wall_y + thrust_uy * (block_length_px / 2)
    block_vx = -thrust_uy
    block_vy = thrust_ux
    block_points = [
        (
            block_cx - block_vx * (block_width_px / 2) - thrust_ux * (block_length_px / 2),
            block_cy - block_vy * (block_width_px / 2) - thrust_uy * (block_length_px / 2),
        ),
        (
            block_cx + block_vx * (block_width_px / 2) - thrust_ux * (block_length_px / 2),
            block_cy + block_vy * (block_width_px / 2) - thrust_uy * (block_length_px / 2),
        ),
        (
            block_cx + block_vx * (block_width_px / 2) + thrust_ux * (block_length_px / 2),
            block_cy + block_vy * (block_width_px / 2) + thrust_uy * (block_length_px / 2),
        ),
        (
            block_cx - block_vx * (block_width_px / 2) + thrust_ux * (block_length_px / 2),
            block_cy - block_vy * (block_width_px / 2) + thrust_uy * (block_length_px / 2),
        ),
    ]

    canvas.polygon(
        block_points,
        fill="#d9d9d9",
        stroke="black",
        stroke_w=2,
    )

    head_base_x = wall_x - thrust_ux * head_len
    head_base_y = wall_y - thrust_uy * head_len
    shaft_start_x = wall_x - thrust_ux * arrow_len
    shaft_start_y = wall_y - thrust_uy * arrow_len

    canvas.line(shaft_start_x, shaft_start_y, head_base_x, head_base_y, stroke="#d32f2f", stroke_w=2.3)
    canvas.polygon(
        [
            (wall_x, wall_y),
            (head_base_x - thrust_uy * 7.0, head_base_y + thrust_ux * 7.0),
            (head_base_x + thrust_uy * 7.0, head_base_y - thrust_ux * 7.0),
        ],
        fill="#d32f2f",
        stroke="#d32f2f",
        stroke_w=1,
    )
    shaft_mid_x = (shaft_start_x + head_base_x) / 2
    shaft_mid_y = (shaft_start_y + head_base_y) / 2
    label_padding = 16.0
    canvas.text(
        shaft_start_x - label_padding,
        shaft_mid_y,
        "T",
        fill="#d32f2f",
        font_size=18,
        font_family="Arial, sans-serif",
        text_anchor="middle",
        dominant_baseline="middle",
    )

    canvas.text(cx, canvas_h - 16.0, "Plan", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
    return _canvas_svg_string(canvas)


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
    """Draw the horizontal bend section as a standalone SVG string."""
    canvas = SVGCanvas(scale=1.0, width=canvas_w, height=canvas_h)
    m_to_px = 46.0
    cx = canvas_w / 2
    cy = canvas_h / 2
    sec_w = block_width * m_to_px
    sec_h = block_height * m_to_px
    left = cx - sec_w / 2
    top = cy - sec_h / 2
    right = left + sec_w
    bottom = top + sec_h
    pipe_r = od * m_to_px / 2
    crown_y = cy - pipe_r
    ground_y = crown_y - depth_crown * m_to_px
    gw_y = ground_y + gw_level * m_to_px
    canvas.rect(left, top, sec_w, sec_h, fill="#d9d9d9", stroke="black", stroke_w=2)
    canvas.line(20.0, ground_y, canvas_w - 20.0, ground_y, stroke="black", stroke_w=2)
    canvas.line(20.0, gw_y, canvas_w - 20.0, gw_y, stroke="#42a5f5", stroke_w=1, dasharray="8,6")
    canvas.circle(cx, cy, pipe_r, fill="white", stroke="black", stroke_w=2)
    draw_vertical_dim(canvas, left - 56.0, ground_y, gw_y, f'Z_GW = {gw_level:.1f}m', color="#42a5f5", text_dx=-8.0, text_anchor="end")
    draw_vertical_dim(canvas, cx + 28.0, ground_y, crown_y, f'Z_0 = {depth_crown:.1f}m')
    draw_vertical_dim(canvas, right + 32.0, top, bottom, f'H = {block_height:.1f}m')
    draw_vertical_dim(canvas, right + 98.0, ground_y, bottom, f'Z_b = {(bottom - ground_y) / m_to_px:.1f}m')
    draw_horizontal_dim(canvas, left, right, bottom + 16.0, f'W = {block_width:.1f}m')
    canvas.text(left + sec_w / 2, bottom + 64, "Section A-A", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
    return _canvas_svg_string(canvas)


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
    canvas = SVGCanvas(scale=1.0, width=canvas_w, height=canvas_h)
    m_to_px = 46.0
    cx = canvas_w / 2
    cy = canvas_h / 2
    sec_w = block_width * m_to_px
    sec_h = block_height * m_to_px
    left = cx - sec_w / 2
    top = cy - sec_h / 2
    right = left + sec_w
    bottom = top + sec_h
    pipe_r = od * m_to_px / 2
    crown_y = cy - pipe_r
    ground_y = crown_y - depth_crown * m_to_px
    gw_y = ground_y + gw_level * m_to_px
    canvas.rect(left, top, sec_w, sec_h, fill="#d9d9d9", stroke="black", stroke_w=2)
    canvas.line(20.0, ground_y, canvas_w - 20.0, ground_y, stroke="black", stroke_w=2)
    canvas.line(20.0, gw_y, canvas_w - 20.0, gw_y, stroke="#42a5f5", stroke_w=1, dasharray="8,6")
    canvas.circle(cx, cy, pipe_r, fill="white", stroke="black", stroke_w=2)
    draw_vertical_dim(canvas, left - 56.0, ground_y, gw_y, f'Z_GW = {gw_level:.1f}m', color="#42a5f5", text_dx=-8.0, text_anchor="end")
    draw_vertical_dim(canvas, cx + 28.0, ground_y, crown_y, f'Z_0 = {depth_crown:.1f}m')
    draw_vertical_dim(canvas, right + 32.0, top, bottom, f'H = {block_height:.1f}m')
    draw_vertical_dim(canvas, right + 98.0, ground_y, bottom, f'Z_b = {(bottom - ground_y) / m_to_px:.1f}m')
    draw_horizontal_dim(canvas, left, right, bottom + 16.0, f'W = {block_width:.1f}m')
    canvas.text(left + sec_w / 2, bottom + 64, "Section A-A", fill="black", font_size=13, font_family="Arial, sans-serif", text_anchor="middle")
    return _canvas_svg_string(canvas)


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
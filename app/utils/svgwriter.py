from typing import TypedDict, Tuple, NewType, List, Callable
import math

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

    def __init__(self, scale=1.0, width=5000, height=5000, pipe_stroke="black"):
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

        self._lines = []  # stores SVG elements

        # Default styles
        self.pipe_fill = "white"
        self.pipe_stroke = pipe_stroke
        self.sw = 3 * scale
        self.dsw = 1.5 * scale


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
        L = math.hypot(vx, vy)
        if L == 0:
            raise ValueError("Zero-length vector")
        return (vx / L, vy / L)


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

        import math

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

    def rect(self, x, y, w, h, fill=None, stroke=None, stroke_w=None):
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

        self._lines.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"/>'
        )


    def circle(self, cx, cy, r, fill=None, stroke=None, stroke_w=None):
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


    def draw_ground_level(self, x1, y1, x2, y2, spacing=20):
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

            L = spacing * 0.4
            x_end = px + dx_tick * L
            y_end = py + dy_tick * L

            self._lines.append(
                f'<line x1="{px:.2f}" y1="{py:.2f}" x2="{x_end:.2f}" y2="{y_end:.2f}" '
                f'stroke="#000" stroke-width="{self.dsw:.2f}"/>'
            )


    def draw_trench(self, x1, y1, x2, y2):
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

    def save(self, filename="output.svg"):
        """
        Write SVG file.
        """
        with open(filename, "w") as f:
            f.write(
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}">\n'
            )
            f.write("\n".join(self._lines))
            f.write("\n</svg>")

def socket_pipe_local(
    canvas: SVGCanvas,
    length: float,
    diameter: float,
    socket_length: float,
    socket_od: float,
    is_inlet: bool = True,
) -> list[Port]:
    """
    Socketed pipe section in local coordinates.

    Returns
    -------
    list[Port]
        [inlet_port, outlet_port]
    """

    # Main barrel
    canvas._lines.append(
        f'<rect x="0" y="{-diameter/2:.2f}" '
        f'width="{length:.2f}" height="{diameter:.2f}" '
        f'fill="{canvas.pipe_fill}" '
        f'stroke="{canvas.pipe_stroke}" '
        f'fh="2"/>'
    )

    if is_inlet:
        # Bellmouth on left-hand end
        points = (
            f'0,{-socket_od/2:.2f} '
            f'{socket_length:.2f},{-diameter/2:.2f} '
            f'{socket_length:.2f},{diameter/2:.2f} '
            f'0,{socket_od/2:.2f}'
        )
    else:
        # Bellmouth on right-hand end
        points = (
            f'{length - socket_length:.2f},{-diameter/2:.2f} '
            f'{length:.2f},{-socket_od/2:.2f} '
            f'{length:.2f},{socket_od/2:.2f} '
            f'{length - socket_length:.2f},{diameter/2:.2f}'
        )

    # Bellmouth
    canvas._lines.append(
        f'<polygon points="{points}" '
        f'fill="{canvas.pipe_fill}" '
        f'stroke="{canvas.pipe_stroke}" '
        f'stroke-width="2"/>'
    )

    # Centreline
    canvas._lines.append(
        f'<line x1="0" y1="0" '
        f'x2="{length:.2f}" y2="0" '
        f'stroke="#999999" '
        f'stroke-width="1" '
        f'stroke-dasharray="6,6" '
        f'stroke-opacity="0.5"/>'
    )

    return [
        canvas.make_port(0, 0, -1, 0),
        canvas.make_port(length, 0, 1, 0),
    ]

def bend_local(
    canvas,
    radius_px: float,
    diameter_px: float,
    angle_deg: float,
) -> list[Port]:
    """
    Bend in LOCAL coordinates.

    Inlet:
        (0,0) tangent +X

        Computed from angle_deg.
    """

    theta = math.radians(angle_deg)

    # Bend centre (local coordinates)
    cx = 0
    cy = radius_px

    # Midpoint of bend arc
    mid_theta = theta / 2

    thrust_x = radius_px * math.sin(mid_theta)
    thrust_y = radius_px * (1 - math.cos(mid_theta))

    # Resultant thrust direction
    thrust_angle = mid_theta

    end_x = radius_px * math.sin(theta)
    end_y = radius_px * (1 - math.cos(theta))

    path = (
        f"M 0 0 "
        f"A {radius_px:.2f} {radius_px:.2f} "
        f"0 0 1 "
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
            math.sin(theta),
        ),
    ]

def taper_local(canvas, L, OD1, OD2, wall=2.0):
    """
    Draw a taper (reducer) using OD only.
    
    Parameters
    ----------
    canvas : SVGCanvas
    L : float
        Length of taper (px)
    OD1 : float
        Upstream outside diameter (px)
    OD2 : float
        Downstream outside diameter (px)
    wall : float
        Constant wall thickness (px)
    
    Returns
    -------
    list[Port]
    """

    # --- derive inner diameters ---
    ID1 = OD1 - 2 * wall
    ID2 = OD2 - 2 * wall

    if ID1 <= 0 or ID2 <= 0:
        raise ValueError("Wall thickness too large for given diameters")

    # --- outer half heights ---
    y1o = OD1 / 2
    y2o = OD2 / 2

    # --- inner half heights ---
    y1i = ID1 / 2
    y2i = ID2 / 2

    # =========================
    # 1. OUTER SHAPE
    # =========================
    canvas._lines.append(
        f'<polygon points="'
        f'0,{y1o:.2f} '
        f'{L:.2f},{y2o:.2f} '
        f'{L:.2f},{-y2o:.2f} '
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
        f'{L:.2f},{y2i:.2f} '
        f'{L:.2f},{-y2i:.2f} '
        f'0,{-y1i:.2f}" '
        f'fill="white" '
        f'stroke="none"/>'
    )

    # =========================
    # 3. CENTRELINE
    # =========================
    canvas._lines.append(
        f'<line x1="0" y1="0" x2="{L:.2f}" y2="0" '
        f'stroke="#999999" '
        f'stroke-width="1" '
        f'stroke-dasharray="6,6" '
        f'stroke-opacity="0.5"/>'
    )

    # =========================
    # OUTPUT PORT
    # =========================
    return [canvas.make_port(L, 0, 1, 0)]

import math


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

    canvas._lines.append(
        f'<polygon points="{points}" '
        f'fill="#d9d9d9" '
        f'stroke="black" '
        f'stroke-width="2"/>'
    )
    

def create_canvas(
    total_len: float,
    max_height: float,
    canvas_w: int,
    canvas_h: int,
    margin_x: int = 110,
    margin_y: int = 90,
) -> dict:
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
    draw_w = canvas_w - 2 * margin_x   # Available horizontal space for the pipe geometry
    draw_h = canvas_h - 2 * margin_y   # Available vertical space for the pipe geometry

    # Scale factor: converts mm → SVG pixels.
    # min() picks the tighter constraint so the drawing never overflows in either direction.
    scale = min(draw_w / total_len, draw_h / (max_height * 1.1))

    cx = canvas_w / 2        # Horizontal centre of the canvas in pixels
    cy = canvas_h / 2 - 20  # Vertical centre, shifted up 20px to leave room for the dim line

    return {
        "scale":    scale,
        "cx":       cx,
        "cy":       cy,
        "canvas_w": canvas_w,
        "canvas_h": canvas_h,
    }

def vertical_downturn_bend_section():

    # =========================
    # CREATE CANVAS
    # =========================
    ctx = create_canvas(4000, 3000, 600, 400)

    canvas = SVGCanvas(
        ctx["scale"],
        ctx["canvas_w"],
        ctx["canvas_h"]
    )

    cx = ctx["cx"]
    cy = ctx["cy"]

    # =========================
    # BEND (CENTRE FEATURE)
    # =========================
    bend_diameter = canvas.mm_to_px(600)
    bend_radius = canvas.mm_to_px(1.5 * 600)

    bend_ports = canvas.place_fitting_local(
        canvas.make_port(cx, cy, 1, 0),
        lambda: bend_local(
            canvas,
            radius_px=bend_radius,
            diameter_px=bend_diameter,
            angle_deg=45
        )
    )

    bend_inlet = bend_ports[0]
    bend_outlet = bend_ports[1]

    # =========================
    # SOCKET ON INLET SIDE
    # =========================
    socket_od = canvas.mm_to_px(1.15*600)

    socket_ports = canvas.place_fitting_local(
        bend_inlet,
        lambda: socket_pipe_local(
            canvas,
            length=canvas.mm_to_px(150),
            diameter=bend_diameter,
            socket_length=canvas.mm_to_px(150),
            socket_od=socket_od,
        )
    )

    socket_inlet = socket_ports[0]

    # =========================
    # INLET PIPE
    # =========================
    inlet_pipe_port = canvas.make_port(
        socket_inlet["center"][0],
        socket_inlet["center"][-1],
        socket_inlet["tangent"][0],
        socket_inlet["tangent"][-1],
    )

    canvas.pipe_from_port( 
        inlet_pipe_port,
        Px(canvas.mm_to_px(1000)),
        Px(bend_diameter),
    )

    # =========================
    # Outlet Socket
    # =========================

    socket_length = canvas.mm_to_px(100)
    socket_od = canvas.mm_to_px(1.15*600)

    socket_ports = canvas.place_fitting_local(
        bend_outlet,
        lambda: socket_pipe_local(
            canvas,
            length=socket_length,
            diameter=bend_diameter,
            socket_length=canvas.mm_to_px(150),
            socket_od=socket_od,
            is_inlet=False
        )
    )

    socket_outlet = socket_ports[1]

    # =========================
    # OUTLET PIPE
    # =========================
    outlet_pipe_port = canvas.make_port(
        socket_outlet["center"][0],
        socket_outlet["center"][1],
        socket_outlet["tangent"][0],
        socket_outlet["tangent"][1],
    )

    canvas.pipe_from_port( 
        socket_outlet,
        Px(canvas.mm_to_px(1000)),
        Px(bend_diameter),
    )

    # =========================
    # SAVE SVG
    # =========================
    canvas.save("./test_pipe.svg")


if __name__ == "__main__":
    vertical_downturn_bend_section()
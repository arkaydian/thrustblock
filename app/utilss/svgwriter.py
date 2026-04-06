class SVGCanvas:
    """Reusable SVG drawing context shared by all fitting builder functions.

    Encapsulates the SVG element accumulator list, the mm→pixel scale factor,
    and all primitive drawing helpers (rect, poly, line, text, dim_arrow,
    vert_dim_arrow).  Each builder function creates one instance, calls the
    drawing methods to build up the scene, then calls ``render()`` to get the
    final SVG string.

    Args:
        scale:      mm → SVG-pixel conversion factor (from ``create_canvas``).
        canvas_w:   SVG canvas width in pixels.
        canvas_h:   SVG canvas height in pixels.
        pipe_fill:  Fill colour for pipe/flange bodies (default light blue-grey).
        pipe_stroke: Outline colour for pipe/flange bodies (default dark navy).
        dim_color:  Colour used for all dimension lines and labels (default dark grey).
    """

    def __init__(
        self,
        scale: float,
        canvas_w: int,
        canvas_h: int,
        pipe_fill:   str = "#d0d8e0",
        pipe_stroke: str = "#1a1a2e",
        dim_color:   str = "#333333",
    ) -> None:
        self.scale       = scale        # mm → pixel conversion factor
        self.canvas_w    = canvas_w     # SVG canvas width in pixels
        self.canvas_h    = canvas_h     # SVG canvas height in pixels
        self.pipe_fill   = pipe_fill    # Fill colour for pipe bodies
        self.pipe_stroke = pipe_stroke  # Outline colour for pipe bodies
        self.dim_color   = dim_color    # Colour for dimension lines and labels

        # Stroke widths derived from scale so they look consistent at any canvas size
        self.sw  = max(1.2, scale * 0.8)  # Pipe outline stroke-width — scales with zoom, min 1.2px
        self.dsw = 0.8                    # Dimension line stroke-width (always thin)

        self._lines: list[str] = []   # Accumulator — all SVG element strings are appended here

    # ── Unit conversion ───────────────────────────────────────────────────────

    def s(self, v: float) -> float:
        """Convert a mm value to SVG pixels using the stored scale factor."""
        return v * self.scale

    # ── SVG primitive helpers ─────────────────────────────────────────────────

    def rect(
        self,
        x: float, y: float, w: float, h: float,
        fill: str, stroke: str, stroke_w: float,
        rx: float = 0,
    ) -> None:
        """Append a filled rectangle element.

        Args:
            x, y:     Top-left corner in SVG pixels.
            w, h:     Width and height in SVG pixels.
            fill:     CSS fill colour string.
            stroke:   CSS stroke colour string.
            stroke_w: Stroke width in pixels.
            rx:       Corner radius (0 = sharp corners).
        """
        self._lines.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}" rx="{rx}"/>'
        )

    def poly(
        self,
        points_list: list[tuple[float, float]],
        fill: str, stroke: str, stroke_w: float,
    ) -> None:
        """Append a closed polygon element.

        Args:
            points_list: List of (x, y) tuples in SVG pixels.
            fill:        CSS fill colour string.
            stroke:      CSS stroke colour string.
            stroke_w:    Stroke width in pixels.
        """
        pts = " ".join(f"{px:.2f},{py:.2f}" for px, py in points_list)
        self._lines.append(
            f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"/>'
        )

    def line(
        self,
        x1: float, y1: float, x2: float, y2: float,
        color: str, stroke_w: float,
        dash: str = "",
    ) -> None:
        """Append a straight line element.

        Args:
            x1, y1: Start point in SVG pixels.
            x2, y2: End point in SVG pixels.
            color:    CSS stroke colour string.
            stroke_w: Stroke width in pixels.
            dash:     SVG stroke-dasharray value, e.g. ``"6,4"`` (empty = solid).
        """
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self._lines.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="{stroke_w:.2f}"{dash_attr}/>'
        )

    def text(
        self,
        x: float, y: float, content: str,
        font_size: int = 11,
        anchor: str = "middle",
        color: str = "#333333",
        bold: bool = False,
    ) -> None:
        """Append a text label element.

        Args:
            x, y:      Anchor point in SVG pixels.
            content:   Text string to display.
            font_size: Font size in points.
            anchor:    SVG text-anchor (``"middle"``, ``"start"``, or ``"end"``).
            color:     CSS fill colour string.
            bold:      If True, renders with ``font-weight: bold``.
        """
        fw = "bold" if bold else "normal"
        self._lines.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="{font_size}" '
            f'font-family="Arial,sans-serif" text-anchor="{anchor}" '
            f'fill="{color}" font-weight="{fw}">{content}</text>'
        )

    def dim_arrow(
        self,
        x1: float, y: float, x2: float,
        label: str,
        font_size: int = 10,
    ) -> None:
        """Draw a horizontal dimension line with arrowheads and a centred label.

        The line is placed 12px above the supplied ``y`` reference coordinate.
        Tick marks are drawn at each end, filled triangular arrowheads point
        inward, and the label is centred above the line.

        Args:
            x1:        Left endpoint x in SVG pixels.
            y:         Reference y coordinate (line is drawn 12px above this).
            x2:        Right endpoint x in SVG pixels.
            label:     Dimension label string (e.g. ``"L = 1200 mm"``).
            font_size: Font size for the label.
        """
        dc  = self.dim_color
        dsw = self.dsw
        ty  = y - 12   # Shift the dim line 12px above the reference y

        self.line(x1, ty, x2, ty, dc, dsw)                  # Horizontal dimension line
        self.line(x1, ty - 4, x1, ty + 4, dc, dsw)          # Left tick mark
        self.line(x2, ty - 4, x2, ty + 4, dc, dsw)          # Right tick mark

        # Left arrowhead — filled triangle pointing right (toward x1)
        self._lines.append(
            f'<polygon points="{x1:.2f},{ty:.2f} {x1+6:.2f},{ty-3:.2f} {x1+6:.2f},{ty+3:.2f}" '
            f'fill="{dc}"/>'
        )
        # Right arrowhead — filled triangle pointing left (toward x2)
        self._lines.append(
            f'<polygon points="{x2:.2f},{ty:.2f} {x2-6:.2f},{ty-3:.2f} {x2-6:.2f},{ty+3:.2f}" '
            f'fill="{dc}"/>'
        )
        self.text((x1 + x2) / 2, ty - 4, label, font_size=font_size, color=dc)

    def vert_dim_arrow(
        self,
        x: float, y1: float, y2: float,
        label: str,
        right: bool = True,
        font_size: int = 10,
    ) -> None:
        """Draw a vertical dimension line with arrowheads and a rotated label.

        The line is offset 14px to the right (or left) of the supplied ``x``
        reference coordinate.  Tick marks are drawn at each end, filled
        triangular arrowheads point inward, and the label is rotated −90°
        beside the line.

        Args:
            x:         Reference x coordinate in SVG pixels.
            y1:        Top endpoint y in SVG pixels.
            y2:        Bottom endpoint y in SVG pixels.
            label:     Dimension label string (e.g. ``"OD = 300 mm"``).
            right:     If True, place the line to the right of x; else to the left.
            font_size: Font size for the label.
        """
        dc     = self.dim_color
        dsw    = self.dsw
        offset = 14 if right else -14   # Positive = right of x; negative = left
        tx     = x + offset             # Actual x position of the vertical dimension line

        self.line(tx, y1, tx, y2, dc, dsw)                  # Vertical dimension line
        self.line(tx - 4, y1, tx + 4, y1, dc, dsw)          # Top tick mark
        self.line(tx - 4, y2, tx + 4, y2, dc, dsw)          # Bottom tick mark

        # Top arrowhead — filled triangle pointing downward (toward y1)
        self._lines.append(
            f'<polygon points="{tx:.2f},{y1:.2f} {tx-3:.2f},{y1+6:.2f} {tx+3:.2f},{y1+6:.2f}" '
            f'fill="{dc}"/>'
        )
        # Bottom arrowhead — filled triangle pointing upward (toward y2)
        self._lines.append(
            f'<polygon points="{tx:.2f},{y2:.2f} {tx-3:.2f},{y2-6:.2f} {tx+3:.2f},{y2-6:.2f}" '
            f'fill="{dc}"/>'
        )

        # Rotated label: SVG transform rotates it −90° around its own anchor point
        mid_y = (y1 + y2) / 2
        self._lines.append(
            f'<text x="{tx + 12:.2f}" y="{mid_y:.2f}" font-size="{font_size}" '
            f'font-family="Arial,sans-serif" text-anchor="middle" fill="{dc}" '
            f'transform="rotate(-90,{tx + 12:.2f},{mid_y:.2f})">{label}</text>'
        )

    # ── Output ────────────────────────────────────────────────────────────────

    def render(self, background: str = "#f8f9fa", border: str = "#ccc") -> str:
        """Serialise all accumulated elements into a complete SVG string.

        Args:
            background: CSS background colour for the SVG canvas.
            border:     CSS border colour for the SVG canvas.

        Returns:
            A complete ``<svg>…</svg>`` string ready for embedding in HTML.
        """
        svg_body = "\n  ".join(self._lines)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.canvas_w}" height="{self.canvas_h}" '
            f'viewBox="0 0 {self.canvas_w} {self.canvas_h}" '
            f'style="background:{background};border:1px solid {border};">\n  '
            f'{svg_body}\n</svg>'
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

def build_socket_pipe_svg(od: float, canvas_w: int = 1100, canvas_h: int = 420) -> str:
    """Generate an SVG plan view of a plain socket (bell-end) pipe.

    The socket pipe consists of:
      - A straight pipe barrel with wall thickness derived from OD
      - A plain square-cut end at the left (spigot-receive) side
      - A bell/socket expansion at the right end that receives the next spigot
      - A dashed centreline through the pipe axis
      - Dimension annotations (OD, bell OD, and overall length L)

    Args:
        od:       Outside diameter of the socket pipe in mm.
        canvas_w: SVG canvas width in pixels (from user input).
        canvas_h: SVG canvas height in pixels (from user input).
    """

    # ── Derived geometry ──────────────────────────────────────────────────────
    wall      = od * 0.08                    # Wall thickness = 8% of OD
    id_       = od - 2 * wall                # Inner diameter = OD minus both walls
    length    = od * 4.0                     # Pipe length = 4× OD for a visually balanced drawing
    bell_od   = od * 1.20                    # Bell outer diameter — 20% wider than the pipe OD
    bell_len  = od * 0.35                    # Axial length of the bell expansion zone
    bell_wall = od * 0.10                    # Bell wall thickness — slightly thicker than barrel wall
    bell_id   = bell_od - 2 * bell_wall      # Bell inner diameter (bore widens to accept the spigot)

    # ── SVG canvas & scale ────────────────────────────────────────────────────
    ctx = create_canvas(length, bell_od * 1.2, canvas_w, canvas_h)
    c   = SVGCanvas(ctx["scale"], canvas_w, canvas_h)
    cx  = ctx["cx"]
    cy  = ctx["cy"]

    # ── X positions ───────────────────────────────────────────────────────────
    x_left       = cx - c.s(length) / 2              # Left edge (plain square-cut end)
    x_bell_start = x_left + c.s(length - bell_len)   # Where the barrel ends and the bell begins
    x_right      = cx + c.s(length) / 2              # Right edge (bell end face)

    # ── Half-heights ─────────────────────────────────────────────────────────
    h_od      = c.s(od)      / 2   # Half the pipe OD
    h_id      = c.s(id_)     / 2   # Half the pipe ID
    h_bell_od = c.s(bell_od) / 2   # Half the bell OD
    h_bell_id = c.s(bell_id) / 2   # Half the bell ID (bore widens inside the bell)

    pf = c.pipe_fill
    ps = c.pipe_stroke
    sw = c.sw

    # ── Draw components ───────────────────────────────────────────────────────

    # 1. PIPE BARREL — outer rectangle spanning the full length at the pipe OD
    c.rect(x_left, cy - h_od, c.s(length), c.s(od), pf, ps, sw)

    # 2. BELL OUTER SHAPE — 4-point polygon widening from pipe OD to bell OD
    c.poly(
        [(x_bell_start, cy - h_od),     (x_right, cy - h_bell_od),
         (x_right,      cy + h_bell_od),(x_bell_start, cy + h_od)],
        pf, ps, sw,
    )

    # 3. BARREL INNER BORE — white rectangle for the straight section hollow interior
    c.rect(x_left, cy - h_id, c.s(length - bell_len), c.s(id_), "white", ps, sw * 0.6)

    # 4. BELL INNER BORE — 4-point polygon; bore widens to accept an incoming spigot
    c.poly(
        [(x_bell_start, cy - h_id),     (x_right, cy - h_bell_id),
         (x_right,      cy + h_bell_id),(x_bell_start, cy + h_id)],
        "white", ps, sw * 0.6,
    )

    # 5. BELL END FACE — vertical line closing off the right end of the socket
    c.line(x_right, cy - h_bell_od, x_right, cy + h_bell_od, ps, sw)

    # 6. RUBBER SEAL GROOVE — narrow dark band inside the bell near the end face
    groove_x   = x_right - c.s(bell_len * 0.30)   # 30% of bell length from the end face
    groove_w   = c.s(od * 0.04)                    # Groove width = 4% of OD (narrow slot)
    c.rect(groove_x, cy - h_bell_id, groove_w, h_bell_id * 2, "#8899aa", ps, sw * 0.4)

    # 7. CENTRELINE (dashed)
    c.line(x_left - 10, cy, x_right + 10, cy, "#888888", 0.8, dash="6,4")

    # ── Dimension annotations ─────────────────────────────────────────────────
    dim_y_top = cy - h_bell_od - 30
    c.dim_arrow(x_left, dim_y_top, x_right, f"L = {length:.0f} mm")
    c.vert_dim_arrow(x_left - 10,  cy - h_od,      cy + h_od,      f"OD = {od:.0f} mm",          right=False, font_size=9)
    c.vert_dim_arrow(x_right + 10, cy - h_bell_od, cy + h_bell_od, f"Bell OD = {bell_od:.0f} mm", right=True,  font_size=9)

    # ── Title block ───────────────────────────────────────────────────────────
    c.text(canvas_w / 2, canvas_h - 12, "Socket Pipe – Plan View", font_size=12, color="#1a1a2e", bold=True)

    return c.render()
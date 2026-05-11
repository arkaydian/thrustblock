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

    def draw_ground_level(
        self,
        x_left: float,
        x_right: float,
        y: float,
        label: str = "Ground Level",
    ) -> None:
        """Draw a standard engineering ground level symbol: a horizontal line with a
        downward-pointing filled triangle sitting on top of it, and an optional label.

        The symbol follows the conventional notation used in civil/structural engineering
        drawings where a solid triangle rests on a horizontal baseline to denote the
        ground surface level.

        Args:
            x_left:  Left x coordinate of the horizontal ground line in SVG pixels.
            x_right: Right x coordinate of the horizontal ground line in SVG pixels.
            y:       Y coordinate of the ground line (top of the triangle base) in SVG pixels.
            label:   Short text label placed to the right of the symbol (default ``"GL"``).
        """
        color = "#333333"   # Dark grey — matches engineering drawing convention
        sw    = 1.4         # Stroke width for the ground line

        # ── Horizontal ground line ────────────────────────────────────────────
        # A solid straight line spanning the full trench width at the ground level y
        self.line(x_left, y, x_right, y, color, sw)

        # ── Downward-pointing triangle ────────────────────────────────────────
        # The triangle sits entirely ABOVE the line — apex touches the line, base is above
        tri_w = 10   # Half-width of the triangle base in pixels
        tri_h = 10   # Height of the triangle (how far the base sits above the line)

        # Position the triangle at 3/4 of the way along the line from left to right
        mid_x = x_left + (x_right - x_left) * 0.75

        # Triangle vertices — downward-pointing, sitting entirely ABOVE the line:
        #   top-left  : (mid_x - tri_w, y - tri_h)  — left corner of the base, tri_h above the line
        #   top-right : (mid_x + tri_w, y - tri_h)  — right corner of the base, tri_h above the line
        #   apex      : (mid_x,         y)           — downward tip touching the line exactly
        self.poly(
            [
                (mid_x - tri_w, y - tri_h),  # Left base corner (above the line)
                (mid_x + tri_w, y - tri_h),  # Right base corner (above the line)
                (mid_x,         y),          # Apex pointing downward, touching the line
            ],
            fill=color,    # Solid filled triangle
            stroke=color,
            stroke_w=0.8,
        )

        # ── Ground hatch lines ────────────────────────────────────────────────
        # Short diagonal lines drawn below the horizontal ground line, spreading
        # outward from the apex — matching the standard engineering ground symbol
        # (similar to the hatch marks seen in the reference image beneath the arrow)
        hatch_count  = 7       # Number of hatch lines to draw
        hatch_len    = 8       # Length of each hatch line in pixels
        hatch_gap    = 5       # Horizontal spacing between hatch lines
        hatch_angle  = 50      # Angle of each hatch line in degrees (from horizontal)

        import math
        dx = hatch_len * math.cos(math.radians(hatch_angle))   # Horizontal component
        dy = hatch_len * math.sin(math.radians(hatch_angle))   # Vertical component (downward)

        # Centre the hatch group under the triangle apex (mid_x)
        total_hatch_w = (hatch_count - 1) * hatch_gap          # Total width of the hatch group
        hatch_x_start = mid_x - total_hatch_w / 2              # Left-most hatch start x

        for i in range(hatch_count):
            hx = hatch_x_start + i * hatch_gap   # X position of this hatch line's start point ON the ground line
            hy = y                                # Start exactly on the ground line (not below it)
            # Each hatch line goes diagonally down-LEFT from the ground line (opposite direction)
            self.line(hx, hy, hx - dx, hy + dy, color, 0.9)

        # ── Label ─────────────────────────────────────────────────────────────
        # "Ground Level" text placed above the triangle base
        if label:
            self.text(
                mid_x,             # Horizontally centred on the triangle
                y - tri_h - 4,     # A few pixels above the triangle base
                label,
                font_size=9,
                anchor="middle",
                color=color,
            )

    def draw_trench(self, x_left: float, x_right: float, cy: float, trench_half: float) -> None:
        """Draw engineering-style trench walls: jagged black lines with outward hatch marks.

        Each trench wall is drawn as a randomly jittered polyline to represent the
        irregular cut face of excavated soil.  Short diagonal hatch marks project
        outward from the wall — above the top wall and below the bottom wall —
        matching the conventional ground/soil symbol used in engineering plan drawings.
        A vertical dimension arrow is drawn to the right to annotate the trench width.

        Args:
            x_left:       Left x coordinate where the trench lines begin (SVG pixels).
            x_right:      Right x coordinate where the trench lines end (SVG pixels).
            cy:           Vertical centreline y coordinate in SVG pixels.
            trench_half:  Half the trench width in SVG pixels (distance from centreline to each wall).
        """
        import math
        import random

        trench_color = "#111111"   # Near-black — matches engineering drawing convention
        trench_sw    = 1.4         # Stroke width for the jagged trench wall lines
        hatch_sw     = 1.0         # Stroke width for the hatch marks
        hatch_len    = 8           # Length of each hatch mark in pixels
        hatch_angle  = 45          # Hatch marks drawn at 45° outward from the wall

        # ── Wave / jitter parameters ──────────────────────────────────────────
        wave_amp    = 4.0    # Maximum random displacement in pixels (height of each jitter)
        wave_period = 18.0   # Approximate horizontal distance between vertices
        margin      = 12     # Extra pixels the line extends beyond the pipe on each side

        x_start = x_left  - margin   # Line starts slightly left of the pipe
        x_end   = x_right + margin   # Line ends slightly right of the pipe

        def make_jagged_path(y_base: float, outward: int) -> tuple[str, list[tuple[float, float]]]:
            """Build a randomly jittered SVG polyline path simulating rough excavated soil.

            Args:
                y_base:  The baseline y coordinate for this wall.
                outward: -1 for the top wall (jitter goes upward), +1 for the bottom wall (downward).
            Returns:
                Tuple of (SVG path 'd' string, list of (x, y) vertex tuples for hatch placement).
            """
            rng = random.Random(int(y_base * 1000))   # Seed from y_base so top/bottom walls differ

            min_seg = wave_period * 0.5    # Minimum horizontal distance between vertices
            max_seg = wave_period * 1.8    # Maximum horizontal distance between vertices

            vertices: list[tuple[float, float]] = []
            x = x_start
            vertices.append((x, y_base))   # Start exactly on the baseline

            while x < x_end:
                step   = rng.uniform(min_seg, max_seg)          # Random step size
                x      = min(x + step, x_end)                  # Clamp to end of span
                jitter = rng.uniform(0, wave_amp) * outward     # Random outward displacement
                vertices.append((x, y_base + jitter))

            vertices.append((x_end, y_base))   # End exactly on the baseline

            path = "M " + " L ".join(f"{vx:.2f},{vy:.2f}" for vx, vy in vertices)
            return path, vertices

        def draw_jagged_with_hatches(y_base: float, outward: int) -> None:
            """Draw one jagged trench wall and its outward hatch marks.

            Args:
                y_base:  Baseline y coordinate for this wall.
                outward: -1 for top wall (hatches project upward), +1 for bottom wall (downward).
            """
            path_d, vertices = make_jagged_path(y_base, outward)

            # Draw the jagged polyline
            self._lines.append(
                f'<path d="{path_d}" fill="none" stroke="{trench_color}" '
                f'stroke-width="{trench_sw:.2f}" stroke-linecap="round" stroke-linejoin="round"/>'
            )

            # ── Hatch marks ───────────────────────────────────────────────────
            angle_rad = math.radians(hatch_angle)
            dx = hatch_len * math.cos(angle_rad)   # Horizontal component of hatch mark
            dy = hatch_len * math.sin(angle_rad)   # Vertical component of hatch mark

            for i, (hx, hy) in enumerate(vertices[1:-1]):
                if i % 2 != 0:
                    continue   # Skip every other vertex to avoid overcrowding

                hx2 = hx + dx             # Horizontal end of hatch (always rightward)
                hy2 = hy + dy * outward   # Vertical end of hatch (outward direction)

                self._lines.append(
                    f'<line x1="{hx:.2f}" y1="{hy:.2f}" x2="{hx2:.2f}" y2="{hy2:.2f}" '
                    f'stroke="{trench_color}" stroke-width="{hatch_sw:.2f}" stroke-linecap="round"/>'
                )

        # Draw top trench wall (above the pipe) — hatches project upward
        draw_jagged_with_hatches(cy - trench_half, outward=-1)

        # Draw bottom trench wall (below the pipe) — hatches project downward
        draw_jagged_with_hatches(cy + trench_half, outward=+1)

    def circle(
        self,
        cx: float, cy: float, r: float,
        fill: str, stroke: str, stroke_w: float,
        dash: str = "",
    ) -> None:
        """Append a circle element.

        Args:
            cx, cy:   Centre point in SVG pixels.
            r:        Radius in SVG pixels.
            fill:     CSS fill colour string (use ``"none"`` for an unfilled circle).
            stroke:   CSS stroke colour string.
            stroke_w: Stroke width in pixels.
            dash:     SVG stroke-dasharray value, e.g. ``"6,4"`` (empty = solid).
        """
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self._lines.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"{dash_attr}/>'
        )

    def elbow(
        self,
        cx: float, cy: float,
        outside_diameter: float,
        fill: str,
        stroke: str,
        stroke_w: float,
        start_angle: float = 0,
        sweep_angle: float = 90,
    ):
        """
        Draw a filled elbow (pipe bend) as a ring sector with trapezoidal bellmouths
        and straight pipe extensions at both ends.
        """
        import math

        # --- Elbow geometry (your original code) ---
        R = 1.25 * outside_diameter - outside_diameter
        r = 1.25 * outside_diameter 
        fill = fill if fill is not None else self.pipe_fill
        stroke = stroke if stroke is not None else self.pipe_stroke
        stroke_w = stroke_w if stroke_w is not None else self.sw

        def pol2xy(cxa, cya, radius, ang_deg):
            ang_rad = math.radians(ang_deg)
            return (cxa + radius * math.cos(ang_rad), cya + radius * math.sin(ang_rad))

        # Outer arc
        start_outer = pol2xy(cx, cy, R, start_angle)
        end_outer = pol2xy(cx, cy, R, start_angle + sweep_angle)
        # Inner arc
        start_inner = pol2xy(cx, cy, r, start_angle)
        end_inner = pol2xy(cx, cy, r, start_angle + sweep_angle)

        large_arc = 1 if abs(sweep_angle) > 180 else 0
        sweep_flag = 1 if sweep_angle > 0 else 0

        # Path: Move to start_outer, arc to end_outer, line to end_inner, arc back, close
        d = (
            f"M {start_outer[0]:.2f},{start_outer[1]:.2f} "
            f"A {R:.2f},{R:.2f} 0 {large_arc} {sweep_flag} {end_outer[0]:.2f},{end_outer[1]:.2f} "
            f"L {end_inner[0]:.2f},{end_inner[1]:.2f} "
            f"A {r:.2f},{r:.2f} 0 {large_arc} {1 - sweep_flag} {start_inner[0]:.2f},{start_inner[1]:.2f} "
            "Z"
        )
        self._lines.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"/>'
        )

        # --- Bellmouths: Fixed parameters ---
        bellmouth_height = outside_diameter * 0.3   # px, typical value
        bellmouth_flare = outside_diameter * 0.3    # px, typical value

        def bellmouth_polygon(outer_pt, inner_pt, angle_deg, reverse=False):
            theta = math.radians(angle_deg)
            tx, ty = -math.sin(theta), math.cos(theta)  # tangent direction
            nx, ny = math.cos(theta), math.sin(theta)   # radial direction
            if reverse:
                tx, ty = -tx, -ty  # Reverse direction for start

            offset_outer = -bellmouth_flare / 2
            offset_inner = bellmouth_flare / 2

            v1 = outer_pt
            v2 = inner_pt
            v3 = (
                inner_pt[0] + bellmouth_height * tx + offset_inner * nx,
                inner_pt[1] + bellmouth_height * ty + offset_inner * ny
            )
            v4 = (
                outer_pt[0] + bellmouth_height * tx + offset_outer * nx,
                outer_pt[1] + bellmouth_height * ty + offset_outer * ny
            )
            return f"{v1[0]:.2f},{v1[1]:.2f} {v2[0]:.2f},{v2[1]:.2f} {v3[0]:.2f},{v3[1]:.2f} {v4[0]:.2f},{v4[1]:.2f}"

        # --- Straight pipe extensions at both ends ---
        pipe_length = outside_diameter*2 # px, typical straight length

        def straight_pipe_polygon(outer_pt, inner_pt, angle_deg, direction=1):
            theta = math.radians(angle_deg)
            tx, ty = -math.sin(theta), math.cos(theta)
            tx, ty = direction * tx, direction * ty
            A = outer_pt
            B = inner_pt
            C = (inner_pt[0] + pipe_length * tx, inner_pt[1] + pipe_length * ty)
            D = (outer_pt[0] + pipe_length * tx, outer_pt[1] + pipe_length * ty)
            return f"{A[0]:.2f},{A[1]:.2f} {B[0]:.2f},{B[1]:.2f} {C[0]:.2f},{C[1]:.2f} {D[0]:.2f},{D[1]:.2f}"

        # Pipe at start (tangent reversed)
        points_pipe_start = straight_pipe_polygon(start_outer, start_inner, start_angle, direction=-1)
        self._lines.append(
            f'<polygon points="{points_pipe_start}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"/>'
        )

        # Pipe at end (tangent as-is)
        points_pipe_end = straight_pipe_polygon(end_outer, end_inner, start_angle + sweep_angle, direction=1)
        self._lines.append(
            f'<polygon points="{points_pipe_end}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"/>'
        )

                # Bellmouth at start
        points_start = bellmouth_polygon(start_outer, start_inner, start_angle, reverse=True)
        self._lines.append(
            f'<polygon points="{points_start}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"/>'
        )

        # Bellmouth at end
        points_end = bellmouth_polygon(end_outer, end_inner, start_angle + sweep_angle)
        self._lines.append(
            f'<polygon points="{points_end}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.2f}"/>'
        )

        # --- Dashed centreline ---
        center_radius = (R + r) / 2

        theta_start = math.radians(start_angle)
        tx_start, ty_start = -math.sin(theta_start), math.cos(theta_start)
        start_center = pol2xy(cx, cy, center_radius, start_angle)
        before_start = (start_center[0] - pipe_length * tx_start, start_center[1] - pipe_length * ty_start)

        theta_end = math.radians(start_angle + sweep_angle)
        tx_end, ty_end = -math.sin(theta_end), math.cos(theta_end)
        end_center = pol2xy(cx, cy, center_radius, start_angle + sweep_angle)
        after_end = (end_center[0] + pipe_length * tx_end, end_center[1] + pipe_length * ty_end)

        d_centerline = (
            f"M {before_start[0]:.2f},{before_start[1]:.2f} "
            f"L {start_center[0]:.2f},{start_center[1]:.2f} "
            f"A {center_radius:.2f},{center_radius:.2f} 0 {large_arc} {sweep_flag} {end_center[0]:.2f},{end_center[1]:.2f} "
            f"L {after_end[0]:.2f},{after_end[1]:.2f}"
        )

        self._lines.append(
            f'<path d="{d_centerline}" stroke="#000" stroke-width="{stroke_w/3:.2f}" fill="none" stroke-dasharray="8,6"/>'
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

    def draw_section_line(
        self,
        x: float,
        y_top: float,
        y_bottom: float,
        label: str = "A",
        arm_len: float = 30.0,
    ) -> None:
        """Draw a standard engineering A-A section cut indicator on the plan view.

        The symbol is a single connected shape consisting of:
          1. One vertical line running from y_top to y_bottom at position x
             (cuts through the full trench width including the pipe)
          2. A horizontal arm branching rightward from the TOP of the vertical line,
             ending with a filled arrowhead and the letter label
          3. A horizontal arm branching rightward from the BOTTOM of the vertical line,
             ending with a filled arrowhead and the letter label

        This matches the conventional A-A section cut indicator seen in engineering
        plan drawings (as shown in the reference image).

        Args:
            x:        X coordinate of the vertical cut line in SVG pixels.
            y_top:    Y coordinate of the top end of the vertical line (top of trench).
            y_bottom: Y coordinate of the bottom end of the vertical line (bottom of trench).
            label:    Single letter label placed at each arrowhead tip (default ``"A"``).
            arm_len:  Length of each horizontal arm in pixels.
        """
        color = "#111111"   # Near-black — matches engineering drawing convention
        sw    = 1.4         # Stroke width for the section indicator lines

        # ── 1. Vertical cut line ──────────────────────────────────────────────
        # One continuous vertical line spanning the full trench height at x.
        # This is the "cut" line that slices through the trench and pipe.
        self.line(x, y_top, x, y_bottom, color, sw)

        # ── 2. TOP horizontal arm (branches right from the top of the vertical) ──
        # Starts at (x, y_top) and runs rightward by arm_len pixels.
        top_x_end = x + arm_len   # Tip of the top arm (where the arrowhead points)
        self.line(x, y_top, top_x_end, y_top, color, sw)

        # Filled rightward arrowhead at the tip of the top arm
        self._lines.append(
            f'<polygon points="{top_x_end:.2f},{y_top:.2f} '
            f'{top_x_end - 7:.2f},{y_top - 3:.2f} '
            f'{top_x_end - 7:.2f},{y_top + 3:.2f}" fill="{color}"/>'
        )

        # Label placed just to the right of the top arrowhead tip
        self.text(top_x_end + 10, y_top + 4, label,
                  font_size=10, anchor="start", color=color, bold=True)

        # ── 3. BOTTOM horizontal arm (branches right from the bottom of the vertical) ──
        # Starts at (x, y_bottom) and runs rightward by the same arm_len pixels.
        bot_x_end = x + arm_len   # Tip of the bottom arm
        self.line(x, y_bottom, bot_x_end, y_bottom, color, sw)

        # Filled rightward arrowhead at the tip of the bottom arm
        self._lines.append(
            f'<polygon points="{bot_x_end:.2f},{y_bottom:.2f} '
            f'{bot_x_end - 7:.2f},{y_bottom - 3:.2f} '
            f'{bot_x_end - 7:.2f},{y_bottom + 3:.2f}" fill="{color}"/>'
        )

        # Label placed just to the right of the bottom arrowhead tip
        self.text(bot_x_end + 10, y_bottom + 4, label,
                  font_size=10, anchor="start", color=color, bold=True)
        
    def draw_horizontal_section_line(
        self,
        x_left: float,
        y: float,
        x_right: float,
        label: str = "A",
        arm_len: float = 30.0,
        ) -> None:
        """
        Draw a horizontal section cut indicator:
        - One horizontal line from (x_left, y) to (x_right, y)
        - Vertical arms at each end, both facing upward with arrowheads
        - Letter label 'A' placed next to each arrowhead, inline horizontally

        Args:
            x_left:   X coordinate of the left end of the horizontal line.
            y:        Y coordinate of the horizontal section line.
            x_right:  X coordinate of the right end of the horizontal line.
            label:    Section label (default "A").
            arm_len:  Length of the vertical arms (default 30).
        """
        color = "#111111"
        sw = 1.4

        # 1. Horizontal section line
        self.line(x_left, y, x_right, y, color, sw)

        # 2. LEFT vertical arm (up)
        left_y_tip = y - arm_len
        self.line(x_left, y, x_left, left_y_tip, color, sw)
        # Upward arrowhead at left tip
        self._lines.append(
            f'<polygon points="{x_left:.2f},{left_y_tip:.2f} '
            f'{x_left - 3:.2f},{left_y_tip + 7:.2f} '
            f'{x_left + 3:.2f},{left_y_tip + 7:.2f}" fill="{color}"/>'
        )
        # Label inline horizontally at left tip
        self.text(x_left, left_y_tip - 5, label,
                font_size=10, anchor="middle", color=color, bold=True)

        # 3. RIGHT vertical arm (up)
        right_y_tip = y - arm_len
        self.line(x_right, y, x_right, right_y_tip, color, sw)
        # Upward arrowhead at right tip
        self._lines.append(
            f'<polygon points="{x_right:.2f},{right_y_tip:.2f} '
            f'{x_right - 3:.2f},{right_y_tip + 7:.2f} '
            f'{x_right + 3:.2f},{right_y_tip + 7:.2f}" fill="{color}"/>'
        )
        # Label inline horizontally at right tip
        self.text(x_right, right_y_tip - 5, label,
                font_size=10, anchor="middle", color=color, bold=True)


    def dim_arrow(
        self,
        x1: float, y: float, x2: float,
        label: str,
        font_size: int = 10,
        label_position: str = "above",
    ) -> None:
        """Draw a horizontal dimension line with arrowheads and a centred label.

        The line is placed 12px above or below the supplied ``y`` reference
        coordinate depending on ``label_position``.  Tick marks are drawn at
        each end, filled triangular arrowheads point inward, and the label is
        centred on the chosen side of the line.

        Args:
            x1:             Left endpoint x in SVG pixels.
            y:              Reference y coordinate (line is offset 12px from this).
            x2:             Right endpoint x in SVG pixels.
            label:          Dimension label string (e.g. ``"L = 1200 mm"``).
            font_size:      Font size for the label.
            label_position: ``"above"`` (default) places the line above ``y`` and
                            the label above the line; ``"below"`` places the line
                            below ``y`` and the label below the line.
        """
        dc  = self.dim_color
        dsw = self.dsw

        # Determine the direction of the offset based on label_position:
        #   "above" → line sits 12px ABOVE y  (ty < y)
        #   "below" → line sits 12px BELOW y  (ty > y)
        if label_position == "below":
            ty         = y + 12    # Shift the dim line 12px below the reference y
            label_y    = ty + 14   # Label sits below the line (larger y = lower on canvas)
            text_anchor_offset = +14   # Positive offset pushes text downward
        else:
            ty         = y - 12    # Shift the dim line 12px above the reference y (default)
            label_y    = ty - 4    # Label sits above the line (smaller y = higher on canvas)
            text_anchor_offset = -4    # Negative offset keeps text above the line

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

        # Label centred horizontally; placed above or below the line depending on label_position
        self.text((x1 + x2) / 2, label_y, label, font_size=font_size, color=dc)

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

    # 6. CENTRELINE (dashed)
    c.line(x_left - 10, cy, x_right + 10, cy, "#888888", 0.8, dash="6,4")

    # ── Dimension annotations ─────────────────────────────────────────────────
    dim_y_top = cy - h_bell_od - 30
    c.dim_arrow(x_left, dim_y_top, x_right, f"L = {length:.0f} mm")
    c.vert_dim_arrow(x_left - 10,  cy - h_od,      cy + h_od,      f"OD = {od:.0f} mm",          right=False, font_size=9)
    c.vert_dim_arrow(x_right + 10, cy - h_bell_od, cy + h_bell_od, f"Bell OD = {bell_od:.0f} mm", right=True,  font_size=9)

    # ── Title block ───────────────────────────────────────────────────────────
    c.text(canvas_w / 2, canvas_h - 12, "Socket Pipe – Plan View", font_size=12, color="#1a1a2e", bold=True)

    return c.render()

def build_taper_thrust_svg(height: float, width: float, length: float, od_large: float, od_small: float, canvas_w: int = 1100, canvas_h: int = 420) -> str:
    """Generate an SVG plan view of a Taper Thrust pipe.
    
    The Taper pipe consists of:
      - A straight pipe barrel with wall thickness derived from OD
      - A plain square-cut end at the left (spigot-receive) side
      - A bell/socket expansion at the right end that receives the next spigot
      - A dashed centreline through the pipe axis
      - Expander pipe
      - Dimension annotations (OD, bell OD, and overall length L)

    Args:
        od:       Outside diameter of the socket pipe in mm.
        canvas_w: SVG canvas width in pixels (from user input).
        canvas_h: SVG canvas height in pixels (from user input).
    """

    # ── Derived geometry spigot ──────────────────────────────────────────────────────
    spigot_wall      = od_large * 0.08                    # Wall thickness = 8% of od_large
    spigot_id_       = od_large - 2 * spigot_wall                # Inner diameter = od_large minus both walls
    spigot_length    = od_large * 4                   # Pipe length = 4× od_large for a visually balanced drawing

    # ── Derived geometry flange ──────────────────────────────────────────────────────
    flange_od   = od_large * 1.25                   # Bell outer diameter — 20% wider than the pipe od_large
    flange_length = od_large * 0.15
    # ── Derived geometry socket ──────────────────────────────────────────────────────
    socket_od = od_large * 1.15
    socket_length = od_large * 0.4
    socket_od_small = od_small * 1.15
    # ── Derived geometry socket_pipe ──────────────────────────────────────────────────────
    socket_pipe_wall_large = od_large * 0.08
    socket_pipe_id_ = od_large - 2 * socket_pipe_wall_large  
    socket_pipe_length = od_large * 4.0

    # ── Derived geometry taper ──────────────────────────────────────────────────────
    wall_large      = od_large * 0.08                    # Wall thickness = 8% of OD
    wall_small      = od_small * 0.08
    large_id_ = od_large - 2 * wall_large                # Inner diameter = OD minus both walls
    small_id_ = od_small - 2 * wall_small
    taper_length    = od_large * 1.5                    # Pipe length = 4× OD for a visually balanced drawing
    bell_od   = od_large * 1.3                    # Bell outer diameter — 20% wider than the pipe OD
    bell_len  = od_large * 0.5                    # Axial length of the bell expansion zone
    bell_wall = od_large * 0.08                   # Bell wall thickness — slightly thicker than barrel wall
    bell_id   = bell_od - 2 * bell_wall                    # Bell outer diameter — 20% wider than the pipe OD

    # ── SVG canvas & scale ────────────────────────────────────────────────────
    total_length = taper_length + 2 * (spigot_length + socket_length  + flange_length + socket_pipe_length)
    ctx = create_canvas(total_length, flange_od, canvas_w, canvas_h)
    c   = SVGCanvas(ctx["scale"], canvas_w, canvas_h)
    cx  = ctx["cx"]
    cy  = ctx["cy"]

    # ── X positions taper ───────────────────────────────────────────────────────────
    x_left       = cx - c.s(taper_length) / 2              # Left edge (plain square-cut end)
    x_right      = cx + c.s(taper_length) / 2              # Right edge (bell end face)

    # ── X positions flange ───────────────────────────────────────────────────────────
    x_left_flange      = cx - c.s(taper_length) / 2  - c.s(flange_length)            # Left edge (plain square-cut end)
    x_right_flange      = x_right   + c.s(flange_length)       # Right edge (bell end face)

    # ── X positions - spiggot pipe ───────────────────────────────────────────────────────────
    x_left_spigot       = cx - c.s(taper_length) / 2 - c.s(flange_length) * 2 - c.s(spigot_length)      # Left edge (plain square-cut end)
    x_right_spigot      = cx + c.s(socket_length) + c.s(taper_length) / 2              # Right edge (bell end face)

    # ── X positions - socket pipe with socket connection ───────────────────────────────────────────────────────────
    x_left_socket_pipe  = cx - c.s(taper_length) / 2 - c.s(flange_length) * 2 - c.s(spigot_length) - c.s(socket_length) - c.s(socket_pipe_length)      # Left edge (plain square-cut end)
    x_right_spigot      = cx + c.s(socket_length) + c.s(taper_length) / 2              # Right edge (bell end face)


    
    # ── Half-heights ─────────────────────────────────────────────────────────
    h_od_large      = c.s(od_large)  / 2   # Half the pipe OD
    h_od_small      = c.s(od_small) /2
    h_id_large = c.s(large_id_) /2
    h_id_small = c.s(small_id_) /2
    h_bell_od = c.s(bell_od) / 2   # Half the bell OD
    h_bell_id = c.s(bell_id) / 2   # Half the bell ID (bore widens inside the bell)
    h_thrust_height = c.s(height) / 2
    h_thrust_width = c.s(width) / 2 
    h_thrust_length = c.s(length) / 2

    pf = c.pipe_fill
    ps = c.pipe_stroke
    sw = c.sw

    # ── Draw components ───────────────────────────────────────────────────────

    # TRENCH - random lines

    c.draw_trench(x_left_socket_pipe, x_right_flange + c.s(flange_length) + c.s(spigot_length) + c.s(socket_length) + c.s(spigot_length), cy, c.s(0.25 * width))
    # 3. SOCKET PIPE BARREL OUTER BORE — white rectangle for the straight section hollow interior
    c.rect(cx - h_thrust_length, cy - h_thrust_width, c.s(length), c.s(width), pf, ps, sw)

    # 3. SOCKET PIPE BARREL OUTER BORE — white rectangle for the straight section hollow interior
    c.rect(x_left_socket_pipe, cy - h_od_large, c.s(socket_pipe_length), c.s(od_large), pf, ps, sw)

    # 3. SOCKET PIPE BARREL INNER BORE — white rectangle for the straight section hollow interior
    c.rect(x_left_socket_pipe, cy - h_id_large, c.s(socket_pipe_length), c.s(large_id_), "white", ps, sw * 0.6)

    # 3. BELL OUTER SHAPE — 4-point polygon widening from pipe OD to bell OD
    c.poly(
        [(x_left_socket_pipe - c.s(bell_len), cy - h_bell_od),     (x_left_socket_pipe, cy - h_od_large),
         (x_left_socket_pipe, cy + h_od_large), (x_left_socket_pipe - c.s(bell_len), cy + h_bell_od)],
        pf, ps, sw,
    )

    # 3. BELL INNER SHAPE — 4-point polygon widening from pipe OD to bell OD
    c.poly(
        [(x_left_socket_pipe - c.s(bell_len), cy - h_bell_id),     (x_left_socket_pipe, cy - h_id_large),
         (x_left_socket_pipe, cy + h_id_large), (x_left_socket_pipe - c.s(bell_len), cy + h_bell_id)],
        "white", ps, sw * 0.6,
    )

    # 3. SOCKET FITTING — white rectangle for the straight section hollow interior
    c.rect(x_left_spigot - c.s(socket_length), cy - c.s(socket_od/2), c.s(socket_length), c.s(socket_od), "white", ps, sw *0.65)

    # 3. SPIGGOT OUTER BORE — white rectangle for the straight section hollow interior
    c.rect(x_left_spigot, cy - h_od_large, c.s(spigot_length), c.s(od_large), pf, ps, sw)

    # 1. SPIGOT INNER BORE — white rectangle for the straight section hollow interior
    c.rect(x_left_spigot, cy - h_id_large, c.s(spigot_length), c.s(large_id_), "white", ps, sw * 0.6)

    # 1. SPIGOT FLANGE — white rectangle for the straight section hollow interior
    c.rect(x_left - c.s(flange_length) * 2, cy - c.s(flange_od/2), c.s(flange_length), c.s(flange_od), "white", ps, sw * 0.6)

    # 1. TAPER FLANGE — white rectangle for the straight section hollow interior
    c.rect(x_left - c.s(flange_length), cy - h_od_large * 1.25, c.s(flange_length), c.s(od_large*1.25), "white", ps, sw * 0.6)

    # 2. THRUST OUTER SHAPE — 4-point polygon widening from pipe OD to bell OD
    c.poly(
        [(x_left, cy - h_od_large),     (x_right, cy - h_od_small),
         (x_right,      cy + h_od_small),(x_left, cy + h_od_large)],
        pf, ps, sw,
    )

    # 3. BELL INNER BORE — 4-point polygon; bore widens to accept an incoming spigot
    c.poly(
        [(x_left, cy - h_id_large),     (x_right, cy - h_id_small),
         (x_right,      cy + h_id_small),(x_left, cy + h_id_large)],
        "white", ps, sw * 0.6,
    )

    # 1. FLANGE INNER BORE — white rectangle for the straight section hollow interior
    c.rect(x_right, cy - h_od_small * 1.25, c.s(100), c.s(od_small*1.25), "white", ps, sw * 0.6)

    # small pipe spiggot flange
    c.rect(x_right_flange, cy - h_od_small * 1.25, c.s(flange_length), c.s(od_small*1.25), "white", ps, sw * 0.6)

    # 1. SMALL SPIGGOT - white rectangle for the straight section hollow interior
    c.rect(x_right_flange + c.s(flange_length), cy - h_od_small, c.s(socket_pipe_length), c.s(od_small), pf, ps, sw )

    # 1. SMALL SPIGGOT - white rectangle for the straight section hollow interior
    c.rect(x_right_flange + c.s(flange_length), cy - h_id_small, c.s(socket_pipe_length), c.s(small_id_), "white", ps, sw * 0.6 )

    # 1. SMALL SPIGGOT - white rectangle for the straight section hollow interior
    c.rect(x_right_flange + c.s(flange_length), cy - h_id_small, c.s(socket_pipe_length), c.s(small_id_), "white", ps, sw * 0.6 )

    # 1. SMALL SOCKET - white rectangle for the straight section hollow interior
    c.rect(x_right_flange + c.s(flange_length) + c.s(spigot_length), cy - c.s(socket_od_small/2), c.s(socket_length), c.s(socket_od_small), "white", ps, sw * 0.6 )

    # 1. SMALL SPIGGOT - white rectangle for the straight section hollow interior
    c.rect(x_right_flange + c.s(flange_length) + c.s(spigot_length) + c.s(socket_length), cy - h_od_small, c.s(socket_pipe_length), c.s(od_small), pf, ps, sw)

    # 1. SMALL SPIGGOT - white rectangle for the straight section hollow interior
    c.rect(x_right_flange + c.s(flange_length) + c.s(spigot_length) + c.s(socket_length), cy - h_id_small, c.s(socket_pipe_length), c.s(small_id_), "white", ps, sw * 0.6 )

    # 4. CENTRELINE (dashed)
    c.line(x_left_socket_pipe - c.s(bell_len), cy, x_right_flange + c.s(flange_length) + c.s(spigot_length) + c.s(socket_length) + c.s(spigot_length), cy, "#888888", 0.8, dash="6,4")

    # ── Dimension annotations ─────────────────────────────────────────────────
    dim_y_top = cy - h_od_large - 30
    # c.dim_arrow(x_left, dim_y_top, x_right, f"L = {length:.0f} mm")
    c.vert_dim_arrow(x_left - c.s(300),  cy - h_od_large,      cy + h_od_large,"D_O_A", right=False, font_size=12)
    c.vert_dim_arrow(x_right + c.s(300), cy - h_od_small, cy + h_od_small, "D_O_B", right=True,  font_size=12)
    c.vert_dim_arrow(x_right_flange + c.s(flange_length) + c.s(spigot_length) + c.s(socket_length) + c.s(spigot_length) + c.s(500), cy - h_thrust_width, cy + h_thrust_width, f"W = {width:.0f}", right=True,  font_size=12)
    c.draw_section_line(cx - h_thrust_length*0.25, cy - h_thrust_width * 1.1, cy + h_thrust_width * 1.1)
    c.dim_arrow(cx - h_thrust_length, cy + h_thrust_width*1.1, cx + h_thrust_length, label=f"L = {length:.0f}", font_size=12, label_position="below")

    # ── Title block ───────────────────────────────────────────────────────────
    c.text(canvas_w / 2, canvas_h - 12, "Taper Thrust – Plan View", font_size=12, color="#1a1a2e", bold=True)

    return c.render()

def build_taper_thrust_section_svg(height: float, width: float, length: float, depth, gw_level: float, od_large: float, depth_crown_pipe: float, canvas_w: int = 1100, canvas_h: int = 420) -> str:
    # ── Derived geometry taper ──────────────────────────────────────────────────────
    wall_large      = od_large * 0.08                    # Wall thickness = 8% of OD
    large_id_ = od_large - 2 * wall_large                # Inner diameter = OD minus both walls                  # Pipe length = 4× OD for a visually balanced drawing

    # ── SVG canvas & scale ────────────────────────────────────────────────────
    total_length =  1.2 * width
    ctx = create_canvas(total_length, depth, canvas_w, canvas_h)
    c   = SVGCanvas(ctx["scale"], canvas_w, canvas_h)
    cx  = ctx["cx"]
    cy  = ctx["cy"]

    # ── X positions block ───────────────────────────────────────────────────────────
    x_left       = cx - c.s(width) / 2              # Left edge (plain square-cut end)
    x_right      = cx + c.s(width) / 2              # Right edge (bell end face)

    # ── X pipe - socket pipe with socket connection ───────────────────────────────────────────────────────────
    x_left_pipe  = cx - c.s(od_large) / 2     # Left edge (plain square-cut end)
    x_right_pipe      = cx + c.s(od_large) /2            # Right edge (bell end face)
    
    # ── Half-heights ─────────────────────────────────────────────────────────
    h_od_large      = c.s(od_large)  / 2   # Half the pipe OD
    h_id_large = c.s(large_id_) /2
    h_thrust_height = c.s(height) / 2
    h_thrust_width = c.s(width) / 2 

    ground_level = cy + h_thrust_height - c.s(depth)

    pf = c.pipe_fill
    ps = c.pipe_stroke
    sw = c.sw

    # ── Draw components ───────────────────────────────────────────────────────

    # TRENCH - random lines
    # 3. SOCKET PIPE BARREL OUTER BORE — white rectangle for the straight section hollow interior
    c.rect(x_left, cy - h_thrust_height, c.s(width), c.s(height), pf, ps, sw)

    # 3. SOCKET PIPE BARREL OUTER BORE — white rectangle for the straight section hollow interior
    c.circle(cx, ground_level + c.s(depth_crown_pipe) + h_od_large, h_od_large, pf, ps, sw)

    # 3. SOCKET PIPE BARREL OUTER BORE — white rectangle for the straight section hollow interior
    c.circle(cx, ground_level + c.s(depth_crown_pipe) + h_od_large, h_id_large, "white", ps, sw)

    c.draw_ground_level(cx - c.s(width)*2, cx + c.s(width)*2, ground_level, label="Ground Level")

    c.line(cx - c.s(width)*2, ground_level + c.s(gw_level), cx + c.s(width)*2,  ground_level + c.s(gw_level), "#63CDE5", 0.8, dash="6,4")

    # c.dim_arrow(x_left, dim_y_top, x_right, f"L = {length:.0f} mm")
    c.dim_arrow(cx - h_thrust_width, cy + h_thrust_height*1.1, cx + h_thrust_width, label=f"W = {width:.0f}", font_size=12, label_position="below")
    c.vert_dim_arrow(cx + h_thrust_width + 2* h_od_large,  cy - h_thrust_height, cy + h_thrust_height, f"H = {height:.0f}",  right=False, font_size=12)
    c.vert_dim_arrow(cx - c.s(width), ground_level, ground_level + c.s(gw_level), f"Z_GW = {gw_level:.0f}", right=True,  font_size=12)
    c.vert_dim_arrow(cx, ground_level, ground_level + c.s(depth_crown_pipe), f"Z_O = {depth_crown_pipe:.0f}", right=True,  font_size=12)
    c.vert_dim_arrow(cx + h_thrust_width + 4* h_od_large,  ground_level, cy + h_thrust_height, f"Z_b = {depth:.0f}",  right=False, font_size=12)

    # ── Title block ───────────────────────────────────────────────────────────
    c.text(canvas_w / 2, canvas_h - 12, "Taper Thrust – Section A-A", font_size=12, color="#1a1a2e", bold=True)

    return c.render()

def build_horizontal_bend(height: float, width: float, length: float, depth, gw_level: float, od: float, depth_crown_pipe: float, start_angle: float, angle: float, canvas_w: int = 600, canvas_h: int = 300) -> str:
    # ── Derived geometry taper ──────────────────────────────────────────────────────
    wall_large      = od * 0.08                    # Wall thickness = 8% of OD
    large_id_ = od - 2 * wall_large                # Inner diameter = OD minus both walls                  # Pipe length = 4× OD for a visually balanced drawing
    # ── SVG canvas & scale ────────────────────────────────────────────────────
    ctx = create_canvas(length, od*8, canvas_w, canvas_h, margin_x=60, margin_y=10)
    c   = SVGCanvas(ctx["scale"], canvas_w, canvas_h)
    cx  = ctx["cx"]
    cy  = ctx["cy"]

    pf = c.pipe_fill
    ps = c.pipe_stroke
    sw = c.sw

    # ── Draw components ───────────────────────────────────────────────────────

    # ELBOW DIMENSIONS TEXTS
    c.elbow(cx-c.s(od), cy, c.s(od), fill="white", stroke=ps, stroke_w=sw, start_angle=start_angle, sweep_angle=angle,)
    c.rect(cx , cy - c.s(width/2), c.s(length), c.s(width), pf, ps, sw)
    c.dim_arrow(cx, cy + c.s(width/2), cx + c.s(length), label=f"L = {length:.0f}", font_size=12, label_position="below")
    c.vert_dim_arrow(cx + c.s(od) + c.s(length),  cy - c.s(width/2), cy + c.s(width/2), f"W = {width:.0f}", font_size=12)
    c.draw_horizontal_section_line(cx - c.s(od*1.4), cy, cx + c.s(length) + c.s(od/3))
    # ── Title block ───────────────────────────────────────────────────────────
    c.text(canvas_w / 2, canvas_h - 12, "Horizontal Bend Thrust – Plan View", font_size=12, color="#1a1a2e", bold=True)

    return c.render()

def build_horizontal_bend_section_svg(height: float, width: float, length: float, depth, gw_level: float, od: float, depth_crown_pipe: float, canvas_w: int = 1100, canvas_h: int = 420) -> str:
    # ── Derived geometry taper ──────────────────────────────────────────────────────
    wall_large      = od * 0.08                    # Wall thickness = 8% of OD
    large_id_ = od - 2 * wall_large                # Inner diameter = OD minus both walls                  # Pipe length = 4× OD for a visually balanced drawing

    # ── SVG canvas & scale ────────────────────────────────────────────────────
    ctx = create_canvas(length, depth, canvas_w, canvas_h)
    c   = SVGCanvas(ctx["scale"], canvas_w, canvas_h)
    cx  = ctx["cx"]
    cy  = ctx["cy"]

    # ── X positions block ───────────────────────────────────────────────────────────
    x_left       = cx - c.s(length) / 2              # Left edge (plain square-cut end)
    x_right      = cx + c.s(width) / 2              # Right edge (bell end face)

    # ── X pipe - socket pipe with socket connection ───────────────────────────────────────────────────────────
    x_left_pipe  = cx - c.s(od) / 2     # Left edge (plain square-cut end)
    x_right_pipe      = cx + c.s(od) /2            # Right edge (bell end face)
    
    # ── Half-heights ─────────────────────────────────────────────────────────
    h_od_large      = c.s(od)  / 2   # Half the pipe OD
    h_id_large = c.s(large_id_) /2
    h_thrust_height = c.s(height) / 2
    h_thrust_length = c.s(length) / 2 

    ground_level = cy + h_thrust_height - c.s(depth)

    pf = c.pipe_fill
    ps = c.pipe_stroke
    sw = c.sw

    # ── Draw components ───────────────────────────────────────────────────────

    # TRENCH - random lines
    # 3. SOCKET PIPE BARREL OUTER BORE — white rectangle for the straight section hollow interior
    c.rect(x_left, cy - h_thrust_height, c.s(length), c.s(height), pf, ps, sw)

    c.rect(cx - h_thrust_length - c.s(3000), ground_level + c.s(depth_crown_pipe), c.s(3000), c.s(od), "white", ps, sw)

    # 3. SOCKET PIPE BARREL OUTER BORE — white rectangle for the straight section hollow interior
    c.circle(cx - h_thrust_length, ground_level + c.s(depth_crown_pipe) + h_od_large, h_od_large, "white", ps, sw)


    c.draw_ground_level(cx - c.s(width)*2, cx + c.s(width)*2, ground_level, label="Ground Level")

    c.line(cx - c.s(width)*2, ground_level + c.s(gw_level), cx + c.s(width)*2,  ground_level + c.s(gw_level), "#63CDE5", 0.8, dash="6,4")


    # c.dim_arrow(x_left, dim_y_top, x_right, f"L = {length:.0f} mm")
    c.dim_arrow(cx - h_thrust_length, cy + h_thrust_height*1.1, cx + h_thrust_length, label=f"L = {length:.0f}", font_size=12, label_position="below")
    c.vert_dim_arrow(cx + h_thrust_length + 2* h_od_large,  cy - h_thrust_height, cy + h_thrust_height, f"H = {height:.0f}",  right=False, font_size=12)
    c.vert_dim_arrow(cx - c.s(width), ground_level, ground_level + c.s(gw_level), f"Z_GW = {gw_level:.0f}", right=True,  font_size=12)
    c.vert_dim_arrow(cx - h_thrust_length, ground_level, ground_level + c.s(depth_crown_pipe), f"Z_O = {depth_crown_pipe:.0f}", right=True,  font_size=12)
    c.vert_dim_arrow(cx + h_thrust_length + 4* h_od_large,  ground_level, cy + h_thrust_height, f"Z_b = {depth:.0f}",  right=False, font_size=12)

    # ── Title block ───────────────────────────────────────────────────────────
    c.text(canvas_w / 2, canvas_h - 12, "Horizontal Bend Thrust – Section A-A", font_size=12, color="#1a1a2e", bold=True)

    return c.render()


def build_vertical_upturn_bend_section_svg(height: float, width: float, length: float, depth, gw_level: float, od: float, depth_crown_pipe: float, start_angle: float, angle: float, canvas_w: int = 600, canvas_h: int = 300) -> str:
    # ── Derived geometry taper ──────────────────────────────────────────────────────
    wall_large      = od * 0.08                    # Wall thickness = 8% of OD
    large_id_ = od - 2 * wall_large                # Inner diameter = OD minus both walls                  # Pipe length = 4× OD for a visually balanced drawing

    # ── SVG canvas & scale ────────────────────────────────────────────────────
    ctx = create_canvas(length*2, depth + height, canvas_w, canvas_h, margin_x=60, margin_y=10)
    c   = SVGCanvas(ctx["scale"], canvas_w, canvas_h)
    cx  = ctx["cx"]
    cy  = ctx["cy"]
    
    # ── Half-heights ─────────────────────────────────────────────────────────
    h_od_large      = c.s(od)  / 2   # Half the pipe OD
    h_id_large = c.s(large_id_) /2
    h_thrust_height = c.s(height) / 2
    h_thrust_length = c.s(length) / 2 

    ground_level = cy - c.s(depth)/2 

    pf = c.pipe_fill
    ps = c.pipe_stroke
    sw = c.sw

    # ── Draw components ───────────────────────────────────────────────────────

    # TRENCH - random lines
    # 3. SOCKET PIPE BARREL OUTER BORE — white rectangle for the straight section hollow interior

    c.rect(cx - h_thrust_length, cy + c.s(depth)/2 - c.s(height), c.s(length), c.s(height), pf, ps, sw)

    c.elbow(cx + h_thrust_length*0.9, ground_level + c.s(depth_crown_pipe), c.s(od), fill="white", stroke=ps, stroke_w=sw, start_angle=start_angle, sweep_angle=angle)

    c.draw_ground_level(cx - c.s(length)*3, cx + c.s(length)*3, ground_level, label="Ground Level")

    c.line(cx - c.s(length)*3, ground_level + c.s(gw_level), cx + c.s(length)*3,  ground_level + c.s(gw_level), "#63CDE5", 0.8, dash="6,4")


    # c.dim_arrow(x_left, dim_y_top, x_right, f"L = {length:.0f} mm")
    c.dim_arrow(cx - h_thrust_length, ground_level + c.s(depth) + h_od_large/4, cx + h_thrust_length, label=f"L = {length:.0f}", font_size=12, label_position="below")
    c.vert_dim_arrow(cx - h_thrust_length - h_od_large, ground_level + c.s(depth) - c.s(height),  ground_level + c.s(depth), f"H = {height:.0f}",  right=False, font_size=12)
    c.vert_dim_arrow(cx - c.s(length) - c.s(od), ground_level, ground_level + c.s(gw_level), f"Z_GW = {gw_level:.0f}", right=True,  font_size=12)
    c.vert_dim_arrow(cx + h_thrust_length + h_od_large, ground_level, ground_level + c.s(depth_crown_pipe) + h_od_large/2, f"Z_O = {depth_crown_pipe:.0f}", right=True,  font_size=12)
    c.vert_dim_arrow(cx + h_thrust_length*1.5 + 4* h_od_large,  ground_level, ground_level + c.s(depth), f"Z_b = {depth:.0f}",  right=False, font_size=12)

    # ── Title block ───────────────────────────────────────────────────────────
    c.text(canvas_w / 2, canvas_h - 12, "Horizontal Bend Thrust – Section A-A", font_size=12, color="#1a1a2e", bold=True)

    return c.render()
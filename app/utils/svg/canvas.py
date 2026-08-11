from __future__ import annotations

import math
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from html import escape
from typing import Iterator


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    def __getitem__(self, index: int) -> float:
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError(index)

    def __len__(self) -> int:
        return 2


@dataclass(frozen=True, slots=True)
class Vector:
    x: float
    y: float

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    def __getitem__(self, index: int) -> float:
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError(index)

    def __len__(self) -> int:
        return 2


@dataclass(frozen=True, slots=True)
class Port(Mapping[str, Point | Vector]):
    center: Point
    tangent: Vector

    def __getitem__(self, key: str) -> Point | Vector:
        if key == "center":
            return self.center
        if key == "tangent":
            return self.tangent
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        yield "center"
        yield "tangent"

    def __len__(self) -> int:
        return 2


@dataclass(frozen=True, slots=True)
class CanvasLayout:
    scale: float
    cx: float
    cy: float
    canvas_w: int
    canvas_h: int

    def __post_init__(self) -> None:
        if self.scale <= 0:
            raise ValueError("scale must be positive")
        if self.canvas_w <= 0:
            raise ValueError("canvas_w must be positive")
        if self.canvas_h <= 0:
            raise ValueError("canvas_h must be positive")

    def __getitem__(self, key: str) -> float | int:
        return getattr(self, key)


class SVGCanvas:

    def __init__(
        self,
        scale: float = 1.0,
        width: int = 5000,
        height: int = 5000,
        pipe_stroke: str = "black",
    ) -> None:
        if scale <= 0:
            raise ValueError("scale must be positive")
        if width <= 0:
            raise ValueError("width must be positive")
        if height <= 0:
            raise ValueError("height must be positive")

        self.scale = scale
        self.width = width
        self.height = height

        self._lines: list[str] = []

        self.pipe_fill = "white"
        self.pipe_stroke = pipe_stroke
        self.sw: float = 3 * scale
        self.dsw: float = 1.5 * scale

    @property
    def centre(self) -> Point:
        return Point(self.width / 2, self.height / 2)

    def _require_positive(self, value: float, name: str) -> None:
        if value <= 0:
            raise ValueError(f"{name} must be positive")

    def mm_to_px(self, v: float) -> float:
        return v * self.scale

    def _unit(self, vx: float, vy: float) -> tuple[float, float]:
        length = math.hypot(vx, vy)
        if length == 0:
            raise ValueError("Zero-length vector")
        return (vx / length, vy / length)

    def make_port(self, x: float, y: float, tx: float, ty: float) -> Port:
        tx, ty = self._unit(tx, ty)
        return Port(center=Point(x, y), tangent=Vector(tx, ty))

    def begin_group(self, transform: str) -> None:
        self._lines.append(f'<g transform="{transform}">')

    def end_group(self) -> None:
        self._lines.append("</g>")

    @contextmanager
    def group(self, transform: str) -> Iterator[None]:
        self.begin_group(transform)
        try:
            yield
        finally:
            self.end_group()

    def pipe_from_port(self, port: Port, length: float, diameter: float) -> Port:
        self._require_positive(length, "length")
        self._require_positive(diameter, "diameter")

        x, y = port.center
        tx, ty = port.tangent

        x2 = x + tx * length
        y2 = y + ty * length

        r = diameter / 2
        nx = -ty
        ny = tx

        x1_top = x + nx * r
        y1_top = y + ny * r
        x1_bot = x - nx * r
        y1_bot = y - ny * r
        x2_top = x2 + nx * r
        y2_top = y2 + ny * r
        x2_bot = x2 - nx * r
        y2_bot = y2 - ny * r

        self._lines.append(
            f'<polygon points="'
            f'{x1_top:.2f},{y1_top:.2f} '
            f'{x2_top:.2f},{y2_top:.2f} '
            f'{x2_bot:.2f},{y2_bot:.2f} '
            f'{x1_bot:.2f},{y1_bot:.2f}" '
            f'fill="{self.pipe_fill}" stroke="{self.pipe_stroke}" stroke-width="2"/>'
        )

        self._lines.append(
            f'<line x1="{x:.2f}" y1="{y:.2f}" '
            f'x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="grey" '
            f'stroke-width="1" '
            f'stroke-dasharray="6,6" '
            f'stroke-opacity="0.5"/>'
        )
        return self.make_port(x2, y2, tx, ty)

    def place_fitting_local(self, port: Port, draw_func) -> list[Port]:
        x, y = port.center
        tx, ty = port.tangent

        angle = math.degrees(math.atan2(ty, tx))

        with self.group(f"translate({x},{y}) rotate({angle})"):
            local_ports = draw_func()

        cos_a = math.cos(math.radians(angle))
        sin_a = math.sin(math.radians(angle))

        global_ports: list[Port] = []
        for p in local_ports:
            lx, ly = p.center
            ltx, lty = p.tangent

            gx = x + lx * cos_a - ly * sin_a
            gy = y + lx * sin_a + ly * cos_a
            gtx = ltx * cos_a - lty * sin_a
            gty = ltx * sin_a + lty * cos_a

            global_ports.append(self.make_port(gx, gy, gtx, gty))

        return global_ports

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
        self._require_positive(w, "w")
        self._require_positive(h, "h")

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
        self._require_positive(r, "r")

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

    def path(
        self,
        d: str,
        stroke: str = "#000",
        stroke_w: float | None = None,
        fill: str = "none",
        dasharray: str | None = None,
        stroke_opacity: float | None = None,
        stroke_linecap: str | None = None,
    ) -> None:
        stroke_w = stroke_w if stroke_w is not None else self.sw
        stroke_width = f"{int(stroke_w)}" if float(stroke_w).is_integer() else f"{stroke_w:.2f}"
        attrs = [
            f'd="{d}"',
            f'stroke="{stroke}"',
            f'stroke-width="{stroke_width}"',
        ]
        if dasharray is not None:
            attrs.append(f'stroke-dasharray="{dasharray}"')
        if stroke_opacity is not None:
            attrs.append(f'stroke-opacity="{stroke_opacity}"')
        attrs.append(f'fill="{fill}"')
        if stroke_linecap is not None:
            attrs.append(f'stroke-linecap="{stroke_linecap}"')
        self._lines.append(f"<path {' '.join(attrs)}/>")

    def polygon(
        self,
        points: list[tuple[float, float]] | str,
        fill: str | None = None,
        stroke: str | None = None,
        stroke_w: float | None = None,
    ) -> None:
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
        transform: str | None = None,
    ) -> None:
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
        if transform is not None:
            attrs.append(f'transform="{transform}"')

        self._lines.append(f"<text {' '.join(attrs)}>{escape(content, quote=False)}</text>")

    def draw_ground_level(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        spacing: float = 20,
    ) -> None:
        self._require_positive(spacing, "spacing")
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
        self._lines.append(
            f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{(x2-x1):.2f}" height="{(y2-y1):.2f}" '
            f'fill="none" stroke="#000" stroke-width="{self.dsw:.2f}"/>'
        )

        cx = (x1 + x2) / 2
        self._lines.append(
            f'<line x1="{cx:.2f}" y1="{y1:.2f}" x2="{cx:.2f}" y2="{y2:.2f}" '
            f'stroke="#000" stroke-dasharray="5,5" stroke-width="{self.dsw:.2f}"/>'
        )

    def to_svg(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">\n'
            + "\n".join(self._lines)
            + "\n</svg>"
        )

    def save(self, filename: str = "output.svg") -> None:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.to_svg())


__all__ = [
    "CanvasLayout",
    "Point",
    "Port",
    "SVGCanvas",
    "Vector",
]
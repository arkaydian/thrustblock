from __future__ import annotations

import math
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from typing import Protocol

try:
    from app.utils.svg.canvas import Point, Port, Vector
except ModuleNotFoundError:
    _canvas_spec = spec_from_file_location(
        "svgwriter_geometry_canvas_module",
        Path(__file__).resolve().parent / "canvas.py",
    )
    assert _canvas_spec is not None
    _canvas_module = module_from_spec(_canvas_spec)
    assert _canvas_spec.loader is not None
    sys.modules[_canvas_spec.name] = _canvas_module
    _canvas_spec.loader.exec_module(_canvas_module)
    Point = _canvas_module.Point
    Port = _canvas_module.Port
    Vector = _canvas_module.Vector


class AnchorGeometry(Protocol):
    @property
    def anchor_point(self) -> Point:
        ...


def _rotate_components(x: float, y: float, angle_deg: float) -> tuple[float, float]:
    theta = math.radians(angle_deg)
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)
    return (
        x * cos_theta - y * sin_theta,
        x * sin_theta + y * cos_theta,
    )


def rotate_point(point: Point, angle_deg: float) -> Point:
    x, y = _rotate_components(point.x, point.y, angle_deg)
    return Point(x, y)


def rotate_vector(vector: Vector, angle_deg: float) -> Vector:
    x, y = _rotate_components(vector.x, vector.y, angle_deg)
    return Vector(x, y)


def translate_point(point: Point, translation: Vector) -> Point:
    return Point(point.x + translation.x, point.y + translation.y)


def scale_vector(vector: Vector, magnitude: float) -> Vector:
    return Vector(vector.x * magnitude, vector.y * magnitude)


def vector_between(start: Point, end: Point) -> Vector:
    return Vector(end.x - start.x, end.y - start.y)


def add_vector(point: Point, vector: Vector) -> Point:
    return Point(point.x + vector.x, point.y + vector.y)


@dataclass(frozen=True, slots=True)
class FittingPlacement:
    orientation_deg: float
    translation: Vector

    @classmethod
    def anchor_at(
        cls,
        local_anchor: Point,
        target: Point,
        orientation_deg: float,
    ) -> FittingPlacement:
        rotated_anchor = rotate_point(local_anchor, orientation_deg)
        translation = vector_between(rotated_anchor, target)
        return cls(orientation_deg=orientation_deg, translation=translation)

    def transform_point(self, point: Point) -> Point:
        return translate_point(rotate_point(point, self.orientation_deg), self.translation)

    def transform_vector(self, vector: Vector) -> Vector:
        return rotate_vector(vector, self.orientation_deg)

    def transform_port(self, port: Port) -> Port:
        return Port(
            center=self.transform_point(port.center),
            tangent=self.transform_vector(port.tangent),
        )

    def svg_transform(self) -> str:
        return f"translate({self.translation.x},{self.translation.y}) rotate({self.orientation_deg})"


@dataclass(frozen=True, slots=True)
class BendGeometry:
    radius_px: float
    angle_deg: float
    arc_center: Point
    inlet_point: Point
    outlet_point: Point
    inlet_tangent: Vector
    outlet_tangent: Vector
    arc_midpoint: Point
    anchor_point: Point
    inside_radial_direction: Vector
    outside_radial_direction: Vector
    resultant_thrust_vector: Vector
    normalized_resultant_thrust_vector: Vector

    @classmethod
    def from_params(cls, radius_px: float, angle_deg: float) -> BendGeometry:
        if radius_px <= 0:
            raise ValueError("radius_px must be positive")

        theta = math.radians(angle_deg)
        mid_theta = theta / 2.0

        arc_center = Point(0.0, -radius_px)
        inlet_point = Point(0.0, 0.0)
        outlet_point = Point(
            radius_px * math.sin(theta),
            -radius_px * (1.0 - math.cos(theta)),
        )

        inlet_tangent = Vector(1.0, 0.0)
        outlet_tangent = Vector(math.cos(theta), -math.sin(theta))

        arc_midpoint = Point(
            radius_px * math.sin(mid_theta),
            -radius_px * (1.0 - math.cos(mid_theta)),
        )

        outside_radial_direction = Vector(math.sin(mid_theta), math.cos(mid_theta))
        inside_radial_direction = Vector(-outside_radial_direction.x, -outside_radial_direction.y)

        resultant_thrust_vector = Vector(
            inlet_tangent.x - outlet_tangent.x,
            inlet_tangent.y - outlet_tangent.y,
        )
        thrust_len = math.hypot(resultant_thrust_vector.x, resultant_thrust_vector.y)
        if thrust_len == 0:
            normalized_thrust = Vector(0.0, 0.0)
        else:
            normalized_thrust = Vector(
                resultant_thrust_vector.x / thrust_len,
                resultant_thrust_vector.y / thrust_len,
            )

        return cls(
            radius_px=radius_px,
            angle_deg=angle_deg,
            arc_center=arc_center,
            inlet_point=inlet_point,
            outlet_point=outlet_point,
            inlet_tangent=inlet_tangent,
            outlet_tangent=outlet_tangent,
            arc_midpoint=arc_midpoint,
            anchor_point=arc_midpoint,
            inside_radial_direction=inside_radial_direction,
            outside_radial_direction=outside_radial_direction,
            resultant_thrust_vector=resultant_thrust_vector,
            normalized_resultant_thrust_vector=normalized_thrust,
        )

    @property
    def inlet_port(self) -> Port:
        return Port(self.inlet_point, self.inlet_tangent)

    @property
    def outlet_port(self) -> Port:
        return Port(self.outlet_point, self.outlet_tangent)

    @property
    def path_d(self) -> str:
        return (
            f"M {self.inlet_point.x:.0f} {self.inlet_point.y:.0f} "
            f"A {self.radius_px:.2f} {self.radius_px:.2f} "
            f"0 0 0 "
            f"{self.outlet_point.x:.2f} {self.outlet_point.y:.2f}"
        )


__all__ = [
    "AnchorGeometry",
    "BendGeometry",
    "FittingPlacement",
    "add_vector",
    "rotate_point",
    "rotate_vector",
    "scale_vector",
    "translate_point",
    "vector_between",
]
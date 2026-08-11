from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.civeng1.calculations.thrust_block_calculation import FittingCalculation
    from app.utils.svgwriter import DrawingOptions, SVGDrawing


class SVGWriterNotRegisteredError(LookupError):
    pass


class SVGWriterRegistrationError(ValueError):
    pass


class SVGWriter(Protocol):
    @classmethod
    def build(
        cls,
        calculation: "FittingCalculation",
        options: "DrawingOptions | None" = None,
    ) -> list["SVGDrawing"]:
        ...


SVG_WRITERS: dict[type[object], type[SVGWriter]] = {}
_DEFAULTS_REGISTERED = False


def register_svg_writer(
    calculation_type: type[object],
    writer_type: type[SVGWriter],
) -> None:
    if calculation_type in SVG_WRITERS:
        raise SVGWriterRegistrationError(
            f"An SVG writer is already registered for {calculation_type.__name__}"
        )
    SVG_WRITERS[calculation_type] = writer_type


def _ensure_default_svg_writers() -> None:
    global _DEFAULTS_REGISTERED
    if _DEFAULTS_REGISTERED:
        return

    from app.civeng1.calculations.thrust_block_calculation import (
        BlankEndThrustBlock,
        HorizontalBendThrustBlock,
        TaperThrustThrustBlock,
        VerticalUpturnBendThrustBlock,
        VerticalDownturnBendThrustBlock,
    )
    from app.utils.svgwriter import (
        BlankEndSVGWriter,
        HorizontalBendSVGWriter,
        TaperSVGWriter,
        VerticalBendSVGWriter,
        VerticalDownturnBendSVGWriter,
    )

    register_svg_writer(HorizontalBendThrustBlock, HorizontalBendSVGWriter)
    register_svg_writer(VerticalUpturnBendThrustBlock, VerticalBendSVGWriter)
    register_svg_writer(VerticalDownturnBendThrustBlock, VerticalDownturnBendSVGWriter)
    register_svg_writer(BlankEndThrustBlock, BlankEndSVGWriter)
    register_svg_writer(TaperThrustThrustBlock, TaperSVGWriter)
    _DEFAULTS_REGISTERED = True


def get_svg_writer(calculation_type: type[object]) -> type[SVGWriter]:
    _ensure_default_svg_writers()
    try:
        return SVG_WRITERS[calculation_type]
    except KeyError as error:
        raise SVGWriterNotRegisteredError(
            f"No SVG writer is registered for {calculation_type.__name__}"
        ) from error


__all__ = [
    "SVGWriter",
    "SVGWriterNotRegisteredError",
    "SVGWriterRegistrationError",
    "SVG_WRITERS",
    "get_svg_writer",
    "register_svg_writer",
]
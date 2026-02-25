from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple

from abc import ABC

# --- Enums ---

class ConcreteType(Enum):
    """Types of concrete."""
    UNREINFORCED = auto()
    REINFORCED = auto()

HorizontalThrustCheck = Tuple[str, float]

# --- Utilities (consider moving to utils.py) ---

def calc_height(diameter: float) -> float:
    """
    Calculates thrust block height in accordance with Ciria C816, Section 7.2.2.

    Args:
        diameter (float): Outside diameter of the pipe.

    Returns:
        float: Height of the thrust block.
    """
    return max(0.2, diameter / 2) * 2 + diameter

# --- Data Classes ---

@dataclass
class Concrete(ABC):
    """Properties of concrete."""
    # Optionally add strength properties if needed
    # compressive_strength: Optional[float] = None  # MPa
    # tensile_strength: Optional[float] = None  # MPa (for reinforced)

@dataclass
class ThrustBlock(Concrete):
    """
    Thrust block properties.

    Args:
        user_height (float): Height of the block.
        user_width (float): Width of the block.
        user_length (float): Length of the block.
        user_depth_block (float): Depth to block base.
    """
    height: float
    width: float
    length: float
    depth: float
    user_effective_depth: Optional[float]
    user_effective_height: Optional[float]
    reinforced_concrete_unit_weight: float = 25

    def __post_init__(self):
        # Example validation
        if self.height <= 0:
            raise ValueError("user_height must be positive")
        if self.width <= 0:
            raise ValueError("user_width must be positive")
        if self.length <= 0:
            raise ValueError("user_length must be positive")
        if self.depth <= 0:
            raise ValueError("user_depth_block must be positive")
        # if not isinstance(self.soil, Soil):
        #     raise TypeError("soil must be an instance of Soil or its subclass")

def create_thrust_block(
    height: float,
    width: float,
    length: float,
    depth: float,
    user_effective_depth : float | None = None,
    user_effective_height: float | None = None
) -> ThrustBlock:
    """
    Factory function to create a ThrustBlock instance with validation.
    """
    return ThrustBlock(

        height=height, 
        width=width, 
        length=length,
        depth=depth,
        user_effective_depth=user_effective_depth,
        user_effective_height=user_effective_height)

if __name__ == "__main__":
    ...
from enum import Enum
from dataclasses import dataclass

class SoilCategory(Enum):
    """
    Soil categories (CIRIA C816 / BS EN ISO 14688-2:2018).
    """
    # VERY_COARSE = "Very Coarse"
    COARSE = "Coarse"
    FINE = "Fine"
    ROCK = "Rock"
    ORGANIC = "Organic"
    ANTHROPOGENIC = "Anthropogenic"

class SoilType(Enum):
    """
    Soil types with their associated categories.
    """
    # BOULDER = ("Boulder", SoilCategory.VERY_COARSE)
    # COBBLE = ("Cobble", SoilCategory.VERY_COARSE)
    GRAVEL = ("Gravel", SoilCategory.COARSE)
    SAND = ("Sand", SoilCategory.COARSE)
    # SILT = ("Silt", SoilCategory.FINE)
    CLAY = ("Clay", SoilCategory.FINE)
    # CEMENT = ("Cement", SoilCategory.ROCK)

    def __init__(self, label, category):
        self.label = label
        self.category = category

class SoilConsistency(Enum):
    """
    Unified soil consistencies for coarse and fine soils. More to be added later
    """
    # Coarse
    # VERY_LOOSE = ("Very Loose", SoilCategory.COARSE)
    LOOSE = ("Loose", SoilCategory.COARSE)
    MEDIUM_DENSE = ("Medium Dense", SoilCategory.COARSE)
    DENSE = ("Dense", SoilCategory.COARSE)
    # VERY_DENSE = ("Very Dense", SoilCategory.COARSE)
    # CEMENTED = ("Cemented", SoilCategory.COARSE)
    # Fine
    # VERY_SOFT = ("Very Soft", SoilCategory.FINE)
    SOFT = ("Soft", SoilCategory.FINE)
    FIRM = ("Firm", SoilCategory.FINE)
    STIFF = ("Stiff", SoilCategory.FINE)
    # VERY_STIFF = ("Very Stiff", SoilCategory.FINE)
    # NONE = ("None", SoilCategory.FINE)  # For silts/peat with no standard consistency

    def __init__(self, label, category):
        self.label = label
        self.category = category

class SoilDesignClass(Enum):
    """
    Soil design classes (C816 Table 2.1).
    """
    CLASS_1 = 1
    CLASS_2 = 2
    CLASS_3 = 3


class WaterCondition(Enum):
    """
    Water conditions for soil unit weight (C816 Table 3.5).
    """
    ABOVE_WATER = "Above Water"
    BELOW_WATER = "Below Water"

@dataclass(frozen=True)
class BearingCapacityCoefficients:
    n_c: float
    n_y: float
    n_q: float
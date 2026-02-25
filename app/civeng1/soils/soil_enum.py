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

class EmbedmentCategory(Enum):
    """
    Docstring for CoarseEmbedmentClass To Be implemented
    """
    COARSE = "coarse"
    CLAY = "clay"

    @property
    def label_capitalized(self):
        # Capitalize first letter, preserve rest
        if not self.value:
            return self.value
        return self.value[0].upper() + self.value[1:]

class EmbedmentClass(Enum):
    """
    Docstring for CoarseEmbedmentClass To Be implemented
    """
    S_ONE = ("s1", EmbedmentCategory.COARSE)
    S_TWO = ("s2", EmbedmentCategory.COARSE)
    S_THREE = ("s3", EmbedmentCategory.COARSE)
    S_FOUR = ("s4", EmbedmentCategory.COARSE)
    S_FIVE = ("s5", EmbedmentCategory.CLAY)

    def __init__(self, label, category):
        self.label = label
        self.category = category

    @property
    def label_capitalized(self):
        # Capitalize only the first character, leave the rest as-is
        if not self.label:
            return self.label
        return self.label[0].upper() + self.label[1:]
    
    @classmethod
    def from_frontend(cls, code: str) -> "EmbedmentClass":
        if not isinstance(code, str):
            raise TypeError("code must be a string")
        key = code.strip()

        # 1) Try exact frontend label match (e.g. "s1", "S2")
        for member in cls:
            if member.label.lower() == key.lower():
                return member  # return the enum member, not member.value
        raise ValueError(f"Unknown embedment code: {code!r}")

# class EmbedmentCompactness(Enum):
#     UNCOMPACTED = ("uncompacted", EmbedmentCategory.COARSE)
#     COMPACTED_EIGHTY_FIVE = ("compacted sands and gravels (85%)", EmbedmentCategory.COARSE)
#     COMPACTED_NINETY = ("compacted sands and gravels (95%)", EmbedmentCategory.COARSE)
#     COMPACTED_CLAY_EIGHTY_FIVE = ("compacted clays (85%)", EmbedmentCategory.CLAY)
#     COMPACTED_CLAY_NINETY = ("compacted clays (90%)", EmbedmentCategory.CLAY)
    
#     def __init__(self, label, category):
#         self.label = label
#         self.category = category




@dataclass(frozen=True)
class BearingCapacityCoefficients:
    n_c: float
    n_y: float
    n_q: float
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

    @classmethod
    def from_string(cls, soil_type: str) -> "SoilType":
        """
        Parse soil type string to SoilType enum.
        
        Args:
            soil_type: Soil type label (e.g., 'Gravel', 'Sand', 'Clay')
        
        Returns:
            Corresponding SoilType enum member
        
        Raises:
            ValueError: If soil type is not recognized
        """
        for member in cls:
            if member.label.lower() == soil_type.lower():
                return member
        raise ValueError(
            f"Unknown soil type: {soil_type!r}. "
            f"Valid types: {', '.join(m.label for m in cls)}"
        )

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

    @classmethod
    def from_string(cls, consistency: str) -> "SoilConsistency":
        """
        Parse soil consistency string to SoilConsistency enum.
        
        Args:
            consistency: Soil consistency label (e.g., 'Loose', 'Dense', 'Soft')
        
        Returns:
            Corresponding SoilConsistency enum member
        
        Raises:
            ValueError: If consistency is not recognized
        """
        for member in cls:
            if member.label.lower() == consistency.lower():
                return member
        raise ValueError(
            f"Unknown soil consistency: {consistency!r}. "
            f"Valid consistencies: {', '.join(m.label for m in cls)}"
        )

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

    @classmethod
    def from_string(cls, condition: str) -> "WaterCondition":
        """
        Parse water condition string to WaterCondition enum.
        
        Args:
            condition: Water condition string (case-insensitive)
        
        Returns:
            Corresponding WaterCondition enum member
        
        Raises:
            ValueError: If condition is not recognized
        """
        for member in cls:
            if member.value.lower() == condition.lower():
                return member
        raise ValueError(
            f"Unknown water condition: {condition!r}. "
            f"Valid values: {', '.join(m.value for m in cls)}"
        )

class EmbedmentCategory(Enum):
    """
    Embedment categories for pipe backfill materials (CIRIA C816 Table 3.3).
    """
    COARSE = "coarse"
    CLAY = "clay"

    @property
    def label_capitalized(self):
        """Return the category value with first letter capitalized."""
        return self.value.capitalize()

class EmbedmentClass(Enum):
    """
    Embedment classes for pipe backfill materials (CIRIA C816 Table 3.3).
    Classes S1-S4 are coarse materials, S5 is clay.
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
        """Return the embedment class label with first letter capitalized."""
        return self.label.capitalize()
    
    @classmethod
    def from_frontend(cls, code: str) -> "EmbedmentClass":
        """
        Parse frontend embedment code string to EmbedmentClass enum.
        
        Args:
            code: Embedment code string (e.g., 's1', 'S2', 's3')
        
        Returns:
            Corresponding EmbedmentClass enum member
        
        Raises:
            TypeError: If code is not a string
            ValueError: If code is not recognized
        """
        if not isinstance(code, str):
            raise TypeError(f"code must be a string, got {type(code).__name__}")
        
        key = code.strip().lower()
        
        # Try exact frontend label match
        for member in cls:
            if member.label.lower() == key:
                return member
        
        raise ValueError(f"Unknown embedment code: {code!r}. Valid codes: {', '.join(m.label for m in cls)}")


@dataclass(frozen=True)
class BearingCapacityCoefficients:
    n_c: float
    n_y: float
    n_q: float
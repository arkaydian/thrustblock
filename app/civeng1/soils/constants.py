from .soil_enum import *
from typing import Dict, Any

# --- Soil Properties Data from CIRIA C816, Table 3.2 & 3.8 ---
SOIL_PROPERTIES: Dict[SoilCategory, Dict[SoilConsistency, Dict[str, Any]]] = {
    SoilCategory.COARSE: {
        SoilConsistency.LOOSE:     {"cohesion": 0, "friction_angle": (0, 30), "soil_passive_resistance_factor": (3.5, 5.0), "soil_sliding_resistance_factor": (2.5, 3.0)},
        SoilConsistency.MEDIUM_DENSE: {"cohesion": 0, "friction_angle": (30, 36), "soil_passive_resistance_factor": (2.5, 3.5), "soil_sliding_resistance_factor": (2.0, 2.5)},
        SoilConsistency.DENSE:     {"cohesion": 0, "friction_angle": (36, 41), "soil_passive_resistance_factor": (1.5, 2.5), "soil_sliding_resistance_factor": (1.5, 2.0)},
    },
    SoilCategory.FINE: {
        SoilConsistency.SOFT:      {"undrained_shear_strength": (20, 40), "soil_passive_resistance_factor": (4.0, 5.0), "soil_sliding_resistance_factor": (2.5, 3)},
        SoilConsistency.FIRM:      {"undrained_shear_strength": (40, 75), "soil_passive_resistance_factor": (3.0, 4.0), "soil_sliding_resistance_factor": (2.0, 2.5)},
        SoilConsistency.STIFF:     {"undrained_shear_strength": (75, 150), "soil_passive_resistance_factor": (2.0, 3.0), "soil_sliding_resistance_factor": (1.5, 2.0)},
    }
}

# --- Embedment Properties from CIRIA C816, Table 3.3 & 3.9 ---
# Note: None values indicate invalid combinations of embedment class and compaction type
SOIL_EMBEDMENT_PROPERTIES: Dict[EmbedmentCategory, Dict[EmbedmentClass, Dict[str, Any]]] = {
    EmbedmentCategory.COARSE : {
        EmbedmentClass.S_ONE: {
            "friction_angle_reduction": 0.8,
            "uncompacted_process_gravels": {
                "embedment_sliding_resistance_factor": 2.5,
                "effective_angle_shearing_resistance": 32
            },
            "compacted_sand_and_gravels_eighty_five": {      
                "embedment_sliding_resistance_factor": None,
                "effective_angle_shearing_resistance": None
            },
            "compacted_sand_and_gravels_ninety": {
            "embedment_sliding_resistance_factor": None,
                "effective_angle_shearing_resistance": None
            },
        },
        EmbedmentClass.S_TWO: {
            "friction_angle_reduction": 0.8,
            "uncompacted_process_gravels": {
                "embedment_sliding_resistance_factor": 2.5,
                "effective_angle_shearing_resistance": 32
            },
            "compacted_sand_and_gravels_eighty_five": {      
                "embedment_sliding_resistance_factor": 2,
                "effective_angle_shearing_resistance": 36
            },
            "compacted_sand_and_gravels_ninety": {
                "embedment_sliding_resistance_factor": 2,
                "effective_angle_shearing_resistance": 38
            },
        },
        EmbedmentClass.S_THREE: {
            "friction_angle_reduction": 0.8,
            "uncompacted_process_gravels": {
                "embedment_sliding_resistance_factor": None,
                "effective_angle_shearing_resistance": None
            },
            "compacted_sand_and_gravels_eighty_five": {      
                "embedment_sliding_resistance_factor": 2,
                "effective_angle_shearing_resistance": 36
            },
            "compacted_sand_and_gravels_ninety": {
                "embedment_sliding_resistance_factor": 2,
                "effective_angle_shearing_resistance": 38
            },
        },
        EmbedmentClass.S_FOUR: {
            "friction_angle_reduction": 0.75,
            "uncompacted_process_gravels": {
                "embedment_sliding_resistance_factor": None,
                "effective_angle_shearing_resistance": None
            },
            "compacted_sand_and_gravels_eighty_five": {      
                "embedment_sliding_resistance_factor": 2,
                "effective_angle_shearing_resistance": 33
            },
            "compacted_sand_and_gravels_ninety": {
                "embedment_sliding_resistance_factor": 2,
                "effective_angle_shearing_resistance": 34
            },
        },
    },
    EmbedmentCategory.CLAY:
    {
        EmbedmentClass.S_FIVE: {
            "representative_adhesion": {
                "soft_clay": 20,
                "firm_stiff_clay": 30
            },
            "compacted_clays_eighty_five" : {
                "embedment_sliding_resistance_factor": 4,
                "adhesion_reduction_factor": 0.5
            },
            "compacted_clays_ninety" : {
                "embedment_sliding_resistance_factor": 3.5,
                "adhesion_reduction_factor": 0.7
            },
        }
    }
}

# --- Soil unit weights in kN/m³ from C816 Table 3.5 ---
SOIL_UNIT_WEIGHT: Dict[SoilType, Dict[SoilConsistency, Dict[WaterCondition, float]]] = {
    SoilType.GRAVEL: {
        SoilConsistency.LOOSE:     {WaterCondition.ABOVE_WATER: 17.5, WaterCondition.BELOW_WATER: 19.5},
        SoilConsistency.MEDIUM_DENSE: {WaterCondition.ABOVE_WATER: 18.5, WaterCondition.BELOW_WATER: 20.5},
        SoilConsistency.DENSE:     {WaterCondition.ABOVE_WATER: 19.5, WaterCondition.BELOW_WATER: 21.5},
    },
    SoilType.SAND: {
        SoilConsistency.LOOSE:     {WaterCondition.ABOVE_WATER: 16.5, WaterCondition.BELOW_WATER: 19.0},
        SoilConsistency.MEDIUM_DENSE: {WaterCondition.ABOVE_WATER: 17.0, WaterCondition.BELOW_WATER: 19.5},
        SoilConsistency.DENSE:     {WaterCondition.ABOVE_WATER: 18.0, WaterCondition.BELOW_WATER: 20.5},
    },
    # SoilType.SILT: {
    #     SoilConsistency.NONE: {WaterCondition.ABOVE_WATER: 18.0, WaterCondition.BELOW_WATER: 19.5}
    # },
    SoilType.CLAY: {
        SoilConsistency.SOFT:       {WaterCondition.ABOVE_WATER: 17.0, WaterCondition.BELOW_WATER: 17.0},
        SoilConsistency.FIRM:       {WaterCondition.ABOVE_WATER: 18.5, WaterCondition.BELOW_WATER: 18.5},
        SoilConsistency.STIFF:      {WaterCondition.ABOVE_WATER: 20.0, WaterCondition.BELOW_WATER: 20.0},
        # SoilConsistency.VERY_STIFF: {WaterCondition.ABOVE_WATER: 21.0, WaterCondition.BELOW_WATER: 21.0},
    }
}

BEARING_CAPACITY_COEFFICIENTS: Dict[int, BearingCapacityCoefficients] = {
    20: BearingCapacityCoefficients(n_c=15, n_y=3, n_q=6),
    25: BearingCapacityCoefficients(n_c=21, n_y=7, n_q=11),
    30: BearingCapacityCoefficients(n_c=30, n_y=16, n_q=18),
    35: BearingCapacityCoefficients(n_c=46, n_y=37, n_q=33),
    40: BearingCapacityCoefficients(n_c=75, n_y=86, n_q=64),
}


def validate_embedment_property(
    category: EmbedmentCategory,
    embedment_class: EmbedmentClass,
    compaction_key: str,
    property_name: str
) -> Any:
    """
    Validate and retrieve embedment property, raising clear error if combination is invalid.
    
    Args:
        category: Embedment category (COARSE or CLAY)
        embedment_class: Embedment class (S_ONE to S_FIVE)
        compaction_key: Compaction class key (e.g., 'uncompacted_process_gravels')
        property_name: Property to retrieve (e.g., 'embedment_sliding_resistance_factor')
    
    Returns:
        The requested property value
    
    Raises:
        ValueError: If the combination is invalid (None value) or if keys are not found
    """
    try:
        value = SOIL_EMBEDMENT_PROPERTIES[category][embedment_class][compaction_key][property_name]
        if value is None:
            raise ValueError(
                f"Invalid combination: {embedment_class.label} with {compaction_key} "
                f"is not a valid configuration according to CIRIA C816 Table 3.3"
            )
        return value
    except KeyError as e:
        raise ValueError(
            f"Property lookup failed for {category.value} {embedment_class.label}: "
            f"compaction='{compaction_key}', property='{property_name}'"
        ) from e


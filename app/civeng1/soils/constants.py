from .soil_enum import *
# --- Soil Properties Data from CIRIA C816, Table 3.2 & 3.8 ---
SOIL_PROPERTIES = {
    SoilCategory.COARSE: {
        SoilConsistency.LOOSE:     {"cohesion": 0, "friction_angle": (25, 25), "soil_passive_resistance_factor": (3.5, 5.0), "soil_sliding_resistance_factor": (2.5, 3.0)},
        SoilConsistency.MEDIUM_DENSE: {"cohesion": 0, "friction_angle": (30, 36), "soil_passive_resistance_factor": (2.5, 3.5), "soil_sliding_resistance_factor": (2.0, 2.5)},
        SoilConsistency.DENSE:     {"cohesion": 0, "friction_angle": (36, 41), "soil_passive_resistance_factor": (1.5, 2.5), "soil_sliding_resistance_factor": (1.5, 2.0)},
    },
    SoilCategory.FINE: {
        SoilConsistency.SOFT:      {"undrained_shear_strength": (20, 40), "soil_passive_resistance_factor": (4.0, 5.0), "soil_sliding_resistance_factor": (2.5, 3)},
        SoilConsistency.FIRM:      {"undrained_shear_strength": (40, 75), "soil_passive_resistance_factor": (3.0, 4.0), "soil_sliding_resistance_factor": (2.0, 2.5)},
        SoilConsistency.STIFF:     {"undrained_shear_strength": (75, 100), "soil_passive_resistance_factor": (2.0, 3.0), "soil_sliding_resistance_factor": (1.5, 2.0)},
    }
}

# --- Particle size ranges in mm: not used as of now ---
PARTICLE_SIZE_RANGES = {
    SoilType.BOULDER: (200, None),  # > 200 mm
    SoilType.COBBLE: (63, 200),     # 63 mm to 200 mm
    SoilType.GRAVEL: (2, 63),       # 2 mm to 63 mm
    SoilType.SAND: (0.063, 2),      # 0.063 mm to 2 mm
    SoilType.SILT: (0.002, 0.063),  # 0.002 mm to 0.063 mm
    SoilType.CLAY: (0, 0.002),      # < 0.002 mm
}

# --- Soil unit weights in kN/m³ from C816 Table 3.5 ---
SOIL_UNIT_WEIGHT = {
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
    SoilType.SILT: {
        SoilConsistency.NONE: {WaterCondition.ABOVE_WATER: 18.0, WaterCondition.BELOW_WATER: 19.5}
    },
    SoilType.CLAY: {
        SoilConsistency.SOFT:       {WaterCondition.ABOVE_WATER: 17.0, WaterCondition.BELOW_WATER: 17.0},
        SoilConsistency.FIRM:       {WaterCondition.ABOVE_WATER: 18.5, WaterCondition.BELOW_WATER: 18.5},
        SoilConsistency.STIFF:      {WaterCondition.ABOVE_WATER: 20.0, WaterCondition.BELOW_WATER: 20.0},
        SoilConsistency.VERY_STIFF: {WaterCondition.ABOVE_WATER: 21.0, WaterCondition.BELOW_WATER: 21.0},
    }
}

BEARING_CAPACITY_COEFFICIENTS = {
    20: BearingCapacityCoefficients(n_c=15, n_y=3, n_q=6),
    25: BearingCapacityCoefficients(n_c=21, n_y=7, n_q=11),
    30: BearingCapacityCoefficients(n_c=30, n_y=16, n_q=18),
    35: BearingCapacityCoefficients(n_c=46, n_y=37, n_q=33),
    40: BearingCapacityCoefficients(n_c=75, n_y=86, n_q=64),
}

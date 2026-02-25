from .thrust_restraint.thrust_block.controller import ThrustBlockController as ThrustBlock
from .thrust_restraint.anchor_block.controller import AnchorBlockController as AnchorBlock
from .root.controller import Controller as Root
from .root.controller import Project as Project

from viktor import InitialEntity

initial_entities = [
    InitialEntity('Root', name='Thrust Restraint', use_as_start_page=True),
]

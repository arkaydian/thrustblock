from .thrust_restraint.thrust_block.controller import ThrustBlockController as ThrustBlock
from .thrust_restraint.anchor_block.controller import AnchorBlockController as AnchorBlock
from .thrust_root.controller import Controller as ThrustRoot
from .thrust_root.controller import Project as Project

from viktor import InitialEntity

initial_entities = [
    InitialEntity('ThrustRoot', name='Thrust Restraint', use_as_start_page=True),
    InitialEntity('ThrustRoot', name='Soil Embedment')
]

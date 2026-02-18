from .my_folder.controller import ThrustRestraintController as MyFolder
from .thrust_restraint.thrust_block.controller import ThrustBlockController as ThrustBlock
from .thrust_restraint.anchor_block.controller import AnchorBlockController as AnchorBlock
from .civeng1 import hydraulics, soils, structures

from viktor import InitialEntity

initial_entities = [
    InitialEntity('MyFolder', name='My Project'),
]

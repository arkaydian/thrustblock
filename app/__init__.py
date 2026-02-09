from .my_folder.controller import Controller as MyFolder
from .my_entity_type.controller import Controller as MyEntityType
from .civeng1 import hydraulics, soils, structures

from viktor import InitialEntity

initial_entities = [
    InitialEntity('MyFolder', name='My Folder'),
]

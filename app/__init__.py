from viktor import InitialEntity

from .thrust_restraint.thrust_block.controller import (
    ThrustBlockController as ThrustBlock,
)
from .thrust_restraint.anchor_block.controller import (
    AnchorBlockController as AnchorBlock,
)
from .thrust_root.controller import ProjectsRoot
from .thrust_root.controller import Project


initial_entities = [
    InitialEntity(
        "ProjectsRoot",
        name="Projects",
        use_as_start_page=True,
    )
]
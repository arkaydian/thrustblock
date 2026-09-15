from viktor import InitialEntity

from .thrust_restraint.thrust_block.controller import (
    ThrustBlockController as ThrustBlock,
)
from .thrust_restraint.anchor_block.controller import (
    AnchorBlockController as AnchorBlock,
)
from .release_notes.controller import (
    ReleaseNotesController as ReleaseNotes
)
from .documentation.controller import (
    DocumentationController as Documentation
)
from .root.controller import ProjectsRoot, ThrustRestraint, QuickCalc, Project


initial_entities = [
    InitialEntity(
        "ProjectsRoot",
        name="📁 Projects",
    ),
    InitialEntity(
        "QuickCalc",
        name="⚡ Quick Calc",
    ),    
    InitialEntity(
        "ReleaseNotes",
        name="📢 Release Notes",
    ),
    InitialEntity(
        "Documentation",
        name="📚 Documentation",
    ),
]
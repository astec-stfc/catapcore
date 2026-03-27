from pathlib import Path
import os
from typing import Dict, List, Tuple
from catapcore.common.machine.area import MachineArea
from collections import namedtuple

_area_names = []

_machine_areas_tuple = namedtuple("MACHINE_AREAS", _area_names)
MACHINE_AREAS = _machine_areas_tuple(*[MachineArea(name=name) for name in _area_names])
"""
Example usage:

.. code-block:: python

    from catapcore.config import MACHINE_AREAS

    # Accessing fields (example)
    print(MACHINE_AREAS.S02)
    print(MACHINE_AREAS.L02)
"""


LATTICE_LOCATION = os.path.join(
    Path(__file__).parent,
    "lattice",
)

SNAPSHOT_LOCATION = "./snapshots/"

EPICS_TIMEOUT = 0.5


_hardware_types = {}


def _convert_types_to_named_tuple(types: Dict[str, List[str]]) -> Tuple:
    _subtypes = [namedtuple(type_name, types[type_name])(*types[type_name]) for type_name in types]
    _types = namedtuple("TYPES", types.keys())
    return _types(*_subtypes)


TYPES = _convert_types_to_named_tuple(types=_hardware_types)
"""
Example usage:

.. code-block:: python

    from catapcore.config import TYPES

    # Accessing fields (example)
    print(TYPES.MAGNET.QUADRUPOLE)
    print(TYPES.CAVITY.LINAC)
"""

VIRTUAL_PREFIX = "VM-"

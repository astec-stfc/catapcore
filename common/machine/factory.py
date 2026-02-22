"""
catapcore Factory Module

This module defines a base class for grouping together multiple objects of the same hardware type.

Classes:
    - :class:`~catapcore.common.constants.machine.factory.Factory`: Base class for creating\
    multiple :class:`~catapcore.common.machine.hardware.Hardware` objects.
"""

import warnings

from pydantic import ValidationError

from catapcore.common.machine.hardware import Hardware
from catapcore.common.machine.area import MachineArea, _string_to_machine_area
from catapcore.common.machine.pv_utils import StatisticalPV
from catapcore.common.machine.snapshot import Snapshot
from catapcore.common.exceptions import (
    InvalidHardwareSubtype,
    InvalidHardwareType,
    MachineAreaNotFound,
    MachineAreaNotProvided,
    HardwareNameNotFound,
    HardwareNameNotProvided,
)
from ruamel.yaml import YAML
from typing import Any, Dict, List, Tuple, Union, Callable, Type
import os
from pathlib import Path
import catapcore.config as cfg


__all__ = ["Factory"]

def flatten(dictionary: Dict, parent_key: str = "", separator: str = "_") -> Dict:
    """
    Flatten a nested dictionary -- used for expanding the nested `BaseModel` structure.

    Args:
        dictionary (Dict): The dictionary to flatten.
        parent_key (str, optional): The base key to use for the flattened keys. Defaults to "".
        separator (str, optional): The separator to use between keys. Defaults to "_".

    Returns:
        Dict: The flattened dictionary.
    """
    items = []
    for key, value in dictionary.items():
        if isinstance(key, str):
            new_key = parent_key + separator + key if parent_key else key
            if isinstance(value, MutableMapping):
                items.extend(flatten(value, new_key, separator=separator).items())
            else:
                items.append((new_key, value))
    return dict(items)


class Factory:
    """
    Base class for creating multiple  :class:`~catapcore.common.machine.hardware.Hardware` objects.
    """

    def __init__(
        self,
        is_virtual: bool = True,
        lattice_folder: str = None,
        hardware_type: Hardware = None,
        connect_on_creation: bool = False,
        areas: Union[MachineArea, List[MachineArea]] = None,
    ):
        self.is_virtual = is_virtual
        self.lattice_folder = lattice_folder or hardware_type.__name__
        self._hardware_type = hardware_type
        self.connect_on_creation = connect_on_creation
        self.areas = areas
        if cfg.CONFIG_FORMAT == "CATAP":
            self.hardware = self.create_hardware(
                T=hardware_type,
                areas=self.areas,
            )
        elif cfg.CONFIG_FORMAT == "LAURA":
            self.hardware = self.create_hardware_laura(
                T=hardware_type,
                areas=self.areas,
            )
        else:
            raise ValueError(f"Unsupported config format: {cfg.CONFIG_FORMAT}")
        self._current_snapshot = Snapshot(
            hardware=self.hardware,
            hardware_type=self._hardware_type.__name__.lower(),
        )
        # if self.areas:
        #     self.hardware = self.get_hardware_by_area(
        #         self.areas,
        #         with_areas=False,
        #     )

    def _get_config_folder(self) -> str:
        """
        Get the path to the folder containing YAML config files for this hardware type.

        :returns: Config folder path
        :rtype: str
        """
        return f"{cfg.LATTICE_LOCATION}/{self.lattice_folder}"

    def create_hardware(
        self,
        T: Type[Hardware],
        areas: MachineArea | List[MachineArea] = None,
    ) -> Dict[str, Hardware]:
        """
        Instantiate :class:`~catapcore.common.machine.hardware.Hardware` objects.

        :param T: Specific :class:`~catapcore.common.machine.hardware.Hardware` class type
        :param areas: Select only objects in the :class:`~catapcore.common.machine.area.MachineArea` provided
        :type T: Type[Hardware]
        :type areas: Union[MachineArea, List[MachineArea], None]

        :returns: Dictionary of :class:`~catapcore.common.machine.hardware.Hardware` objects
        :rtype: Dict[str, Hardware]
        """
        try:
            files = os.listdir(self._get_config_folder())
        except FileNotFoundError:
            raise InvalidHardwareType(
                f"Could not find hardware type {self._hardware_type.__name__} in "
                + f"lattice [{self._get_config_folder()}].",
            )
        hardware_mappings = {}
        if areas is None:
            # no specific machine areas applied, load everything.
            areas = cfg.MACHINE_AREAS
        if isinstance(areas, str) or isinstance(areas, MachineArea):
            areas = [areas]
        yaml = YAML(typ="safe")
        for file in files:
            with open(
                os.path.join(
                    self._get_config_folder(),
                    file,
                ),
                "r",
            ) as f:
                settings = dict(yaml.load(f))  # , Loader=yamlcore.CoreLoader))
                name = Path(file).stem
                try:
                    hardware_area = MachineArea(
                        name=settings["properties"]["machine_area"]
                    )
                    if any(
                        [
                            hardware_area.name
                            == _string_to_machine_area(area=area).name
                            for area in areas
                        ]
                    ):
                        hardware_mappings[name] = T(
                            is_virtual=self.is_virtual,
                            connect_on_creation=self.connect_on_creation,
                            **settings,
                        )
                except KeyError:
                    raise MachineAreaNotProvided(
                        f"Could not find machine area property for {name} in {file}",
                    )
        hardware_mappings = {
            name: hardware
            for name, hardware in sorted(
                hardware_mappings.items(),
                key=lambda item: item[1],
            )
        }
        return hardware_mappings

    def create_hardware_laura(
        self,
        T: Type[Hardware],
        areas: MachineArea | List[MachineArea] = None,
    ) -> Dict[str, Hardware]:
        """
        Instantiate :class:`~catapcore.common.machine.hardware.Hardware` objects.

        :param T: Specific :class:`~catapcore.common.machine.hardware.Hardware` class type
        :param areas: Select only objects in the :class:`~catapcore.common.machine.area.MachineArea` provided
        :type T: Type[Hardware]
        :type areas: Union[MachineArea, List[MachineArea], None]

        :returns: Dictionary of :class:`~catapcore.common.machine.hardware.Hardware` objects
        :rtype: Dict[str, Hardware]
        """
        hardware_type = T.__name__
        elems = {
            k: v
            for k, v in cfg.LAURA_LATTICE.elements.items()
            if v.hardware_class == hardware_type
            or v.hardware_type == hardware_type
            or v.__class__.model_fields["hardware_type"].alias == hardware_type
            or v.__class__.model_fields["hardware_class"].alias == hardware_type
        }
        hardware_mappings = {}
        if areas is None:
            # no specific machine areas applied, load everything.
            areas = cfg.MACHINE_AREAS
        if isinstance(areas, str) or isinstance(areas, MachineArea):
            areas = [areas]
        for name, elem in elems.items():
            if elem.controls is not None:
                try:
                    hardware_area = MachineArea(name=elem.machine_area)
                    if any(
                        [
                            hardware_area.name
                            == _string_to_machine_area(area=area).name
                            for area in areas
                        ]
                    ):
                        hardware_mappings[name] = T(
                            is_virtual=self.is_virtual,
                            connect_on_creation=self.connect_on_creation,
                            controls_information=elem.controls.model_dump(),
                            properties=flatten(elem.model_dump()),
                        )
                except KeyError:
                    raise MachineAreaNotProvided(
                        f"Could not find machine area property for {name} in LAURA lattice.",
                    )
                except ValidationError:
                    print(f"Validation error for {elem.name} in LAURA lattice")
                    raise
        hardware_mappings = {
            name: hardware
            for name, hardware in sorted(
                hardware_mappings.items(),
                key=lambda item: item[1],
            )
        }
        return hardware_mappings

    def _name_exists(self, name: str = None) -> Tuple[bool, Hardware]:
        """
        Check if hardware name exists in the Factory.

        :param name: Name of :class:`~catapcore.common.machine.hardware.Hardware` object

        :returns: True if name exists
        :rtype: Tuple[bool, Hardware]
        """
        if name:
            if name in self.hardware:
                return True, self.hardware[name]
            for _, component in self.hardware.items():
                if name in component.aliases:
                    return True, component
        return False, None

    def _get_by_area(
        self,
        area: MachineArea = None,
        with_areas: bool = True,
    ) -> Dict[str, Hardware]:
        """Filter the hardware dictionary by machine area
        (example areas can be found in :mod:`~catapcore.common.constants.areas`).
        Using with_areas arg returns a dictionary with/without the areas
        as keys.

        :param area: Machine area
        :param with_areas: Returns a dictionary with the areas as keys if true
        :type area: :class:`~catapcore.common.machine.area.MachineArea`
        :type with_areas: bool

        :returns: Dictionary of hardware by area
        :rtype: Dict[str, Hardware]
        """
        area_components = {area.name: {}} if with_areas else {}
        if area:
            for _, component in self.hardware.items():
                if area == component.machine_area:
                    if with_areas:
                        area_components[area.name].update(
                            {
                                component.name: component,
                            }
                        )
                    if not with_areas:
                        area_components.update({component.name: component})
        return area_components

    def get_hardware_by_area(
        self,
        machine_areas: Union[
            MachineArea,
            List[MachineArea],
        ] = None,
        with_areas: bool = True,
    ) -> Dict[
        str,
        Dict[
            str,
            Hardware,
        ],
    ]:
        """
        Filter the hardware dictionary by machine area
        (example areas can be found in :mod:`~catapcore.common.constants.areas`).
        Using with_areas arg returns a dictionary with/without the areas
        as keys.

        :param machine_areas: Machine area
        :param with_areas: Returns a dictionary with the areas as keys if true
        :type machine_areas: :class:`~catapcore.common.machine.area.MachineArea`
        :type with_areas: bool

        :returns: Dictionary of hardware by area
        :rtype: Dict[str, Hardware]
        """
        if not machine_areas:
            raise MachineAreaNotProvided(
                f"Please specify the machine areas you want to get {self._hardware_type.__name__}s from."
            )
        if not isinstance(machine_areas, (list, str, MachineArea)):
            raise MachineAreaNotProvided(
                "Please provide a MachineArea or list of MachineAreas to filter by.",
            )
        elif isinstance(machine_areas, (MachineArea, str)):
            # convert arg into MachineArea format
            _area = _string_to_machine_area(machine_areas)
            if _area not in cfg.MACHINE_AREAS:
                raise MachineAreaNotFound(f"Could not find machine area: {_area.name}")
            else:
                return self._get_by_area(_area, with_areas=with_areas)
        elif isinstance(machine_areas, list):
            # convert arg into MachineArea format
            _areas_to_check = [_string_to_machine_area(area) for area in machine_areas]
            component_by_machine_area = {}
            for area in cfg.MACHINE_AREAS:
                if area in _areas_to_check:
                    component_by_machine_area.update(
                        self._get_by_area(
                            area,
                            with_areas=with_areas,
                        ),
                    )
            # Sort the hardware dictionary by machine area order if areas are the keys.
            if with_areas:
                component_by_machine_area = {
                    area: {**hardware}
                    for area, hardware in sorted(
                        component_by_machine_area.items(),
                        key=lambda x: cfg.MACHINE_AREAS.index(
                            _string_to_machine_area(x[0])
                        ),
                    )
                }
            # # Sort the hardware dictionary by hardware order there are no area keys.
            else:
                component_by_machine_area = {
                    name: hardware
                    for name, hardware in sorted(
                        component_by_machine_area.items(),
                        key=lambda item: item[1],
                    )
                }
            return component_by_machine_area

    def _get_by_subtype(
        self,
        subtype: str = None,
        with_subtypes: bool = True,
    ) -> Dict[str, Hardware]:
        """Filter the hardware dictionary by machine area
        (example areas can be found in :mod:`~catapcore.common.constants.areas`).
        Using with_areas arg returns a dictionary with/without the areas
        as keys.

        :param area: Machine area
        :param with_areas: Returns a dictionary with the areas as keys if true
        :type area: :class:`~catapcore.common.machine.area.MachineArea`
        :type with_areas: bool

        :returns: Dictionary of hardware by area
        :rtype: Dict[str, Hardware]
        """
        if subtype is None:
            raise MachineAreaNotProvided(
                f"Please specify the {self._hardware_type.__name__} subtypes you want to get."
            )
        subtype_components = {subtype: {}} if with_subtypes else {}
        if subtype:
            for _, component in self.hardware.items():
                if subtype == component.subtype:
                    if with_subtypes:
                        subtype_components[subtype].update(
                            {
                                component.name: component,
                            }
                        )
                    if not with_subtypes:
                        subtype_components.update({component.name: component})
        return subtype_components

    def get_hardware_by_subtype(
        self,
        subtypes: Union[
            str,
            List[str],
        ] = None,
        with_subtypes: bool = True,
    ) -> Dict[
        str,
        Dict[
            str,
            Hardware,
        ],
    ]:
        """
        Filter the hardware dictionary by machine area
        (example areas can be found in :mod:`~catapcore.common.constants.areas`).
        Using with_areas arg returns a dictionary with/without the areas
        as keys.

        :param machine_areas: Machine area
        :param with_areas: Returns a dictionary with the areas as keys if true
        :type machine_areas: :class:`~catapcore.common.machine.area.MachineArea`
        :type with_areas: bool

        :returns: Dictionary of hardware by area
        :rtype: Dict[str, Hardware]
        """
        try:
            valid_subtypes = cfg._hardware_types[self._hardware_type.__name__.upper()]
        except KeyError:
            warnings.warn(
                message=f"Could not find any subtypes for {self._hardware_type.__name__.upper()}",
                category=InvalidHardwareSubtype,
            )
            return None
        if not subtypes:
            raise InvalidHardwareType(
                f"Please specify the {self._hardware_type.__name__} subtypes you want to get."
            )
        elif not isinstance(
            subtypes,
            (str, list),
        ):
            raise InvalidHardwareType(
                "Please provide a subtype or list of subtypes to filter by."
            )
        elif isinstance(subtypes, str):
            if subtypes not in valid_subtypes:
                raise InvalidHardwareType(
                    f"Could not find {self._hardware_type.__name__} subtype: {subtypes}"
                )
            else:
                return self._get_by_subtype(subtypes, with_subtypes=with_subtypes)
        elif isinstance(subtypes, list):
            # convert arg into MachineArea format
            _types_to_check = subtypes
            component_by_subtype = {}
            for subtype in valid_subtypes:
                if subtype in _types_to_check:
                    component_by_subtype.update(
                        self._get_by_subtype(
                            subtype,
                            with_subtypes=with_subtypes,
                        ),
                    )
            # Sort the hardware dictionary by machine area order if areas are the keys.
            if with_subtypes:
                component_by_subtype = {
                    subtype: {**hardware}
                    for subtype, hardware in sorted(
                        component_by_subtype.items(),
                        key=lambda x: subtypes.index(x[0]),
                    )
                }
            # # Sort the hardware dictionary by hardware order there are no area keys.
            else:
                component_by_subtype = {
                    name: hardware
                    for name, hardware in sorted(
                        component_by_subtype.items(),
                        key=lambda item: item[1],
                    )
                }
            return component_by_subtype

    def get_statistics(
        self,
        names: Union[List[str], str, Hardware, List[Hardware]] = None,
        stats: Union[List[str], str, None] = None,
    ) -> Union[StatisticalPV, Dict[str, StatisticalPV]]:
        """
        Returns all :class:`~catapcore.common.machine.pv_utils.StatisticalPV` objects defined in the :class:`~PVMap`
        for the :class:`~catapcore.common.machine.hardware.Hardware` objects requested

        :param names: Names of :class:`~catapcore.common.machine.hardware.Hardware` objects required (get all if `None`)
        :type names: Union[List[str], str, Hardware, List[Hardware]]
        :param stats: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV`
        objects required (get all if `None`)
        :type stats: Union[List[str], str, None]

        :returns: Statistics objects
        :rtype: Union[StatisticalPV, Dict[str, StatisticalPV]]
        """
        hardware = self.get_hardware(names)
        if isinstance(hardware, dict):
            return {hw.name: hw.get_statistics(stats) for hw in hardware.values()}
        else:
            return hardware.get_statistics(stats)

    def is_buffer_full(
        self,
        names: Union[List[str], str, Hardware, List[Hardware]] = None,
        stats: Union[List[str], str, None] = None,
    ) -> Union[bool, Dict[str, bool], Dict[str, Dict[str, bool]]]:
        """
        Check if :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types is buffering
        for the :class:`~catapcore.common.machine.hardware.Hardware` objects requested.

        :param names: Names of :class:`~catapcore.common.machine.hardware.Hardware` types -- if `None`, start all.
        :type names: Union[str, List[str], None]
        :param stats: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV`
        objects required (start all if `None`)
        :type stats: Union[List[str], str, None]
        :returns: True if the parameter is buffering
        :rtype: bool | Dict[str, bool] | Dict[str, Dict[str, bool]]
        """
        if not names:
            names = self.names
        hardware = self.get_hardware(names)
        if isinstance(hardware, dict):
            return {hw.name: hw.is_buffer_full(stats) for hw in list(hardware.values())}
        else:
            return hardware.is_buffer_full(stats)

    def start_buffering(
        self,
        names: Union[List[str], str, Hardware, List[Hardware]] = None,
        stats: Union[List[str], str, None] = None,
    ):
        """
        Starts buffering :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types
        for the :class:`~catapcore.common.machine.hardware.Hardware` objects requested.

        :param names: Names of :class:`~catapcore.common.machine.hardware.Hardware` types -- if `None`, start all.
        :type names: Union[str, List[str], None]
        :param stats: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV`
        objects required (start all if `None`)
        :type stats: Union[List[str], str, None]
        """
        hardware = self.get_hardware(names)
        if isinstance(hardware, dict):
            [hw.start_buffering(stats) for hw in list(hardware.values())]
        else:
            hardware.start_buffering(stats)

    def stop_buffering(
        self,
        names: Union[List[str], str, Hardware, List[Hardware]] = None,
        stats: Union[List[str], str, None] = None,
    ):
        """
        Stops buffering :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types
        for the :class:`~catapcore.common.machine.hardware.Hardware` objects requested.

        :param names: Names of :class:`~catapcore.common.machine.hardware.Hardware` types -- if `None`, stop all.
        :type names: Union[str, List[str], None]
        :param stats: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV`
        objects required (stop all if `None`)
        :type stats: Union[List[str], str, None]
        """
        hardware = self.get_hardware(names)
        if isinstance(hardware, dict):
            [hw.stop_buffering(stats) for hw in list(hardware.values())]
        else:
            hardware.stop_buffering(stats)

    def clear_buffer(
        self,
        names: Union[List[str], str, Hardware, List[Hardware]] = None,
        stats: Union[List[str], str, None] = None,
    ):
        """
        Clear buffers :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types
        for the :class:`~catapcore.common.machine.hardware.Hardware` objects requested.

        :param names: Names of :class:`~catapcore.common.machine.hardware.Hardware` types -- if `None`, clear all.
        :type names: Union[str, List[str], None]
        :param stats: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV`
        objects required (clear all if `None`)
        :type stats: Union[List[str], str, None]
        """
        hardware = self.get_hardware(names)
        if isinstance(hardware, dict):
            [hw.clear_buffer(stats) for hw in list(hardware.values())]
        else:
            hardware.clear_buffer(stats)

    def is_buffering(
        self,
        names: Union[List[str], str, Hardware, List[Hardware]] = None,
        stats: Union[List[str], str, None] = None,
    ) -> Union[bool, Dict[str, bool], Dict[str, Dict[str, bool]]]:
        """
        Check if :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types are buffering
        for the :class:`~catapcore.common.machine.hardware.Hardware` objects requested.

        :param names: Names of :class:`~catapcore.common.machine.hardware.Hardware` types -- if `None`, check all.
        :type names: Union[str, List[str], None]
        :param stats: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV`
        objects required (check all if `None`)
        :type stats: Union[List[str], str, None]

        :return: True if is buffering
        :rtype: Union[bool, Dict[str, bool], Dict[str, Dict[str, bool]]]
        """
        hardware = self.get_hardware(names)
        if isinstance(hardware, dict):
            return {hw.name: hw.is_buffering(stats) for hw in list(hardware.values())}
        else:
            return hardware.is_buffering(stats)

    def set_buffer_size(
        self,
        names: Union[List[str], str, Hardware, List[Hardware]] = None,
        stats: Union[List[str], str, None] = None,
        val: int = 10,
    ):
        """
        Set buffer size of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types
        for the :class:`~catapcore.common.machine.hardware.Hardware` objects requested.

        :param names: Names of :class:`~catapcore.common.machine.hardware.Hardware` types -- if `None`, set all.
        :type names: Union[str, List[str], None]
        :param stats: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV`
        objects required (set all if `None`)
        :type stats: Union[List[str], str, None]
        :param val: Buffer size
        :type val: int
        """
        hardware = self.get_hardware(names)
        if isinstance(hardware, dict):
            [hw.set_buffer_size(stats, val) for hw in list(hardware.values())]
        else:
            hardware.set_buffer_size(stats, val)

    def get_hardware(
        self, names: Union[List[str], str] = None
    ) -> Union[Dict[str, Hardware], Hardware]:
        """
        Get :class:`~catapcore.common.machine.hardware.Hardware` object.

        :param names: Names of :class:`~catapcore.common.machine.hardware.Hardware` types.
        :type names: Union[List[str], str]

        :returns: Hardware objects (as Dict or individual object)
        :rtype: Union[Dict[str, Hardware], Hardware]
        """
        if not names:
            raise HardwareNameNotProvided(
                f"Please specify {self._hardware_type.__name__} name(s)."
            )
        if isinstance(names, str):
            does_exist, component = self._name_exists(names)
            if not does_exist:
                raise HardwareNameNotFound(
                    f"Could not find {self._hardware_type.__name__} with name {names}"
                )
            return component
        else:
            return_hardware = {}
            for name in names:
                does_exist, component = self._name_exists(name)
                if not does_exist:
                    raise HardwareNameNotFound(
                        f"Could not find {self._hardware_type.__name__} with name {name}"
                    )
                return_hardware.update({component.name: component})
            return return_hardware

    @property
    def names(self) -> List[str]:
        """
        Get names of all :class:`~catapcore.common.machine.hardware.Hardware` objects in the Factory.

        :returns: Names of objects
        :rtype: List[str]
        """
        return list(self.hardware.keys())

    def _get_property(
        self,
        names: Union[str, List[str], None],
        property_: Callable,
    ):
        """
        Return a specific property for a :class:`~catapcore.common.machine.hardware.Hardware` object.
        If `names` is `None`, return a dictionary of all hardware names and their property values.

        :param names: Name(s) of Hardware objects
        :type names: Union[str, List[str], None]
        :param property_: Property inside Hardware class
        :type property_: Callable
        """
        if names is None:
            return {name: property_(hw) for name, hw in self.hardware.items()}
        elif isinstance(names, str):
            return property_(self.get_hardware(names))
        elif isinstance(names, list):
            return {name: property_(self.get_hardware(name)) for name in names}
        else:
            raise ValueError("Invalid input type for 'names'")

    def _set_property(
        self,
        names: Union[str, List[str]],
        values: Union[Union[float, int], List[Union[float, int]]],
        setter_: Callable,
    ):
        """
        Set a specific property for a :class:`~catapcore.common.machine.hardware.Hardware` object.

        :param names: Name(s) of Hardware objects
        :type names: Union[str, List[str]]
        :param values: Value to set
        :type values: Union[Union[float, int], List[Union[float, int]]]
        :param setter_: Setter for property
        :type setter_: Callable
        """
        if values is None:
            raise ValueError("Please provide values to set for property.")
        if (
            names is None
            and isinstance(values, list)
            or isinstance(names, str)
            and isinstance(values, list)
        ):
            raise ValueError("Cannot set multiple values for property")
        if isinstance(names, str) and not isinstance(values, list):
            # set one hardware to one value
            setter_(self.get_hardware(names), values)
        if isinstance(names, list) and isinstance(values, list):
            # set many hardware to many value
            for name, value in zip(names, values):
                setter_(self.get_hardware(name), value)
        if isinstance(names, list) and not isinstance(values, list):
            # set many hardware to one value
            for name in names:
                setter_(self.get_hardware(name), values)
        if names is None and not isinstance(values, list):
            for _, hardware in self.hardware.items():
                setter_(hardware, values)

    def _call_with_no_args_on_many(
        self,
        names: str | List[str] | None,
        call_: Callable,
    ) -> None:
        """
        Call a specific function in a :class:`~catapcore.common.machine.hardware.Hardware` class without any arguments.

        :param names: Name(s) of Hardware objects (call on all if `None`).
        :type names: Union[str, List[str], None]
        :param call_: Function to call
        :type call_: Callable
        """
        if not callable(call_):
            raise ValueError("Please provide a callable function.")
        if names is None:
            for _, hardware in self.hardware.items():
                call_(hardware)
        if isinstance(names, list):
            for name in names:
                call_(self.get_hardware(name))
        if isinstance(names, str):
            call_(self.get_hardware(names))

    def _set_property_multiple(
        self,
        settings: Dict[str, Union[float, int]],
        setter_: Callable,
    ) -> None:
        """
        Set a specific property to multiple :class:`~catapcore.common.machine.hardware.Hardware` objects.

        :param settings: Name(s) of Hardware objects and value(s) to set.
        :type settings: Dict[str, Union[float, int]]
        :param setter_: Setter to call
        :type setter_: Callable
        """
        if settings is None:
            raise ValueError("Please provide settings")
        for name, value in settings.items():
            setter_(self.get_hardware(name), value)

    def create_snapshot(self) -> None:
        """
        Updates the current values in the snapshot of the factory
        (see :class:`~catapcore.common.machine.snapshot.Snapshot`)
        """
        self._current_snapshot.update()

    def get_snapshot(self) -> Dict:
        """
        Returns the current values in the snapshot of the factory
        (see :class:`~catapcore.common.machine.snapshot.Snapshot`)

        :returns: Snapshot dict
        :rtype: Dict
        """
        return self._current_snapshot.get()

    def set_snapshot(self, snapshot=Dict[str, Dict[str, Any]]):
        """
        Sets the current values in the snapshot of the factory
        (see :class:`~catapcore.common.machine.snapshot.Snapshot`)

        :param snapshot: Snapshot dict to set
        :type snapshot: Dict[str, Dict[str, Any]]
        """
        self._current_snapshot.set(
            snapshot=snapshot,
        )

    # todo : add option to save new snapshot
    def save_snapshot(self, filename: str = None, comment: str = "") -> str:
        """
        Saves the current snapshot of the factory to a yaml file in a default location

        :param filename: Name of file to save
        :type filename: str
        :param comment: Comment to add to snapshot file
        :type comment: str

        :returns: The filepath to the snapshot file
        :rtype: str
        """
        return self._current_snapshot.save(
            filename=filename,
            comment=comment,
        )

    def load_snapshot(
        self,
        filename: str = None,
        apply: bool = False,
    ) -> None:
        """
        Loads a snapshot from yaml file.
        This snapshot is set but not applied, unless apply is set to True.

        :param filename: Snapshot file to load
        :type filename: str
        :param apply: Apply to Factory if `True`
        :type apply: bool
        """
        self._current_snapshot.load(filename=filename)
        if apply:
            self._current_snapshot.apply()

    def apply_snapshot(self, exclude: List[str] = []) -> None:
        """
        Applies the snapshot that is currently stored.
        Use :func:`~catapcore.common.machine.factory.Factory.set_snapshot` or
        :func:`~catapcore.common.machine.factory.Factory.load_snapshot` to change the current snapshot.

        :param exclude: Can be used to not apply the snapshot to supplied hardware names.
        :type exclude: List[str]
        """
        self._current_snapshot.apply(exclude=exclude)

    def compare_snapshot_with_current_snapshot(
        self, snapshot: Dict[str, Dict[str, Any]]
    ) -> Dict:
        """
        Get the difference between a snapshot and the one that is currently stored.

        :param snapshot: Snapshot data not currently stored
        :type snapshot: Dict[str, Dict[str, Any]]

        :returns: Diff between these snapshots
        :rtype: Dict
        """
        return self._current_snapshot.diff(
            first_snapshot=self.get_snapshot(),
            second_snapshot=snapshot,
        )

    def compare_file_with_current_snapshot(self, filename: str) -> Dict:
        """
        Get the difference between a snapshot in a file and the one that is currently stored.

        :param filename: Path to snapshot YAML file
        :type filename: str

        :returns: Diff between these snapshots
        :rtype: Dict
        """
        _snapshot = self._current_snapshot._load_file(filename)
        return self._current_snapshot.diff(
            first_snapshot=self.get_snapshot(),
            second_snapshot=_snapshot,
        )

    def compare_snapshot_files(
        self,
        first_filename: str = None,
        second_filename: str = None,
    ) -> Dict:
        """
        Get the difference between two snapshot files

        :param first_filename: Path to snapshot YAML file
        :type first_filename: str
        :param second_filename: Path to snapshot YAML file
        :type second_filename: str

        :returns: Diff between these snapshots
        :rtype: Dict
        """
        _first_snapshot = self._current_snapshot._load_file(first_filename)
        _second_snapshot = self._current_snapshot._load_file(second_filename)
        return self._current_snapshot.diff(
            first_snapshot=_first_snapshot,
            second_snapshot=_second_snapshot,
        )

    def snapshot_applied(self) -> bool:
        """
        Returns the status of the last applied snapshot

        :return: `True` if applied
        :rtype: bool
        """
        return self._current_snapshot.applied

    def snapshot_last_applied(self) -> str:
        """
        Returns the timestamp of the last applied snapshot

        :return: Timestamp of when snapshot was applied
        :rtype: str
        """
        return self._current_snapshot.last_applied

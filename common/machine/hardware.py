"""
catapcore Hardware Module

This module defines a base class for interacting with specific hardware objects via the control system.

Classes:
    - :class:`~catapcore.common.constants.machine.hardware.PVMap`: Base class for creating a map of EPICS PVs.
    - :class:`~catapcore.common.constants.machine.hardware.ControlsInformation`: Base class for accessing\
    PVs stored in the `~PVMap` and controlling the object
    - :class:`~catapcore.common.constants.machine.hardware.Properties`: Base class for defining and accessing metadata\
    and information not defined directly in the controls system.
    - :class:`~catapcore.common.constants.machine.hardware.Hardware`: Base class defining middle-layer\
    functions for accessing the controls system.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    SerializeAsAny,
    field_validator,
    Field,
    AliasChoices
)
import catapcore.config as cfg
from typing import Any, ClassVar, Dict, List, Union, Type, Callable
from catapcore.common.machine.pv_utils import (
    BinaryPV,
    PVInfo,
    ScalarPV,
    StatePV,
    StatisticalPV,
    StringPV,
    WaveformPV,
)
from epics import ca
from catapcore.common.machine.area import MachineArea
from catapcore.common.exceptions import (
    InvalidSnapshotSetting,
    UnexpectedPVEntry,
)
import warnings
from numpy import array
import inspect

__all__ = [
    "PVMap",
    "ControlsInformation",
    "Properties",
    "Hardware",
    "create_dynamic_stats_pv_property_from_getter",
    "add_stats_to_controls_information",
    "add_stats_to_hardware",
]


class PVMap(BaseModel):
    """
    Base class for creating a map of EPICS PVs (see :mod:`~catapcore.common.machine.pv_utils`).
    """

    is_virtual: ClassVar[bool]
    """Flag to connect either to the virtual or physical controls system"""
    connect_on_creation: ClassVar[bool]
    """Option to connect automatically to PVs when created"""
    _statistics: Dict[str, StatisticalPV]
    """Dictionary of StatisticalPV types for calculating statistics
    (see :class:`~catapcore.common.machine.pv_utils.StatisticalPV`)"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
    )

    def __init__(
        self,
        is_virtual: bool,
        connect_on_creation: bool = False,
        *args,
        **kwargs,
    ):
        PVMap.is_virtual = is_virtual
        PVMap.connect_on_creation = connect_on_creation
        super().__init__(
            is_virtual=self.is_virtual,
            connect_on_creation=self.connect_on_creation,
            *args,
            **kwargs,
        )
        self._statistics = {}
        self._pvs = {}
        # Go through all fields that have been set
        # and check if they are StatisticalPVs.
        # Add all StatisticalPV attributes to _statistics.
        for name in self.model_fields_set:
            try:
                if isinstance(
                    self.__getattribute__(name),
                    ScalarPV
                    | BinaryPV
                    | StatePV
                    | StringPV
                    | WaveformPV
                    | StatisticalPV,
                ):
                    entry = {name: self.__getattribute__(name)}
                    if isinstance(self.__getattribute__(name), StatisticalPV):
                        self._statistics.update(entry)
                    self._pvs.update(entry)
            except AttributeError:
                warnings.warn(
                    message=UnexpectedPVEntry(
                        f"Found unexpected entry ({name}) in pv_record_map."
                    )
                )

    @field_validator(
        "*",
        mode="before",
    )
    @classmethod
    def validate_pvs(
        cls, v: Dict
    ) -> ScalarPV | BinaryPV | StatePV | StringPV | WaveformPV | StatisticalPV:
        pv_info = PVInfo(**v)
        if cls.is_virtual:
            if pv_info.virtual_pv:
                pv_info.pv = pv_info.virtual_pv
            else:
                # If the PV does not have specific virtual_pv in the config
                # we will just preprend the virtual prefix to the pv name
                pv_info.pv = cfg.VIRTUAL_PREFIX + pv_info.pv
            pv_info.read_only = False
        return pv_info.create()

    @field_validator(
        "*",
        mode="after",
    )
    @classmethod
    def connect_pvs(
        cls, v: ScalarPV | BinaryPV | StatePV | StringPV | WaveformPV | StatisticalPV
    ) -> ScalarPV | BinaryPV | StatePV | StringPV | WaveformPV | StatisticalPV:
        if cls.connect_on_creation:
            v.connect()
        return v

    @property
    def statistics(self) -> Dict[str, StatisticalPV]:
        """
        Return a dictionary containing the :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types in the map.

        :returns: Dict[str, StatisticalPV]
        """
        return {name: s_pv for name, s_pv in self._statistics.items()}

    @property
    def pvs(
        self,
    ) -> Dict[
        str, BinaryPV | ScalarPV | StatePV | StatisticalPV | StringPV | WaveformPV
    ]:
        """
        Return a dictionary of all PVs in the map (see :mod:`~catapcore.common.machine.pv_utils`).

        :returns: Dict[str, PVSignal]
        """
        return self._pvs

    def is_buffer_full(
        self, names: Union[str, List[str], None]
    ) -> Union[bool, Dict[str, bool]]:
        """
        Check if the statistics buffer is full (i.e. if `len(PV.buffer) == PV.buffer_size)`.

        See :attr:`~catapcore.common.machine.pv_utils.StatisticalPV.is_buffer_full`.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, check all.
        :type names: Union[str, List[str], None]
        :returns: True if buffer is full
        :rtype: bool | Dict[str, bool]
        """
        if isinstance(names, str):
            self.check_name_in_statistics(names)
            return self._statistics[names].is_buffer_full
        elif not names:
            names = list(self._statistics.keys())
        full = {}
        for name in names:
            self.check_name_in_statistics(name)
            full.update({name: self._statistics[name].is_buffer_full})
        return full

    def clear_buffer(self, names: Union[str, List[str], None]) -> None:
        """
        Clears the statistics buffers.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, clear all.
        :type names: Union[str, List[str], None]
        """
        if isinstance(names, str):
            names = [names]
        elif not names:
            names = list(self._statistics.keys())
        for name in names:
            self.check_name_in_statistics(name)
            self._statistics[name]._buffer.clear()

    def set_buffer_size(self, names: Union[str, List[str], None], size: int) -> None:
        """
        Sets the size of the statistics buffers.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, set all.
        :param size: Size of statistics buffer
        :type names: Union[str, List[str], None]
        :type size: int
        """
        if isinstance(names, str):
            names = [names]
        elif not names:
            names = list(self._statistics.keys())
        for name in names:
            self.check_name_in_statistics(name)
            self._statistics[name].buffer_size = size

    def start_buffering(self, names: Union[str, List[str], None]) -> None:
        """
        Starts buffering :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, start all.
        :type names: Union[str, List[str], None]
        """
        if isinstance(names, str):
            names = [names]
        elif not names:
            names = list(self._statistics.keys())
        for name in names:
            self.check_name_in_statistics(name)
            self._statistics[name].start_buffering()

    def stop_buffering(self, names: Union[str, List[str], None]) -> None:
        """
        Stops buffering :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, stop all.
        :type names: Union[str, List[str], None]
        """
        if isinstance(names, str):
            names = [names]
        elif not names:
            names = list(self._statistics.keys())
        for name in names:
            self.check_name_in_statistics(name)
            self._statistics[name].stop_buffering()

    def check_name_in_statistics(self, name: str):
        """
        Check if a PV is in the `_statistics` dictionary

        :param str name: Name PV to check.
        :raises ValueError: If `name` is not in the `_statistics` dictionary.
        """
        if name not in self._statistics:
            raise ValueError(f"Could not find {name} in statistics.")


class ControlsInformation(BaseModel):
    """
    Base class for accessing PVs stored in the `~PVMap`).
    """

    is_virtual: ClassVar[bool]
    """Flag to connect either to the virtual or physical controls system"""
    connect_on_creation: ClassVar[bool]
    """Flag to connect automatically to PVs when created"""
    model_config = ConfigDict(
        extra="allow",
        arbitrary_types_allowed=True,
    )
    pv_record_map: PVMap = None

    def __init__(
        self, is_virtual: bool, connect_on_creation: bool = False, *args, **kwargs
    ):
        ControlsInformation.is_virtual = is_virtual
        ControlsInformation.connect_on_creation = connect_on_creation
        super(
            ControlsInformation,
            self,
        ).__init__(
            is_virtual=self.is_virtual,
            connect_on_creation=self.connect_on_creation,
            *args,
            **kwargs,
        )

    @field_validator("pv_record_map", mode="before")
    @classmethod
    def validate_pv_map(cls, v: Any) -> PVMap:
        return PVMap(
            is_virtual=cls.is_virtual,
            connect_on_creation=cls.connect_on_creation,
            **v,
        )

    @property
    def statistics(self) -> Dict[str, StatisticalPV]:
        """
        Returns all :class:`~catapcore.common.machine.pv_utils.StatisticalPV` objects defined in the :class:`~PVMap`

        :returns: Dict[str, StatisticalPV]
        """
        return self.pv_record_map.statistics

    def is_buffer_full(
        self, name: Union[str, List[str], None]
    ) -> Union[bool, Dict[str, bool]]:
        """
        Check if the statistics buffer is full (i.e. if `len(PV.buffer) == PV.buffer_size)`.

        See :attr:`~catapcore.common.machine.pv_utils.StatisticalPV.is_buffer_full`.

        :param name: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, check all.
        :type name: Union[str, List[str], None]
        :returns: True if buffer is full
        :rtype: bool | Dict[str, bool]
        """
        return self.pv_record_map.is_buffer_full(name)

    def clear_buffer(self, name: Union[str, List[str], None]) -> None:
        """
        Clears statistics buffers.

        :param name: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, clear all.
        :type name: Union[str, List[str], None]
        """
        self.pv_record_map.clear_buffer(name)

    def set_buffer_size(self, name: Union[str, List[str], None], size: int) -> None:
        """
        Sets the size of the statistics buffers.

        :param name: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, set all.
        :param size: Size of statistics buffer
        :type name: Union[str, List[str], None]
        :type size: int
        """
        self.pv_record_map.set_buffer_size(name, size)

    def start_buffering(self, name: Union[str, List[str], None]) -> None:
        """
        Starts buffering :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types.

        :param name: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, start all.
        :type name: Union[str, List[str], None]
        """
        self.pv_record_map.start_buffering(name)

    def stop_buffering(self, name: Union[str, List[str], None]) -> None:
        """
        Stops buffering :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types.

        :param name: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, stop all.
        :type name: Union[str, List[str], None]
        """
        self.pv_record_map.stop_buffering(name)


class Properties(BaseModel):
    """
    Base class for defining and accessing metadata and information not defined directly in the controls system.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="allow",
        arbitrary_types_allowed=True,
    )
    name: str
    """Name of hardware object"""
    name_alias: List[str] | None = Field(
        default=None, validation_alias=AliasChoices("name_alias", "alias")
    )
    """Aliases to the name of the hardware object"""
    hardware_type: str
    """Type of hardware object"""
    position: Union[float, List[float]] = Field(
        validation_alias=AliasChoices("position", "physical_middle_z", "physical_middle")
    )
    """Z position along the lattice in meters"""
    machine_area: MachineArea
    """Machine area of the hardware object"""
    subtype: str | None = None
    """Subtype of the hardware object"""

    def __init__(self, *args, **kwargs):
        super(
            Properties,
            self,
        ).__init__(
            *args,
            **kwargs,
        )

    @field_validator("machine_area", mode="before")
    def create_machine_area(cls, v: str) -> MachineArea:
        area = MachineArea(name=v.upper())
        if area in cfg.MACHINE_AREAS:
            return area
        else:
            raise ValueError(
                f"Could not find machine_area {area} in Machine Areas:"
                + f"{','.join([_area.name for _area in cfg.MACHINE_AREAS])}",
            )

    @field_validator("name_alias", mode="before")
    def create_alias_list(cls, v: str | None) -> List[str]:
        if v is None:
            return [""]
        aliases = v.split(",")
        return [alias.strip() for alias in aliases]

    @field_validator("position", mode="before")
    def validate_position(cls, v: float | List[float]) -> float:
        if isinstance(v, list):
            return v[2]
        return v


class Hardware(BaseModel):
    """
    Base class defining middle-layer functions for accessing the controls system
    """

    is_virtual: ClassVar[bool]
    """Flag to connect either to the virtual or physical controls system"""
    connect_on_creation: ClassVar[bool]
    """Flag to connect automatically to PVs when created"""
    controls_information: SerializeAsAny[ControlsInformation]
    """See :class:`~catapcore.common.machine.hardware.ControlsInformation`"""
    properties: SerializeAsAny[Properties]
    """See :class:`~catapcore.common.machine.hardware.Properties`"""
    _aliases: ClassVar[Dict[str, str]]
    """Dictionary of alias names for this object"""
    _snapshot_settables: List[str]
    """PVs to apply to the object when calling :func:`~catapcore.common.machine.hardware.Hardware.apply_snapshot`"""
    _snapshot_gettables: List[str]
    """PVs to read from the object when calling :func:`~catapcore.common.machine.hardware.Hardware.create_snapshot`"""
    _additional_snapshot_information: Dict[str, Any]
    """Additional properties to save in the snapshot"""

    def __init__(
        self,
        is_virtual: bool = True,
        connect_on_creation: bool = False,
        **kwargs,
    ):
        Hardware.is_virtual = is_virtual
        Hardware.connect_on_creation = connect_on_creation
        Hardware._aliases = {}
        super().__init__(
            is_virtual=is_virtual,
            connect_on_creation=connect_on_creation,
            _aliases={},
            **kwargs,
        )
        self._snapshot_settables = []
        self._snapshot_gettables = []
        self._additional_snapshot_information = {}

    @field_validator("controls_information", mode="before")
    @classmethod
    def validate_controls_information(cls, v: Any) -> ControlsInformation:
        return ControlsInformation(
            is_virtual=cls.is_virtual,
            connect_on_creation=cls.connect_on_creation,
            **v,
        )

    @property
    def name(self):
        """
        Name of the hardware object

        :returns: Name as string
        """
        return self.properties.name

    @property
    def aliases(self):
        """
        Aliases for the hardware object name

        :returns: Alias names as list
        """
        return self.properties.name_alias

    @property
    def machine_area(self) -> MachineArea:
        """
        Machine area for the object

        :returns: :class:`~catapcore.common.constants.areas.MachineArea`
        """
        return self.properties.machine_area

    @property
    def position(self) -> float:
        return self.properties.position

    @property
    def subtype(self) -> str:
        return self.properties.subtype

    @property
    def statistics(self) -> Dict[str, StatisticalPV]:
        """
        Returns all :class:`~catapcore.common.machine.pv_utils.StatisticalPV` objects defined in the :class:`~PVMap`

        :returns: Dict[str, StatisticalPV]
        """
        return self.controls_information.statistics

    def get_statistics(
        self, names: Union[str, List[str], None] = None
    ) -> Union[StatisticalPV, Dict[str, StatisticalPV]]:
        """
        Returns all :class:`~catapcore.common.machine.pv_utils.StatisticalPV` objects defined in the :class:`~PVMap`

        :param names: Names of PVs to check
        :type names: Union[str, List[str]]

        :returns: Statistics objects
        :rtype: Union[StatisticalPV, Dict[str, StatisticalPV]]
        """
        if not names:
            names = list(self.statistics.keys())
        elif isinstance(names, str):
            return self.statistics[names]
        return {
            pv: self.statistics[pv] for pv in names if len(self.statistics[pv]._buffer)
        }

    def is_buffer_full(
        self, names: Union[str, List[str], None] = None
    ) -> Union[bool, Dict[str, bool]]:
        """
        Check if the statistics buffer is full (i.e. if `len(PV.buffer) == PV.buffer_size)`.

        See :attr:`~catapcore.common.machine.pv_utils.StatisticalPV.is_buffer_full`.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, check all.
        :type names: Union[str, List[str], None]
        :returns: True if buffer is full
        :rtype: bool | Dict[str, bool]
        """
        return self.controls_information.is_buffer_full(names)

    def is_buffering(
        self, names: Union[str, List[str]] = None
    ) -> Union[bool, Dict[str, bool]]:
        """
        Check if :class:`~catapcore.common.machine.pv_utils.StatisticalPV` objects is currently buffering

        :param names: Names of PVs to check
        :type names: Union[str, List[str]]

        :returns: True if buffering
        :rtype: Union[StatisticalPV, Dict[str, StatisticalPV]]
        """
        if not names:
            raise ValueError(
                "Please enter a name to check for buffering: \n"
                + ", ".join(self.controls_information.pv_record_map._statistics.keys())
            )
        if isinstance(names, str):
            return names in self.statistics
        if isinstance(names, list):
            handle_results = {
                handle: True if handle in self.statistics else False for handle in names
            }
            return handle_results

    def set_buffer_size(
        self, names: Union[str, List[str], None] = None, size: int = 10
    ) -> None:
        """
        Sets the size of the statistics buffers.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, set all.
        :param size: Size of statistics buffer
        :type names: Union[str, List[str], None]
        :type size: int
        """
        if not names:
            names = list(self.statistics.keys())
        self.controls_information.set_buffer_size(names, size)

    def start_buffering(self, names: Union[str, List[str], None] = None) -> None:
        """
        Starts buffering :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, start all.
        :type names: Union[str, List[str], None]
        """
        if not names:
            names = list(self.statistics.keys())
        self.controls_information.start_buffering(names)

    def stop_buffering(self, names: Union[str, List[str], None] = None) -> None:
        """
        Stops buffering :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, stop all.
        :type names: Union[str, List[str], None]
        """
        if not names:
            names = list(self.statistics.keys())
        self.controls_information.stop_buffering(names)

    def clear_buffer(self, names: Union[str, List[str], None] = None) -> None:
        """
        Clears statistics buffers.

        :param names: Names of :class:`~catapcore.common.machine.pv_utils.StatisticalPV` types -- if `None`, clear all.
        :type names: Union[str, List[str], None]
        """
        if not names:
            names = list(self.statistics.keys())
        self.controls_information.clear_buffer(names)

    def update_additional_information(self, key, value):
        try:
            self._additional_snapshot_information[key] = value
        except KeyError:
            warnings.warn(
                f"Could not find {key} in _additional_snapshot_information",
            )

    def create_snapshot(self) -> Dict:
        """
        Read the :attr:`~_snapshot_gettables` and save them to a dictionary.

        If the gettable is a :class:`~catapcore.common.machine.pv_utils.StatisticalPV` and is buffering,
        then save the buffer data as well

        :returns: Dict containing `value` (and `buffer`/`timestamp`) for all PVs in :attr:`~_snapshot_gettables`
        """
        ca.use_initial_context()
        snapshot = {self.name: {}}
        for handle, pv in self.controls_information.pv_record_map.pvs.items():
            if handle in self._snapshot_gettables or handle in self._snapshot_settables:
                if isinstance(pv, StatePV):
                    value = pv.get()
                    if value is None:
                        snapshot[self.name].update({handle: {"value": None}})
                    else:
                        snapshot[self.name].update({handle: {"value": value.name}})
                else:
                    snapshot[self.name].update({handle: {"value": pv.get()}})
                if self.is_buffering(handle):
                    stats = self.get_statistics(handle)
                    stats_buffer = (
                        array(stats.buffer)[::, 1] if stats.buffer else array([])
                    )
                    timestamps = (
                        array(stats.buffer)[::, 0] if stats.buffer else array([])
                    )
                    snapshot[self.name][handle].update(
                        {
                            "buffer": stats_buffer.tolist(),
                            "timestamps": timestamps.tolist(),
                        }
                    )
        if self._additional_snapshot_information:
            for handle, value in self._additional_snapshot_information.items():
                if handle in snapshot:
                    warnings.warn(
                        f"Additional snapshot information cannot have entry {handle} "
                        + "as this is set in default snapshot.",
                        category=InvalidSnapshotSetting,
                    )
                else:
                    snapshot[self.name].update({handle: {"value": value}})
        return snapshot

    def apply_snapshot(self, snapshot: Dict) -> None:
        """
        Apply a snapshot to the machine for all PVs in :attr:`~_snapshot_settables`

        :param snapshot: Dictionary containing snapshot settables
        :type snapshot: Dict
        """
        for handle, setting in snapshot.items():
            if handle in self._snapshot_settables:
                ca.use_initial_context()
                self.controls_information.pv_record_map.pvs[handle].put(
                    setting["value"]
                )

    def __eq__(self, other):
        return (self.name == other.name) and (self.position == other.position)

    def __lt__(self, other):
        this_machine_area_index = cfg.MACHINE_AREAS.index(self.machine_area)
        other_machine_area_index = cfg.MACHINE_AREAS.index(other.machine_area)
        return (this_machine_area_index, self.position) < (
            other_machine_area_index,
            other.position,
        )

    def __gt__(self, other):
        this_machine_area_index = cfg.MACHINE_AREAS.index(self.machine_area)
        other_machine_area_index = cfg.MACHINE_AREAS.index(other.machine_area)
        return (this_machine_area_index, self.position) > (
            other_machine_area_index,
            other.position,
        )


def create_dynamic_stats_pv_property_from_getter(getter_func: Callable):
    """
    Extract the source code from a property getter

    :param getter_func: Source code
    :type getter_func: Callable
    """
    # Extract the source code of the getter method
    getter_code = inspect.getsource(getter_func)

    # Extract the PV from the code for the property
    def dynamic_function(self):
        call = getter_code.split("pv_record_map.")[-1].split(".")[0]
        # Retrieve the statistics for that PV in pv_record_map
        return self.pv_record_map._statistics[call]

    return dynamic_function


def add_stats_to_controls_information(
    cls: Type[ControlsInformation],
    target_func_name: str,
    exclude: Union[List, str, None] = None,
):
    """
    Function to add a statistics property dynamically to a class based on an existing property getter

    :param cls: Specific :class:`~ControlsInformation` class
    :param target_func_name: Target function to check
    :param exclude: Properties to exclude from dynamic addition of statistics properties
    :type cls: :class:`~ControlsInformation`
    :type target_func_name: str
    :type exclude: Union[List, str, None]
    """
    # Loop through all the properties in the class
    if exclude is None:
        exclude = ["stats"]
    newprops = {}
    for name, attr in cls.__dict__.items():
        if (
            isinstance(attr, property)
            and ("stats" not in name)
            and (name not in exclude)
        ):
            getter_code = inspect.getsource(
                attr.fget
            )  # Get the source code of the getter
            # Check if the property calls the target function
            if target_func_name in getter_code:
                # Create the new function based on the getter code
                new_function = create_dynamic_stats_pv_property_from_getter(attr.fget)
                # Dynamically add the new function
                newprops.update({f"{name}_stats": new_function})
    for k, v in newprops.items():
        setattr(cls, k, property(v))


def create_dynamic_controls_stats_property_from_getter(getter_func: Callable):
    """
    Extract the :class:`~ControlsInformation` property from a :class:`~Hardware` property getter

    :param getter_func: Source code
    :type getter_func: Callable
    """
    # Extract the source code of the getter method
    getter_code = inspect.getsource(getter_func)
    newl = "\n"

    # Append 'stats' to the function call in controls_information
    # Remember that we already know there is a '_stats' property in controls_information
    def dynamic_function(self):
        return getattr(
            self.controls_information, f"{getter_code.split('.')[-1].strip(newl)}_stats"
        )

    return dynamic_function


def add_stats_to_hardware(cls1: Type[ControlsInformation], cls2: Type[Hardware]):
    """
    Function to add a statistics property dynamically to a class based on a property getter in another class

    :param cls1: Specific :class:`~ControlsInformation` class
    :param cls2: Specific :class:`~Hardware` class
    :type cls1: :class:`~ControlsInformation`
    :type cls2: :class:`~Hardware`
    """
    # Loop through all the properties in the first class (controls_information)
    newprops = {}
    for name, attr in cls1.__dict__.items():
        # Find properties with '_stats' in controls_information
        if (
            isinstance(attr, property)
            and ("stats" in name)
            and type(cls2.__dict__[name.split("_stats")[0]]) == property
        ):
            # Create a '_stats' function for the Hardware object
            # if there is a '_stats' property in controls_information
            new_function = create_dynamic_controls_stats_property_from_getter(
                getattr(cls2, name.split("_stats")[0]).fget
            )
            newprops.update({f"{name}": new_function})
    for k, v in newprops.items():
        # Add '_stats' properties to Hardware
        setattr(cls2, k, property(v))

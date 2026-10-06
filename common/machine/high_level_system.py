"""
catapcore High-Level System Module

This module defines a base class for interacting with a group of hardware objects pertaining to a common system.

Classes:
    - :class:`~catapcore.common.constants.machine.high_level_system.HighLevelSystem`: Base class\
    for high-level systems.
    - :class:`~catapcore.common.constants.machine.high_level_system.HighLevelSystemComponents`: Base class\
    for high-level system components.
    - :class:`~catapcore.common.constants.machine.high_level_system.HighLevelSystemProperties`: Base class\
    for high-level system properties.
"""

import os
import warnings
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Any, ClassVar, Dict, List
from ruamel.yaml import YAML
from catapcore.common.exceptions import InvalidSnapshotSetting
from catapcore.common.machine.hardware import Hardware
from catapcore.config import LATTICE_LOCATION

__all__ = ["HighLevelSystem", "HighLevelSystemComponents", "HighLevelSystemProperties"]


class HighLevelSystemProperties(BaseModel):
    """
    Base class for defining and accessing metadata and information not defined directly in the controls system.
    """

    name: str
    """Name of :class:`~catapcore.common.machine.high_level_system.HighLevelSystem` object"""
    hardware_type: str
    """Type of :class:`~catapcore.common.machine.high_level_system.HighLevelSystem` object"""
    aliases: List[str]
    """Alias names for :class:`~catapcore.common.machine.high_level_system.HighLevelSystem` object"""
    model_config = ConfigDict(
        extra="allow",
        frozen=True,
    )


class HighLevelSystemComponents(BaseModel):
    """
    Base class for defining the sub-components (:class:`~catapcore.common.machine.hardware.Hardware` objects)
    of a :class:`~catapcore.common.machine.high_level_system.HighLevelSystem` object.
    """

    is_virtual: ClassVar[bool]
    """Flag to connect either to the virtual or physical controls system"""
    connect_on_creation: ClassVar[bool]
    """Flag to connect automatically to PVs when created"""
    model_config = ConfigDict(
        extra="allow",
        arbitrary_types_allowed=True,
    )

    def __init__(
        self,
        is_virtual: bool,
        connect_on_creation: bool = False,
        *args,
        **kwargs,
    ):
        HighLevelSystemComponents.is_virtual = is_virtual
        HighLevelSystemComponents.connect_on_creation = connect_on_creation
        super(HighLevelSystemComponents, self).__init__(
            is_virtual=self.is_virtual,
            connect_on_creation=self.connect_on_creation,
            *args,
            **kwargs,
        )

    @classmethod
    def _create_component(
        self,
        name: str,
        T: Hardware,
    ) -> Hardware:
        """
        Instantiate :class:`~catapcore.common.machine.hardware.Hardware` objects.

        :param name: Name of :class:`~catapcore.common.machine.hardware.Hardware` object
        :type name: str
        :param T: Specific :class:`~catapcore.common.machine.hardware.Hardware` class type
        :type T: Type[:class:`~catapcore.common.machine.hardware.Hardware`]

        :returns: Hardware object
        :rtype: :class:`~catapcore.common.machine.hardware.Hardware`
        """
        config_file = name + ".yaml"
        config_location = os.path.join(LATTICE_LOCATION, T.__name__, config_file)
        yaml = YAML(typ="safe")
        if os.path.exists(config_location):
            with open(config_location) as file:
                config = yaml.load(file)
                return T(
                    is_virtual=self.is_virtual,
                    connect_on_creation=self.connect_on_creation,
                    **config,
                )
        else:
            raise FileNotFoundError(
                f"Could not find {config_location} when configuring {T.__name__}",
            )

    def create_snapshot(self):
        """
        Create full snapshot of :class:`~catapcore.common.machine.hardware.Hardware` objects
        (see :func:`~catapcore.common.machine.hardware.Hardware.create_snapshot`)
        """
        snapshot: Dict[str, Dict[str, Any]] = {}
        # Go through the set fields and look for Hardware objects
        # these will be the components
        for component_handle in self.model_fields_set:
            # if the field is a Hardware object, just create the
            # snapshot and update that component section
            if isinstance(getattr(self, component_handle), Hardware):
                component: Hardware = getattr(self, component_handle)
                snapshot.update({component_handle: component.create_snapshot()})
            # some fields represent multiple components in Dict form
            # so we have to treat them differently
            elif isinstance(getattr(self, component_handle), dict):
                components: Dict[str, Hardware] = getattr(self, component_handle)
                for _, component in components.items():
                    if isinstance(component, Hardware):
                        if component_handle not in snapshot:
                            # if this is the first component of its type in the snapshot
                            # update as normal
                            snapshot.update(
                                {component_handle: {**component.create_snapshot()}}
                            )
                        else:
                            # otherwise, we want to append to current type of component
                            snapshot[component_handle].update(
                                {**component.create_snapshot()}
                            )
        return snapshot

    def _apply_single_component_snapshot(
        self,
        snapshot: Dict[str, Dict[str, Any]],
        component: Hardware,
    ) -> None:
        """
        Apply snapshot to a sub-component of the
        :class:`~catapcore.common.machine.high_level_system.HighLevelSystem` object
        (see :func:`~catapcore.common.machine.hardware.Hardware.apply_snapshot`)

        :param snapshot: Snapshot dictionary to apply
        :param component: Hardware object to which the snapshot should be applied
        :type snapshot: Dict[str, Dict[str, Any]]
        :type component: :class:`~catapcore.common.machine.hardware.Hardware`
        """
        try:
            settings = snapshot[component.name]
            component.apply_snapshot(snapshot=settings)
        except KeyError:
            # error has occurred, the snapshot contains a hardware component
            # that we do not have as a part of the high-level system.
            warnings.warn(
                "High Level System failed to apply snapshot "
                + f"for {component.name} ({component.properties.hardware_type}) as it "
                + " was missing from the snapshot.",
                category=InvalidSnapshotSetting,
            )

    def apply_snapshot(
        self, snapshot: Dict[str, Dict[str, Any]], apply_to: List[str] = None
    ):
        """
        Apply snapshot to the entire
        :class:`~catapcore.common.machine.high_level_system.HighLevelSystem` object
        (see :func:`~catapcore.common.machine.hardware.Hardware.apply_snapshot`)

        :param snapshot: Snapshot dictionary to apply
        :param apply_to: Hardware objects to which the snapshot should be applied (apply to all if `None`)
        :type snapshot: Dict[str, Dict[str, Any]]
        :type apply_to: Union[List[str], None]
        """
        # Go through each component type in the snapshot
        if not apply_to:
            apply_to = list(snapshot.keys())
        for component_type in apply_to:
            try:
                # if the type yields a Hardware object,
                # we can directly pass the settings through to apply_snapshot
                component_settings = snapshot[component_type]
                if isinstance(getattr(self, component_type), Hardware):
                    component: Hardware = getattr(self, component_type)
                    self._apply_single_component_snapshot(
                        snapshot=component_settings,
                        component=component,
                    )
                # if we have multiple components of this type,
                # we will iterate over the dictionary
                elif isinstance(getattr(self, component_type), dict):
                    components: Dict[str, Hardware] = getattr(
                        self,
                        component_type,
                    )
                    for _, component in components.items():
                        self._apply_single_component_snapshot(
                            snapshot=component_settings,
                            component=component,
                        )
            except KeyError:
                warnings.warn(
                    f"High Level System snapshot does not contain supplied component type {component_type}. "
                    + f"Please use the following types {set(snapshot.keys())}"
                )
            except AttributeError:
                warnings.warn(
                    f"High Level System does not have component {component_type} "
                    + "as such, no settings for this component can be applied.",
                    category=InvalidSnapshotSetting,
                )


class HighLevelSystem(BaseModel):
    """
    Base class for grouping together multiple sub-components
    (:class:`~catapcore.common.machine.hardware.Hardware` objects).
    """

    is_virtual: ClassVar[bool]
    """Flag to connect either to the virtual or physical controls system"""
    connect_on_creation: ClassVar[bool]
    """Flag to connect automatically to PVs when created"""
    components: HighLevelSystemComponents
    """Sub-components (:class:`~catapcore.common.machine.hardware.Hardware` objects)"""
    properties: HighLevelSystemProperties
    """Metadata for the high-level system"""
    model_config = ConfigDict(
        extra="allow",
        frozen=False,
        arbitrary_types_allowed=True,
    )

    def __init__(
        self,
        is_virtual: bool,
        connect_on_creation: bool = False,
        *args,
        **kwargs,
    ):
        HighLevelSystem.is_virtual = is_virtual
        HighLevelSystem.connect_on_creation = connect_on_creation
        super(HighLevelSystem, self).__init__(
            is_virtual=self.is_virtual,
            connect_on_creation=self.connect_on_creation,
            *args,
            **kwargs,
        )

    @field_validator("components", mode="before")
    @classmethod
    def validate_components(cls, v) -> HighLevelSystemComponents:
        return HighLevelSystemComponents(
            is_virtual=cls.is_virtual,
            connect_on_creation=cls.connect_on_creation,
            component_types_with_names=v,
        )

    @field_validator("properties", mode="before")
    def validate_properties(cls, v) -> HighLevelSystemComponents:
        return HighLevelSystemProperties(**v)

    @property
    def name(self) -> str:
        """
        Name of the high-level system object

        :returns: Name
        :rtype: str
        """
        return self.properties.name

    @property
    def aliases(self) -> List[str]:
        """
        Aliases for the high-level system object

        :returns: Names
        :rtype: List[str]
        """
        return self.properties.aliases

    @property
    def hardware_type(self) -> str:
        """
        Hardware type of the high-level system object.

        :returns: Type
        :rtype: str
        """
        return self.properties.hardware_type

    def create_snapshot(self) -> Dict[
        str,
        Dict[str, Any],
    ]:
        """
        Create snapshot for the high-level system object
        (see :func:`~catapcore.common.machine.high_level_system.HighLevelSystemComponents.create_snapshot`)

        :returns: Type
        :rtype: str
        """
        return {self.name: self.components.create_snapshot()}

    def apply_snapshot(
        self, snapshot: Dict[str, Dict[str, Any]], apply_to: List[str] = None
    ) -> None:
        """
        Apply snapshot for the high-level system object
        (see :func:`~catapcore.common.machine.high_level_system.HighLevelSystemComponents.apply_snapshot`)

        :returns: Type
        :rtype: str
        """
        self.components.apply_snapshot(snapshot=snapshot, apply_to=apply_to)

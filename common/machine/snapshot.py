"""
catapcore Snapshot Module

This module defines the base class for reading, writing and saving the state of a hardware object.

Classes:
    - :class:`~catapcore.common.constants.machine.snapshot.Snapshot`: Base class for\
     generating, saving, and applying hardware settings on
    :class:`~catapcore.common.machine.hardware.Hardware` objects.
"""

from copy import deepcopy
from os import path, makedirs
from typing import Any, Dict, List, Union
import warnings
from catapcore.common.exceptions import InvalidSnapshotSetting
from catapcore.common.machine.hardware import Hardware
import catapcore.config as cfg
from ruamel.yaml import YAML
from datetime import datetime
from epics import ca

__all__ = ["Snapshot"]


class Snapshot:
    """
    Base class for generating, saving, and applying, hardware settings on
    :class:`~catapcore.common.machine.hardware.Hardware` objects
    """

    _hardware_type: str
    """Hardware type"""
    _hardware: Union[Dict[str, Hardware], Hardware]
    """Hardware object(s)"""
    _snapshot: Dict[str, Dict[str, Any]]
    """Dictionary containing values associated with the Hardware object(s), keyed by type"""
    _applied: bool = False
    """Flag indicating whether this snapshot was applied"""
    _last_applied: datetime = None
    """Timestamp of when the last snapshot was applied"""

    def __init__(
        self,
        hardware: Dict[str, Hardware] = None,
        hardware_type: str = None,
    ):
        self._hardware = hardware
        self._hardware_type = hardware_type
        self._default_snapshot_location = path.join(
            cfg.SNAPSHOT_LOCATION,
            self._hardware_type,
        )
        if not path.exists(self._default_snapshot_location):
            makedirs(self._default_snapshot_location)
        self._snapshot = None

    def _update(
        self, hardware: Hardware, snapshot: Dict[str, Dict[str, Any]] = {}
    ) -> None:
        """
        Update the current snapshot for a specific object

        :param hardware: Hardware object to update
        :param snapshot: Dictionary containing values for that object
        :type hardware: :class:`~catapcore.common.machine.hardware.Hardware`
        :type snapshot: Dictionary of values, keyed by `_hardware_type`
        """
        snapshot[self._hardware_type].update(hardware.create_snapshot())

    def update(self) -> None:
        """
        Update the current snapshot for all objects defined in the snapshot
        """
        snapshot = {self._hardware_type: {}}
        if isinstance(self._hardware, Hardware):
            snapshot[self._hardware_type].update(self._hardware.create_snapshot())
        else:
            threads: List[ca.CAThread] = []
            for _, hardware in self._hardware.items():
                ca.use_initial_context()
                snapshot_thread = ca.threading.Thread(
                    target=self._update,
                    args=(hardware, snapshot),
                    name=f"{hardware.name}-create-snapshot-thread",
                )
                snapshot_thread.start()
                threads.append(snapshot_thread)
            for thread in threads:
                thread.join()
        self.set(snapshot=snapshot)

    def _find_diff(
        self,
        d1: Dict,
        d2: Dict,
    ) -> Dict:
        """
        Find differences in values between two dictionaries.
        Relies on being passed hardware-specific settings like:
        d1 = {GETX: 1.0, GETY: -1.0, GETZ: 0.0}
        d2 = {GETX: -1.0, GETY: 1.0, GETZ: 0.0}

        :param d1: First dictionary to compare
        :param d2: Second dictionary to compare
        :type d1: dict
        :type d2: dict

        :returns: Difference between dictionaries
        :rtype: dict
        """
        return {
            k: {
                "current": d1[k]["value"],
                "diff": d2[k]["value"],
            }
            for k in d1
            if d1[k]["value"] != d2[k]["value"]
        }

    def _is_snapshot_correct_type(
        self, snapshot: Dict[str, Dict[str, Any]] = None
    ) -> bool:
        """
        Check if the hardware type of the snapshot matches `self._hardware_type`

        :returns: True if type is correct
        :rtype: bool
        """
        return snapshot and self._hardware_type in snapshot

    def diff(
        self,
        first_snapshot: Dict[str, Dict[str, Any]] = None,
        second_snapshot: Dict[str, Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Find differences in values between two dictionaries.

        :param first_snapshot: First snapshot to compare
        :param second_snapshot: Second snapshot to compare
        :type first_snapshot: Dict[str, Dict[str, Any]]
        :type second_snapshot: Dict[str, Dict[str, Any]]

        :returns: Difference between snapshots
        :rtype: Dict[str, Dict[str, Any]]
        """
        if first_snapshot and second_snapshot:
            if self._is_snapshot_correct_type(
                first_snapshot
            ) and self._is_snapshot_correct_type(second_snapshot):
                diffs = {}
                s1 = first_snapshot[self._hardware_type]
                s2 = second_snapshot[self._hardware_type]
                for name, settings in s1.items():
                    if name in s2:
                        found_differences = self._find_diff(
                            settings,
                            s2[name],
                        )
                        if found_differences:
                            diffs.update(
                                {
                                    name: found_differences,
                                }
                            )
                    else:
                        print(f"{name} not found in snapshot")
                        diffs.update({name: settings})
                return diffs
            else:
                raise InvalidSnapshotSetting(
                    f"Please provide {self._hardware_type} snapshots to compare against. "
                    + f"Snapshot types provided were: {first_snapshot.keys()[0]} and {first_snapshot.keys()[0]}"
                )
        else:
            raise ValueError("Please provide two snapshots to compare.")

    def get(self) -> Dict:
        """
        Get the current snapshot stored in memory

        :returns: Current snapshot
        :rtype: Dict
        """
        return self._snapshot

    def set(self, snapshot: Dict[str, Dict[str, Any]]) -> None:
        """
        Write the snapshot provided to memory (`self._snapshot`). Key of `snapshot` must match `self._hardare_type`.

        :param snapshot: Snapshot to write
        :type snapshot: Dict[str, Dict[str, Any]]
        """
        if self._hardware_type not in snapshot:
            raise InvalidSnapshotSetting(
                f"Cannot set snapshot for {self._hardware_type} with a {snapshot.keys()[0]} snapshot.",
            )
        self._snapshot = snapshot
        self._applied = False

    def save(self, filename: str = None, comment: str = "") -> str:
        """
        Save the snapshot in memory (`self._snapshot`) to a YAML file.
        Relies on `self._default_snapshot_location` to be set correctly.

        :param filename: Filename to write (cannot be `None`)
        :param comment: Comments to add to snapshot file
        :type filename: str
        :type comment: str

        :returns: Save file location
        :rtype: str
        """
        if not path.exists(self._default_snapshot_location):
            makedirs(self._default_snapshot_location)
        if filename:
            root, extension = path.splitext(filename)
            if extension in ["yaml", "yml"]:
                save_location = path.join(self._default_snapshot_location, filename)
            else:
                save_location = path.join(
                    self._default_snapshot_location, root + ".yaml"
                )
            output = deepcopy(self._snapshot)
            output.update(
                {
                    "comment": comment,
                    "created": datetime.now().isoformat(),
                }
            )
            with open(save_location, "w") as file:
                yaml = YAML(typ="rt")
                yaml.dump(output, file)
            return save_location
        else:
            raise ValueError(
                f"Please provide a filename to save {self._hardware_type} snapshot"
            )

    def _load_file(self, filename: str = None) -> Dict:
        """
        Read a snapshot YAML file.
        Relies on `self._default_snapshot_location` to be set correctly.

        :param filename: Filename to read (cannot be `None`)
        :type filename: str

        :returns: Contents of YAML file
        :rtype: dict
        """
        if not path.exists(self._default_snapshot_location):
            raise FileNotFoundError(
                f"Could not find snapshot location: {self._default_snapshot_location}",
            )
        if filename:
            root, extension = path.splitext(filename)
            if extension in ["yaml", "yml"]:
                load_location = path.join(self._default_snapshot_location, filename)
            else:
                load_location = path.join(
                    self._default_snapshot_location, root + ".yaml"
                )
            with open(load_location, "r") as file:
                yaml = YAML(typ="safe")
                return yaml.load(file.read())
        else:
            raise ValueError(
                f"Please provide a filename to load {self._hardware_type} snapshot"
            )

    def load(self, filename: str = None) -> None:
        """
        Load a snapshot from a YAML file and write to memory as `self._snapshot`
        (see :func:`~catapcore.common.machine.snapshot.Snapshot.set`)

        :param filename: Filename to read (cannot be `None`)
        :type filename: str
        """
        _snapshot = self._load_file(filename)
        self.set(snapshot=_snapshot)

    def _apply(self, hardware: Hardware, snapshot: Dict[str, Any] = {}) -> None:
        """
        Apply snapshot to the specific Hardware object provided
        (see :func:`~catapcore.common.machine.hardware.Hardware.apply_snapshot`)

        :param hardware: Hardware object to which the snapshot should be applied
        :param snapshot: Dictionary of values to apply
        :type hardware: :class:`~catapcore.common.machine.hardware.Hardware`
        :type snapshot: Dict
        """
        hardware.apply_snapshot(snapshot=snapshot)

    def apply(self, exclude: List[str] = []) -> None:
        """
        Apply snapshot to all Hardware objects provided in the snapshot
        (see :func:`~catapcore.common.machine.hardware.Hardware.apply_snapshot`)

        :param exclude: Hardware object to which the snapshot should **not** be applied
        :type exclude: List[str]
        """
        threads: List[ca.CAThread] = []
        for name, hardware in self._hardware.items():
            if name not in exclude:
                try:
                    snapshot = self._snapshot[self._hardware_type][name]
                    ca.use_initial_context()
                    snapshot_thread = ca.threading.Thread(
                        target=self._apply,
                        args=(hardware, snapshot),
                        name=f"{hardware.name}-create-snapshot-thread",
                    )
                    snapshot_thread.start()
                    threads.append(snapshot_thread)
                except KeyError:
                    self._applied = False
                    warnings.warn(
                        f"Could not find {hardware.name} in snapshot settings.",
                        InvalidSnapshotSetting,
                    )
        for thread in threads:
            thread.join()
        self._applied = True
        self._last_applied = datetime.now()

    @property
    def last_applied(self) -> str:
        """
        Timestamp of when last snapshot was applied

        :returns: Time of last applied snapshot
        :rtype: str
        """
        return self._last_applied.isoformat()

    @property
    def applied(self) -> bool:
        """
        Check if the snapshot in memory was applied

        :returns: True if it was applied
        :rtype: bool
        """
        return self._applied

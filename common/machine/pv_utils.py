"""
catapcore PV Utils Module

This module defines the base class for interacting with the controls system and EPICS PVs.

Classes:
    - :class:`~catapcore.common.constants.machine.pv_utils.PVSignal`: Base class for interacting with EPICS PVs.
    - :class:`~catapcore.common.constants.machine.pv_utils.StringPV`: Sub-class of\
    :class:`~catapcore.common.constants.machine.pv_utils.PVSignal` class for string-type PVs.
    - :class:`~catapcore.common.constants.machine.pv_utils.ScalarPV`: Sub-class of\
    :class:`~catapcore.common.constants.machine.pv_utils.PVSignal` class for scalar-type PVs.
    - :class:`~catapcore.common.constants.machine.pv_utils.StatePV`: Sub-class of\
    :class:`~catapcore.common.constants.machine.pv_utils.PVSignal` class for enum-type PVs.
    - :class:`~catapcore.common.constants.machine.pv_utils.BinaryPV`: Sub-class of\
    :class:`~catapcore.common.constants.machine.pv_utils.PVSignal` class for binary-type PVs.
    - :class:`~catapcore.common.constants.machine.pv_utils.WaveformPV`: Sub-class of\
    :class:`~catapcore.common.constants.machine.pv_utils.PVSignal` class for waveform-type PVs.
    - :class:`~catapcore.common.constants.machine.pv_utils.StatisticalPV`: Sub-class of\
    :class:`~catapcore.common.constants.machine.pv_utils.PVSignal` class for statistical-type PVs.
    - :class:`~catapcore.common.constants.machine.pv_utils.PVInfo`: Base class for\
    defining attributes associated with a PV.
    - :class:`~catapcore.common.constants.machine.pv_utils.StateMap`: Enum for\
    mapping states to integers.
"""

import functools
import warnings
import threading
from collections import deque
from datetime import datetime
from enum import Enum, EnumMeta
from statistics import (
    mean,
    median,
    mode,
    stdev,
)
from sys import float_info
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Literal,
    Type,
    Union,
)

import numpy as np

# To set the ca.dll path for pyepics from p4p
import epicscorelibs.path.pyepics  # noqa: F401
from epics import ca
from p4p.nt.scalar import ntfloat, ntint
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
    model_validator,
)

from catapcore.common.exceptions import FailedEPICSOperationWarning, UnexpectedPVEntry
from catapcore.common.machine.protocol import CA, PVA, Protocol
from catapcore.config import EPICS_TIMEOUT


__all__ = [
    "PVSignal",
    "StringPV",
    "ScalarPV",
    "StatePV",
    "BinaryPV",
    "WaveformPV",
    "StatisticalPV",
    "PVInfo",
    "return_none_if_epics_warns",
    "StateMap",
]


class StateMap(Enum):
    pass


def use_initial_context(func: Callable):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        obj = args[0]
        if obj.protocol == "CA":
            ca.use_initial_context()
        return func(*args, **kwargs)

    return inner


class PVSignal(BaseModel):
    """
    Base class for interacting with an EPICS PV.
    """

    name: str
    """PV name"""
    protocol: str = "CA"
    """:class:`~catapcore.common.machine.protocol.Protocol` to use for the PV
     (:class:`~catapcore.common.machine.protocol.CA` or :class:`~catapcore.common.machine.protocol.PVA`),
     Channel Access is selected by default
    """
    description: str | None = ""
    """Description for a PV"""
    read_only: bool = True
    """Flag to define whether a PV has write-access"""

    _value: Any
    """Value of the PV"""
    _timestamp: datetime
    """Timestamp of the PV"""
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    def __init__(self, *args, **kwargs):
        super(PVSignal, self).__init__(*args, **kwargs)
        self._pv: Protocol = None
        self.create_pv_instance()
        self._value = None
        self._timestamp = None

    @property
    def pv(self):
        return self._pv

    @field_validator("protocol", mode="before")
    def normalize_protocol(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in {"CA", "PVA"}:
            raise ValueError("Protocol must be 'CA' or 'PVA'")
        return v_upper

    def create_pv_instance(self):
        if self.protocol == "CA":
            self._pv = CA(pvname=self.name, timeout=EPICS_TIMEOUT, auto_monitor=True)
        elif self.protocol == "PVA":
            self._pv = PVA(pvname=self.name, timeout=EPICS_TIMEOUT)

    @use_initial_context
    def get(
        self,
        expected_type: Any | List[Any],
        as_numpy: bool = False,
        count: int = 1,
        as_string: bool = False,
    ) -> Any:
        """
        Get the current value of a PV. Will raise a warning if the PV did not connect, or if the return
        type is different from `expected_type`.

        :param expected_type: Expected type of the PV
        :param as_numpy: Return PV as numpy type
        :param count: Expected length of PV
        :param as_string: Convert PV value to string
        :type expected_type: Union[Any, List[Any]]
        :type as_numpy: bool
        :type count: int
        :type as_string: bool

        :returns: Current value of the PV
        :rtype: Any
        """
        try:
            retrieved_value = self._pv.get(
                as_numpy=as_numpy, as_string=as_string, count=count
            )
            if isinstance(expected_type, list):
                is_valid_type = any(
                    [isinstance(retrieved_value, type_) for type_ in expected_type]
                )
                if not is_valid_type:
                    raise ValueError
            if not isinstance(expected_type, list):
                if not isinstance(retrieved_value, expected_type):
                    raise ValueError
                self._value = retrieved_value
                if self._value is not None:
                    self._timestamp = datetime.fromtimestamp(self._pv.timestamp)
                return self._value
            else:
                retrieved_value = self._pv.get(
                    as_numpy=as_numpy,
                    count=count,
                    timeout=1.0,
                )
            if isinstance(expected_type, list):
                is_valid_type = any(
                    [isinstance(retrieved_value, type_) for type_ in expected_type]
                )
                if not is_valid_type:
                    raise ValueError
            if not isinstance(expected_type, list):
                if not isinstance(retrieved_value, expected_type):
                    raise ValueError
            self._value = retrieved_value
            if self._value is not None:
                self._timestamp = datetime.fromtimestamp(self._pv.timestamp)
            return self._value
        except ValueError:
            if retrieved_value is None:
                warnings.warn(
                    f"Failed to get value from {self._pv.pvname} due to failed connection",
                    FailedEPICSOperationWarning,
                )
            else:
                warnings.warn(
                    f"Expected {expected_type} to be retrieved from {self._pv.pvname}."
                    + f" Instead {type(retrieved_value)} was returned.",
                    category=FailedEPICSOperationWarning,
                )

    @use_initial_context
    def put(
        self,
        value: Any,
    ) -> None:
        """
        Set the value of a PV. Will raise a warning if `read_only` is True.

        :param value: Value to write to the PV
        :type value: Any
        """
        if not self.read_only:
            self._pv.put(value)
        else:
            warnings.warn(
                f"Failed to put to {self._pv.pvname} because read-only is {self.read_only}",
                category=FailedEPICSOperationWarning,
            )

    def connect(self) -> None:
        """
        Connect to a PV. Will raise a warning if the connection fails
        """
        if not self._pv.connected:
            warnings.warn(
                f"Failed to connect to {self._pv.pvname}",
                FailedEPICSOperationWarning,
            )

    @property
    @use_initial_context
    def timestamp(self) -> Union[str, None]:
        """
        Get the timestamp of the PV in ISO format if connected.
        """
        if self._timestamp:
            return self._timestamp.isoformat()
        return ""

    # TODO: Remove once all PV-types are converted
    @use_initial_context
    def activate(self, value: int = 1) -> None:
        """
        Sends an `activate` (1) signal to the PV

        :param value: Value to write to the PV (default 1)
        :type value: int
        """
        self.put(value=value)

    # TODO: Remove once all PV-types are converted
    @use_initial_context
    def send(self, value: int = 0) -> None:
        """
        Sends a `send` (0) signal to the PV

        :param value: Value to write to the PV (default 0)
        :type value: int
        """
        self.put(value=value)

    def __repr__(self) -> str:
        return (
            "<PVSignal>("
            + f"name={self._pv.pvname}, "
            + f"connected={self._pv.connected})"
        )


class StringPV(PVSignal):
    """
    Sub-class of :class:`~catapcore.common.machine.pv_utils.PVSignal` class for string-type PVs
    """

    _value: str
    """Value of the PV"""
    count: int = 256
    """Length of the PV"""

    def __init__(self, *args, **kwargs):
        super(StringPV, self).__init__(*args, **kwargs)

    def __repr__(self) -> str:
        return (
            "<StringPV>("
            + f"name={self._pv.pvname}, timestamp={self._timestamp},"
            + f" value={self._value})"
        )

    @model_validator(mode="after")
    def create_pv_instance(self):
        if self.protocol == "CA":
            self._pv = CA(pvname=self.name, timeout=EPICS_TIMEOUT, auto_monitor=False)
        elif self.protocol == "PVA":
            self._pv = PVA(pvname=self.name, timeout=EPICS_TIMEOUT)
        return self

    def put(
        self,
        value: str,
    ) -> None:
        try:
            if not (isinstance(value, str)):
                raise ValueError
            super().put(value=value)
        except ValueError:
            warnings.warn(
                f"Cannot put value of type {type(value)} to pv {self._pv.pvname}."
                + f" Expected type: {self._pv.type}",
                category=FailedEPICSOperationWarning,
            )

    def get(self) -> str:
        """
        Get the current value of a PV (see :func:`~catapcore.common.machine.pv_utils.PVSignal.get`)

        :returns: Current value of the PV
        :rtype: str
        """
        return super().get(
            expected_type=str,
            as_string=True,
            count=self.count,
        )


class ScalarPV(PVSignal):
    """
    Sub-class of :class:`~catapcore.common.machine.pv_utils.PVSignal` class for scalar-type PVs
    """

    units: str = "arb. units"
    """Units of the PV"""
    _value: float | int
    """Value of the PV"""

    def __init__(self, *args, **kwargs):
        super(ScalarPV, self).__init__(*args, **kwargs)

    def __repr__(self) -> str:
        if self._value is not None:
            return (
                "<ScalarPV>("
                + f"name={self._pv.pvname}, timestamp={self.timestamp},"
                + f" value={round(self._value, 5)})"
            )
        return (
            f"<ScalarPV>(name={self._pv.pvname}, timestamp={self.timestamp},"
            + f" value={self._value})"
        )

    def put(
        self,
        value: float | int,
    ) -> None:
        """
        Set the value of a PV. Will raise a warning if `read_only` is True or if the type is incorrect.

        :param value: Value to write to the PV
        :type value: Union[float, int]
        """
        try:
            if not (isinstance(value, float) or isinstance(value, int)):
                raise ValueError
            super().put(value=value)
        except ValueError:
            warnings.warn(
                f"Cannot put value of type {type(value)} to pv {self._pv.pvname}."
                + f" Expected type: {self._pv.type}",
                category=FailedEPICSOperationWarning,
            )

    def get(self) -> float | int:
        """
        Get the current value of a PV (see :func:`~catapcore.common.machine.pv_utils.PVSignal.get`)

        :returns: Current value of the PV
        :rtype: Union[float, int]
        """
        return super().get(expected_type=[float, int])


class StatePV(PVSignal):
    """
    Sub-class of :class:`~catapcore.common.machine.pv_utils.PVSignal` class for enum-type PVs
    """

    _value: int
    """Value of the PV as int"""
    _state: Enum
    """Enum of the PV (str, int)"""
    states: EnumMeta
    """Mapping between state names as string and values as integers"""

    def __init__(self, *args, **kwargs):
        super(StatePV, self).__init__(*args, **kwargs)

    @field_validator("states", mode="before")
    def validate_states(cls, v: Dict):
        """Convert the states from yaml-format to StateMap enums"""
        return StateMap(
            value="State",
            names=v,
        )

    def __repr__(self):
        return (
            "<StatePV>("
            + f"name={self._pv.pvname}, timestamp={self._timestamp},"
            + f" value={self._value})"
        )

    def put(
        self,
        value: int | str | Enum,
    ) -> None:
        """
        Set the value of a PV. Will raise a warning if `read_only` is True or if the state map is invalid.

        :param value: Value to write to the PV
        :type value: Union[str, int]
        """
        try:
            if isinstance(value, Enum):
                if value not in self.states:
                    raise ValueError
                super().put(value)
            elif isinstance(value, bool):
                raise ValueError
            elif isinstance(value, str):
                set_state: Enum = self.states[value]
                super().put(set_state.value)
            elif isinstance(value, int):
                set_state: Enum = self.states(value)
                super().put(set_state.value)
            else:
                raise ValueError
        except (KeyError, ValueError):
            warnings.warn(
                FailedEPICSOperationWarning(
                    f"Could not find valid state map for {value} in {self.states}."
                )
            )

    def get(self) -> Enum | None:
        """
        Get the current value of a PV (see :func:`~catapcore.common.machine.pv_utils.PVSignal.get`).
        The enum returned is based on the map provided to the config file.
        Will raise a warning if this map is not provided

        :returns: Current value of the PV
        :rtype: Union[Enum, None]
        """
        super().get(expected_type=[int, float])
        try:
            if self._value is not None:
                self._state = self.states(int(self._value))
                if self._state is not None:
                    self._timestamp = datetime.fromtimestamp(self._pv.timestamp)
            else:
                raise ValueError
        except ValueError:
            warnings.warn(
                FailedEPICSOperationWarning(
                    f"{self._pv.pvname} : Could not find valid state map for {self._value} in state map."
                )
            )
            return None
        return self._state


class BinaryPV(PVSignal):
    """
    Sub-class of :class:`~catapcore.common.machine.pv_utils.PVSignal` class for binary-type PVs
    """

    _value: bool | Literal[0, 1]
    """Value of the PV"""

    def __init__(self, *args, **kwargs):
        super(BinaryPV, self).__init__(*args, **kwargs)

    def __repr__(self):
        return (
            "<BinaryPV>("
            + f"name={self._pv.pvname}, timestamp={self._timestamp},"
            + f" value={self._value})"
        )

    def put(
        self,
        value: bool | int,
    ) -> None:
        """
        Set the value of a PV. Will raise a warning if `read_only` is True or if `value` is not 0 or 1 (or a boolean).

        :param value: Value to write to the PV
        :type value: Union[bool, int]
        """
        try:
            if not (isinstance(value, bool) or value in [0, 1]):
                raise ValueError
            super().put(value=int(value))
        except ValueError:
            warnings.warn(
                f"Cannot put value of type {type(value)} with value {value} to pv {self._pv.pvname}."
                + " Expected type: bool, 0, or 1",
                category=FailedEPICSOperationWarning,
            )

    def get(self) -> bool | int:
        """
        Get the current value of a PV (see :func:`~catapcore.common.machine.pv_utils.PVSignal.get`)

        :returns: Current value of the PV
        :rtype: Union[bool, int]
        """
        return bool(super().get(expected_type=[bool, int]))

    @use_initial_context
    def activate(self, value: int = 1) -> None:
        self.put(value=value)

    @use_initial_context
    def send(self, value: int = 0) -> None:
        self.put(value=value)


class WaveformPV(PVSignal):
    """
    Sub-class of :class:`~catapcore.common.machine.pv_utils.PVSignal` class for waveform-type PVs
    """

    _value: np.ndarray
    """Value of the PV"""

    units: str = "arb. units"
    """Units of the PV"""

    def __init__(self, *args, **kwargs):
        super(WaveformPV, self).__init__(*args, **kwargs)

    @model_validator(mode="after")
    def create_pv_instance(self):
        if self.protocol == "CA":
            self._pv = CA(pvname=self.name, timeout=EPICS_TIMEOUT, auto_monitor=False)
        elif self.protocol == "PVA":
            self._pv = PVA(pvname=self.name, timeout=EPICS_TIMEOUT)
        return self

    def __repr__(self):
        return (
            "<WaveformPV>("
            + f"name={self._pv.pvname}, timestamp={self._timestamp},"
            + f"connected={self._pv.connected})"
        )

    def get(self, count: int = 1, as_numpy: bool = True) -> np.ndarray:
        """
        Get the current value of a PV (see :func:`~catapcore.common.machine.pv_utils.PVSignal.get`)

        :param count: Length of the PV
        :param as_numpy: Convert return value to numpy array
        :type count: int
        :type as_numpy: bool

        :returns: Current value of the PV
        :rtype: numpy.ndarray
        """
        return super().get(
            expected_type=np.ndarray,
            as_numpy=as_numpy,
            count=count,
        )

    def put(self, value: np.ndarray | list) -> None:
        """
        Set the value of a PV. Will raise a warning if `read_only` is True or if the type is incorrect.

        :param value: Value to write to the PV
        :type value: Union[numpy.ndarray, list]
        """
        if not (isinstance(value, list) or isinstance(value, np.ndarray)):
            raise ValueError
        else:
            if isinstance(value, np.ndarray):
                value = value.flatten().tolist()
            elif isinstance(value, list):
                value = value
            super().put(value=value)


class StatisticalPV(ScalarPV):
    """
    Sub-class of :class:`~catapcore.common.machine.pv_utils.PVSignal` class for statistical-type PVs
    """

    model_config = ConfigDict(
        extra="allow",
        frozen=False,
        arbitrary_types_allowed=True,
    )
    auto_buffer: bool
    """Flag to indicate whether to begin buffering automatically"""
    buffer_capacity: PositiveInt = Field(alias="buffer_size")
    """Size of the buffer"""

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super(StatisticalPV, self).__init__(*args, **kwargs)
        self._is_buffering = False
        self._value = self.pv._value
        self._timestamp = self.pv._timestamp
        self._min = float_info.max
        self._max = float_info.min
        self._mean = None
        self._stdev = None
        self._median = None
        self._mode = None
        self._buffer_size = self.buffer_capacity
        self._buffer = deque(maxlen=self._buffer_size)
        self.lock = threading.RLock()
        self._callback_index = None
        if self.auto_buffer:
            if isinstance(self._pv, PVA):
                self._callback_index = self._pv.add_callback(
                    self.update_pva_stats,
                )
            else:
                self._callback_index = self._pv.add_callback(
                    self.update_ca_stats,
                )
            self._is_buffering = True

    def __repr__(self) -> str:
        if self._is_buffering and self.stdev:
            return (
                "<StatisticalPV>("
                + f"name={self._pv.pvname}, timestamp={self.timestamp}, value={round(self._value, 5)},"
                + f" min={round(self.min, 5)}, max={round(self.max, 5)}, mean={round(self.mean, 5)},"
                + f"stdev={round(self.stdev, 5)}, buffer_full={self.is_buffer_full}"
                + ")"
            )
        else:
            return f"<StatisticalPV>(name={self._pv.pvname}, buffering={self._is_buffering})"

    def update_pva_stats(self, update):
        try:
            if isinstance(update, ntfloat) or isinstance(update, ntint):
                timestamp = update.timestamp
                value = update.real
                with self.lock:
                    self._buffer.append((timestamp, value))
                    if len(self._buffer) > 2:
                        self._mean = mean([v for _, v in self._buffer])
                        self._stdev = stdev(
                            [v for _, v in self._buffer], xbar=self._mean
                        )
                        self._median = median([v for _, v in self._buffer])
                        self._mode = mode([v for _, v in self._buffer])

                if abs(value) > abs(self._max):
                    self._max = value
                if abs(value) < abs(self._min):
                    self._min = value
                self._value = value
                self._timestamp = (
                    datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
                )
        except Exception as e:
            warnings.warn(
                FailedEPICSOperationWarning(f"Callback error: {e}"),
            )

    @use_initial_context
    def update_ca_stats(
        self, value: float | int | ntfloat | ntint, timestamp: float = None, **kw
    ):
        """
        Update the buffer statistics and push back the buffer deque

        :param value: New value for the buffer
        :param timestamp: Timestamp of new value
        :type value: Union[float, int]
        :type timestamp: float
        """
        if isinstance(value, ntfloat) or isinstance(value, ntint):
            # Decode the value and timestamp from p4p types to native types
            timestamp = value.timestamp
            value = value.real
        self._value = value
        if timestamp:
            self._timestamp = datetime.fromtimestamp(timestamp)
        else:
            self._timestamp = datetime.now()
        self._buffer.append((timestamp, value))
        if len(self._buffer) > 2:
            self._mean = mean([v for _, v in self._buffer])
            self._stdev = stdev([v for _, v in self._buffer], xbar=self._mean)
            self._median = median([v for _, v in self._buffer])
            self._mode = mode([v for _, v in self._buffer])
        if abs(value) > abs(self._max):
            self._max = value
        if abs(value) < abs(self._min):
            self._min = value

    @property
    def buffer(self) -> list:
        """
        Get the statistics buffer

        :return: Buffer object
        :rtype: List
        """
        with self.lock:
            return list(self._buffer)

    @property
    def max(self) -> float:
        """
        Get the maximum value in the statistics buffer

        :return: Max value
        :rtype: float
        """
        return self._max

    @property
    def min(self) -> float:
        """
        Get the minimum value in the statistics buffer

        :return: Min value
        :rtype: float
        """
        return self._min

    @property
    @use_initial_context
    def stdev(self) -> float:
        """
        Get the standard deviation of the statistics buffer

        :return: std. dev
        :rtype: float
        """
        return self._stdev

    @property
    @use_initial_context
    def mean(self) -> float:
        """
        Get the mean value of the statistics buffer
        """
        return self._mean

    @property
    @use_initial_context
    def mode(self) -> float:
        """
        Get the mode value of the statistics buffer

        :return: Mode value
        :rtype: float
        """
        return self._mode

    @property
    @use_initial_context
    def median(self) -> float:
        """
        Get the median value of the statistics buffer

        :return: Median value
        :rtype: float
        """
        return self._median

    @property
    def buffer_size(self) -> int:
        """
        The size of the statistics buffer

        :getter: Get the buffer size
        :setter: Set the buffer size
        :type: int
        """

        return self._buffer_size

    @property
    def is_buffer_full(self) -> bool:
        """
        Check if the buffer is full (i.e. length of `_buffer` is equal to its maximum length)

        :return: True if full
        :rtype: bool
        """
        with self.lock:
            return len(self._buffer) == self._buffer.maxlen

    def clear_buffer(self) -> None:
        """
        Empty the statistics buffer
        """
        with self.lock:
            self._buffer.clear()

    @buffer_size.setter
    def buffer_size(self, size: int) -> None:
        with self.lock:
            self._buffer = deque(self.buffer, maxlen=size)
            self._buffer_size = size

    def stop_buffering(self) -> None:
        """
        Stop adding values to the statistics buffer
        """
        self._pv.remove_callback(self._callback_index)
        self._callback_index = None
        self._is_buffering = False

    def start_buffering(self) -> None:
        """
        Stop adding values to the statistics buffer
        """
        if self._callback_index is None:
            with self.lock:
                self.buffer.clear()
            if isinstance(self._pv, CA):
                self._callback_index = self._pv.add_callback(self.update_ca_stats)
            elif isinstance(self._pv, PVA):
                self._callback_index = self._pv.add_callback(self.update_pva_stats)
            self._is_buffering = True

    @property
    def is_buffering(self) -> bool:
        """
        Check if the PV is buffering

        :returns: True if buffering
        :rtype: bool
        """
        return self._is_buffering


class PVInfo(BaseModel):
    """
    Base class for defining attributes associated with a PV
    """

    pv: str
    """Full name of PV"""
    virtual_pv: str | None = None
    """Virtual PV name, if applicable"""
    description: str | None = None
    """Description of PV"""
    type: Type[
        ScalarPV | BinaryPV | StatePV | StringPV | WaveformPV | StatisticalPV
    ] = StatisticalPV
    """Type of PV (see :mod:`~catapcore.common.machine.pv_utils`)"""
    protocol: Literal["CA", "PVA"] = "CA"
    """Chosen Protocol for the PV (ChannelAccess or PVAccess)"""
    auto_buffer: bool | None = None
    """Automatically start buffering the PV on instantiation"""
    buffer_size: PositiveInt | None = 10
    """Size of statistics buffer"""
    states: Dict | None = None
    """State map of states to integers for :class:`~catapcore.common.machine.pv_utils.StatePV` types"""
    read_only: bool = True
    """Flag to enable write access to PVs"""
    units: str = "arb. units"
    """ Units for the PV """
    _type_definitions: ClassVar[Dict[str, Type]] = {
        "scalar": ScalarPV,
        "binary": BinaryPV,
        "state": StatePV,
        "waveform": WaveformPV,
        "statistical": StatisticalPV,
        "string": StringPV,
    }
    """Possible PV types (see :mod:`~catapcore.common.machine.pv_utils`"""

    @field_validator("type", mode="before")
    def validate_pv_type(cls, v: str) -> Type:
        try:
            return cls._type_definitions[v]
        except KeyError:
            raise UnexpectedPVEntry(
                f"PV Type {v} has not been defined as a PV type."
                + f" Please use the defined types: {list(cls._type_definitions.keys())}",
            )

    def create(
        self,
    ) -> ScalarPV | BinaryPV | StatePV | StringPV | WaveformPV | StatisticalPV:
        """
        Create specific instance of a PV based on `type` (see :mod:`~catapcore.common.machine.pv_utils`)

        :return: Instance of PV object
        :rtype: Union[:class:`~catapcore.common.machine.pv_utils.ScalarPV`,
        :class:`~catapcore.common.machine.pv_utils.BinaryPV`,
        :class:`~catapcore.common.machine.pv_utils.StatePV`,
        :class:`~catapcore.common.machine.pv_utils.WaveformPV`,
        :class:`~catapcore.common.machine.pv_utils.StatisticalPV`,
        :class:`~catapcore.common.machine.pv_utils.StringPV`]
        """
        if self.type == ScalarPV:
            return ScalarPV(
                name=self.pv,
                description=self.description,
                read_only=self.read_only,
                protocol=self.protocol,
                units=self.units,
            )
        if self.type == BinaryPV:
            return BinaryPV(
                name=self.pv,
                description=self.description,
                read_only=self.read_only,
                protocol=self.protocol,
            )
        if self.type == StatePV:
            return StatePV(
                name=self.pv,
                description=self.description,
                states=self.states,
                read_only=self.read_only,
                protocol=self.protocol,
            )
        if self.type == WaveformPV:
            return WaveformPV(
                name=self.pv,
                description=self.description,
                read_only=self.read_only,
                protocol=self.protocol,
                units=self.units,
            )
        if self.type == StatisticalPV:
            return StatisticalPV(
                name=self.pv,
                description=self.description,
                auto_buffer=self.auto_buffer,
                buffer_size=self.buffer_size,
                read_only=self.read_only,
                protocol=self.protocol,
                units=self.units,
            )
        if self.type == StringPV:
            return StringPV(
                name=self.pv,
                description=self.description,
                read_only=self.read_only,
                protocol=self.protocol,
            )


def return_none_if_epics_warns(func: Callable):
    """
    Return `None` if an EPICS warning is raised when calling a function:

    :param func: Function to call
    :type func: Callable

    :returns: Result of function if successful
    :rtype: Callable, None
    """

    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AttributeError:
            return None
        except FailedEPICSOperationWarning:
            return None

    return inner

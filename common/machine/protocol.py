import warnings
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

# To set the ca.dll path for pyepics from p4p
import epicscorelibs.path.pyepics  # noqa: F401
import numpy as np
from epics import PV, ca
from p4p.client.thread import Context
from p4p.nt.scalar import ntstr, ntstringarray
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from catapcore.common.exceptions import FailedEPICSOperationWarning
from catapcore.config import EPICS_TIMEOUT


class Protocol(BaseModel, ABC):
    """
    Base class for defining control system interaction protocol
    """

    pvname: str
    """pv name"""
    timeout: float = Field(default=EPICS_TIMEOUT)
    """timeout for connection to the control system and other operations"""

    # Pydantic model config
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=False)
    """pydantic model config"""

    # Internal state (not serialized/validated)
    _value: Any = PrivateAttr(default=None)
    """internal reference to the value of the PV, updated in :meth:`get`"""
    _timestamp: Any = PrivateAttr(default=None)
    """internal reference to the timestamp of the PV, updated in :meth:`get`"""

    @property
    def connected(self) -> bool:
        """
        Connection status of the control system
        Returns:
            bool: True if the connection to the control system is established, False otherwise
        """
        return self._connected

    @property
    def type(self) -> Optional[str]:
        """
        The type of value returned by the protocol
        Returns:
            str: The type returned by :meth:`get` or used in :meth:`put`
        """
        return self._type

    @property
    def timestamp(self) -> float:
        """
        Last timestamp from :meth:`get` request
        Returns:
            float: Seconds past the unix epoch.
        """
        return self._timestamp

    @property
    def value(self) -> float:
        """
        Last value from :meth:`get` request
        Returns:
            float: Value retrieved from the protocol
        """
        return self._value

    @abstractmethod
    def get(self, *args, **kwargs) -> Any:
        """
        To be implemented by the child Protocol class
        Returns:
            Any: The value retrieved from the protocol.
        """
        raise NotImplementedError()

    @abstractmethod
    def put(self, value: Any) -> None:
        """
        To be implemented by the child Protocol class
        :param value: value to be sent to the PV via the protocol
        """
        raise NotImplementedError()

    @abstractmethod
    def add_callback(self, callback: Callable) -> int:
        """
        To be implemented by the child Protocol class
        :param callback: The function which will be called by the protocol on update.
        Returns:
            int: The callback index for the registered callback
        """
        raise NotImplementedError()

    @abstractmethod
    def remove_callback(self, callback_index: int) -> None:
        """
        To be implemented by the child Protocol class
        :param callback_index: The callback index returned from :meth:`add_callback` after registration
        """
        raise NotImplementedError()


class PVA(Protocol):
    """
    PV Access Protocol Implementation
    """

    def __init__(self, **data):
        """
        Initialize the PVA protocol instance.

        Args:
            **data: Arbitrary keyword arguments passed to the parent Protocol class.
        """
        super().__init__(**data)
        self._ctx = Context("pva")
        self._connected = False
        self._type: Optional[str] = None
        self._value: Optional[Any] = None
        self._timestamp: Optional[Any] = None
        self._callbacks: list[Callable] = []
        # Start a single monitor
        self._sub = self._ctx.monitor(self.pvname, self._dispatch_callback)

    def _dispatch_callback(self, update: Any):
        if isinstance(update, Exception):
            self._connected = False
            warnings.warn(
                f"Connection to PV {self.pvname} failed: {type(update)}:{update}",
                category=RuntimeWarning,
            )
            return

        self._connected = True
        self._type = type(update).__name__

        # Extract value and timestamp
        if isinstance(update, ntstr):
            val = update.removeprefix("")
        elif isinstance(update, ntstringarray):
            val = np.array(update)
        else:
            val = update.real

        self._value = val
        self._timestamp = update.timestamp

        # Dispatch to all registered callbacks
        for cb in self._callbacks:
            try:
                cb(update)
            except Exception as e:
                warnings.warn(
                    f"Callback raised exception: {e}", category=RuntimeWarning
                )

    # def _connection_callback(
    #     self,
    #     state: (
    #         ntfloat
    #         | ntint
    #         | ntbool
    #         | ntstr
    #         | ntnumericarray
    #         | ntstringarray
    #         | ntenum
    #         | ntndarray
    #         | Exception
    #     ),
    # ):
    #     """
    #     Callback for connection state changes.

    #     Args:
    #         state: The state object or exception indicating the connection status.
    #     """
    #     if isinstance(state, (Disconnected, TimeoutError, RemoteError, Cancelled)):
    #         # not entirely sure what the second two states represent so for now we assume that it means
    #         # the PV isn't connected and we just log the warning
    #         self._connected = False
    #         warnings.warn(
    #             f"Connection to PV {self.pvname} could not be established due to: {type(state)}:{state}",
    #             category=FailedEPICSOperationWarning,
    #         )
    #     else:
    #         self._connected = True
    #         # TODO work out if there's a better way of getting this rather than mangling
    #         # the type of the returned value
    #         self._type = type(state).__name__

    def get(self, *args, **kwargs) -> Any | None:
        _val = self._ctx.get(self.pvname, timeout=self.timeout, throw=False)
        if isinstance(_val, Exception):
            warnings.warn(
                f"Could not retrieve value of {self.pvname} due to: {type(_val)}:{_val}",
                category=FailedEPICSOperationWarning,
            )
            return None
        elif isinstance(_val, ntstr):
            val = _val.removeprefix("")
        elif isinstance(_val, ntstringarray):
            val = np.array(_val)
        else:
            # NOTE .real will work for double, integer, enum and array types
            # in the case of the Enum type it returns the index of the list of choices
            val = _val.real
        self._value = val
        self._timestamp = _val.timestamp
        return val

    def put(self, value: Any) -> None:
        result = self._ctx.put(self.pvname, value, timeout=self.timeout, throw=False)
        if result is not None:
            warnings.warn(
                f"Could not update {self.pvname} to {value}: {type(result)}:{result}",
                category=RuntimeWarning,
            )

    def add_callback(self, callback: Callable[[Any], None]) -> int:
        """
        Register a callback to be called on PV updates.

        Args:
            callback: A function accepting a single argument (the PV update).

        Returns:
            int: Index of the registered callback.
        """
        self._callbacks.append(callback)
        return len(self._callbacks) - 1

    def remove_callback(self, callback_index: int) -> None:
        """
        Remove a previously registered callback.

        Args:
            callback_index: The index of the callback to remove. Generated when :meth:`add_callback` is used.
        """
        # in p4p we don't remove the callback we can just stop it
        self._callbacks[callback_index].close()


class CA(Protocol):
    def __init__(self, auto_monitor: bool = False, **data):
        """
        Initialize the CA protocol instance.

        Args:
            auto_monitor (bool): Whether to enable automatic monitoring of the PV.
            **data: Arbitrary keyword arguments passed to the parent Protocol class.
        """
        super().__init__(**data)
        self._pv = PV(
            self.pvname,
            auto_monitor=auto_monitor,
            connection_timeout=self.timeout,
        )

    def get(
        self,
        as_numpy: bool = False,
        count: int = 1,
        as_string: bool = False,
        timeout=EPICS_TIMEOUT,
    ):
        """
        Retrieve the value of the PV using CA protocol.

        Args:
            as_numpy (bool): Whether to return the value as a numpy array.
            count (int): Number of values to retrieve.
            as_string (bool): Whether to return the value as a string.
            timeout (float): Timeout for the get, put, and connection operations.

        Returns:
            The value retrieved from the PV.
        """
        ca.use_initial_context()
        if self._pv.auto_monitor:
            if as_string:
                retrieved_value = self._pv.char_value
            else:
                retrieved_value = self._pv.value
        else:
            retrieved_value = self._pv.get(
                as_numpy=as_numpy,
                as_string=as_string,
                count=count,
                timeout=EPICS_TIMEOUT,
            )
        self._timestamp = self._pv.timestamp
        return retrieved_value

    def put(self, value: Any):
        """
        Set the value of the PV using CA protocol.

        Args:
            value: The value to set on the PV.
        """
        self._pv.put(
            value=value,
            wait=True,
            use_complete=True,
            timeout=self.timeout,
        )

    def add_callback(self, callback: Callable) -> int:
        """
        Register a callback to be called on PV updates.

        Args:
            callback: The function to call when the PV updates.

        Returns:
            int: The index of the registered callback.
        """
        return self._pv.add_callback(callback)

    def remove_callback(self, callback_index: int) -> None:
        """
        Remove a previously registered callback.

        Args:
            callback_index: The index of the callback to remove. Generated when :meth:`add_callback` is used
        """
        self._pv.remove_callback(callback_index)

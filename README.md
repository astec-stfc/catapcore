# catapcore

A Middle Layer Python framework for interacting with EPICS PVs (via Channel Access and PV Access protocols) through an object-oriented interface. This library provides a structured way to define, manage, and control complex hardware setups.

## Overview

catapcore is a core framework that enables users to interact with EPICS PVs through defined Python classes. Instead of directly managing PV connections and values, users create custom hardware classes that inherit from the framework's base classes to encapsulate hardware-specific behavior and control logic.

### Key Features

- **Unified PV Access**: Support for both Channel Access (CA) and PV Access (PVA) protocols
- **Type-Safe PV Management**: Define PVs with specific types (Scalar, Binary, State, String, Waveform)
- **Statistical Analysis**: Built-in support for statistical PVs with buffering and analysis capabilities
- **Hardware Abstraction**: Object-oriented interface for defining custom hardware classes
- **Snapshot Functionality**: Save and restore hardware states with snapshot management
- **Virtual Control System Support**: Mock EPICS connections for testing and development
- **Structured Configuration**: YAML-based hardware configuration with machine area support

## Architecture

### Core Classes

The framework is built around five main base classes that work together to provide a complete hardware interaction system:

#### 1. **PVMap** (`common.machine.hardware.PVMap`)
Maps and manages EPICS PV connections for a specific hardware object.

- Handles both physical and virtual PV connections
- Supports automatic connection on creation
- Manages different PV types (Scalar, Binary, State, String, Waveform)
- Tracks statistical PVs separately for analysis
- Validates PVs using Pydantic models

**Key Methods:**
- `statistics`: Get all statistical PVs
- `pvs`: Get all PVs in the map
- `is_buffer_full()`: Check if statistics buffers are full
- `clear_buffer()`: Clear statistics buffers
- `set_buffer_size()`: Configure buffer sizes
- `start_buffering()`: Start collecting statistics
- `stop_buffering()`: Stop collecting statistics

#### 2. **ControlsInformation** (`common.machine.hardware.ControlsInformation`)
Provides access to PVs and control functionality for a hardware object.

- Wraps the `PVMap` for PV access
- Delegates statistical operations to the underlying PVMap
- Acts as the interface for reading/writing PV values
- Inherits from Pydantic BaseModel for validation

**Key Methods:**
- `statistics`: Access statistical PVs
- `is_buffer_full()`: Check buffer status
- `clear_buffer()`: Clear buffers
- `set_buffer_size()`: Set buffer sizes
- `start_buffering()`: Start statistics collection
- `stop_buffering()`: Stop statistics collection

#### 3. **Properties** (`common.machine.hardware.Properties`)
Defines and manages metadata and static information about hardware.

Attributes include:
- `name`: Hardware object name
- `name_alias`: Alternative names for the object
- `hardware_type`: Type classification (e.g., "magnet", "detector")
- `position`: Z-position along the lattice (meters)
- `machine_area`: Location in the accelerator
- `subtype`: Optional hardware subtype

#### 4. **Hardware** (`common.machine.hardware.Hardware`)
The main high-level interface combining `PVMap`, `ControlsInformation`, and `Properties`.

- Provides unified interface for hardware interaction, ability to combine `ControlsInformation` with `Property` information
- Supports snapshot creation and restoration
- Handles virtual and physical control system modes

**Key Methods:**
- `create_snapshot()`: Capture current hardware state
- `apply_snapshot()`: Restore hardware to a saved state

#### 5. **Factory** (`common.machine.factory.Factory`)
Creates and manages multiple Hardware objects of the same type.

- Loads hardware configurations from folder of YAML files
- Instantiates hardware objects from config templates
- Supports filtering by machine area
- Supports filtering by hardware type
- Manages hardware lifecycle (creation, connection, disconnection)

**Key Methods:**
- `create_hardware()`: Instantiate hardware objects
- `get_hardware_by_area()`: Filter hardware by machine area
- `get_hardware()`: Retrieve specific hardware
- `create_snapshot()`: Capture all current hardware states
- `apply_snapshot()`: Restore all hardware to a saved state
- `save_snapshot()`: Save snapshot to yaml file
- `load_snapshot()`: Load snapshot in memory from yaml file

#### 6. **High-Level System** (`common.machine.high_level_system.HighLevelSystem`)
Creates and manages multiple Hardware objects of different types.

- Loads hardware configurations from folder of YAML files (types/names listed in `components` field)
- Checks the types of each Hardware component against Pydantic definition
- Snapshot functionality from `HighLevelSystem` level

**Key Methods:**:
- `create_snapshot()`: Capture all current component states
- `apply_snapshot()`: Restore all components to a saved state



## Usage Examples

### Basic Hardware Definition

```python
from catapcore.common.machine.hardware import Hardware, PVMap, ControlsInformation, Properties
from catapcore.common.machine.pv_utils import ScalarPV, BinaryPV
from time import sleep

# Define a PVMap for your hardware
class MyDevicePVMap(PVMap):
    voltage: StatisticalPV
    current: StatisticalPV
    power_on: BinaryPV

    def __init__(
        self,
        is_virtual: bool,
        connect_on_creation: bool = False,
        *args,
        **kwargs,
    ):
        MyDevicePVMap.is_virtual = is_virtual
        MyDevicePVMap.connect_on_creation = connect_on_creation
        super().__init__(
            is_virtual=is_virtual,
            *args,
            **kwargs,
        )


# Define control information
class MyDeviceControls(ControlsInformation):
    pv_record_map: MyDevicePVMap

    @property
    def current(self) -> float:
        return self.pv_record_map.current.get()

    @current.setter
    def current(self, value: float) -> None:
        self.pv_record_map.current.put(value)

    @property
    def is_on(self) -> float:
        return self.pv_record_map.power_on.get()

    def switch_on(self) -> None:
        if not self.is_on:
            self.pv_record_map.power_on.put(True)

    def switch_off(self) -> None:
        if self.is_on:
            self.pv_record_map.power_on.put(False)

# Define static properties
class MyDeviceProperties(Properties):
    current_limit: float

# Create your hardware class
class MyDevice(Hardware):
    def __init__(self, is_virtual=True, **kwargs):
        super().__init__(is_virtual=is_virtual, **kwargs)

    @property
    def is_on(self) -> bool:
        return self.controls_information.is_on

    @property
    def is_off(self) -> bool:
        return not self.controls_information.is_on

    def switch_on(self) -> bool:
        return self.controls_information.switch_on

    def switch_off(self) -> bool:
        return not self.controls_information.switch_off

    @property
    def current(self) -> float:
        return self.controls_information.current

    @current.setter
    def current(self, value: float) -> None:
        if value > current_limt:
            raise ValueError(f"Unable to set {self.name} current because {value} was greater than limit: {current_limit}")
        if self.is_off:
            self.controls_information.switch_on()
        while not self.is_on:
            time.sleep(0.1)
        self.controls_information.current = value


```

### Using a Factory

```python
from catapcore.common.machine.hardware import Hardware
from catapcore.common.machine.area import MachineArea
from catapcore.common.machine.factory import Factory
from my_hardware import MyDevice

from typing import Dict, Union, List

class MyFactory(Factory):
    def __init__(
        self, 
        is_virtual=True,
        lattice_folder: str = None,
        hardware_type: Hardware,
        connection_on_creation: bool = False,
        areas: MachineArea | List[MachineArea]
    ):
        super().__init__(
            is_virtual=is_virtual,
            connection_on_creation=connection_on_creation,
            lattice_folder=lattice_folder,
            hardware_type=hardware_type,
            areas=areas,
        )
    
    def get_current(self, names: str | List[str] | None) -> Dict[str, float]:
        def _get_current(device: MyDevice) -> float:
            return device.current
        return self._get_property(names, property_=_get_current)

    def set_current(
        self, 
        names: str | List[str],
        values: float | List[float],
        settings: Dict[str, float] = None
    ):
        def _set_current(device: MyDevice, value: float) -> None:
            device.current = value
        if settings:
            self._set_property_multiple(
                settings=settings,
                setter_=_set_current,
            )
        else:
            self._set_property(
                names=names,
                values=value,
                setter_=_set_current,
            )

            

# Create a factory for multiple devices
factory = MyFactory(
    is_virtual=False,
    lattice_folder="./my_devices",
    hardware_type=MyDevice
    connect_on_creation=True
)

# Access hardware
devices = factory.hardware  # Dict[str, Hardware]

# Get hardware by name
device = factory.get_hardware("DEVICE_001")

# Get hardware by area
area_devices = factory.get_hardware_by_area("AREA_01")
```

### Working with Snapshots

```python
# Create a snapshot of current state
factory.current_snapshot.update()

# Save to file
factory.current_snapshot.save("my_snapshot.yaml")

# Load and apply a snapshot
factory.current_snapshot.load("my_snapshot.yaml")
factory.current_snapshot.apply()
```

### Working with Statistical PVs

```python
# Enable statistics collection
factory.hardware["DEVICE_001"].start_buffering("voltage")

# Check if buffer is full
if factory.hardware["DEVICE_001"].is_buffer_full("voltage"):
    stats = factory.hardware["DEVICE_001"].statistics["voltage"]
    print(f"Mean: {stats.mean()}, Std Dev: {stats.stdev()}")

# Clear buffers
factory.hardware["DEVICE_001"].clear_buffer(None)  # Clear all
```

## PV Types

The framework supports several PV types for different use cases:

- **ScalarPV**: Floating-point values
- **BinaryPV**: Boolean/on-off values
- **StatePV**: Enumerated states (requires StateMap)
- **StringPV**: Text values
- **WaveformPV**: Array data
- **StatisticalPV**: Scalar values with buffering for statistical analysis

## Configuration

### YAML Hardware Configuration

Hardware objects are typically defined in YAML files located in the `lattice` directory:

```yaml
controls_information:
    pv_record_map:
    voltage:
        pv: DEVICE:VOLTAGE
        type: statistical
        buffer_size: 10
        auto_buffer: True
    current:
        pv: DEVICE:CURRENT
        type: statistical
        buffer_size: 10
        auto_buffer: True
        virtual_pv: VIRTUAL:DEVICE:CURRENT
    power_on:
        pv: DEVICE:POWER
        type: binary
properties:
    name: DEVICE_001
    name_alias:
    - DEV_1
    hardware_type: MyDevice
    position: 10.5
    current_limt: 10
    machine_area: AREA_01

```

### Virtual vs. Physical Mode

Run in virtual mode for testing and development:

```python
factory = MyDevice(
    is_virtual=True,  # Use virtual prefix for all PV names
    connect_on_creation=True
)
```

Configure the virtual prefix in `config.py`:

```python
VIRTUAL_PREFIX = "TEST:"  # All PVs become "TEST:ORIGINAL_NAME" unless virtual_pv is defined in YAML
```

You can also specify virtual PVs on an individual basis in the YAML PV defintion.

## Installation

```bash
pip install -e .
```

## Dependencies

- pydantic: Data validation and settings
- pyepics: Channel Access protocol support
- p4p: PV Access protocol support
- epicscorelibs: EPICS core libraries
- ruamel.yaml: YAML configuration handling
- numpy: Numerical operations

## Documentation

Complete API documentation is available at: [https://astec-stfc.github.io/catapcore](https://astec-stfc.github.io/catapcore)

The documentation is automatically generated from docstrings and built using Sphinx. Updates are published when changes are merged to the main branch.

## License

See LICENSE file for details.

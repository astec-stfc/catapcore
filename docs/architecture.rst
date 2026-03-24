Architecture
=============

Overview
--------

catapcore is built on a layered architecture that provides progressively higher levels of abstraction for interacting with EPICS control systems. The framework is composed of five core base classes that work together to provide a complete hardware interaction system.

Core Components
---------------

PVMap
~~~~~

:class:`~catapcore.common.machine.hardware.PVMap` is the lowest-level component that directly manages EPICS PV connections.

**Responsibilities:**
- Map and connect to EPICS PVs
- Support both physical and virtual control systems
- Manage different PV types (Scalar, Binary, State, String, Waveform)
- Track statistical PVs separately for analysis
- Validate PVs using Pydantic models

**Key Properties:**
- ``pvs``: Dictionary of all PVs in the map
- ``statistics``: Dictionary of statistical PVs only

**Key Methods:**
- ``is_buffer_full()``: Check if statistics buffers are full
- ``clear_buffer()``: Clear statistics buffers
- ``set_buffer_size()``: Configure buffer sizes
- ``start_buffering()``: Start collecting statistics
- ``stop_buffering()``: Stop collecting statistics

ControlsInformation
~~~~~~~~~~~~~~~~~~~

:class:`~catapcore.common.machine.hardware.ControlsInformation` wraps :class:`~catapcore.common.machine.hardware.PVMap` to provide a controlled interface for accessing and manipulating PVs.

**Responsibilities:**
- Provide controlled access to PVs through the wrapped PVMap
- Delegate statistical operations to the underlying PVMap
- Act as the interface for reading and writing PV values
- Inherit from Pydantic BaseModel for validation

**Key Methods:**
- All methods from PVMap (``statistics``, ``is_buffer_full``, ``clear_buffer``, etc.)

Properties
~~~~~~~~~~

:class:`~catapcore.common.machine.hardware.Properties` defines and manages metadata and static information about a hardware object.

**Attributes:**
- ``name``: Unique name of the hardware object
- ``name_alias``: Alternative names for the object
- ``hardware_type``: Type classification (e.g., "magnet", "detector")
- ``position``: Z-position along the lattice (meters)
- ``machine_area``: Location in the accelerator structure
- ``subtype``: Optional hardware subtype for further categorization

Hardware
~~~~~~~~~

:class:`~catapcore.common.machine.hardware.Hardware` is the main user-facing interface that combines PVMap, ControlsInformation, and Properties.

**Architecture:**
- Inherits from Pydantic BaseModel for validation
- Composes ControlsInformation and Properties
- Provides unified interface for all hardware operations

**Key Features:**
- Snapshot creation and restoration
- Virtual and physical control system support
- Buffer and statistics management
- Hardware comparison and sorting

**Key Methods:**
- ``create_snapshot()``: Capture current hardware state
- ``apply_snapshot()``: Restore hardware to a saved state
- Comparison operators for sorting by area and position

Factory
~~~~~~~

:class:`~catapcore.common.machine.factory.Factory` creates and manages multiple Hardware objects of the same type.

**Responsibilities:**
- Load hardware configurations from YAML files
- Instantiate Hardware objects from templates
- Support filtering by machine area and subtype
- Manage hardware lifecycle (creation, connection, disconnection)
- Batch operations on multiple hardware objects

**Key Methods:**
- ``create_hardware()``: Instantiate hardware objects
- ``get_hardware_by_area()``: Filter by machine area
- ``get_hardware_by_name()``: Retrieve specific hardware
- ``get_hardware_by_subtype()``: Filter by subtype
- ``create_snapshot()``, ``load_snapshot()``, ``apply_snapshot()``: Manage snapshots

Design Patterns
---------------

Composition over Inheritance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rather than using deep inheritance hierarchies, catapcore uses composition to build complex objects from simpler components. Hardware is composed of ControlsInformation and Properties, not inherited from them.

Delegation
~~~~~~~~~~

Many methods in Hardware delegate to the underlying ControlsInformation and PVMap objects. This allows for clean separation of concerns while maintaining a simple user interface.

Pydantic Validation
~~~~~~~~~~~~~~~~~~~

All major classes inherit from Pydantic's BaseModel, providing:
- Automatic validation of input data
- Type checking at instantiation
- Easy serialization and deserialization
- Clear schema definition

PV Types
--------

catapcore supports several PV type classes, each optimized for specific data types:

- :class:`~catapcore.common.machine.pv_utils.ScalarPV`: Floating-point and integer values
- :class:`~catapcore.common.machine.pv_utils.BinaryPV`: Boolean/on-off values
- :class:`~catapcore.common.machine.pv_utils.StatePV`: Enumerated states with mapping
- :class:`~catapcore.common.machine.pv_utils.StringPV`: Text values
- :class:`~catapcore.common.machine.pv_utils.WaveformPV`: Array/waveform data
- :class:`~catapcore.common.machine.pv_utils.StatisticalPV`: Scalar with buffering and statistics

Control Protocols
-----------------

catapcore supports two EPICS control protocols:

- **Channel Access (CA)**: The traditional EPICS protocol, recommended for most applications
- **PV Access (PVA)**: The newer EPICS protocol with improved performance and features

Each PV can specify which protocol to use via the ``protocol`` attribute.

Virtual Mode Architecture
--------------------------

In virtual mode, catapcore prepends a virtual prefix to all PV names, allowing for testing and development without affecting the real control system:

.. code-block:: python

    # Physical mode
    pv_name = "DEVICE:VOLTAGE"  # Connects to actual EPICS PV

    # Virtual mode
    pv_name = "TEST:DEVICE:VOLTAGE"  # Connects to virtual/test PV

This is controlled by the ``is_virtual`` flag at all levels of the hierarchy, ensuring consistent behavior throughout the framework.

Snapshot Architecture
---------------------

Snapshots provide a mechanism to save and restore hardware states:

1. **Creation**: :meth:`~catapcore.common.machine.snapshot.Snapshot.update` reads current PV values
2. **Storage**: Snapshots can be saved to YAML files with timestamps
3. **Loading**: Snapshots can be loaded from files into memory
4. **Application**: :meth:`~catapcore.common.machine.snapshot.Snapshot.apply` writes saved values back to hardware

Snapshots can include:
- Current PV values
- Statistical buffer data (for buffering PVs)
- Additional metadata

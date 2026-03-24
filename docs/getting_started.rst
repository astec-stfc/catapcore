Getting Started
===============

Installation
------------

To install catapcore, use pip:

.. code-block:: bash

    pip install -e .

Or if you have the source code:

.. code-block:: bash

    cd catapcore
    pip install -e .

Basic Concepts
--------------

catapcore provides an object-oriented interface for interacting with EPICS PVs. The framework is built on five core classes:

1. **PVMap** - Maps and manages EPICS PV connections
2. **ControlsInformation** - Provides access to PVs and control functionality
3. **Properties** - Defines hardware metadata
4. **Hardware** - High-level interface combining the above three
5. **Factory** - Creates and manages multiple Hardware objects

Quick Start
-----------

Here's a minimal example to get you started:

.. code-block:: python

    from catapcore.common.machine.hardware import Hardware, PVMap, ControlsInformation, Properties
    from catapcore.common.machine.pv_utils import ScalarPV, BinaryPV

    # Define a PVMap for your hardware
    class MyDevicePVMap(PVMap):
        voltage = ScalarPV(name="DEVICE:VOLTAGE", description="Device voltage")
        current = ScalarPV(name="DEVICE:CURRENT", description="Device current")
        power_on = BinaryPV(name="DEVICE:POWER", description="Power status")

    # Define control information
    class MyDeviceControls(ControlsInformation):
        pv_record_map: MyDevicePVMap

    # Create your hardware class
    class MyDevice(Hardware):
        def __init__(self, is_virtual=True, **kwargs):
            super().__init__(is_virtual=is_virtual, **kwargs)

    # Use it
    device = MyDevice(is_virtual=True, connect_on_creation=True)

Virtual Mode
------------

For testing and development, catapcore supports a virtual mode where PV names are prefixed:

.. code-block:: python

    # This will use "TEST:DEVICE:VOLTAGE" instead of "DEVICE:VOLTAGE"
    device = MyDevice(is_virtual=True, connect_on_creation=False)

Physical Mode
-------------

To connect to real EPICS PVs:

.. code-block:: python

    device = MyDevice(is_virtual=False, connect_on_creation=True)

Next Steps
----------

- Check the :doc:`api_reference` for detailed class and method documentation
- See :doc:`examples` for more advanced usage patterns
- View the :doc:`architecture` for an in-depth explanation of the framework design

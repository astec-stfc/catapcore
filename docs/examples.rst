Examples
========

Basic Hardware Definition
--------------------------

Here's how to define a custom hardware class using catapcore:

.. code-block:: python

    from catapcore.common.machine.hardware import Hardware, PVMap, ControlsInformation, Properties
    from catapcore.common.machine.pv_utils import ScalarPV, BinaryPV, StatePV

    # Step 1: Define the PVMap
    class MyDevicePVMap(PVMap):
        """Maps EPICS PVs for MyDevice hardware."""
        voltage = ScalarPV(
            name="DEVICE:VOLTAGE",
            description="Device output voltage",
            units="Volts",
            read_only=False
        )
        current = ScalarPV(
            name="DEVICE:CURRENT",
            description="Device output current",
            units="Amperes",
            read_only=True
        )
        power_on = BinaryPV(
            name="DEVICE:POWER",
            description="Power status",
            read_only=False
        )

    # Step 2: Define the ControlsInformation
    class MyDeviceControls(ControlsInformation):
        """Provides controlled access to MyDevice PVs."""
        pv_record_map: MyDevicePVMap

        @property
        def is_powered_on(self) -> bool:
            """Check if device is powered on."""
            return self.pv_record_map.power_on.get()

        def power_on_device(self):
            """Turn the device on."""
            self.pv_record_map.power_on.put(True)

        def power_off_device(self):
            """Turn the device off."""
            self.pv_record_map.power_on.put(False)

    # Step 3: Define the Hardware
    class MyDevice(Hardware):
        """High-level interface for MyDevice hardware."""

        def __init__(self, is_virtual=True, **kwargs):
            super().__init__(is_virtual=is_virtual, **kwargs)

        def set_voltage(self, voltage: float):
            """Set the device voltage."""
            self.controls_information.pv_record_map.voltage.put(voltage)

        def get_voltage(self) -> float:
            """Get the current device voltage."""
            return self.controls_information.pv_record_map.voltage.get()

        def get_current(self) -> float:
            """Get the current device current."""
            return self.controls_information.pv_record_map.current.get()


Using a Factory
---------------

When you have multiple devices of the same type, use Factory to manage them:

.. code-block:: python

    from catapcore.common.machine.factory import Factory

    # Create a factory for managing multiple MyDevice instances
    factory = Factory(
        is_virtual=False,  # Use real EPICS
        lattice_folder="my_devices",  # YAML config folder
        hardware_type=MyDevice,
        connect_on_creation=True
    )

    # Access all hardware
    all_devices = factory.hardware  # Dict[str, Hardware]

    # Access specific hardware
    device_001 = factory.get_hardware("DEVICE_001")

    # Get hardware by machine area
    s02_devices = factory.get_hardware_by_area("S02")

    # Get hardware by subtype
    bending_magnets = factory.get_hardware_by_subtype("bending")


Working with Snapshots
----------------------

Save and restore hardware states:

.. code-block:: python

    # Create a snapshot of current state
    factory.create_snapshot()

    # Save to file
    factory.save_snapshot(filename="my_snapshot.yaml", comment="Initial setup")

    # Modify some hardware
    factory.get_hardware("DEVICE_001").set_voltage(10.5)

    # Load and apply a snapshot
    factory.load_snapshot(filename="my_snapshot.yaml", apply=True)


Statistical Analysis
--------------------

Collect statistics on PV values:

.. code-block:: python

    from catapcore.common.machine.pv_utils import StatisticalPV

    # In your PVMap, use StatisticalPV for values you want to analyze
    class MyDevicePVMap(PVMap):
        voltage = StatisticalPV(
            name="DEVICE:VOLTAGE",
            description="Device voltage with statistics",
            auto_buffer=True,
            buffer_size=100
        )

    # Later, access statistics
    device = factory.get_hardware("DEVICE_001")

    # Check if buffer is full
    if device.is_buffer_full("voltage"):
        stats = device.get_statistics("voltage")
        print(f"Mean: {stats.mean}")
        print(f"Std Dev: {stats.stdev}")
        print(f"Min: {stats.min}")
        print(f"Max: {stats.max}")

    # Manually control buffering
    device.start_buffering("voltage")
    device.set_buffer_size("voltage", 200)
    # ... do some operations ...
    device.stop_buffering("voltage")

    # Clear buffers when done
    device.clear_buffer("voltage")


Virtual Mode Testing
--------------------

Test your code without connecting to real EPICS:

.. code-block:: python

    # Create device in virtual mode
    device = MyDevice(
        is_virtual=True,
        connect_on_creation=False,
        properties={
            "name": "TEST_DEVICE",
            "hardware_type": "test_device",
            "position": 0.0,
            "machine_area": "TEST",
            "name_alias": []
        },
        controls_information={
            "pv_record_map": {
                "voltage": {"pv": "TEST:VOLTAGE", "type": "scalar"},
                "current": {"pv": "TEST:CURRENT", "type": "scalar"},
                "power_on": {"pv": "TEST:POWER", "type": "binary"}
            }
        }
    )

    # Use normally, but PVs will be virtual
    device.set_voltage(5.0)


Custom Hardware Methods
-----------------------

Add custom business logic to your Hardware classes:

.. code-block:: python

    class MyDevice(Hardware):
        """Hardware with custom methods."""

        def ramp_voltage(self, target: float, steps: int = 10, delay: float = 1.0):
            """Ramp voltage to target over multiple steps."""
            current = self.get_voltage()
            step_size = (target - current) / steps

            for i in range(1, steps + 1):
                new_voltage = current + (step_size * i)
                self.set_voltage(new_voltage)
                time.sleep(delay)

        def is_safe_state(self) -> bool:
            """Check if device is in a safe state."""
            return (
                self.get_voltage() < 50.0 and
                self.get_current() < 100.0 and
                not self.controls_information.is_powered_on
            )

        def emergency_shutdown(self):
            """Perform emergency shutdown."""
            self.set_voltage(0.0)
            self.controls_information.power_off_device()


Batch Operations
----------------

Perform operations on multiple devices:

.. code-block:: python

    # Start buffering on all devices
    factory.start_buffering(stats="voltage")

    # Get statistics from multiple specific devices
    device_names = ["DEVICE_001", "DEVICE_002", "DEVICE_003"]
    stats = factory.get_statistics(names=device_names, stats="voltage")

    # Set a property on all devices in an area
    area_devices = factory.get_hardware_by_area("S02", with_areas=False)
    for device_name, device in area_devices.items():
        device.set_voltage(10.0)

    # Stop buffering on all devices
    factory.stop_buffering(stats=None)  # None means all stats


Advanced: Dynamic Statistics Properties
----------------------------------------

Create dynamic statistics properties:

.. code-block:: python

    from catapcore.common.machine.hardware import add_stats_to_controls_information, add_stats_to_hardware

    class MyDeviceControls(ControlsInformation):
        pv_record_map: MyDevicePVMap

        @property
        def voltage(self) -> float:
            """Get voltage from PV map."""
            return self.pv_record_map.voltage.get()

    # Add statistics properties dynamically
    add_stats_to_controls_information(
        MyDeviceControls,
        target_func_name="get"
    )
    add_stats_to_hardware(MyDeviceControls, MyDevice)

    # Now you can access voltage_stats property
    device = MyDevice(...)
    print(device.voltage_stats.mean)

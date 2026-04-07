API Reference
=============

Core Hardware Classes
---------------------

PVMap
~~~~~

.. autoclass:: catapcore.common.machine.hardware.PVMap
   :members:
   :undoc-members:
   :show-inheritance:

ControlsInformation
~~~~~~~~~~~~~~~~~~~

.. autoclass:: catapcore.common.machine.hardware.ControlsInformation
   :members:
   :undoc-members:
   :show-inheritance:

Properties
~~~~~~~~~~

.. autoclass:: catapcore.common.machine.hardware.Properties
   :members:
   :undoc-members:
   :show-inheritance:

Hardware
~~~~~~~~

.. autoclass:: catapcore.common.machine.hardware.Hardware
   :members:
   :undoc-members:
   :show-inheritance:

Factory Classes
---------------

Factory
~~~~~~~

.. autoclass:: catapcore.common.machine.factory.Factory
   :members:
   :undoc-members:
   :show-inheritance:

PV Types
--------

PVSignal
~~~~~~~~

.. autoclass:: catapcore.common.machine.pv_utils.PVSignal
   :members:
   :undoc-members:
   :show-inheritance:

ScalarPV
~~~~~~~~

.. autoclass:: catapcore.common.machine.pv_utils.ScalarPV
   :members:
   :undoc-members:
   :show-inheritance:

BinaryPV
~~~~~~~~

.. autoclass:: catapcore.common.machine.pv_utils.BinaryPV
   :members:
   :undoc-members:
   :show-inheritance:

StatePV
~~~~~~~

.. autoclass:: catapcore.common.machine.pv_utils.StatePV
   :members:
   :undoc-members:
   :show-inheritance:

StringPV
~~~~~~~~

.. autoclass:: catapcore.common.machine.pv_utils.StringPV
   :members:
   :undoc-members:
   :show-inheritance:

WaveformPV
~~~~~~~~~~

.. autoclass:: catapcore.common.machine.pv_utils.WaveformPV
   :members:
   :undoc-members:
   :show-inheritance:

StatisticalPV
~~~~~~~~~~~~~~

.. autoclass:: catapcore.common.machine.pv_utils.StatisticalPV
   :members:
   :undoc-members:
   :show-inheritance:

PVInfo
~~~~~~

.. autoclass:: catapcore.common.machine.pv_utils.PVInfo
   :members:
   :undoc-members:
   :show-inheritance:

Control Protocols
-----------------

Protocol
~~~~~~~~

.. autoclass:: catapcore.common.machine.protocol.Protocol
   :members:
   :undoc-members:
   :show-inheritance:

CA
~~

.. autoclass:: catapcore.common.machine.protocol.CA
   :members:
   :undoc-members:
   :show-inheritance:

PVA
~~~

.. autoclass:: catapcore.common.machine.protocol.PVA
   :members:
   :undoc-members:
   :show-inheritance:

Snapshot Management
-------------------

Snapshot
~~~~~~~~

.. autoclass:: catapcore.common.machine.snapshot.Snapshot
   :members:
   :undoc-members:
   :show-inheritance:

Machine Area
------------

MachineArea
~~~~~~~~~~~

.. autoclass:: catapcore.common.machine.area.MachineArea
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
-------------

.. automodule:: catapcore.config
   :members:
   :show-inheritance:

Utilities
---------

.. autofunction:: catapcore.common.machine.hardware.create_dynamic_stats_pv_property_from_getter

.. autofunction:: catapcore.common.machine.hardware.add_stats_to_controls_information

.. autofunction:: catapcore.common.machine.hardware.add_stats_to_hardware

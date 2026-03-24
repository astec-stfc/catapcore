API Reference
=============

Core Hardware Classes
---------------------

PVMap
~~~~~

.. autoclass:: common.machine.hardware.PVMap
   :members:
   :undoc-members:
   :show-inheritance:

ControlsInformation
~~~~~~~~~~~~~~~~~~~

.. autoclass:: common.machine.hardware.ControlsInformation
   :members:
   :undoc-members:
   :show-inheritance:

Properties
~~~~~~~~~~

.. autoclass:: common.machine.hardware.Properties
   :members:
   :undoc-members:
   :show-inheritance:

Hardware
~~~~~~~~

.. autoclass:: common.machine.hardware.Hardware
   :members:
   :undoc-members:
   :show-inheritance:

Factory Classes
---------------

Factory
~~~~~~~

.. autoclass:: common.machine.factory.Factory
   :members:
   :undoc-members:
   :show-inheritance:

PV Types
--------

PVSignal
~~~~~~~~

.. autoclass:: common.machine.pv_utils.PVSignal
   :members:
   :undoc-members:
   :show-inheritance:

ScalarPV
~~~~~~~~

.. autoclass:: common.machine.pv_utils.ScalarPV
   :members:
   :undoc-members:
   :show-inheritance:

BinaryPV
~~~~~~~~

.. autoclass:: common.machine.pv_utils.BinaryPV
   :members:
   :undoc-members:
   :show-inheritance:

StatePV
~~~~~~~

.. autoclass:: common.machine.pv_utils.StatePV
   :members:
   :undoc-members:
   :show-inheritance:

StringPV
~~~~~~~~

.. autoclass:: common.machine.pv_utils.StringPV
   :members:
   :undoc-members:
   :show-inheritance:

WaveformPV
~~~~~~~~~~

.. autoclass:: common.machine.pv_utils.WaveformPV
   :members:
   :undoc-members:
   :show-inheritance:

StatisticalPV
~~~~~~~~~~~~~~

.. autoclass:: common.machine.pv_utils.StatisticalPV
   :members:
   :undoc-members:
   :show-inheritance:

PVInfo
~~~~~~

.. autoclass:: common.machine.pv_utils.PVInfo
   :members:
   :undoc-members:
   :show-inheritance:

Control Protocols
-----------------

Protocol
~~~~~~~~

.. autoclass:: common.machine.protocol.Protocol
   :members:
   :undoc-members:
   :show-inheritance:

CA
~~

.. autoclass:: common.machine.protocol.CA
   :members:
   :undoc-members:
   :show-inheritance:

PVA
~~~

.. autoclass:: common.machine.protocol.PVA
   :members:
   :undoc-members:
   :show-inheritance:

Snapshot Management
-------------------

Snapshot
~~~~~~~~

.. autoclass:: common.machine.snapshot.Snapshot
   :members:
   :undoc-members:
   :show-inheritance:

Machine Area
------------

MachineArea
~~~~~~~~~~~

.. autoclass:: common.machine.area.MachineArea
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
-------------

.. automodule:: config
   :members:
   :show-inheritance:

Utilities
---------

.. autofunction:: common.machine.hardware.create_dynamic_stats_pv_property_from_getter

.. autofunction:: common.machine.hardware.add_stats_to_controls_information

.. autofunction:: common.machine.hardware.add_stats_to_hardware

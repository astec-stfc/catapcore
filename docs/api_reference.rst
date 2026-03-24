API Reference
=============

Core Hardware Classes
---------------------

.. autosummary::
   :toctree: _autosummary
   :recursive:

   catapcore.common.machine.hardware.PVMap
   catapcore.common.machine.hardware.ControlsInformation
   catapcore.common.machine.hardware.Properties
   catapcore.common.machine.hardware.Hardware

.. autoclass:: catapcore.common.machine.hardware.PVMap
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.hardware.ControlsInformation
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.hardware.Properties
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.hardware.Hardware
   :members:
   :undoc-members:
   :show-inheritance:

Factory Classes
---------------

.. autosummary::
   :toctree: _autosummary
   :recursive:

   catapcore.common.machine.factory.Factory

.. autoclass:: catapcore.common.machine.factory.Factory
   :members:
   :undoc-members:
   :show-inheritance:

PV Types
--------

.. autosummary::
   :toctree: _autosummary
   :recursive:

   catapcore.common.machine.pv_utils.PVSignal
   catapcore.common.machine.pv_utils.ScalarPV
   catapcore.common.machine.pv_utils.BinaryPV
   catapcore.common.machine.pv_utils.StatePV
   catapcore.common.machine.pv_utils.StringPV
   catapcore.common.machine.pv_utils.WaveformPV
   catapcore.common.machine.pv_utils.StatisticalPV
   catapcore.common.machine.pv_utils.PVInfo

.. autoclass:: catapcore.common.machine.pv_utils.PVSignal
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.pv_utils.ScalarPV
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.pv_utils.BinaryPV
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.pv_utils.StatePV
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.pv_utils.StringPV
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.pv_utils.WaveformPV
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.pv_utils.StatisticalPV
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.pv_utils.PVInfo
   :members:
   :undoc-members:
   :show-inheritance:

Control Protocols
-----------------

.. autosummary::
   :toctree: _autosummary
   :recursive:

   catapcore.common.machine.protocol.Protocol
   catapcore.common.machine.protocol.CA
   catapcore.common.machine.protocol.PVA

.. autoclass:: catapcore.common.machine.protocol.Protocol
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.protocol.CA
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: catapcore.common.machine.protocol.PVA
   :members:
   :undoc-members:
   :show-inheritance:

Snapshot Management
-------------------

.. autosummary::
   :toctree: _autosummary
   :recursive:

   catapcore.common.machine.snapshot.Snapshot

.. autoclass:: catapcore.common.machine.snapshot.Snapshot
   :members:
   :undoc-members:
   :show-inheritance:

Machine Area
------------

.. autosummary::
   :toctree: _autosummary
   :recursive:

   catapcore.common.machine.area.MachineArea

.. autoclass:: catapcore.common.machine.area.MachineArea
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
-------------

.. autosummary::
   :toctree: _autosummary
   :recursive:

   catapcore.config

.. automodule:: catapcore.config
   :members:
   :show-inheritance:

Utilities
---------

.. autosummary::
   :toctree: _autosummary
   :recursive:

   catapcore.common.machine.pv_utils.return_none_if_epics_warns
   catapcore.common.machine.pv_utils.StateMap
   catapcore.common.machine.hardware.create_dynamic_stats_pv_property_from_getter
   catapcore.common.machine.hardware.add_stats_to_controls_information
   catapcore.common.machine.hardware.add_stats_to_hardware

.. autofunction:: catapcore.common.machine.hardware.create_dynamic_stats_pv_property_from_getter

.. autofunction:: catapcore.common.machine.hardware.add_stats_to_controls_information

.. autofunction:: catapcore.common.machine.hardware.add_stats_to_hardware

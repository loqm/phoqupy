"""PhoQuPy — automation-first framework for quantum optics experiments.

Every experiment runs in simulation on any machine (no hardware) and drives the
real instruments when the optional drivers are installed. See ``phoqupy[hardware]``.
"""
from .core import PLMap
from .experiments.confocal import ConfocalScan
from .experiments.cryo import CryoScan
from .experiments.hbt import HBTMeasurement
from .experiments.fiber import FiberAlignment
from .experiments.stitching import StitchedScan
from .experiments.hyperspectral import HyperspectralScan

__version__ = "0.1.0"
__all__ = [
    "ConfocalScan", "CryoScan", "HBTMeasurement",
    "FiberAlignment", "StitchedScan", "HyperspectralScan", "PLMap",
]

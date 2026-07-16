"""Piezoconcept C3200 stage (cryostat fast scan) — real + simulated."""
from .base import try_import, DeviceError


class PiezoconceptStage:
    driver = "Piezoconcept_C3200"

    def __init__(self, port="COM5", simulate=False):
        self.port = port
        self.simulate = simulate
        self._x = self._y = self._z = 0.0
        self.dev = None
        if not simulate:
            mod = try_import(self.driver)
            if mod is None:
                raise DeviceError(
                    "Piezoconcept driver not found. Use simulate=True or add the C3200 module.")
            self.dev = mod.Piezoconcept(port)

    def recenter(self, center=100):
        self._x = self._y = self._z = center
        if self.dev:
            self.dev.recenter(center)

    def move_xyz(self, x_val=0, y_val=0, z_val=0, unit="u"):
        self._x, self._y, self._z = x_val, y_val, z_val
        if self.dev:
            self.dev.move_xyz(x_val=x_val, y_val=y_val, z_val=z_val, unit=unit)

    @property
    def position(self):
        return (self._y, self._z)   # scan plane

    def close(self):
        if self.dev and hasattr(self.dev, "close"):
            self.dev.close()

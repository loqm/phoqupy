"""Thorlabs NanoMax (MDT69x piezo controller) stage — real + simulated."""
from .base import try_import, DeviceError


class NanoMaxStage:
    driver = "mdt69x"

    def __init__(self, port="COM4", simulate=False):
        self.port = port
        self.simulate = simulate
        self._x = self._y = 0.0
        self.con = None
        if not simulate:
            mod = try_import(self.driver)
            if mod is None:
                raise DeviceError(
                    "mdt69x not installed. `pip install phoqupy[stage]` or use simulate=True.")
            self.con = mod.Controller(port)
            print(f"Connected to: {self.con.get_id()}")

    def center_stage(self, start, end):
        c = (end - start) / 2
        self._x = self._y = c
        if self.con:
            self.con.set_xyz_voltage(c, c, 0.0)

    def move_to(self, x=None, y=None):
        if x is not None:
            self._x = x
            if self.con:
                self.con.set_x_voltage(x)
        if y is not None:
            self._y = y
            if self.con:
                self.con.set_y_voltage(y)

    @property
    def position(self):
        return (self._x, self._y)

    def close(self):
        if self.con:
            self.con.set_xyz_voltage(0.0, 0.0, 0.0)
            self.con.close()

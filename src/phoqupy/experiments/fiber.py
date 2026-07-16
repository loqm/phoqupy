"""Fiber alignment: raster the Y-Z piezo voltages, map coupling efficiency."""
import numpy as np
from ..devices.base import resolve_simulate, try_import, DeviceError
from .._sim import sim_fiber_heatmap


class FiberAlignment:
    def __init__(self, v_max=75, resolution=50, port="COM4", simulate=None, seed=0):
        self.v_max, self.resolution, self.port = v_max, resolution, port
        self.simulate = resolve_simulate(simulate, "mdt69x")
        self.seed = seed

    @staticmethod
    def _safe_v(v, vmin=0, vmax=75):
        return max(vmin, min(vmax, v))

    def run(self):
        if self.simulate:
            self.y, self.z, self.C = sim_fiber_heatmap(self.v_max, self.resolution, self.seed)
            return self
        mod = try_import("mdt69x")
        if mod is None:
            raise DeviceError("mdt69x not installed. `pip install phoqupy[stage]` or simulate=True.")
        ctl = mod.Controller(self.port)
        ys = np.linspace(0, self.v_max, self.resolution)
        zs = np.linspace(0, self.v_max, self.resolution)
        C = np.zeros((self.resolution, self.resolution))
        for iz, z in enumerate(zs):
            for iy, y in enumerate(ys):
                ctl.set_y_voltage(self._safe_v(y)); ctl.set_z_voltage(self._safe_v(z))
                C[iz, iy] = self._read_counts()      # PM100D power or Andor count
        self.y, self.z, self.C = ys, zs, C
        return self

    def _read_counts(self):
        return 0.0   # wired to PM100D / Andor in the lab build

    def optimum(self):
        iz, iy = np.unravel_index(np.argmax(self.C), self.C.shape)
        return (self.y[iy], self.z[iz])

    def plot(self, savepath=None):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        im = ax.imshow(self.C, origin="lower", cmap="viridis",
                       extent=[0, self.v_max, 0, self.v_max])
        ax.set_xlabel("Y voltage (V)"); ax.set_ylabel("Z voltage (V)")
        ax.set_title("Fiber coupling map"); fig.colorbar(im, ax=ax, label="power (W)")
        if savepath:
            fig.savefig(savepath, dpi=130); return savepath
        plt.show(); return fig

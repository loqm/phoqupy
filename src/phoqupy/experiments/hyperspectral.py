"""Hyperspectral imaging: Gemini interferometer + Princeton EMCCD, per-pixel FFT."""
import numpy as np
from ..devices.base import resolve_simulate, try_import, DeviceError
from .._sim import sim_hyperspectral_cube


class HyperspectralScan:
    def __init__(self, grid=(40, 40), spectral_points=80, start_wave=560, end_wave=600,
                 simulate=None, seed=0):
        self.grid, self.spectral_points = grid, spectral_points
        self.start_wave, self.end_wave = start_wave, end_wave
        self.simulate = resolve_simulate(simulate, "pylablib")
        self.seed = seed
        self.wl = self.cube = None

    def run(self):
        if self.simulate:
            self.wl, self.cube = sim_hyperspectral_cube(self.grid, self.spectral_points, seed=self.seed)
            return self
        if try_import("pylablib") is None:
            raise DeviceError("pylablib not installed. `pip install phoqupy[spectrometer]` or simulate=True.")
        # Lab build: step the Gemini OPD, grab a Princeton EMCCD frame per step,
        # then per-pixel FFT (see gemini/Python Scripts/Main_emccd.py + Processing.py).
        raise DeviceError("Real acquisition runs on the lab rig; use simulate=True off-site.")

    def slice(self, wavelength_nm=585):
        if self.cube is None:
            self.run()
        k = int(np.argmin(np.abs(self.wl - wavelength_nm)))
        return self.cube[:, :, k]

    def plot(self, wavelength_nm=585, savepath=None):
        import matplotlib.pyplot as plt
        img = self.slice(wavelength_nm)
        fig, ax = plt.subplots(figsize=(5.5, 5))
        im = ax.imshow(img, origin="lower", cmap="inferno")
        ax.set_title(f"Hyperspectral slice @ {wavelength_nm} nm"); ax.axis("off")
        fig.colorbar(im, ax=ax, label="intensity")
        if savepath:
            fig.savefig(savepath, dpi=130); return savepath
        plt.show(); return fig

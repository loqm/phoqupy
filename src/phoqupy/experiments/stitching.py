"""Stitched wide-field imaging: Zaber raster + Thorlabs camera + MIST stitch."""
import numpy as np
from ..devices.base import resolve_simulate, try_import, DeviceError
from .._sim import sim_tile


class StitchedScan:
    def __init__(self, grid=(20, 20), overlap=0.2, port="COM5", simulate=None, seed=0):
        self.grid, self.overlap, self.port = grid, overlap, port
        self.simulate = resolve_simulate(simulate, "zaber_motion")
        self.seed = seed
        self.tiles = None

    def run(self):
        rows, cols = self.grid
        if self.simulate:
            self.tiles = [[sim_tile(i, j, seed=self.seed) for j in range(cols)]
                          for i in range(rows)]
            return self
        if try_import("zaber_motion") is None:
            raise DeviceError("zaber-motion not installed. `pip install phoqupy[zaber]` or simulate=True.")
        # Lab build: open the Zaber connection, serpentine raster, grab a Thorlabs
        # frame per tile (see zaber image stitching/python/image_stitching.py).
        raise DeviceError("Real acquisition runs on the lab rig; use simulate=True off-site.")

    def stitch(self, method="MIST"):
        if self.tiles is None:
            self.run()
        step = int(sim_tile(0, 0).shape[0] * (1 - self.overlap))
        rows, cols = self.grid
        size = sim_tile(0, 0).shape[0]
        H = step * (rows - 1) + size
        W = step * (cols - 1) + size
        canvas = np.zeros((H, W), dtype=np.float32)
        for i in range(rows):
            for j in range(cols):
                canvas[i*step:i*step+size, j*step:j*step+size] = self.tiles[i][j]
        self.mosaic = canvas.astype(np.uint8)
        return self.mosaic

    def plot(self, savepath=None):
        import matplotlib.pyplot as plt
        if not hasattr(self, "mosaic"):
            self.stitch()
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.imshow(self.mosaic, cmap="magma"); ax.set_title("Stitched image")
        ax.axis("off")
        if savepath:
            fig.savefig(savepath, dpi=130); return savepath
        plt.show(); return fig

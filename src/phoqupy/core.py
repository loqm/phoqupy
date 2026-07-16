"""Shared result objects."""
import numpy as np


class PLMap:
    """Confocal PL scan result.

    ``matrix`` has shape ``(resolution**2 + 1, 1024)``: row 0 is the wavelength
    axis and each subsequent row is the spectrum at one pixel — the exact layout
    used by the LOQM scan scripts.
    """

    def __init__(self, matrix, resolution, x_range, y_range):
        self.matrix = np.asarray(matrix)
        self.resolution = resolution
        self.x_range = x_range
        self.y_range = y_range
        self.wavelengths = self.matrix[0]

    def peak_map(self):
        return self.matrix[1:].max(axis=1).reshape(self.resolution, self.resolution)

    def spectrum_at(self, ix, iy):
        idx = iy * self.resolution + ix + 1
        return self.wavelengths, self.matrix[idx]

    def pick_brightest(self):
        pk = self.matrix[1:].max(axis=1)
        i = int(pk.argmax())
        return (i % self.resolution, i // self.resolution)

    def save(self, path="pl_map.npy"):
        np.save(path, self.matrix)
        return path

    def plot_map(self, block=True, savepath=None):
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
        im = ax1.imshow(self.peak_map(), origin="lower", cmap="inferno",
                        extent=[*self.x_range, *self.y_range])
        ax1.set_title("Confocal PL map"); ax1.set_xlabel("x (um)"); ax1.set_ylabel("y (um)")
        fig.colorbar(im, ax=ax1, label="peak intensity")
        ix, iy = self.pick_brightest()
        wl, sp = self.spectrum_at(ix, iy)
        line, = ax2.plot(wl * 1e9, sp)
        ax2.set_title(f"Spectrum @ ({ix},{iy})"); ax2.set_xlabel("wavelength (nm)")

        def on_click(ev):
            if ev.inaxes is ax1 and ev.xdata is not None:
                jx = int(round((ev.xdata - self.x_range[0]) /
                               (self.x_range[1] - self.x_range[0]) * (self.resolution - 1)))
                jy = int(round((ev.ydata - self.y_range[0]) /
                               (self.y_range[1] - self.y_range[0]) * (self.resolution - 1)))
                jx = min(max(jx, 0), self.resolution - 1)
                jy = min(max(jy, 0), self.resolution - 1)
                w, s = self.spectrum_at(jx, jy)
                line.set_ydata(s); ax2.set_title(f"Spectrum @ ({jx},{jy})")
                ax2.relim(); ax2.autoscale_view(); fig.canvas.draw_idle()

        fig.canvas.mpl_connect("button_press_event", on_click)
        fig.tight_layout()
        if savepath:
            fig.savefig(savepath, dpi=130); return savepath
        plt.show(block=block)
        return fig

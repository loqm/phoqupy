"""HBT: second-order correlation g2(tau) and lifetime via PicoQuant TCSPC."""
import numpy as np
from ..devices.base import resolve_simulate, try_import, DeviceError
from .._sim import sim_g2, sim_lifetime


class HBTMeasurement:
    def __init__(self, simulate=None, ptu_path=None, seed=0):
        self.simulate = resolve_simulate(simulate, "snAPI")
        self.ptu_path = ptu_path
        self.seed = seed
        self._mh = self._an = None
        if not self.simulate:
            if try_import("snAPI") is None:
                raise DeviceError("snAPI not installed. `pip install phoqupy[picoquant]` or simulate=True.")
            from HBT.interface import MultiHarpWrapper
            from HBT.analyser import Analyser
            from snAPI.Main import MeasMode
            self._an = Analyser(silent=True)
            self._mh = MultiHarpWrapper(silent=True)
            if ptu_path:
                self._mh.connectFile(ptu_path)
            else:
                self._mh.connect(measMode=MeasMode.T3)

    def g2(self, time_window_ns=20, normalized=True):
        if self.simulate:
            return sim_g2(time_window_ns, seed=self.seed)
        self._mh.measure("correlation")
        data, bins = self._mh.get_data("correlation")
        sync = 1 / self._mh.get_sync_rate()
        g2 = self._an.get_g2(readoutData=data, readoutBins=bins,
                             syncPeriod=sync, normalized=normalized)
        return np.asarray(bins), np.asarray(g2)

    def lifetime(self, channel=1, horizon=1000, nExp=2):
        if self.simulate:
            t, y = sim_lifetime(seed=self.seed)
            fit = {"lifetimes_ps": [13237.0, 6564.0], "amplitudes": [763.0, 4925.0]}
            return t, y, fit
        self._mh.measure("histogram")
        data, bins = self._mh.get_data("histogram")
        fit = self._an.get_lifetimes(readoutData=data[channel], readoutBins=bins,
                                     horizon=horizon, nExp=nExp)
        return np.asarray(bins), np.asarray(data[channel]), fit

    def plot_g2(self, time_window_ns=20, savepath=None):
        import matplotlib.pyplot as plt
        tau, g2 = self.g2(time_window_ns)
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(tau, g2); ax.axhline(0.5, ls="--", color="crimson")
        ax.set_xlabel("tau (ns)"); ax.set_ylabel("g2(tau)"); ax.set_title("HBT correlation")
        if savepath:
            fig.savefig(savepath, dpi=130); return savepath
        plt.show(); return fig

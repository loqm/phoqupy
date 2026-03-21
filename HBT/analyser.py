import argparse 
import numpy as np 
import matplotlib.pyplot as plt
import scipy.optimize as opt 
from snAPI.Main import *

class Analyser():
    def __init__(self, silent=False, debug=False, settings_config="settings.json", measurement_config="measurement.json", irf_path=f"{'/'.join(__file__.split('/')[:-1])}/data/irf.ptu"):
        self.silent = silent
        self.debug = debug
        self.settings_config = settings_config
        self.measurement_config = measurement_config

        self.lifetime_fit = None
        self.g2_fit = None

    def debug_print(self, msg):
        if (not self.silent and self.debug): print(msg)

    @staticmethod
    def _get_nnls_amplitudes(tau, data, bins, horizon, deconvolve, out="rnorm"):
        bins = bins[np.argmax(data):horizon]
        data = data[np.argmax(data):horizon]
        decays = []
        for t in tau:
            decays.append(np.exp(-bins/t)) # unnormalised exponentials, convolve with irf later
        decays.append(np.ones_like(bins)) # for offset
        A = np.array(decays).T
        x, rnorm = opt.nnls(A, data)
        y = np.dot(A, np.array(x))
        result = {
            "A": A,
            "amplitudes": x,
            "fit": y,
            "rnorm": rnorm
        }
        return result.get(out, None)

    def get_lifetimes(self, readoutData, readoutBins, horizon=1000, nExp=2, deconvolve=False, tau0=None, bounds=None, method=None, maxiter=None):
        # select data has to be passed
        if (tau0==None or not hasattr(tau0, '__iter__')): tau0 = [1.0]*nExp
        if (bounds==None): bounds = ((0, 100),)*nExp
        if (method==None): method = "Nelder-Mead" # this method provides no error estimates
        if (maxiter==None): maxiter = 1000
        options = {
            "disp": (not self.silent),
            # "return_all": (not self.silent and self.debug),
            "maxiter": maxiter
        }
        scaleFactor = 1000 
        scaledBins = readoutBins/scaleFactor # scale bins to ns
        result = opt.minimize(self._get_nnls_amplitudes, tau0, args=(readoutData, scaledBins, horizon, deconvolve), method=method, bounds=bounds, options=options)
        print(f"Lifetime Fitting Complete: {result.message}")
        if (result.success): self.debug_print(f"Fitted Lifetimes: {result.x}")
        self.lifetime_fit = {
            "data": readoutData,
            "bins": readoutBins,
            "lifetimes": result.x * scaleFactor,
            "amplitudes": self._get_nnls_amplitudes(result.x, readoutData, scaledBins, horizon, deconvolve, out="amplitudes"),
            "fit": self._get_nnls_amplitudes(result.x, readoutData, scaledBins, horizon, deconvolve, out="fit"),
            "rnorm": self._get_nnls_amplitudes(result.x, readoutData, scaledBins, horizon, deconvolve, out="rnorm"),
            "success": result.success,
            "message": result.message
        }
        return self.lifetime_fit
    
    def plot_lifetimes(self, horizon=1000):
        if (not self.lifetime_fit):
            print("No lifetime fit available to plot.")
            return None, None

        horizon = horizon if (horizon is not None and horizon<len(self.lifetime_fit["bins"])) else len(self.lifetime_fit["bins"])
        data = self.lifetime_fit["data"]
        bins = self.lifetime_fit["bins"][np.argmax(data):horizon]
        fit = self.lifetime_fit["fit"][:horizon]
        data = data[np.argmax(data):horizon]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(bins, data, label="Data", marker='o', markersize=2, color='blue')
        ax.plot(bins, fit, label="Fitted Curve", color='red')
        ax.set_xlabel("Time (ps)")
        ax.set_ylabel("Counts")
        ax.set_title("Lifetime Fit Results")
        ax.legend()
        ax.grid()
        # DON'T call plt.show() here - let the caller control when to show
        return fig, ax

    def get_g2(self, readoutData, readoutBins, syncPeriod, normalized=False):
        scaleFactor = 1e9
        scaledBins = readoutBins*scaleFactor
        # Find peaks separated by syncPeriod
        scaledSyncPeriod = syncPeriod*scaleFactor
        dt = scaledBins[1] - scaledBins[0]
        center_idx = np.argmin(np.abs(scaledBins))
        maxPeriods = int((len(scaledBins) // 2) / (scaledSyncPeriod / dt))
        print(f"Max Periods: {maxPeriods}")

        peak_heights = []
        for p in range(-maxPeriods, maxPeriods + 1):
            targetIdx = center_idx + int(p * scaledSyncPeriod / dt)
            window = slice(max(0, targetIdx - 50), min(len(readoutData), targetIdx + 51))
            if window.stop - window.start >= 10:
                peak_heights.append(np.max(readoutData[window]))

        # g2 calculation and variance
        central_peak = peak_heights[maxPeriods]  # Peak at p=0
        side_peaks = np.array([h for i, h in enumerate(peak_heights) if i != maxPeriods])
        g2 = central_peak / np.mean(side_peaks)
        peakVariance = np.var(side_peaks)
        self.g2_fit = {
            "data": readoutData,
            "bins": readoutBins,
            "g2": g2,
            "variance": peakVariance,
            "normalized": normalized
        }
        return self.g2_fit

    def plot_g2(self, horizon):
        pass
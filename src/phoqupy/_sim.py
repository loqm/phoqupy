"""Synthetic data generators so every experiment runs without hardware."""
import numpy as np

N_PIXELS = 1024


class SimSample:
    """A fake sample with a few point emitters, used to synthesise spectra."""

    def __init__(self, x_range=(0, 50), y_range=(0, 50), n_emitters=5,
                 psf=2.0, seed=0):
        rng = np.random.default_rng(seed)
        self.wl = np.linspace(520e-9, 650e-9, N_PIXELS)   # metres
        self.psf = psf
        self.emitters = [
            (rng.uniform(*x_range), rng.uniform(*y_range),
             rng.uniform(1500, 2600), rng.uniform(578e-9, 592e-9))
            for _ in range(n_emitters)
        ]

    def spectrum(self, x, y):
        s = np.full(N_PIXELS, 1200.0)
        for ex, ey, amp, wl0 in self.emitters:
            w = np.exp(-((x - ex) ** 2 + (y - ey) ** 2) / (2 * self.psf ** 2))
            s += amp * w * np.exp(-((self.wl - wl0) ** 2) / (2 * (6e-9) ** 2))
        return s + np.random.normal(0, 15, N_PIXELS)


def sim_g2(time_window_ns=20, n=400, dip=0.15, tau_ns=4.0, seed=0):
    """Antibunched g2(tau): a single emitter gives g2(0) < 0.5."""
    rng = np.random.default_rng(seed)
    tau = np.linspace(-time_window_ns, time_window_ns, n)
    g2 = 1.0 - (1.0 - dip) * np.exp(-np.abs(tau) / tau_ns)
    return tau, np.clip(g2 + rng.normal(0, 0.02, n), 0, None)


def sim_lifetime(horizon_ps=80000, n=1024, taus=(13237.0, 6564.0),
                 amps=(763.0, 4925.0), bg=1.5, seed=0):
    """Bi-exponential decay histogram (values from the paper's hBN fit)."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, horizon_ps, n)
    y = bg + amps[0] * np.exp(-t / taus[0]) + amps[1] * np.exp(-t / taus[1])
    return t, np.clip(rng.poisson(np.clip(y, 0, None)).astype(float), 0, None)


def sim_fiber_heatmap(v_max=75, res=50, seed=0):
    rng = np.random.default_rng(seed)
    y = np.linspace(0, v_max, res)
    z = np.linspace(0, v_max, res)
    Y, Z = np.meshgrid(y, z)
    peak = (0.55 * v_max, 0.45 * v_max)
    C = 3.2e-4 * np.exp(-(((Y - peak[0]) ** 2 + (Z - peak[1]) ** 2) / (2 * 9.0 ** 2)))
    return y, z, C + rng.normal(0, 3e-6, C.shape)


def sim_hyperspectral_cube(grid=(40, 40), spectral=80, band_nm=585, seed=0):
    rng = np.random.default_rng(seed)
    h, w = grid
    wl = np.linspace(560, 600, spectral)
    cube = rng.normal(30, 4, (h, w, spectral))
    yy, xx = np.mgrid[0:h, 0:w]
    blob = 400 * np.exp(-(((xx - w * 0.5) ** 2 + (yy - h * 0.45) ** 2) / (2 * (h * 0.12) ** 2)))
    k = int(np.argmin(np.abs(wl - band_nm)))
    cube[:, :, k] += blob
    return wl, cube


def sim_tile(i, j, size=200, seed=0):
    rng = np.random.default_rng(seed + i * 97 + j)
    base = np.linspace(40, 120, size)
    img = np.tile(base, (size, 1)) + rng.normal(0, 8, (size, size))
    for _ in range(6):
        cy, cx = rng.integers(0, size, 2)
        img[max(0, cy-2):cy+2, max(0, cx-2):cx+2] += 90
    return np.clip(img, 0, 255).astype(np.uint8)

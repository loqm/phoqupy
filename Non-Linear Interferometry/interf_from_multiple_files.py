import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Edit these three entries (file path, start µm, end µm, optional label)
FILES = [
    {"path": r"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\Non-Linear Interferometry\\filename1", "start_um": 100.0, "end_um": 105.0, "label": "HWP 100"},
    {"path": r"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\Non-Linear Interferometry\\filename2", "start_um": 100.0, "end_um": 105.0, "label": "HWP 145"},
    {"path": r"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\Non-Linear Interferometry\\filename3", "start_um": 100.0, "end_um": 105.0, "label": "HWP 190"},
]

SMOOTH_WINDOW = 5  # set to 1 to disable smoothing
SAVE_COMBINED = True
COMBINED_OUT = "combined_interferograms.txt"  # saved as two columns: global position (µm) and intensity

def smooth(x, window):
    if window <= 1 or len(x) < 2:
        return x
    if window > len(x):
        window = len(x)
    if window % 2 == 0:
        window += 1
    pad = window // 2
    kernel = np.ones(window) / window
    padded = np.pad(x, pad, mode="reflect")
    return np.convolve(padded, kernel, mode="valid")

plots = []
all_positions = []
all_intens = []

for entry in FILES:
    p = Path(entry["path"])
    if not p.exists():
        print(f"File not found: {p}; skipping")
        continue
    data = np.loadtxt(p)
    # saved files in this project are often saved as scan_matrix.T -> transpose back
    scan = data.T if data.shape[0] < data.shape[1] else data.T if data.shape[0] == 1024 else data.T
    # prefer to ensure shape (1 + n_positions, n_pixels)
    if scan.shape[0] < 2:
        scan = data.T
    wavelengths = scan[0]
    spectra = scan[1:]  # rows = positions
    npos = spectra.shape[0]
    start = float(entry["start_um"])
    end = float(entry["end_um"])
    positions = np.linspace(start, end, npos)
    # pick a single metric across wavelength axis: max intensity per position (can change)
    intens = spectra.max(axis=1)
    intens = smooth(intens, SMOOTH_WINDOW)
    plots.append((positions, intens, entry.get("label", p.name)))
    all_positions.append(positions)
    all_intens.append(intens)

# --- normalize means so all traces sit on the same level ---
means = [np.mean(inten) for _, inten, _ in plots]
target_mean = float(np.mean(means)) if means else 0.0
normalized_plots = []
for (pos, inten, label), m in zip(plots, means):
    inten_norm = inten - m + target_mean
    normalized_plots.append((pos, inten_norm, label))

# plot overlap (using normalized traces)
plt.figure(figsize=(10, 3))
for pos, inten, label in normalized_plots:
    plt.plot(pos, inten, '-o', markersize=3, label=label)
plt.xlabel("Position (µm)")
plt.ylabel("Intensity (counts)")
plt.title("Overlapped interferograms (means normalized)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# optional: append into single two-column file (sorted by position) using normalized data
if SAVE_COMBINED and normalized_plots:
    # concatenate all points
    pos_all = np.concatenate([p for p, _, _ in normalized_plots])
    int_all = np.concatenate([i for _, i, _ in normalized_plots])
    order = np.argsort(pos_all)
    out = np.column_stack((pos_all[order], int_all[order]))
    np.savetxt(COMBINED_OUT, out, header="position_um intensity_counts", fmt="%.6e")
    print("Combined file saved:", COMBINED_OUT)

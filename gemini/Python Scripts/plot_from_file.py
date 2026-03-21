import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

# -------- USER CONFIGURE THESE VALUES BELOW --------
CUBE_FILE = r"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini_data\\filename\\hyperspectral_cube.npy"
WAVELENGTH_FILE = r"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini_data\\filename\\wavelength_axis.npy"

# Default starting bin (0-based) - click the image to override
ROW = 2
COL = 2

# Output options
SAVE_TXT_ON_CLICK = False   # only save when Save button is clicked
SHOW_INITIAL_SPECTRUM = True  # show initial spectrum at ROW,COL on start

# --------------------------------------------------

def load_paths(cube_path, wl_path=None):
    if not os.path.isfile(cube_path):
        raise SystemExit(f"Hyperspectral cube not found: {cube_path}")
    base_dir = os.path.dirname(cube_path)
    if wl_path is None:
        wl_path = os.path.join(base_dir, "wavelength_axis.npy")
    return cube_path, wl_path

def format_txt_save(dirpath, r, c, wave, spectrum):
    txt_out = os.path.join(dirpath, f"bin_{r}_{c}_spectrum.txt")
    np.savetxt(txt_out,
               np.column_stack((wave, spectrum)),
               header="wavelength_nm\tamplitude",
               fmt="%.6e",
               delimiter="\t")
    return txt_out

def main():
    cube_path, wl_path = load_paths(CUBE_FILE, WAVELENGTH_FILE)
    base_dir = os.path.dirname(cube_path)

    cube = np.load(cube_path)  # shape: (n_rows, n_cols, n_spec)
    if not os.path.isfile(wl_path):
        raise SystemExit(f"Wavelength axis not found: {wl_path}")
    wave = np.load(wl_path)

    if cube.ndim != 3:
        raise SystemExit(f"Expected cube with 3 dims (rows,cols,spec); got shape {cube.shape}")

    n_rows, n_cols, n_spec = cube.shape

    # Build spatial intensity map (mean over spectral axis)
    spatial_map = np.mean(cube, axis=2)

    # Create figure with image (left) and spectrum (right)
    fig, (ax_img, ax_spec) = plt.subplots(1, 2, figsize=(12, 6), gridspec_kw={'width_ratios': [1, 1]})
    im = ax_img.imshow(spatial_map, cmap="viridis", origin="upper", interpolation="nearest", aspect="auto")
    ax_img.set_title("Spatial intensity map (click a pixel)")
    ax_img.set_xlabel("Column (X)")
    ax_img.set_ylabel("Row (Y)")
    cbar = fig.colorbar(im, ax=ax_img, shrink=0.8)
    cbar.set_label("Mean intensity")

    # Spectrum axis initial layout
    ax_spec.set_xlabel("Wavelength [nm]")
    ax_spec.set_ylabel("Amplitude")
    ax_spec.grid(True, alpha=0.3)
    ax_spec.set_title("Spectrum (select a bin)")

    # Marker and initial spectrum line
    marker_plot, = ax_img.plot([], [], marker='o', markersize=12, markerfacecolor='none',
                               markeredgecolor='r', markeredgewidth=2, linestyle='None')
    spec_line, = ax_spec.plot([], [], lw=1.5)

    # Current selection holder for save button callback
    current = {'row': None, 'col': None, 'spectrum': None}

    def update_spectrum_display(row, col):
        spectrum = cube[row, col, :]
        # update marker on image
        marker_plot.set_data([col], [row])
        # update spectrum plot
        spec_line.set_data(wave, spectrum)
        ax_spec.relim()
        ax_spec.autoscale_view()
        ax_spec.set_title(f"Spectrum at bin ({row}, {col})")
        fig.canvas.draw_idle()
        current['row'] = row
        current['col'] = col
        current['spectrum'] = spectrum
        return spectrum

    def onclick(event):
        if event.inaxes is not ax_img:
            return
        x = event.xdata
        y = event.ydata
        if x is None or y is None:
            return
        col = int(round(x))
        row = int(round(y))
        col = int(np.clip(col, 0, n_cols - 1))
        row = int(np.clip(row, 0, n_rows - 1))

        spectrum = update_spectrum_display(row, col)

        print(f"Clicked bin: ({row}, {col}) — spectrum updated (use Save button to write TXT)")

    cid = fig.canvas.mpl_connect('button_press_event', onclick)

    # Add a Save button (only saves when clicked)
    btn_ax = fig.add_axes([0.82, 0.02, 0.14, 0.06])  # position: [left, bottom, width, height]
    save_btn = Button(btn_ax, 'Save spectrum', hovercolor='0.975')

    def on_save(event):
        if current['spectrum'] is None:
            print("No bin selected to save.")
            return
        r = current['row']; c = current['col']; spec = current['spectrum']
        path = format_txt_save(base_dir, r, c, wave, spec)
        print(f"Saved by button: {path}")

    save_btn.on_clicked(on_save)

    # Optionally display initial spectrum for configured ROW/COL (do not auto-save)
    if SHOW_INITIAL_SPECTRUM:
        if 0 <= ROW < n_rows and 0 <= COL < n_cols:
            update_spectrum_display(ROW, COL)
        else:
            print("Configured ROW/COL out of range; skipping initial spectrum")

    plt.tight_layout()
    plt.show()
    fig.canvas.mpl_disconnect(cid)

if __name__ == "__main__":
    main()
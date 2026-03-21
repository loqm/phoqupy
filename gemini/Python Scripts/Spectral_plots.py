import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
import csv


filename = input("Enter the folder name: ")
# Changed: use fixed filepaths / parameters instead of CLI
CUBE_FILE = rf"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini_data\\{filename}\\hyperspectral_cube.npy"
WAVELENGTH_FILE = rf"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini_data\\{filename}\\wavelength_axis.npy"
OUT_DIR = rf"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini_data\\{filename}\\spectral_slices_output"
INTERVAL_NM = 1.0
START_WL = None   # set to None to use min(wave)
END_WL = None     # set to None to use max(wave)
UPSCALE = (200, 200)
MONTAGE_FILENAME = os.path.join(OUT_DIR, "spectral_slices_montage.png")
MAX_MONTAGE = 20
DEFAULT_REL_THRESHOLD = 0.5


def load_inputs(cube_path, wl_path):
    if not os.path.isfile(cube_path):
        raise SystemExit(f"Hyperspectral cube not found: {cube_path}")
    if not os.path.isfile(wl_path):
        raise SystemExit(f"Wavelength axis not found: {wl_path}")
    cube = np.load(cube_path)  # shape: (rows, cols, n_wl)
    wave = np.load(wl_path)
    return cube, wave

def save_slice_image(spatial_slice, out_path, upscale=(200, 200)):
    mn, mx = spatial_slice.min(), spatial_slice.max()
    if mx > mn:
        norm = 255.0 * (spatial_slice - mn) / (mx - mn)
    else:
        norm = np.zeros_like(spatial_slice)
    img = norm.astype(np.uint8)
    img_up = cv2.resize(img, upscale, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(out_path, img_up)

def generate_slices(cube, wave, start_wave, end_wave, interval_nm, out_dir, upscale=(200,200)):
    os.makedirs(out_dir, exist_ok=True)
    target_wls = np.arange(start_wave, end_wave + interval_nm, interval_nm)
    target_wls = target_wls[target_wls <= end_wave]
    saved = []
    for wl in target_wls:
        idx = np.argmin(np.abs(wave - wl))
        spatial = cube[:, :, idx]
        out_file = os.path.join(out_dir, f"slice_{int(wl)}nm.png")
        save_slice_image(spatial, out_file, upscale)
        saved.append((wl, idx, out_file))
    return saved

def create_montage(cube, wave, target_wavelengths, out_file, max_slices=20, n_cols=5, cmap='viridis'):
    max_slices = min(max_slices, len(target_wavelengths))
    montage_indices = np.linspace(0, len(target_wavelengths) - 1, max_slices, dtype=int)
    montage_wls = target_wavelengths[montage_indices]
    global_min = float(np.min(cube))
    global_max = float(np.max(cube))

    n_rows = int(np.ceil(max_slices / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols*3.6, n_rows*3.6))
    axes = np.atleast_1d(axes).flatten()

    im = None
    for ax, wl in zip(axes[:max_slices], montage_wls):
        idx = np.argmin(np.abs(wave - wl))
        spatial = cube[:, :, idx]
        im = ax.imshow(spatial, cmap=cmap, vmin=global_min, vmax=global_max, interpolation='nearest')
        ax.set_title(f"{int(wl)} nm")
        ax.axis('off')
        ax.set_aspect(0.75)

    for ax in axes[max_slices:]:
        ax.axis('off')

    fig.subplots_adjust(right=0.92)
    cax = fig.add_axes([0.94, 0.15, 0.02, 0.7])
    fig.colorbar(im, cax=cax, label='Amplitude')
    plt.suptitle("Spectral Slices Montage (common scale)", fontsize=14, y=0.98)
    plt.savefig(out_file, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return out_file

def _longest_run_length(bool_row):
    maxlen = 0
    cur = 0
    for v in bool_row:
        if v:
            cur += 1
            if cur > maxlen:
                maxlen = cur
        else:
            cur = 0
    return maxlen

def _longest_run_bounds(bool_row):
    """Return (length, start_index, end_index) of longest True run in 1D boolean array."""
    maxlen = 0
    cur = 0
    cur_start = None
    max_start = None
    max_end = None
    for i, v in enumerate(bool_row):
        if v:
            if cur == 0:
                cur_start = i
            cur += 1
            if cur > maxlen:
                maxlen = cur
                max_start = cur_start
                max_end = i
        else:
            cur = 0
            cur_start = None
    if maxlen == 0:
        return 0, None, None
    return int(maxlen), int(max_start), int(max_end)

def measure_diameter(spatial_slice, threshold=None, rel_threshold=0.5, axis='row'):
    """
    Measure diameter (in pixels) by auto-detecting the line (row or column) with the longest run.
    axis: 'row' or 'col'
    Returns (diameter_px, index_of_longest_run, start_idx, end_idx, threshold_used)
    """
    mn, mx = float(spatial_slice.min()), float(spatial_slice.max())
    if threshold is None:
        threshold = mn + rel_threshold * (mx - mn)
    mask = spatial_slice > threshold
    max_len = 0
    max_idx = None
    max_start = None
    max_end = None

    if axis == 'row':
        for r in range(mask.shape[0]):
            lr, s, e = _longest_run_bounds(mask[r, :])
            if lr > max_len:
                max_len = lr
                max_idx = r
                max_start = s
                max_end = e
    else:  # 'col'
        for c in range(mask.shape[1]):
            lr, s, e = _longest_run_bounds(mask[:, c])
            if lr > max_len:
                max_len = lr
                max_idx = c
                max_start = s
                max_end = e

    return int(max_len), (int(max_idx) if max_idx is not None else None), (int(max_start) if max_start is not None else None), (int(max_end) if max_end is not None else None), float(threshold)

def get_line_mask(spatial_slice, index, threshold, axis='row'):
    """Return boolean mask for positions on given line where intensity > threshold.
       If axis=='row' returns mask over columns; if axis=='col' returns mask over rows."""
    h, w = spatial_slice.shape
    if index is None:
        return None
    if axis == 'row':
        r = max(0, min(int(index), h - 1))
        return spatial_slice[r, :] > threshold
    else:
        c = max(0, min(int(index), w - 1))
        return spatial_slice[:, c] > threshold

def save_highlighted_slice(spatial_slice, index=None, start_idx=None, end_idx=None, line_mask=None, out_path=None, axis='row', upscale=(200,200)):
    """
    Save an RGB PNG where the slice is shown in grayscale and either:
      - the contiguous run from start_idx to end_idx on the chosen line is highlighted, or
      - all True positions in line_mask are highlighted.
    axis: 'row' or 'col'
    """
    mn, mx = float(spatial_slice.min()), float(spatial_slice.max())
    if mx > mn:
        norm = 255.0 * (spatial_slice - mn) / (mx - mn)
    else:
        norm = np.zeros_like(spatial_slice)
    img = np.clip(norm, 0, 255).astype(np.uint8)  # HxW
    rgb = np.stack([img, img, img], axis=2)
    h, w = img.shape

    if line_mask is not None:
        if axis == 'row':
            r = max(0, min(int(index) if index is not None else 0, h-1))
            cols = np.where(np.asarray(line_mask).astype(bool))[0]
            if cols.size > 0:
                rgb[r, cols, 0] = 255; rgb[r, cols, 1] = 0; rgb[r, cols, 2] = 0
        else:
            c = max(0, min(int(index) if index is not None else 0, w-1))
            rows = np.where(np.asarray(line_mask).astype(bool))[0]
            if rows.size > 0:
                rgb[rows, c, 0] = 255; rgb[rows, c, 1] = 0; rgb[rows, c, 2] = 0
    else:
        if axis == 'row':
            if index is not None and start_idx is not None and end_idx is not None:
                r = max(0, min(int(index), h-1))
                s = max(0, min(int(start_idx), w-1))
                e = max(0, min(int(end_idx), w-1))
                if s <= e:
                    rgb[r, s:e+1, 0] = 255; rgb[r, s:e+1, 1] = 0; rgb[r, s:e+1, 2] = 0
        else:
            if index is not None and start_idx is not None and end_idx is not None:
                c = max(0, min(int(index), w-1))
                s = max(0, min(int(start_idx), h-1))
                e = max(0, min(int(end_idx), h-1))
                if s <= e:
                    rgb[s:e+1, c, 0] = 255; rgb[s:e+1, c, 1] = 0; rgb[s:e+1, c, 2] = 0

    rgb_up = cv2.resize(rgb, upscale, interpolation=cv2.INTER_NEAREST)
    if out_path is not None:
        cv2.imwrite(out_path, cv2.cvtColor(rgb_up, cv2.COLOR_RGB2BGR))

def create_highlighted_montage(image_paths, out_file, max_slices=20, n_cols=5):
    """
    Create and save a montage from a list of RGB image file paths.
    """
    max_slices = min(max_slices, len(image_paths))
    n_rows = int(np.ceil(max_slices / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols*3.6, n_rows*3.6))
    axes = np.atleast_1d(axes).flatten()
    for ax, img_path in zip(axes[:max_slices], image_paths[:max_slices]):
        img = plt.imread(img_path)
        ax.imshow(img)
        ax.axis('off')
        ax.set_title(os.path.basename(img_path).replace('_', ' '))
    for ax in axes[max_slices:]:
        ax.axis('off')
    plt.suptitle("Highlighted Diameter Slices", fontsize=14, y=0.98)
    plt.savefig(out_file, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return out_file

def compute_and_plot_row_spectral_map(cube, diameters, line_index_user, out_dir, map_fname="spectral_row_map.png", min_diameter=0, axis='row'):
    """
    Build a 2D map (wavelength x relative position) of intensities along the chosen line (row/col),
    resample each diameter segment to a common grid (-30..+30) and interpolate the
    resulting 2D map for a smoother colormap.
    axis: 'row' or 'col'
    Returns (out_path, fig) if a map was generated, otherwise None.
    """
    if len(diameters) == 0:
        return None

    h, w, _ = cube.shape
    rows_resampled = []
    wl_vals = []
    N_TARGET = 61  # original resample points for -30..+30

    for d in diameters:
        wl, spec_idx, diam_px, slice_idx, start_idx, end_idx, used_th = d
        if diam_px is None or diam_px < min_diameter:
            continue

        line_to_use = int(line_index_user) if (line_index_user is not None) else (int(slice_idx) if slice_idx is not None else None)
        if line_to_use is None:
            continue
        if axis == 'row':
            if line_to_use < 0 or line_to_use >= h:
                continue
            if start_idx is None or end_idx is None:
                continue
            s = int(start_idx); e = int(end_idx)
            if e <= s:
                continue
            line_vals_full = cube[line_to_use, :, int(spec_idx)].astype(float)  # columns
        else:
            if line_to_use < 0 or line_to_use >= w:
                continue
            if start_idx is None or end_idx is None:
                continue
            s = int(start_idx); e = int(end_idx)
            if e <= s:
                continue
            line_vals_full = cube[:, line_to_use, int(spec_idx)].astype(float)  # rows

        segment = line_vals_full[s:e+1].astype(float)
        segment_masked = np.where(segment > float(used_th), segment, np.nan)

        x_old = np.arange(s, e+1)
        valid = ~np.isnan(segment_masked)
        if valid.sum() < 2:
            row_resampled = np.full((N_TARGET,), np.nan, dtype=float)
        else:
            x_valid = x_old[valid]
            y_valid = segment_masked[valid]
            x_target = np.linspace(s, e, N_TARGET)
            row_resampled = np.interp(x_target, x_valid, y_valid, left=np.nan, right=np.nan)

        rows_resampled.append(row_resampled)
        wl_vals.append(float(wl))

    if len(rows_resampled) == 0:
        return None

    spec_map = np.vstack(rows_resampled)  # (n_wl, N_TARGET)

    # Interpolate horizontally and vertically for smoothness
    new_cols = N_TARGET * 3
    x_old = np.arange(N_TARGET)
    x_new = np.linspace(0, N_TARGET - 1, new_cols)
    horiz_interp = np.full((spec_map.shape[0], new_cols), np.nan, dtype=float)
    for i in range(spec_map.shape[0]):
        row = spec_map[i, :]
        valid = ~np.isnan(row)
        if valid.sum() < 2:
            continue
        horiz_interp[i, :] = np.interp(x_new, x_old[valid], row[valid], left=np.nan, right=np.nan)

    n_rows = spec_map.shape[0]
    new_rows = max(n_rows * 3, n_rows)
    wl_old = np.arange(n_rows)
    wl_new = np.linspace(0, n_rows - 1, new_rows)
    full_interp = np.full((new_rows, new_cols), np.nan, dtype=float)
    for j in range(new_cols):
        col = horiz_interp[:, j]
        valid = ~np.isnan(col)
        if valid.sum() < 2:
            continue
        full_interp[:, j] = np.interp(wl_new, wl_old[valid], col[valid], left=np.nan, right=np.nan)

    m = np.ma.masked_invalid(full_interp)

    wl_min, wl_max = wl_vals[0], wl_vals[-1]
    out_path = os.path.join(out_dir, map_fname)

    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.imshow(m, aspect='auto', origin='lower',
                   cmap='viridis',
                   extent=[-30, 30, wl_min, wl_max])
    xlabel = "Relative position (mapped -30 .. +30, center=0)"
    if axis == 'row':
        xlabel = "Column offset from center (mapped -30..+30)"
    else:
        xlabel = "Row offset from center (mapped -30..+30)"
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Wavelength (nm)")
    ax.set_title(f"Interpolated intensity (axis={axis}, line={line_index_user if line_index_user is not None else 'per-slice'}) — excluded diam < {min_diameter}px")
    fig.colorbar(im, ax=ax, label="Intensity")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')

    return out_path, fig

def run_from_config():
    cube, wave = load_inputs(CUBE_FILE, WAVELENGTH_FILE)

    start_wave = START_WL if START_WL is not None else float(np.min(wave))
    end_wave = END_WL if END_WL is not None else float(np.max(wave))
    if start_wave < wave.min(): start_wave = float(wave.min())
    if end_wave > wave.max(): end_wave = float(wave.max())

    # Ask user for threshold input (absolute) or use relative default if blank
    print(f"Enter absolute intensity threshold (numeric).")
    print(f"Or press Enter to use relative threshold = {DEFAULT_REL_THRESHOLD} of dynamic range.")
    thresh_input = input("Threshold (absolute) or Enter for relative: ").strip()
    if thresh_input == "":
        user_threshold = None
        user_rel_threshold = DEFAULT_REL_THRESHOLD
    else:
        try:
            user_threshold = float(thresh_input)
            user_rel_threshold = None
        except ValueError:
            print("Invalid input; falling back to relative threshold.")
            user_threshold = None
            user_rel_threshold = DEFAULT_REL_THRESHOLD

    # Ask user for axis: row or column
    axis_input = input("Cut axis: enter 'r' for row or 'c' for column (default r): ").strip().lower()
    cut_axis = 'row' if axis_input != 'c' else 'col'

    # Ask user for the line index to evaluate (0-based). Enter = auto-detect.
    line_input = input(f"{'Row' if cut_axis=='row' else 'Column'} index (0-based) to use for diameter (Enter to auto-detect): ").strip()
    if line_input == "":
        user_line = None
    else:
        try:
            user_line = int(line_input)
        except ValueError:
            print("Invalid line input; using auto-detect.")
            user_line = None

    os.makedirs(OUT_DIR, exist_ok=True)
    saved = generate_slices(cube, wave, start_wave, end_wave, INTERVAL_NM, OUT_DIR, UPSCALE)
    if len(saved) == 0:
        print("No slices generated (check interval/start/end).")
        return

    # measure diameters for each saved slice (use user-specified threshold/line/axis)
    diameters = []
    highlighted_paths = []
    for wl, idx, out_file in saved:
        spatial = cube[:, :, idx]
        mn, mx = float(spatial.min()), float(spatial.max())
        used_th = (user_threshold if user_threshold is not None else (mn + (user_rel_threshold if user_rel_threshold is not None else DEFAULT_REL_THRESHOLD) * (mx - mn)))

        if user_line is None:
            diam_px, auto_idx, s_idx, e_idx, _ = measure_diameter(spatial, threshold=user_threshold, rel_threshold=(user_rel_threshold if user_rel_threshold is not None else DEFAULT_REL_THRESHOLD), axis=cut_axis)
            line_idx = auto_idx
        else:
            line_idx = int(user_line)
            line_mask = get_line_mask(spatial, line_idx, used_th, axis=cut_axis)
            lr, s_idx, e_idx = _longest_run_bounds(line_mask)
            diam_px = int(lr)

        line_mask = get_line_mask(spatial, line_idx, used_th, axis=cut_axis) if line_idx is not None else None

        diameters.append((wl, int(idx), diam_px, line_idx, s_idx, e_idx, float(used_th)))

        highlight_fn = os.path.join(OUT_DIR, f"slice_{int(wl)}nm_highlight.png")
        save_highlighted_slice(spatial, index=line_idx, start_idx=s_idx, end_idx=e_idx, line_mask=line_mask, out_path=highlight_fn, axis=cut_axis, upscale=UPSCALE)
        highlighted_paths.append(highlight_fn)

    # save diameters CSV
    diam_file = os.path.join(OUT_DIR, "diameters.csv")
    with open(diam_file, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter=",")
        writer.writerow(["wavelength_nm", "spec_index", "diameter_px", "line_index_of_run", "start_idx", "end_idx", "threshold_used"])
        writer.writerows(diameters)

    # prepare target wavelengths and montage indices (use same selection for both montages)
    target_wls = np.array([s[0] for s in saved])
    n_show = min(MAX_MONTAGE, len(target_wls))
    montage_indices = np.linspace(0, len(target_wls) - 1, n_show, dtype=int)

    # create and save regular montage (uses same selection logic internally)
    create_montage(cube, wave, target_wls, MONTAGE_FILENAME, max_slices=MAX_MONTAGE)

    # create and save highlighted montage showing the same wavelength cuts as the regular montage
    highlighted_montage = os.path.join(OUT_DIR, "spectral_slices_highlighted_montage.png")
    montage_highlight_paths = [highlighted_paths[i] for i in montage_indices]
    if montage_highlight_paths:
        create_highlighted_montage(montage_highlight_paths, highlighted_montage, max_slices=n_show)

    print(f"Saved {len(saved)} slices to: {os.path.abspath(OUT_DIR)}")
    print(f"Montage saved to: {os.path.abspath(MONTAGE_FILENAME)}")
    print(f"Diameters saved to: {os.path.abspath(diam_file)}")
    print(f"Highlighted montage saved to: {os.path.abspath(highlighted_montage)}")

    # --- build and display interpolated 2D colormap of intensities along chosen line ---
    spectral_map_ret = compute_and_plot_row_spectral_map(cube, diameters, user_line, OUT_DIR, map_fname="spectral_row_map.png", min_diameter=1, axis=cut_axis)
    if spectral_map_ret is not None:
        spectral_map_path, fig_map = spectral_map_ret
        print(f"Spectral row map saved to: {os.path.abspath(spectral_map_path)}")
        fig_map.show()
        plt.show()
    else:
        print("No spectral row map generated (no valid highlighted pixels or all diameters < min).")
    # -------------------------------------------------------------------------

    # Display the saved montage
    img = plt.imread(MONTAGE_FILENAME)
    fig = plt.figure(figsize=(10, 8))
    plt.imshow(img)
    plt.axis('off')
    plt.title("Spectral Slices Montage")
    plt.show()

if __name__ == "__main__":
    run_from_config()
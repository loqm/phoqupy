import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd
import cv2
import matplotlib.pyplot as plt

# Gemini motion & processing modules (same as existing pipeline)
import MovementsMCS as Mov
import Processing

# Princeton EMCCD (pylablib)
from pylablib.devices import PrincetonInstruments

# ---------------- USER CONFIG ----------------
CUBE_SAVE_DIR = r"filepath"
os.makedirs(CUBE_SAVE_DIR, exist_ok=True)

# scan / spectrum parameters 
start_wave = 560
end_wave = 600
resolution = 5
sampling_factor = 4
apodization_width = 10
spectral_points = 80
SLICE_INTERVAL_NM = 0.5

# Binning 
BIN_HEIGHT = 1
BIN_WIDTH = 1
BINNED_ROWS = int(512/BIN_HEIGHT)
BINNED_COLS = int(512/BIN_WIDTH)

# Princeton camera settings (edit serial / exposure as needed)
CAM_SERIAL = 'None'  # e.g. 'X092527425' ; if None will open first listed camera
EXPOSURE_MS = 30.0  # exposure in milliseconds

# ------------------------------------------------

def bin_image(image, bin_height, bin_width, n_rows, n_cols):
    h, w = image.shape
    binned = np.zeros((n_rows, n_cols), dtype=np.float32)
    for r in range(n_rows):
        y0 = r * bin_height
        y1 = min((r + 1) * bin_height, h)
        for c in range(n_cols):
            x0 = c * bin_width
            x1 = min((c + 1) * bin_width, w)
            region = image[y0:y1, x0:x1]
            binned[r, c] = np.mean(region) if region.size else 0.0
    return binned

def open_emccd(serial=None, exposure_ms=30.0):
    PrincetonInstruments.list_cameras()
    if serial is None:
        cams = PrincetonInstruments.list_cameras()
        if not cams:
            raise SystemExit("No Princeton cameras found")
        serial = cams[0]
    cam = PrincetonInstruments.PicamCamera(serial)
    cam.open()
    # Set exposure (attribute name may vary by firmware; typical: "Exposure Time" or "Exposure")
    try:
        cam.set_attribute_value("Exposure Time", exposure_ms)
    except Exception:
        # fallback to exposure in ms attribute names
        try:
            cam.set_attribute_value("Exposure", exposure_ms)
        except Exception:
            pass
    return cam

def main():
    print("Initializing (EMCCD version)...")
    # Processing / motor init (same as Main.py)
    P_freq2wave, P_wave2freq = Processing.spectral_calibration()
    system_index, channelIndex, errorflag = Mov.initialization()
    if errorflag == 1:
        sys.exit()

    lambda_mean = (start_wave + end_wave) / 2
    start_position, end_position = Processing.scan_range(lambda_mean, resolution)

    # clamp to positioner limits (use same parameter file lookup as Main.py)
    # find parameters_int file in cwd, else fall back to hardcoded file used previously
    filename = None
    for n in os.listdir("."):
        if n.endswith("parameters_int.txt"):
            filename = n
            break
    if filename is None:
        filename = r"absolute_filepath\\parameters_int.txt"
    ref = pd.read_csv(filename, sep="\t", header=None)
    position_ref = ref.iloc[0].to_numpy(dtype='float64')
    start_position = max(start_position, position_ref[0])
    end_position = min(end_position, position_ref[-1])

    freq = np.polyval(P_wave2freq, 1 / start_wave)
    freq_mm = 1 / freq
    number_steps = int(np.ceil((abs(start_position - end_position)) / (freq_mm / sampling_factor)))
    step = (end_position - start_position) / number_steps if number_steps != 0 else 0.0

    # open EMCCD
    cam = open_emccd(CAM_SERIAL, EXPOSURE_MS)
    print("Camera opened. Attributes (sample):")
    try:
        print(cam.get_all_attribute_values())
    except Exception:
        pass

    try:
        # move to start
        Mov.move_absolute(system_index, channelIndex, start_position)
        time.sleep(0.05)

        data_acquired = []
        positions = []
        means = []

        # simple live plot setup
        fig, ax = plt.subplots()
        ln, = ax.plot([], [], '-o')
        ax.set_xlabel("Position [mm]")
        ax.set_ylabel("Mean intensity")
        fig.show()
        fig.canvas.draw()

        # Acquire at start and subsequent steps
        pos = start_position
        for i in range(number_steps + 1):
            Mov.move_absolute(system_index, channelIndex, pos)
            # wait for motion complete
            while True:
                status = Mov.get_status(system_index, channelIndex)
                if Mov.identify() == 'SCU':
                    if status.value in (0, 4):
                        break
                else:
                    if status.value in (0, 3):
                        break
                time.sleep(0.01)

            # acquire image from EMCCD (snap is synchronous)
            img = cam.snap()
            if img is None:
                img = np.zeros((1,1), dtype=np.uint16)
            img = np.asarray(img)
            # ensure 2D
            if img.ndim == 3:
                # if color, convert to grayscale first channel
                img = img[..., 0]
            data_acquired.append(img)
            positions.append(pos)
            means.append(np.mean(img))

            # update live plot
            ln.set_xdata(positions)
            ln.set_ydata(means)
            ax.relim()
            ax.autoscale_view()
            fig.canvas.draw_idle()
            fig.canvas.flush_events()

            pos = pos + step

        # Convert to numpy array: (n_frames, height, width)
        data_stack = np.array(data_acquired)
        height, width = data_stack.shape[1], data_stack.shape[2]
        np.save(os.path.join(CUBE_SAVE_DIR, "raw_stack_emccd.npy"), data_stack)

        # Binning
        binned_frames = []
        for frame in data_stack:
            binned = bin_image(frame, BIN_HEIGHT, BIN_WIDTH, BINNED_ROWS, BINNED_COLS)
            binned_frames.append(binned)
        binned_frames = np.array(binned_frames)  # (n_frames, rows, cols)
        np.save(os.path.join(CUBE_SAVE_DIR, "binned_frames_emccd.npy"), binned_frames)

        # Calibrate positions and compute spectra per bin
        calibrated_positions = Processing.get_calibrated_position_axis(np.array(positions))
        hyperspectral_cube = np.zeros((BINNED_ROWS, BINNED_COLS, spectral_points), dtype=np.float32)

        total_bins = BINNED_ROWS * BINNED_COLS
        idx = 0
        t0 = time.time()
        for r in range(BINNED_ROWS):
            for c in range(BINNED_COLS):
                signal = binned_frames[:, r, c].flatten()
                try:
                    spectrum, wave, freq, signal_out = Processing.get_spectrum(
                        signal, calibrated_positions, start_wave, end_wave, spectral_points, apodization_width
                    )
                    hyperspectral_cube[r, c, :] = spectrum
                except Exception as e:
                    # leave zeros on error
                    print(f"Error bin ({r},{c}): {e}")
                idx += 1
                if idx % 100 == 0 or idx == total_bins:
                    elapsed = time.time() - t0
                    print(f"Processed {idx}/{total_bins} bins ({idx/total_bins*100:.1f}%) Elapsed: {elapsed:.1f}s")

        # Save outputs
        np.save(os.path.join(CUBE_SAVE_DIR, "hyperspectral_cube.npy"), hyperspectral_cube)
        np.save(os.path.join(CUBE_SAVE_DIR, "wavelength_axis.npy"), wave)
        np.save(os.path.join(CUBE_SAVE_DIR, "frequency_axis.npy"), freq)
        np.save(os.path.join(CUBE_SAVE_DIR, "position_axis.npy"), calibrated_positions)

        # Visualization: average spectrum and center bin (wrt wavelength only)
        avg_spec = np.mean(hyperspectral_cube, axis=(0, 1))
        fig, ax = plt.subplots(figsize=(8,4.5))
        ax.plot(wave, avg_spec)
        ax.set_xlabel("Wavelength [nm]")
        ax.set_ylabel("Amplitude")
        ax.set_title("Average Spectrum (all bins)")
        ax.grid(True)
        plt.show()

        center_r, center_c = BINNED_ROWS // 2, BINNED_COLS // 2
        fig, ax = plt.subplots(figsize=(8,4.5))
        ax.plot(wave, hyperspectral_cube[center_r, center_c, :])
        ax.set_xlabel("Wavelength [nm]")
        ax.set_ylabel("Amplitude")
        ax.set_title(f"Center bin spectrum ({center_r},{center_c})")
        ax.grid(True)
        plt.show()

        # Integrated intensity map
        integrated = np.sum(hyperspectral_cube, axis=2)
        fig, ax = plt.subplots(figsize=(8,8))
        im = ax.imshow(integrated, cmap='viridis', interpolation='nearest')
        plt.colorbar(im, ax=ax, label='Integrated Intensity')
        ax.set_title("Integrated spectral intensity")
        plt.show()

        # spectral slices (saved)
        slices_dir = os.path.join(CUBE_SAVE_DIR, "spectral_slices_emccd")
        os.makedirs(slices_dir, exist_ok=True)
        targets = np.arange(start_wave, end_wave+SLICE_INTERVAL_NM, SLICE_INTERVAL_NM)
        targets = targets[targets <= end_wave]
        for wl in targets:
            wl_idx = int(np.argmin(np.abs(wave - wl)))
            slice2d = hyperspectral_cube[:, :, wl_idx]
            mn, mx = slice2d.min(), slice2d.max()
            if mx > mn:
                norm = ((slice2d - mn) / (mx - mn) * 255).astype(np.uint8)
            else:
                norm = np.zeros_like(slice2d, dtype=np.uint8)
            up = cv2.resize(norm, (200,200), interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(os.path.join(slices_dir, f"slice_{int(wl)}nm.png"), up)

        # summary file
        with open(os.path.join(CUBE_SAVE_DIR, "scan_summary_emccd.txt"), "w") as f:
            f.write(f"EMCCD Gemini scan summary\nTimestamp: {datetime.now()}\n")
            f.write(f"Frames captured: {len(data_stack)}\n")
            f.write(f"Hyperspectral cube shape: {hyperspectral_cube.shape}\n")

        print("Processing complete. Files saved to:", CUBE_SAVE_DIR)

    finally:
        try:
            cam.close()
        except Exception:
            pass
        try:
            Mov.close_system()
        except Exception:
            pass

if __name__ == "__main__":
    main()
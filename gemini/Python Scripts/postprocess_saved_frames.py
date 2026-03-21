import os
import sys
import numpy as np
import cv2
import matplotlib.pyplot as plt
from datetime import datetime
import Processing

# --- User parameters (edit as needed) ---
# Directory containing the saved raw frame images and position file
FRAMES_DIRECTORY = r"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini_data\\filename"
# Directory where all post-processing outputs will be written
OUTPUT_DIRECTORY = r"C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini_data\\filename_processed"

start_wave = 550
end_wave = 700
spectral_points = 150
apodization_width = 10
camera=1 #1 for thorlabs and 0 for EMCCD
BIN_HEIGHT = 3
BIN_WIDTH = 3

SLICE_INTERVAL_NM = 1

if camera==1:
    BINNED_ROWS = int(1080/BIN_HEIGHT)
    BINNED_COLS = int(1440/BIN_WIDTH)
elif camera==0:
    BINNED_ROWS = int(512/BIN_HEIGHT)
    BINNED_COLS = int(512/BIN_WIDTH)
# ---------------------------------------

def bin_image(image, bin_height, bin_width, n_rows, n_cols):
    h, w = image.shape
    binned = np.zeros((n_rows, n_cols), dtype=np.float32)
    for r in range(n_rows):
        for c in range(n_cols):
            y0 = r*bin_height
            y1 = min((r+1)*bin_height, h)
            x0 = c*bin_width
            x1 = min((c+1)*bin_width, w)
            region = image[y0:y1, x0:x1]
            binned[r, c] = np.mean(region) if region.size else 0
    return binned

# collect frame files from FRAMES_DIRECTORY
if not os.path.isdir(FRAMES_DIRECTORY):
    print("Frames directory not found:", FRAMES_DIRECTORY); sys.exit(1)

# ensure output directory exists
os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

files = [f for f in os.listdir(FRAMES_DIRECTORY) if f.lower().endswith(('.png','.tif','.tiff','.bmp')) and 'frame_' in f]
if not files:
    print("No frame images found in", FRAMES_DIRECTORY); sys.exit(1)

# sort by numeric index after 'frame_'
def frame_key(fn):
    import re
    m = re.search(r'(\d+)', fn)
    return int(m.group(1)) if m else fn
files = sorted(files, key=frame_key)
paths = [os.path.join(FRAMES_DIRECTORY, f) for f in files]

# load frames
stack = []
for p in paths:
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is None:
        print("Warning: failed to read", p); continue
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    stack.append(img.astype(np.float32))
stack = np.stack(stack, axis=0)  # (n_frames, H, W)
print("Loaded frames:", stack.shape)

# try to load position axis from FRAMES_DIRECTORY
pos_candidates = ['position_axis.npy','positions.npy','position_axis.txt','positions.txt']
positions = None
for c in pos_candidates:
    p = os.path.join(FRAMES_DIRECTORY, c)
    if os.path.exists(p):
        try:
            if p.lower().endswith('.npy'):
                positions = np.load(p)
            else:
                positions = np.loadtxt(p)
            break
        except Exception:
            pass

if positions is None:
    print("Position axis file not found in frames directory. Provide a 1D positions file named position_axis.npy or positions.txt in the frames directory"); sys.exit(1)

# bin frames
n_frames, H, W = stack.shape
print("Binning frames to", BINNED_ROWS, "x", BINNED_COLS)
binned = np.zeros((n_frames, BINNED_ROWS, BINNED_COLS), dtype=np.float32)
for i in range(n_frames):
    binned[i] = bin_image(stack[i], BIN_HEIGHT, BIN_WIDTH, BINNED_ROWS, BINNED_COLS)
    if (i+1) % 10 == 0 or i+1==n_frames:
        print(f"  Binned {i+1}/{n_frames}")

np.save(os.path.join(OUTPUT_DIRECTORY, "binned_frames.npy"), binned)
print("Saved binned_frames.npy to", OUTPUT_DIRECTORY)

# calibrate positions
calibrated_positions = Processing.get_calibrated_position_axis(np.array(positions))
print("Calibrated positions:", calibrated_positions.shape)

# compute hyperspectral cube
cube = np.zeros((BINNED_ROWS, BINNED_COLS, spectral_points), dtype=np.float32)
wave = None; freq = None
total = BINNED_ROWS * BINNED_COLS
cnt = 0
for r in range(BINNED_ROWS):
    for c in range(BINNED_COLS):
        signal = binned[:, r, c].flatten()
        try:
            spectrum, wave, freq, _ = Processing.get_spectrum(
                signal, calibrated_positions, start_wave, end_wave, spectral_points, apodization_width
            )
            cube[r, c, :] = spectrum
        except Exception as e:
            print(f"  Error at bin ({r},{c}): {e}")
        cnt += 1
        if cnt % 50 == 0 or cnt==total:
            print(f"  Processed {cnt}/{total} bins")

# save cube and axes to OUTPUT_DIRECTORY
np.save(os.path.join(OUTPUT_DIRECTORY, "hyperspectral_cube.npy"), cube)
if wave is not None:
    np.save(os.path.join(OUTPUT_DIRECTORY, "wavelength_axis.npy"), wave)
    np.save(os.path.join(OUTPUT_DIRECTORY, "frequency_axis.npy"), freq)
np.save(os.path.join(OUTPUT_DIRECTORY, "position_axis.npy"), calibrated_positions)
print("Saved hyperspectral_cube and axes to", OUTPUT_DIRECTORY)

# average spectrum plot
avg = np.mean(cube, axis=(0,1))
plt.figure(figsize=(8,4)); plt.plot(wave, avg); plt.xlabel('Wavelength (nm)'); plt.ylabel('Amplitude'); plt.grid(True)
plt.title('Average Spectrum'); plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIRECTORY, "average_spectrum.png"), dpi=150)
plt.close()

# spatial integrated intensity map
integrated = np.sum(cube, axis=2)
plt.figure(figsize=(6,6)); plt.imshow(integrated, cmap='viridis'); plt.colorbar(label='Integrated Intensity')
plt.title('Integrated Intensity Map'); plt.savefig(os.path.join(OUTPUT_DIRECTORY, "spatial_intensity_map.png"), dpi=150); plt.close()

# spectral slices (every SLICE_INTERVAL_NM nm) saved to OUTPUT_DIRECTORY/spectral_slices
slices_dir = os.path.join(OUTPUT_DIRECTORY, "spectral_slices")
os.makedirs(slices_dir, exist_ok=True)
target_wls = np.arange(start_wave, end_wave+SLICE_INTERVAL_NM, SLICE_INTERVAL_NM)
target_wls = target_wls[target_wls <= end_wave]
for tw in target_wls:
    idx = np.argmin(np.abs(wave - tw))
    slice2d = cube[:, :, idx]
    mn, mx = slice2d.min(), slice2d.max()
    if mx>mn:
        img = ((slice2d - mn)/(mx-mn) * 255).astype(np.uint8)
    else:
        img = np.zeros_like(slice2d, dtype=np.uint8)
    up = cv2.resize(img, (200,200), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(os.path.join(slices_dir, f"slice_{int(tw)}nm.png"), up)
print("Saved spectral slices to", slices_dir)

# write summary to OUTPUT_DIRECTORY
with open(os.path.join(OUTPUT_DIRECTORY, "postprocess_summary.txt"), 'w') as f:
    f.write(f"Postprocessing summary\nTimestamp: {datetime.now()}\n")
    f.write(f"Frames loaded: {n_frames}\nCube shape: {cube.shape}\n")
print("Done.")

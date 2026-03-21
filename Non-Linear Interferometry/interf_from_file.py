import numpy as np
import matplotlib.pyplot as plt
import pathlib as Path


# Plotting

# plot_wavelength_index = 807.5E-9  # Index of wavelength to plot (change as needed)

# Find index of wavelength closest to plot_wavelength_index
data = np.loadtxt("C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\Non-Linear Interferometry\\filename")
scan_matrix = data.T  # data is transposed, so transpose back
START = 96.4
RANGE_MM = 0.8
STEP_MM = 0.0002
positions = np.linspace(START, START + RANGE_MM, scan_matrix.shape[0]-1)
wavelengths = scan_matrix[0]

intensities = scan_matrix.max(axis=1)[1:]

# --- moving average with edge-padding to avoid start/end dip ---
window = 1

if window <= 1:
    smoothed_intensities = intensities.copy()
else:
    # ensure window is not larger than data
    if window > len(intensities):
        window = len(intensities)
    # prefer odd window for symmetric padding
    if window % 2 == 0:
        window += 1
    pad = window // 2
    kernel = np.ones(window) / window
    # use 'reflect' padding to avoid introducing edge zeros/dips
    padded = np.pad(intensities, pad_width=pad, mode='reflect')
    smoothed_intensities = np.convolve(padded, kernel, mode='valid')

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# save smoothed data
np.savetxt(f"interferometer_data_smoothed.txt", np.column_stack((positions, smoothed_intensities)))

# Plot smoothed intensity vs position
ax1.plot(positions, smoothed_intensities, 'o-', label=f'{window}-pt MA')
ax1.set_xlabel('Position (µm)')
ax1.set_ylabel('Intensity (counts)')
ax1.set_title(f'Intensity vs Position (smoothed)')
ax1.grid(True)
ax1.legend()

# Plot all spectra as 2D colormap
extent = [wavelengths.min(), wavelengths.max(), positions[-1], positions[0]]
im = ax2.imshow(scan_matrix[1:], aspect='auto', cmap='coolwarm', extent=extent)
ax2.set_xlabel('Wavelength (nm)')
ax2.set_ylabel('Position (µm)')
ax2.set_title('Spectra vs Position')
fig.colorbar(im, ax=ax2, label='Intensity')

plt.tight_layout()
plt.show()
#Use MovementsMCS if you have an GEMINI HP, otherwise use MovementsSCU
import MovementsMCS as Mov 

#import packages
import Processing
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import sys
import time
import cv2
from datetime import datetime
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

try:
    from windows_setup import configure_path
    configure_path()
except ImportError:
    pass

'''This values have to be changed accordingly to your measurements, values in [nm]'''
start_wave = 750
end_wave = 900
resolution = 10
sampling_factor = 4
apodization_width = 10
spectral_points = 150
EXPOSURE_TIME_US = 1500000#s
SAVE_DIRECTORY = "C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini_data\\filename"

# Binning parameters
BIN_HEIGHT = 9  # pixels per bin in y-direction
BIN_WIDTH = 12   # pixels per bin in x-direction
BINNED_ROWS = int(1080/BIN_HEIGHT)  # number of bins in y-direction
BINNED_COLS = int(1440/BIN_WIDTH)  # number of bins in x-direction

# Spectral slice parameters
SLICE_INTERVAL_NM = 1  # Save spectral slice every 1 nm

# Create save directory
os.makedirs(SAVE_DIRECTORY, exist_ok=True)
print(f"Images will be saved to: {os.path.abspath(SAVE_DIRECTORY)}\n")

def data_acquisition(camera, frame_number, save_dir):
    """
    Capture a single monochrome frame from Thorlabs camera and save as PNG.
    Returns a scalar value (mean intensity) for the interferogram plot.
    """
    time.sleep(0.3)
    
    try:
        # Trigger and capture frame
        camera.issue_software_trigger()
        frame = camera.get_pending_frame_or_null()
        
        if frame is None:
            print(f"    ⚠ Failed to capture frame #{frame_number}")
            return 0  # Return zero if capture fails
        
        # Get image dimensions
        image_width = camera.image_width_pixels
        image_height = camera.image_height_pixels
        
        # Get raw monochrome image buffer
        mono_image = np.copy(frame.image_buffer)
        mono_image_reshape = mono_image.reshape(image_height, image_width)
        
        # Save with frame number in filename
        filename = f"frame_{frame_number}.png"
        filepath = os.path.join(save_dir, filename)
        
        # Save as PNG (lossless)
        # Handle different bit depths
        if camera.bit_depth > 8:
            # Scale to 8-bit for PNG
            mono_image_8bit = (mono_image_reshape / (2**camera.bit_depth - 1) * 255).astype(np.uint8)
            cv2.imwrite(filepath, mono_image_8bit)
        else:
            cv2.imwrite(filepath, mono_image_reshape)
        
        return mono_image_reshape
    
    except Exception as e:
        print(f"    ❌ Error in data acquisition: {e}")
        return 0


def bin_image(image, bin_height, bin_width, n_rows, n_cols):
    """
    Bin image into blocks and compute mean of each block.
    
    Parameters:
    -----------
    image : ndarray, shape (height, width)
        Input image
    bin_height : int
        Height of each bin in pixels
    bin_width : int
        Width of each bin in pixels
    n_rows : int
        Number of bins in vertical direction
    n_cols : int
        Number of bins in horizontal direction
    
    Returns:
    --------
    binned : ndarray, shape (n_rows, n_cols)
        Mean intensity of each bin
    """
    height, width = image.shape
    binned = np.zeros((n_rows, n_cols), dtype=np.float32)
    
    for row in range(n_rows):
        for col in range(n_cols):
            # Calculate pixel range for this bin
            y_start = row * bin_height
            y_end = min((row + 1) * bin_height, height)
            x_start = col * bin_width
            x_end = min((col + 1) * bin_width, width)
            
            # Extract region and compute mean
            region = image[y_start:y_end, x_start:x_end]
            binned[row, col] = np.mean(region)
    
    return binned


'''Initialization'''
print('Initializing...')
P_freq2wave, P_wave2freq = Processing.spectral_calibration()
print(P_freq2wave, P_wave2freq)

system_index, channelIndex, errorflag = Mov.initialization()
print(system_index, channelIndex)

if errorflag == 1:
    sys.exit()

print('Setting scan parameters...')

lambda_mean = (start_wave + end_wave) / 2
start_position, end_position = Processing.scan_range(lambda_mean, resolution)
print('Start position [mm]: ', start_position)
print('End position [mm]: ', end_position)

# Check that the start_position and end_position are inside the positioner's travel range
items = os.listdir(".")
for names in items:
    if names.endswith("parameters_int.txt"):
        filename = names
filename = "absolute_filepath\\parameters_int.txt"
ref = pd.read_csv(filename, sep="\t", header=None)
first_row = (ref.iloc[0])
second_row = (ref.iloc[1])

position_ref = first_row.to_numpy(dtype='float64')

if start_position < position_ref[0]:
    start_position = position_ref[0]

if end_position > position_ref[-1]:
    end_position = position_ref[-1]

freq = np.polyval(P_wave2freq, 1 / start_wave)
freq_mm = 1 / freq
number_steps = np.ceil((abs(start_position - end_position)) / (freq_mm / sampling_factor))
step = (end_position - start_position) / number_steps

items = os.listdir(".")
for names in items:
    if names.endswith("parameters_scale.txt"):
        filename = names

ref = pd.read_csv(filename, sep="\t", header=None)
first_row = (ref.iloc[0])
scale = first_row.to_numpy(dtype='float64')

'''Data acquisition'''
print('Acquiring Data...')

try:
    # Initialize Thorlabs camera
    print('Initializing Thorlabs camera...')
    with TLCameraSDK() as camera_sdk:
        available_cameras = camera_sdk.discover_available_cameras()
        if len(available_cameras) < 1:
            print("❌ No cameras detected")
            sys.exit()
        
        with camera_sdk.open_camera(available_cameras[0]) as camera:
            camera.exposure_time_us = EXPOSURE_TIME_US
            camera.frames_per_trigger_zero_for_unlimited = 0
            camera.image_poll_timeout_ms = 2000
            camera.arm(2)
            
            print(f"✓ Camera initialized (exposure: {EXPOSURE_TIME_US/1000:.1f} ms)")
            print(f"  Resolution: {camera.image_width_pixels}×{camera.image_height_pixels}")
            print(f"  Bit depth: {camera.bit_depth}-bit")
            print(f"  Binning: {BIN_HEIGHT}×{BIN_WIDTH} pixels → {BINNED_ROWS}×{BINNED_COLS} bins\n")
            
            next_position = start_position
            
            Mov.move_absolute(system_index, channelIndex, next_position)
            
            # First data point
            first_data = data_acquisition(camera, 0, SAVE_DIRECTORY)
            data_acquired = [first_data]
            positions = [start_position]
            data = [np.mean(first_data)]
            
            # Used to generate the background of the live figure
            x = np.linspace(start_position, end_position, 100)
            y = np.linspace(0, 2**camera.bit_depth - 1, 100)  # Range for bit depth
            fig1, ax1 = plt.subplots()
            (ln,) = ax1.plot(x, y, animated=True)
            fig1.suptitle('Interferogram as a function of position')
            ax1.set_ylabel('Mean Intensity')
            ax1.set_xlabel('Position [mm]')
            plt.show(block=False)
            plt.pause(0.1)
            bg = fig1.canvas.copy_from_bbox(fig1.bbox)
            ax1.draw_artist(ln)
            fig1.canvas.blit(fig1.bbox)
            fig1.canvas.flush_events()
            print(f"Total steps: {int(number_steps)}\n")
            
            for i in range(0, int(number_steps)):
                next_position = next_position + step
                Mov.move_absolute(system_index, channelIndex, next_position)
                
                while True:
                    status = Mov.get_status(system_index, channelIndex)
                    
                    if Mov.identify() == 'SCU':
                        if status.value == 0 or status.value == 4:
                            break
                    
                    if Mov.identify() == 'MCS':
                        if status.value == 0 or status.value == 3:
                            break
                
                # Capture frame and get mean intensity
                raw = data_acquisition(camera, i + 1, SAVE_DIRECTORY)
                data_acquired.append(raw)
                print(f"  Step {i+1}/{int(number_steps)}")
                
                positions.append(Mov.get_position(system_index, channelIndex))
                print(f"  Position: {positions[-1]:.4f} mm\n")
                mean_intensity = np.mean(raw)
                data.append(mean_intensity)
                # Update live plot
                fig1.canvas.restore_region(bg)
                ln.set_ydata(data)
                ln.set_xdata(positions)
                ax1.draw_artist(ln)
                fig1.canvas.blit(fig1.bbox)
                fig1.canvas.flush_events()
            
            ln.set_animated(False)  # stops manual rendering
            
            camera.disarm()
            print("✓ Camera disarmed")
    #
    # Close GEMINI motor system before processing
    print("\n" + "=" * 60)
    print("Data acquisition complete. Closing GEMINI motor system...")
    print("=" * 60)
    Mov.close_system()
    print("✓ GEMINI motor system closed\n")

    # Get image dimensions from first frame
    height, width = np.shape(data_acquired[0])
    print(f"Original image dimensions: {height} × {width}")
    print(f"Number of frames: {len(data_acquired)}")
    print(f"Binning into: {BINNED_ROWS} × {BINNED_COLS} regions")
    print(f"Bin size: {BIN_HEIGHT} × {BIN_WIDTH} pixels")
    print(f"Total bins to process: {BINNED_ROWS * BINNED_COLS}\n")
    
    # Convert data_acquired list to numpy array for easier indexing
    data_acquired_array = np.array(data_acquired)  # Shape: (n_frames, height, width)
    print(f"Data stack shape: {data_acquired_array.shape}\n")
    
    # Bin all frames into reduced resolution
    print("Binning all frames...")
    binned_frames = []
    for i, frame in enumerate(data_acquired_array):
        binned = bin_image(frame, BIN_HEIGHT, BIN_WIDTH, BINNED_ROWS, BINNED_COLS)
        binned_frames.append(binned)
        if (i + 1) % 10 == 0:
            print(f"  Binned {i+1}/{len(data_acquired_array)} frames")
    
    binned_frames_array = np.array(binned_frames)  # Shape: (n_frames, BINNED_ROWS, BINNED_COLS)
    print(f"✓ Binned frames array shape: {binned_frames_array.shape}\n")
    
    # Save binned frames for verification
    binned_frames_file = os.path.join(SAVE_DIRECTORY, "binned_frames.npy")
    np.save(binned_frames_file, binned_frames_array)
    print(f"✓ Binned frames saved to: {binned_frames_file}\n")
    
    # Initialize 3D array to store spectra: (BINNED_ROWS, BINNED_COLS, spectral_points)
    hyperspectral_cube = np.zeros((BINNED_ROWS, BINNED_COLS, spectral_points), dtype=np.float32)
    
    # Calibrate position axis once (same for all pixels)
    position_axis = np.array(positions)
    print('Calibrating position axis...')
    calibrated_positions = Processing.get_calibrated_position_axis(position_axis)
    print(f"Calibrated positions shape: {calibrated_positions.shape}\n")
    
    print("=" * 60)
    print("Computing hyperspectral cube on binned data...")
    print("=" * 60)
    
    # Nested loop to process each binned region
    total_bins = BINNED_ROWS * BINNED_COLS
    print(f"Total bins to process: {total_bins}")
    processed_bins = 0
    start_time = time.time()
    
    for row in range(BINNED_ROWS):
        for col in range(BINNED_COLS):
            # Extract interferogram time series for this bin
            bin_interferogram = binned_frames_array[:, row, col]  # Shape: (n_frames,)
            
            # Flatten to 1D array
            signal = bin_interferogram.flatten()
            
            # Compute spectrum for this bin
            try:
                spectrum, wave, freq, signal_out = Processing.get_spectrum(
                    signal, calibrated_positions, start_wave, end_wave, spectral_points, apodization_width
                )
                
                # Store spectrum in hyperspectral cube
                hyperspectral_cube[row, col, :] = spectrum
                
            except Exception as e:
                print(f"  ⚠ Error processing bin ({row}, {col}): {e}")
                # Leave zeros in hyperspectral_cube for failed bins
            
            processed_bins += 1
            
            # Print progress
            if processed_bins % 10 == 0 or processed_bins == total_bins:
                elapsed_time = time.time() - start_time
                bins_per_sec = processed_bins / elapsed_time
                remaining_bins = total_bins - processed_bins
                eta_seconds = remaining_bins / bins_per_sec if bins_per_sec > 0 else 0
                
                print(f"  Progress: {processed_bins}/{total_bins} bins "
                      f"({100*processed_bins/total_bins:.1f}%) | "
                      f"Speed: {bins_per_sec:.2f} bins/s | "
                      f"ETA: {eta_seconds:.1f} s")
        
        # Print row completion
        print(f"  ✓ Completed row {row+1}/{BINNED_ROWS}")
    
    total_time = time.time() - start_time
    print(f"\n✓ Hyperspectral cube computation complete!")
    print(f"  Total time: {total_time:.1f} seconds ({total_time/60:.2f} minutes)")
    print(f"  Average speed: {total_bins/total_time:.2f} bins/second")
    print(f"  Cube shape: {hyperspectral_cube.shape}")
    
    # Save hyperspectral cube
    print("\nSaving hyperspectral cube...")
    cube_file = os.path.join(SAVE_DIRECTORY, "hyperspectral_cube.npy")
    np.save(cube_file, hyperspectral_cube)
    print(f"✓ Hyperspectral cube saved to: {cube_file}")
    
    # Save wavelength axis (same for all bins)
    wavelength_file = os.path.join(SAVE_DIRECTORY, "wavelength_axis.npy")
    np.save(wavelength_file, wave)
    print(f"✓ Wavelength axis saved to: {wavelength_file}")
    
    # Save frequency axis
    frequency_file = os.path.join(SAVE_DIRECTORY, "frequency_axis.npy")
    np.save(frequency_file, freq)
    print(f"✓ Frequency axis saved to: {frequency_file}")
    
    # Save position axis
    position_file = os.path.join(SAVE_DIRECTORY, "position_axis.npy")
    np.save(position_file, calibrated_positions)
    print(f"✓ Position axis saved to: {position_file}")
    
    # Compute and plot average spectrum across all bins
    print('\nComputing average spectrum for visualization...')
    avg_spectrum = np.mean(hyperspectral_cube, axis=(0, 1))  # Average over spatial dimensions
    
    '''Plots of the average spectra'''
    print('Plotting average spectrum...')
    fig, axs = plt.subplots(2, figsize=(10, 8))
    fig.suptitle(f'Average Spectrum across all {BINNED_ROWS}×{BINNED_COLS} bins')
    axs[0].plot(wave, avg_spectrum)
    axs[1].plot(freq, avg_spectrum)
    axs[0].set_ylabel('Amplitude')
    axs[0].set_xlabel('Wavelength [nm]')
    axs[0].grid(True, alpha=0.3)
    axs[1].set_ylabel('Amplitude')
    axs[1].set_xlabel('Spatial frequency [mm^-1]')
    axs[1].grid(True, alpha=0.3)
    plt.tight_layout()
    
    spectrum_plot_file = os.path.join(SAVE_DIRECTORY, "average_spectrum.png")
    plt.savefig(spectrum_plot_file, dpi=150)
    print(f"✓ Average spectrum plot saved to: {spectrum_plot_file}")
    plt.show()
    
    # Plot example bin spectrum (center bin)
    center_row, center_col = BINNED_ROWS // 2, BINNED_COLS // 2
    center_spectrum = hyperspectral_cube[center_row, center_col, :]
    
    fig, axs = plt.subplots(2, figsize=(10, 8))
    fig.suptitle(f'Spectrum at center bin ({center_row}, {center_col})')
    axs[0].plot(wave, center_spectrum)
    axs[1].plot(freq, center_spectrum)
    axs[0].set_ylabel('Amplitude')
    axs[0].set_xlabel('Wavelength [nm]')
    axs[0].grid(True, alpha=0.3)
    axs[1].set_ylabel('Amplitude')
    axs[1].set_xlabel('Spatial frequency [mm^-1]')
    axs[1].grid(True, alpha=0.3)
    plt.tight_layout()
    
    center_plot_file = os.path.join(SAVE_DIRECTORY, "center_bin_spectrum.png")
    plt.savefig(center_plot_file, dpi=150)
    print(f"✓ Center bin spectrum plot saved to: {center_plot_file}")
    plt.show()
    
    # Create spatial heatmap of integrated spectrum intensity
    print("\nGenerating spatial intensity map...")
    integrated_intensity = np.sum(hyperspectral_cube, axis=2)  # Sum over wavelength axis
    
    fig, ax = plt.subplots(figsize=(8, 8))
    im = ax.imshow(integrated_intensity, cmap='viridis', interpolation='nearest')
    ax.set_title(f'Integrated Spectral Intensity Map ({BINNED_ROWS}×{BINNED_COLS})')
    ax.set_xlabel('Bin Column')
    ax.set_ylabel('Bin Row')
    plt.colorbar(im, ax=ax, label='Integrated Intensity')
    
    # Add bin labels
    for i in range(BINNED_ROWS):
        for j in range(BINNED_COLS):
            ax.text(j, i, f'({i},{j})', ha='center', va='center', 
                   color='white', fontsize=6, alpha=0.7)
    
    intensity_map_file = os.path.join(SAVE_DIRECTORY, "spatial_intensity_map.png")
    plt.savefig(intensity_map_file, dpi=150)
    print(f"✓ Spatial intensity map saved to: {intensity_map_file}")
    plt.show()
    
    # Generate spectral slice images at every 5nm across the entire range
    print(f"\nGenerating spectral slice images every {SLICE_INTERVAL_NM} nm...")
    
    # Create subdirectory for spectral slices
    slices_dir = os.path.join(SAVE_DIRECTORY, "spectral_slices")
    os.makedirs(slices_dir, exist_ok=True)
    
    # Generate target wavelengths at 5nm intervals
    target_wavelengths = np.arange(start_wave, end_wave + SLICE_INTERVAL_NM, SLICE_INTERVAL_NM)
    
    # Ensure we don't exceed the end_wave
    target_wavelengths = target_wavelengths[target_wavelengths <= end_wave]
    
    print(f"  Wavelength range: {start_wave} - {end_wave} nm")
    print(f"  Interval: {SLICE_INTERVAL_NM} nm")
    print(f"  Total slices to generate: {len(target_wavelengths)}\n")
    
    saved_slices = 0
    for target_wl in target_wavelengths:
        # Find closest wavelength index in the computed spectrum
        wl_idx = np.argmin(np.abs(wave - target_wl))
        actual_wl = wave[wl_idx]
        
        # Extract 2D spatial map at this wavelength
        spatial_slice = hyperspectral_cube[:, :, wl_idx]
        
        # Normalize to 0-255 for visualization
        slice_min, slice_max = spatial_slice.min(), spatial_slice.max()
        if slice_max > slice_min:
            spatial_slice_normalized = 255 * (spatial_slice - slice_min) / (slice_max - slice_min)
        else:
            spatial_slice_normalized = np.zeros_like(spatial_slice)
        
        spatial_slice_normalized = spatial_slice_normalized.astype(np.uint8)
        
        # Upscale for better visualization (40x40 → 200x200)
        spatial_slice_upscaled = cv2.resize(spatial_slice_normalized, (200, 200), 
                                            interpolation=cv2.INTER_NEAREST)
        
        # Save with target wavelength in filename
        slice_filename = os.path.join(slices_dir, f"slice_{target_wl:.0f}nm.png")
        cv2.imwrite(slice_filename, spatial_slice_upscaled)
        
        saved_slices += 1
        if saved_slices % 5 == 0 or saved_slices == len(target_wavelengths):
            print(f"  Saved {saved_slices}/{len(target_wavelengths)} slices (last: {target_wl:.0f} nm)")
    
    print(f"\n✓ Generated {saved_slices} spectral slice images")
    print(f"  Saved to: {os.path.abspath(slices_dir)}")
    
    # Create a summary plot showing all wavelengths with COMMON SCALE BAR
    print("\nCreating spectral slice summary montage with common scale...")
    
    # Find global min/max across ALL wavelengths for common scale
    global_min = np.min(hyperspectral_cube)
    global_max = np.max(hyperspectral_cube)
    print(f"  Global intensity range: {global_min:.2f} to {global_max:.2f}")
    
    # Select subset for montage (max 20 slices to fit on page)
    max_montage_slices = min(20, len(target_wavelengths))
    montage_indices = np.linspace(0, len(target_wavelengths) - 1, max_montage_slices, dtype=int)
    montage_wavelengths = target_wavelengths[montage_indices]
    
    # Create montage
    n_cols = 5
    n_rows = int(np.ceil(max_montage_slices / n_cols))
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 3.6 * n_rows))
    axes = axes.flatten()
    
    # Create all images with common vmin/vmax
    for idx, (ax, target_wl) in enumerate(zip(axes[:max_montage_slices], montage_wavelengths)):
        wl_idx = np.argmin(np.abs(wave - target_wl))
        spatial_slice = hyperspectral_cube[:, :, wl_idx]
        
        # Use common vmin/vmax for all images
        im = ax.imshow(spatial_slice, cmap='viridis', interpolation='nearest', 
                      vmin=global_min, vmax=global_max)
        ax.set_title(f'{target_wl:.0f} nm', fontsize=10)
        ax.axis('off')
    
    # Hide unused subplots 
    for idx in range(max_montage_slices, len(axes)):
        axes[idx].axis('off')
    
    # Add single shared colorbar on the right
    fig.subplots_adjust(right=0.92)
    cbar_ax = fig.add_axes([0.94, 0.15, 0.02, 0.7])  # [left, bottom, width, height]
    cbar = fig.colorbar(im, cax=cbar_ax, label='Amplitude')
    
    plt.suptitle(f'Spectral Slices Montage (every {SLICE_INTERVAL_NM} nm) - Common Scale', 
                fontsize=16, y=0.98)
    
    montage_file = os.path.join(SAVE_DIRECTORY, "spectral_slices_montage.png")
    plt.savefig(montage_file, dpi=150, bbox_inches='tight')
    print(f"✓ Spectral slice montage saved to: {montage_file}")
    plt.show()
    
    # Save summary
    summary_file = os.path.join(SAVE_DIRECTORY, "scan_summary.txt")
    with open(summary_file, 'w') as f:
        f.write(f"Hyperspectral Cube Summary (Binned)\n")
        f.write(f"{'=' * 60}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Wavelength range: {start_wave} - {end_wave} nm\n")
        f.write(f"Resolution: {resolution} nm\n")
        f.write(f"Spectral points: {spectral_points}\n")
        f.write(f"Total frames captured: {len(data_acquired)}\n")
        f.write(f"Original image dimensions: {height} × {width}\n")
        f.write(f"Bin size: {BIN_HEIGHT} × {BIN_WIDTH} pixels\n")
        f.write(f"Binned dimensions: {BINNED_ROWS} × {BINNED_COLS}\n")
        f.write(f"Total bins processed: {BINNED_ROWS * BINNED_COLS}\n")
        f.write(f"Hyperspectral cube shape: {hyperspectral_cube.shape}\n")
        f.write(f"Position range: {start_position:.4f} - {end_position:.4f} mm\n")
        f.write(f"Step size: {step:.6f} mm\n")
        f.write(f"Processing time: {total_time:.1f} seconds ({total_time/60:.2f} minutes)\n")
        f.write(f"\nSpectral slices:\n")
        f.write(f"  - Interval: {SLICE_INTERVAL_NM} nm\n")
        f.write(f"  - Total slices: {saved_slices}\n")
        f.write(f"  - Wavelengths: {target_wavelengths[0]:.0f} to {target_wavelengths[-1]:.0f} nm\n")
        f.write(f"  - Global intensity range: {global_min:.2f} to {global_max:.2f}\n")
        f.write(f"\nData files:\n")
        f.write(f"  - hyperspectral_cube.npy: Main data cube ({BINNED_ROWS} × {BINNED_COLS} × {spectral_points})\n")
        f.write(f"  - binned_frames.npy: Binned frame stack ({len(data_acquired)} × {BINNED_ROWS} × {BINNED_COLS})\n")
        f.write(f"  - wavelength_axis.npy: Wavelength coordinates\n")
        f.write(f"  - frequency_axis.npy: Frequency coordinates\n")
        f.write(f"  - position_axis.npy: Position coordinates\n")
        f.write(f"  - spectral_slices/: Directory containing {saved_slices} spectral slice images\n")
    print(f"\n✓ Scan summary saved to: {summary_file}")

except KeyboardInterrupt:
    print('\n⚠ Measurement interrupted by user.')
finally:
    # Ensure hardware is always shut down/closed
    try:
        Mov.close_system()
        print("✓ Motor system closed")
    except Exception as e:
        # Motor might already be closed
        pass

file_name = input("\nPress Enter to exit...")
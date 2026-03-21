from Piezoconcept_C3200 import Piezoconcept
import time
import numpy as np
import matplotlib.pyplot as plt
from andor_control import AndorSystem
import sys

date = "20250615"
start = 100
end = 105
step = 0.05
resolution = int(((end- start)/step) + 1)
print(resolution)
filename = f"interf_piezo_{start}_{end}_step_{step*1000:.0f}nm_{date}_HWP100"
temp_setpoint = -75
exposure = 0.5
grating = 1
filter_slot = 5
center_wavelength = 810E-9
acquisition_mode = "single"
accum_time = 0.5
num_of_accum = 10
plot_wavelength_index = 808E-9  # Index of wavelength to plot (change as needed)

NUM_AVG = 5  # number of spectra to average at each position

scan_matrix = np.zeros((resolution + 1, 1024))
step = (end - start) / (resolution - 1)
center = start + ((end - start) / 2)

# Init
stage = Piezoconcept("COM5")
stage.recenter(center)
input("Press Enter to start scan...")

# Move to start position
stage.move_xyz(x_val=start, z_val=center)
time.sleep(0.1)

andor = AndorSystem(temp_setpoint=temp_setpoint, exposure=exposure, grating=grating, 
                    filter_slot=filter_slot, center_wavelength=center_wavelength, 
                    acquisition_mode=acquisition_mode, num_of_accum=num_of_accum, 
                    accum_time=accum_time)

try:
    scan_matrix[0] = andor.setup_spectrograph()
    andor.wait_for_stabilization()

    file_counter = 1
    run = 1
    
    while run == 1:
        positions = []
        
        # Scan along x-axis
        for i, x_position in enumerate(np.linspace(start, end, resolution)):
            stage.move_xyz(x_val=float(f"{x_position:.2f}"), z_val=center)
            andor.wait_for_stabilization()
            print(f"Position: {x_position:.2f}  —  taking {NUM_AVG} acquisitions...")
            
            # acquire and average NUM_AVG spectra
            acc = np.zeros_like(scan_matrix[0], dtype=float)
            for a in range(NUM_AVG):
                spectrum = andor.acquire_spectrum()
                if andor.check_overexposure(spectrum) == "over":
                    print("Camera overexposed, reduce LASER intensity")
                    andor.shutdown()
                    stage.close()
                    sys.exit()
                acc += spectrum
                time.sleep(0.01)  # short pause between accumulations
            avg_spectrum = acc / NUM_AVG

            scan_matrix[i + 1] = avg_spectrum
            positions.append(x_position)

        # Save data
        scan_matrix_transposed = scan_matrix.T
        np.savetxt(f"{filename}{file_counter}.txt", scan_matrix_transposed)
        # np.save(f"{filename}{file_counter}.npy", scan_matrix)  # Save as numpy binary file

        # Plotting
        wavelengths = scan_matrix[0]
        
        # Find index of wavelength closest to plot_wavelength_index
        wavelength_index = np.argmin(np.abs(wavelengths - plot_wavelength_index))
        actual_wavelength = wavelengths[wavelength_index]
        
        intensities = scan_matrix[1:, wavelength_index]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Plot intensity vs position at selected wavelength
        ax1.plot(positions, intensities, 'o-')
        ax1.set_xlabel('Position (µm)')
        ax1.set_ylabel('Intensity (counts)')
        ax1.set_title(f'Intensity vs Position at {actual_wavelength*1e9:.2f} nm')
        ax1.grid(True)
        
        # Plot all spectra as 2D colormap
        extent = [wavelengths.min()*1e9, wavelengths.max()*1e9, positions[-1], positions[0]]
        im = ax2.imshow(scan_matrix[1:], aspect='auto', cmap='coolwarm', extent=extent)
        ax2.set_xlabel('Wavelength (nm)')
        ax2.set_ylabel('Position (µm)')
        ax2.set_title('Spectra vs Position')
        fig.colorbar(im, ax=ax2, label='Intensity')
        
        plt.tight_layout()
        plt.show()

        stage.recenter(center)
        run = int(input("\nenter 1 for repeat\nenter 0 for exit: "))
        file_counter += 1

    # Shutdown
    stage.close()
    andor.shutdown()

except KeyboardInterrupt:
    print("Scan Interrupted")
    stage.close()
    andor.shutdown()
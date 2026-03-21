

from Piezoconcept_C3200 import Piezoconcept
import time
import numpy as np
import matplotlib.pyplot as plt
from andor_control import AndorSystem
import sys
# # Load config
# with open("F:\\AMRITA\\Andor spectrometer\\Codes\\refactored\\config.yaml", "r") as f:
#     config = yaml.safe_load(f)

resolution = 41
start = 90
end = 110
filename = "filename"
temp_setpoint = -80
exposure = 0.5
grating = 1
filter_slot = 5
center_wavelength = 600E-9
acquisition_mode = "single"
accum_time = 0.5
num_of_accum = 10

scan_matrix = np.zeros(((resolution**2) + 1, 1024))
step = (end - start) / (resolution - 1)
center = start + ((end - start) / 2)

# Init
# Empty initializer cycles through all ports to find the first port that responds like a MTD69x
# Specifying the port name lead to a faster connection
andor = AndorSystem(temp_setpoint=temp_setpoint, exposure=exposure, grating=grating, filter_slot=filter_slot,center_wavelength=center_wavelength, acquisition_mode=acquisition_mode, num_of_accum=num_of_accum, accum_time=accum_time)
stage = Piezoconcept("COM5")
stage.recenter(center)
input("Press Enter to start scan...")


stage.move_xyz(x_val=float(f"{center:.2f}"),y_val=float(f"{start:.2f}"), z_val=float(f"{start:.2f}"), unit = "u")
# time.sleep(0.1)



try:

    scan_matrix[0] = andor.setup_spectrograph()
    andor.wait_for_stabilization()

    def on_click(event):
        if event.inaxes:
            x = int(event.xdata + 0.5)
            y = int(event.ydata + 0.5)
            index=(y*resolution)+(x)+1
            ax2.cla()
            ax2.plot(scan_matrix[0], scan_matrix[index])
            plt.draw()

    file_counter = 1
    run = 1
    while(run == 1):
        a = 1
        z_position = start
        while z_position <= end:
            y_positions = np.arange(start, end + (step/2), step) 
            for y in y_positions:
                stage.move_xyz(x_val=float(f"{center:.2f}"), y_val=float(f"{y:.2f}"), z_val=float(f"{z_position:.2f}"), unit = "u")
                andor.wait_for_stabilization()
                # time.sleep(0.3)
                print(y, z_position)
                spectrum = andor.acquire_spectrum()
                if(andor.check_overexposure(spectrum) == "over"):
                    print("Camera overexposed, reduce LASER intensity")
                    andor.shutdown()
                    stage.close()
                    sys.exit()
                scan_matrix[a] = spectrum
                a += 1

            z_position += step

        scan_matrix = scan_matrix.T
        np.savetxt(f"{filename}{file_counter}.txt", scan_matrix)

        # Plotting

        max_values = scan_matrix.max(axis=0)[1:]
        matrix = max_values.reshape(resolution, resolution)

        scan_matrix = scan_matrix.T

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        map = ax1.imshow(matrix, cmap='coolwarm')
        fig.colorbar(map, ax=ax1, label='Peak Intensity')
        ax1.set_title("Confocal Map")
        ax2.set_title("Click on a pixel to display its PL")
        fig.canvas.mpl_connect('button_press_event', on_click)
        plt.show()

        X, Y = np.meshgrid(np.arange(resolution), np.arange(resolution))
        fig = plt.figure()
        ax = plt.axes(projection='3d')
        ax.plot_surface(X, Y, matrix, cmap='cool', edgecolor='green')
        ax.set_title('Surface plot')
        plt.show()
        stage.recenter(center)
        run = int(input("\nenter 1 for repeat\nenter 0 for exit"))
        file_counter+=1

    # Shutdown
    stage.close()
    andor.shutdown()

except KeyboardInterrupt:
    print("Scan Interrupted")
    stage.close()
    andor.shutdown()
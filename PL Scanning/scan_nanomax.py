import os
import time
import numpy as np
import matplotlib.pyplot as plt
import yaml
from nanomax_stage import NanoMaxStage
from andor_control import AndorSystem

# Load config
with open("F:\\AMRITA\\Andor spectrometer\\Codes\\refactored\\config.yaml", "r") as f:
    config = yaml.safe_load(f)

resolution = config["resolution"]
start = config["start"]
end = config["end"]
filename = config["filename"]
temp_setpoint = config["temp_setpoint"]
exposure = config["exposure"]
grating = config["grating"]
filter_slot = config["filter_slot"]
center_wavelength = config["center_wavelength"]
acquisition_mode = config["acquisition_mode"]
accum_time = config["accumulation_time"]
num_of_accum = ["number_of_accumulations"]

scan_matrix = np.zeros(((resolution**2) + 1, 1024))
step = (end - start) / (resolution - 1)
center = (end - start) / 2

# Init
# Empty initializer cycles through all ports to find the first port that responds like a MTD69x
# Specifying the port name lead to a faster connection
stage = NanoMaxStage("COM4")
stage.center_stage(start, end)
input("Press Enter to start scan...")

for i in np.arange(center, start-0.5, -2.5):
    stage.move_to(x=i,y=i)
    time.sleep(0.3)

andor = AndorSystem(temp_setpoint=temp_setpoint, exposure=exposure, grating=grating, filter_slot=filter_slot,center_wavelength=center_wavelength, acquisition_mode=acquisition_mode, num_of_accum=num_of_accum, accum_time=accum_time)

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
        y_position = start
        while y_position <= end:
            x_positions = np.arange(start, end + (step/2), step)
            for x in x_positions:
                stage.move_to(x=float(f"{x:.2f}"), y=float(f"{y_position:.2f}"))
                andor.wait_for_stabilization()
                time.sleep(0.3)

                spectrum = andor.acquire_spectrum()
                if(andor.check_overexposure(spectrum) == "over"):
                    print("Camera overexposed, reduce LASER intensity")
                    andor.shutdown()
                    stage.close()
                    exit()
                scan_matrix[a] = spectrum
                a += 1

            x_positions = np.arange(end, start - (step/2), -step)
            for x in x_positions:
                stage.move_to(x=float(f"{x:.2f}"), y=float(f"{y_position:.2f}"))
                time.sleep(0.3)
            y_position += step

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
        stage.center_stage(start, end)
        run = int(input("\nenter 1 for repeat\nenter 0 for exit"))
        file_counter+=1

    # Shutdown
    stage.shutdown()
    andor.shutdown()

except KeyboardInterrupt:
    print("Scan Interrupted")
    stage.shutdown()
    andor.shutdown()
# PL Mapping Procedure

## Files

1) scan.py: This script is the main scanning script and the parameters in the config.yaml file are used to perform the scan.

2) config.yaml: Contains all the configuration variables like resolution, exposure, filename, grating, filter, etc. (ensure to SAVE the file before running scan.py)

3) andor_control.py: Contains the methods required to control the Andor spectrometer

4) nanomax_stage.py: Contains the methods required to control the MDT694B Controller for the NanoMAX stage.

## SOP

Step 1: After aligning all the elements on the optical table and preparing your sample, set all the variables as you require in config.yaml and save the file (Ensure to change the filename)

Step 2: Run the scan.py script

Step 3: Wait for the controller to reach the center of the stage(X=37.5V, Y=37.5V)

Step 4: Align the sample such that the LASER spot is at the center of the required scan area and focus the LASER on the plane of the sample.

Step 5: Press Enter in the terminal to start the cooling cycle of the spectrometer and start the scan. (ensure white light is turned off and Andor SOLIS software is not open).

Step 6: Wait for the temperature to stabilize and the scan will start automatically.

Step 7: Once the scan has finished, the confocal image and the 3D plot will be displayed.

Step 8: Once you close the image windows the program will ask you to enter "1" in the terminal to repeat the scan or enter "0" to exit the program.

Step 9: If you wish to perform another scan you can set the position of your sample in the new location and then enter "1" in the terminal and press enter.

Step 10: If you wish to exit the program then Enter "0" in the terminal.

Step 11: Before the program closes it will wait for the spectrometer to warm up upto -20 C. to protect the CCD, and then will exit.

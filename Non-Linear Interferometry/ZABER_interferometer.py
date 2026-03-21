"""Single-axis linear scan over 4 cm with 1 µm step size.

- Connects to one Zaber stage (device/address configurable).
- Performs an absolute raster along X (single axis) starting from the current
  position and moving +40.0 mm in steps of 0.001 mm (1 µm).
- Stops cleanly on KeyboardInterrupt and sends a stop command.
- Adjust SERIAL_PORT, DEVICE, AXIS_NUM if needed.
"""
from typing import Tuple
import logging
import time
from andor_control import AndorSystem
import numpy as np
import matplotlib.pyplot as plt
import sys

from zaber_motion import Units, MotionLibException
from zaber_motion.ascii import Connection, Axis

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# Connection / axis mapping (adjust to your hardware)
SERIAL_PORT = "COM9"
DEVICE = 2
AXIS_NUM = 1

# Units and scan parameters
UNITS = Units.LENGTH_MILLIMETRES
START = 60
RANGE_MM = 40           # 1 cm = 10 mm
STEP_MM = 0.01         # 1 micron = 0.001 mm
# INTER_MOVE_DELAY = 0.001  # small delay between commands (seconds)
# PROGRESS_INTERVAL = 500   # report progress every N steps

temp_setpoint = -80
exposure = 0.5
grating = 1
filter_slot = 5
center_wavelength = 810E-9
acquisition_mode = "single"
accum_time = 0.5
num_of_accum = 10
plot_wavelength_index = 807E-9  # Index of wavelength to plot (change as needed)

filename = f"Coarse_start_{START}_Ran_{RANGE_MM}mm_step_{STEP_MM*1000:.0f}um_{plot_wavelength_index*1e9:.0f}nm_Jan26"

scan_matrix = np.zeros((int(RANGE_MM / STEP_MM) + 2, 1024))

andor = AndorSystem(temp_setpoint=temp_setpoint, exposure=exposure, grating=grating, 
                    filter_slot=filter_slot, center_wavelength=center_wavelength, 
                    acquisition_mode=acquisition_mode, num_of_accum=num_of_accum, 
                    accum_time=accum_time)

def single_axis_scan(serial_port: str, device: int, axis_num: int) -> None:
    """Run a single-axis scan of RANGE_MM with STEP_MM step size."""

    home = input("homing required?")

    steps = int(round(RANGE_MM / STEP_MM))
    if steps <= 0:
        log.error("Invalid step configuration: steps=%d", steps)
        return

    log.info("Connecting to %s / device %d axis %d", serial_port, device, axis_num)
    with Connection.open_serial_port(serial_port) as conn:

        try:
            dev = conn.get_device(device)
            dev.identify()
            axis = dev.get_axis(axis_num)
        except MotionLibException:
            log.exception("Failed to identify device/axis")
            return
        
        if home=="1":
            log.info("Homing (blocking start).")
            axis.home(wait_until_idle=True)
            log.info("Device Homed")
        
        try:
            start_pos = START
        except Exception:
            log.warning("Could not read current position, assuming 0.0")
            start_pos = 0.0


        end_pos = start_pos + RANGE_MM
        log.info(
            "Starting single-axis scan from %.6f -> %.6f %s in %d steps (step=%.6f %s)",
            start_pos,
            end_pos,
            UNITS.name,
            steps,
            STEP_MM,
            UNITS.name,
        )

        try:
            scan_matrix[0] = andor.setup_spectrograph()
            andor.wait_for_stabilization()

            wavelengths = scan_matrix[0]
            wavelength_index = np.argmin(np.abs(wavelengths - plot_wavelength_index))
            actual_wavelength = wavelengths[wavelength_index]

            file_counter = 1
            run = 1

            axis.move_absolute(START, UNITS, wait_until_idle=True)

            while run == 1:
                positions = []

                # --- Live plotting setup ---
                plt.ion()
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
                line, = ax1.plot([], [], 'o-')
                ax1.set_xlabel('Position (µm)')
                ax1.set_ylabel('Intensity (counts)')
                ax1.set_title(f'Live: Intensity vs Position at {actual_wavelength*1e9:.2f} nm')
                ax1.grid(True)

                im_data = np.zeros((steps + 1, scan_matrix.shape[1]))
                im = ax2.imshow(im_data, aspect='auto', cmap='coolwarm',
                                extent=[wavelengths.min(), wavelengths.max(), 0, 1])
                ax2.set_xlabel('Wavelength (nm)')
                ax2.set_ylabel('Position (µm)')
                ax2.set_title('Live Spectra vs Position')
                cbar = fig.colorbar(im, ax=ax2, label='Intensity')
                plt.tight_layout()
                fig.canvas.draw()
                plt.pause(0.001)

                for i in range(steps + 1):
                    target = start_pos + i * STEP_MM
                    # Clamp final point to end_pos to avoid tiny rounding overshoot
                    if target > end_pos:
                        target = end_pos

                    try:
                        axis.move_absolute(target, UNITS, wait_until_idle=True)
                    except MotionLibException:
                        log.exception("Move command failed at step %d (target=%.6f)", i, target)
                        raise

                    # place for acquisition/measurement call
                    # e.g. capture_image() or read_sensor()
                    andor.wait_for_stabilization()
                    spectrum = andor.acquire_spectrum()
                    if andor.check_overexposure(spectrum) == "over":
                        print("Camera overexposed, reduce LASER intensity")
                        andor.shutdown()
                        axis.stop(wait_until_idle=False)
                        sys.exit()

                    scan_matrix[i + 1] = spectrum
                    positions.append(target)

                    intensity = scan_matrix[i+1, wavelength_index]
                    print(intensity)

                    log.info("Step %d/%d at position %.6f %s", i, steps, target, UNITS.name)

                    # --- Update live plots ---
                    # update line plot
                    pos_arr = np.array(positions)
                    intens_arr = scan_matrix[1:len(positions)+1, wavelength_index]
                    line.set_data(pos_arr, intens_arr)
                    ax1.relim()
                    ax1.autoscale_view()

                    # update image: use current collected rows
                    current_rows = scan_matrix[1:len(positions)+1]
                    im.set_data(current_rows)
                    # update extent y-limits to reflect current positions (top=first, bottom=last)
                    if len(positions) > 0:
                        im.set_extent([wavelengths.min(), wavelengths.max(), positions[-1], positions[0]])
                        ax2.set_ylim(positions[-1], positions[0])

                    fig.canvas.draw_idle()
                    plt.pause(0.01)

                # final save for this scan
                log.info("Scan complete. Final position: %.6f %s", axis.get_position(UNITS), UNITS.name)
                scan_matrix_transposed = scan_matrix.T
                np.savetxt(f"{filename}{file_counter}.txt", scan_matrix_transposed)
                plt.ioff()
                plt.show()

                run = int(input("\nenter 1 for repeat\nenter 0 for exit: "))
                file_counter += 1
                
            andor.shutdown()
        except KeyboardInterrupt:
            log.warning("Scan interrupted by user; stopping axis.")
            try:
                axis.stop(wait_until_idle=False)
                andor.shutdown()
            except Exception:
                log.debug("Error sending stop to axis", exc_info=True)


def main() -> None:
    single_axis_scan(SERIAL_PORT, DEVICE, AXIS_NUM)


if __name__ == "__main__":
    main()
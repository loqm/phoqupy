"""Simple raster-scan and goto utility for two Zaber stages.

- Uses device/address mapping for X and Y stages.
- Performs a serpentine raster scan by default.
- Provides goto_position(x, y) for direct moves.
- Stops cleanly on KeyboardInterrupt.
"""
import logging
import time
from typing import Tuple
import numpy as np
import os
import cv2
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessorSDK
from thorlabs_tsi_sdk.tl_mono_to_color_enums import COLOR_SPACE
from thorlabs_tsi_sdk.tl_color_enums import FORMAT

from zaber_motion import Units, MotionLibException
from zaber_motion.ascii import Connection, Axis

try:
    from windows_setup import configure_path
    configure_path()
except ImportError:
    configure_path = None
    
log = logging.getLogger(__name__)

# Connection / axis mapping (adjust to your hardware)
SERIAL_PORT = "COM5"
X_DEVICE = 1
X_AXIS_NUM = 1
Y_DEVICE = 2
Y_AXIS_NUM = 1

# Units used for absolute moves (assumes linear stages in millimetres)
STAGE_UNITS = Units.LENGTH_MILLIMETRES

# Safety / timing
INTER_MOVE_DELAY = 0.5  # seconds between issuing commands
POLL_INTERVAL = 0.05


def connect_axes(serial_port: str) -> Tuple[Axis, Axis]:
    """Open connection and return (x_axis, y_axis). Caller should ensure context."""
    conn = Connection.open_serial_port(serial_port)
    # return the connection object too by using context manager in caller; here we return axes and connection object
    connection = conn  # alias
    try:
        x_device = connection.get_device(X_DEVICE)
        x_device.identify()
        x_axis = x_device.get_axis(X_AXIS_NUM)
    except MotionLibException:
        connection.close()
        raise

    try:
        if Y_DEVICE != X_DEVICE:
            y_device = connection.get_device(Y_DEVICE)
            y_device.identify()
        else:
            y_device = x_device
        y_axis = y_device.get_axis(Y_AXIS_NUM)
    except MotionLibException:
        connection.close()
        raise

    return connection, x_axis, y_axis


def wait_for_axes_idle(x_axis: Axis, y_axis: Axis, poll: float = POLL_INTERVAL) -> None:
    """Block until both axes report idle."""
    while True:
        try:
            # print(x_axis.wait_until_idle(), y_axis.wait_until_idle())
            # if x_axis.wait_until_idle() and y_axis.wait_until_idle():
                # print(x_axis.wait_until_idle(), y_axis.wait_until_idle())
            return
        except MotionLibException:
            # If communication hiccup, sleep and retry
            log.debug("Error querying idle state; retrying.", exc_info=True)
        time.sleep(poll)


def goto_position(x: float, y: float, x_axis: Axis, y_axis: Axis, units: Units = STAGE_UNITS) -> None:
    """Move both axes to an absolute (x, y) position and wait until move completes.

    Moves are issued non-blocking for both axes, then the function waits until both axes are idle.
    """
    log.info("Goto absolute position X=%.6g, Y=%.6g %s", x, y, units.name)
    try:
        x_axis.move_absolute(x, units, wait_until_idle=True)
        # small delay between commands to avoid command overlap on bus
        # time.sleep(INTER_MOVE_DELAY)
        y_axis.move_absolute(y, units, wait_until_idle=True)
        # wait_for_axes_idle(x_axis, y_axis)
    except MotionLibException:
        log.error("Error during goto_position", exc_info=True)
        raise


def acquire_single_frame(position_index: int, camera, mono_to_color_processor) -> None:
    """Acquire a single frame from the camera and save it as JPG."""
    # with TLCameraSDK() as camera_sdk, MonoToColorProcessorSDK() as mono_to_color_sdk:
    #     available_cameras = camera_sdk.discover_available_cameras()
    #     if len(available_cameras) < 1:
    #         log.error("No cameras detected")
    #         return

    # with camera_sdk.open_camera(available_cameras[0]) as camera:
    # camera.exposure_time_us = 10000  # set exposure to 10 ms
    # camera.frames_per_trigger_zero_for_unlimited = 0
    # camera.image_poll_timeout_ms = 1000

    camera.arm(2)
    
    image_width = camera.image_width_pixels
    image_height = camera.image_height_pixels

    camera.issue_software_trigger()

    frame = camera.get_pending_frame_or_null()
    if frame is not None:
        log.info(f"Frame #{frame.frame_count} received at position {position_index}")
        
        # with mono_to_color_sdk.create_mono_to_color_processor(
        #     camera.camera_sensor_type,
        #     camera.color_filter_array_phase,
        #     camera.get_color_correction_matrix(),
        #     camera.get_default_white_balance_matrix(),
        #     camera.bit_depth
        # ) as mono_to_color_processor:
            
        mono_to_color_processor.color_space = COLOR_SPACE.SRGB
        mono_to_color_processor.output_format = FORMAT.RGB_PIXEL
        
        color_image = mono_to_color_processor.transform_to_24(
            frame.image_buffer,
            image_width,
            image_height
        )
        
        color_image_reshape = color_image.reshape(image_height, image_width, 3)
        
        # Create Images directory if it doesn't exist
        os.makedirs('Images3', exist_ok=True)
        
        # Save as JPG with position index in filename
        save_path = f'Images3/img_{position_index:04d}.jpg'
        cv2.imwrite(save_path, cv2.cvtColor(color_image_reshape, cv2.COLOR_RGB2BGR))
        log.info(f"Image saved as: {os.path.abspath(save_path)}")
            
    else:
        log.error(f"Failed to acquire image at position {position_index}")
        
    camera.disarm()


def raster_scan(
    x_start: float,
    x_steps: int,
    x_step_size: float,
    y_start: float,
    y_steps: int,
    y_step_size: float,
    x_axis: Axis,
    y_axis: Axis,
    units: Units = STAGE_UNITS,
    serpentine: bool = True,
) -> None:
    """Perform a raster scan with image acquisition at each position."""
    log.info("Starting raster scan: x_steps=%d, y_steps=%d, x_step=%.6g, y_step=%.6g %s",
             x_steps, y_steps, x_step_size, y_step_size, units.name)

    # Precompute X positions for a single row (left-to-right)
    x_positions = [x_start + i * x_step_size for i in range(x_steps)]
    position_index = 0

    camera_sdk = TLCameraSDK()
    mono_to_color_sdk = MonoToColorProcessorSDK()
    available_cameras = camera_sdk.discover_available_cameras()
    if len(available_cameras) < 1:
        log.error("No cameras detected")
        return
    
    camera = camera_sdk.open_camera(available_cameras[0])
    camera.exposure_time_us = 10000  # set exposure to 10 ms
    camera.frames_per_trigger_zero_for_unlimited = 0
    camera.image_poll_timeout_ms = 1000

    mono_to_color_processor = mono_to_color_sdk.create_mono_to_color_processor(
        camera.camera_sensor_type,
        camera.color_filter_array_phase,
        camera.get_color_correction_matrix(),
        camera.get_default_white_balance_matrix(),
        camera.bit_depth
    )

    try:
        for row in range(y_steps):
            y_pos = y_start + row * y_step_size
            # choose X order for this row
            if serpentine and (row % 2 == 1):
                iter_x = reversed(x_positions)
            else:
                iter_x = x_positions

            for x_pos in iter_x:
                log.info("Row %d / %d -> moving to (%.6g, %.6g)", row + 1, y_steps, x_pos, y_pos)
                goto_position(x_pos, y_pos, x_axis, y_axis, units)
                
                # Add delay for stage settling
                # time.sleep(INTER_MOVE_DELAY)
                
                # Acquire image at current position
                acquire_single_frame(position_index, camera, mono_to_color_processor)
                position_index += 1

    except KeyboardInterrupt:
        log.warning("Scan interrupted by user; stopping axes.")
        try:
            x_axis.stop(wait_until_idle=False)
            y_axis.stop(wait_until_idle=False)
        except Exception:
            log.debug("Error sending stop to axes", exc_info=True)
        raise


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    # Example scan parameters (adjust to your experiment)
    # x_start = x_axis.get_position(STAGE_UNITS)
    x_steps = 3
    x_step_size = 0.3  # mm
    # y_start = y_axis.get_position(STAGE_UNITS)
    y_steps = 3
    y_step_size = 0.3 # mm

    # Connect and run scan
    # Use context manager so connection closes cleanly
    with Connection.open_serial_port(SERIAL_PORT) as conn:
        try:
            # get axes
            x_device = conn.get_device(X_DEVICE)
            x_device.identify()
            x_axis = x_device.get_axis(X_AXIS_NUM)
            x_start = x_axis.get_position(STAGE_UNITS)

            if Y_DEVICE != X_DEVICE:
                y_device = conn.get_device(Y_DEVICE)
                y_device.identify()
            else:
                y_device = x_device
            y_axis = y_device.get_axis(Y_AXIS_NUM)
            y_start = y_axis.get_position(STAGE_UNITS)

            # Optional: print current positions
            try:
                current_x = x_axis.get_position(STAGE_UNITS)
                current_y = y_axis.get_position(STAGE_UNITS)
                log.info("Current position X=%.6g, Y=%.6g %s", current_x, current_y, STAGE_UNITS.name)
            except Exception:
                log.debug("Could not read current positions", exc_info=True)

            # Run raster scan
            raster_scan(
                x_start=x_start,
                x_steps=x_steps,
                x_step_size=x_step_size,
                y_start=y_start,
                y_steps=y_steps,
                y_step_size=y_step_size,
                x_axis=x_axis,
                y_axis=y_axis,
                units=STAGE_UNITS,
                serpentine=False,
            )

            log.info("Raster scan complete.")

            try:
                x_axis.stop(wait_until_idle=False)
                y_axis.stop(wait_until_idle=False)
            except Exception:
                log.debug("Error sending stop to axes", exc_info=True)
                
        except MotionLibException:
            log.error("Motion library error during setup or scan", exc_info=True)


if __name__ == "__main__":
    main()
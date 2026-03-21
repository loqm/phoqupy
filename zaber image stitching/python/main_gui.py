"""
main_gui.py
Unified GUI for:
 - Live camera feed (Tkinter)
 - Joystick stage control
 - Image stitching and scanning trigger
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
import os

# Local imports
from tkinter_camera_live_view import LiveViewCanvas, ImageAcquisitionThread
from image_stitching import main as run_image_stitching
import stitch
from joystick import scale_deflection
from windows_setup import configure_path

# Hardware imports
from zaber_motion.ascii import Connection
from zaber_motion import Units, MotionLibException
from inputs import get_gamepad
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

# Ensure DLLs are visible
configure_path()

# --- Hardware Config ---
SERIAL_PORT = "COM5"
X_AXIS = (1, 1)
Y_AXIS = (2, 1)
CAPTURE_BUTTON = "BTN_SOUTH"   # joystick button to trigger stitching


def joystick_controller(x_axis, y_axis, stop_event, capture_event):
    """
    Background joystick controller thread.
    Moves stage with analog stick and triggers scan/stitch when button pressed.
    """
    from joystick import MAX_DEFLECTION, SPEED_GAIN, RESPONSE_EXPONENT, DEAD_ZONE

    input_states = {
        "BTN_SELECT": 0,
        "ABS_X": 0,
        "ABS_Y": 0,
        "BTN_EAST": 0,
        "BTN_WEST": 0,
        "BTN_SELECT": 0,
    }

    max_speed_x = x_axis.settings.get("maxspeed")
    max_speed_y = y_axis.settings.get("maxspeed")

    print("Joystick controller running. Use left stick to move stage.")
    print(f"Press {CAPTURE_BUTTON} to trigger image stitching routine.")

    while not stop_event.is_set():
        try:
            events = get_gamepad()  # blocking, runs in worker thread so UI stays responsive
        except Exception:
            print("get_gamepad error, retrying", exc_info=True)
            time.sleep(0.05)
            continue

        for event in events:
            if event.ev_type in ("Absolute", "Key"):
                input_states[event.code] = event.state
            else:
                continue

            # Exit request from joystick
            if input_states["BTN_SELECT"] == 1:
                print("Start button pressed: requesting stop.")
                stop_event.set()
                break
            
            # Trigger scan/stitch on button press
            if event.code == CAPTURE_BUTTON and event.state == 1:
                print("Joystick trigger pressed — initiating image stitching routine.")
                capture_event.set()
                
            try:
                # Homing
                if input_states["BTN_WEST"] == 1:
                    print("Homing (blocking start).")
                    x_axis.home(wait_until_idle=True)
                    y_axis.home(wait_until_idle=True)
                    # do not block waiting here so other inputs can interrupt homing
                    print("Device homed.")
                # Stop
                elif input_states["BTN_EAST"] == 1:
                    print("Stopping")
                    x_axis.stop(wait_until_idle=False)
                    y_axis.stop(wait_until_idle=False)
                else:
                    # compute scaled deflection in [-1,1]
                    x_raw = scale_deflection(input_states["ABS_X"])
                    y_raw = scale_deflection(input_states["ABS_Y"])

                    # apply gain and convert to device velocity, then clamp to device max
                    x_speed = x_raw * max_speed_x * SPEED_GAIN
                    y_speed = y_raw * max_speed_y * SPEED_GAIN

                    def clamp(v, limit):
                        return max(min(v, limit), -limit)

                    x_speed = clamp(x_speed, max_speed_x)
                    y_speed = clamp(y_speed, max_speed_y)

                    x_axis.move_velocity(x_speed)
                    y_axis.move_velocity(y_speed)

            except MotionLibException:
                print("Error sending move command")

        # Update shared position for plotting (best-effort; ignore read errors)
        # try:
        #     cur_x = x_axis.get_position(Units.LENGTH_MILLIMETRES)
        #     cur_y = y_axis.get_position(Units.LENGTH_MILLIMETRES)
        #     with lock:
        #         pos["x"] = cur_x
        #         pos["y"] = cur_y
        # except Exception:
        #     log.debug("Could not read position for plotting", exc_info=True)

        # time.sleep(0.05)

    print("Joystick thread terminated.")


def background_stitch_worker(capture_event, stop_event):
    """
    Waits for capture_event to trigger image stitching.
    Runs image_stitching.main() and stitch.mist() sequentially.
    """
    while not stop_event.is_set():
        capture_event.wait()
        if stop_event.is_set():
            break
        capture_event.clear()

        try:
            messagebox.showinfo("Capture", "Starting raster scan and image capture...")
            run_image_stitching()
            messagebox.showinfo("Capture", "Image capture complete. Starting stitching...")
            stitch.mist()  # from stitch.py
            messagebox.showinfo("Stitching", "Image stitching complete!")
        except Exception as e:
            messagebox.showerror("Error", f"Error during stitching process:\n{e}")


def start_main_gui():
    """
    Main entrypoint — launches GUI, camera thread, joystick, and stitching monitor.
    """
    # --- Camera setup ---
    with TLCameraSDK() as sdk:
        cameras = sdk.discover_available_cameras()
        if not cameras:
            print("No cameras found.")
            return
        camera = sdk.open_camera(cameras[0])
        camera.frames_per_trigger_zero_for_unlimited = 0
        camera.arm(2)
        camera.issue_software_trigger()

        # --- Tkinter GUI setup ---
        root = tk.Tk()
        root.title("Unified Zaber Stage + Camera Control")
        root.geometry("800x600")

        # Camera live feed canvas
        image_thread = ImageAcquisitionThread(camera)
        live_view = LiveViewCanvas(root, image_thread.get_output_queue())
        image_thread.start()

        # --- Stage + joystick setup ---
        connection = Connection.open_serial_port(SERIAL_PORT)
        try:
            x_device = connection.get_device(X_AXIS[0])
            x_device.identify()
            x_axis = x_device.get_axis(X_AXIS[1])
        except MotionLibException:
            print("Failed to identify the X axis at address /%d %d", X_AXIS[0], X_AXIS[1])
            return

        try:
            if Y_AXIS[0] != X_AXIS[0]:
                y_device = connection.get_device(Y_AXIS[0])
                y_device.identify()
            else:
                y_device = x_device
            y_axis = y_device.get_axis(Y_AXIS[1])
        except MotionLibException:
            print("Failed to identify the Y axis at address /%d %d", Y_AXIS[0], Y_AXIS[1])
            return

        # Shared events
        stop_event = threading.Event()
        capture_event = threading.Event()

        # --- Background threads ---
        threading.Thread(
            target=joystick_controller,
            args=(x_axis, y_axis, stop_event, capture_event),
            daemon=True
        ).start()

        threading.Thread(
            target=background_stitch_worker,
            args=(capture_event, stop_event),
            daemon=True
        ).start()

        # --- GUI controls ---
        def on_close():
            stop_event.set()
            image_thread.stop()
            image_thread.join()
            try:
                camera.disarm()
                connection.close()
            except Exception:
                pass
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)

        tk.Label(root, text="Camera Live View + Joystick Control", font=("Arial", 14)).pack(pady=10)
        tk.Label(root, text=f"Press '{CAPTURE_BUTTON}' on joystick to start stitching").pack()

        root.mainloop()


if __name__ == "__main__":
    start_main_gui()

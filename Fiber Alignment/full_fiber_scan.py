import time
import numpy as np
import matplotlib.pyplot as plt
from mdt69x import Controller
from TLPMX import TLPMX, TLPM_DEFAULT_CHANNEL
from ctypes import byref, create_string_buffer, c_char_p, c_double, c_int16, c_bool
import HBT.andor as andor

def get_counts():
    """Return counts for the configured target wavelength.
    Prefer Andor spectrograph if available; otherwise fall back to power meter.
    """
    # If Andor is available and initialized, use it
    try:
        if andor_sys is not None and andor_sys.cam is not None:
            spec = andor_sys.acquire_spectrum()  # list/array of intensity values
            if spec is None:
                raise RuntimeError("Andor returned no spectrum")
            spec = np.array(spec)

            # If we have wavelength calibration, use it; otherwise approximate
            if wavelengths is not None:
                idx = int(np.argmin(np.abs(wavelengths - target_wavelength)))
            else:
                # fallback: assume center wavelength maps to center pixel
                idx = int(np.argmin(np.abs(np.arange(len(spec)) - len(spec)//2)))
            return float(spec[idx])
    except Exception as e:
        print(f"Andor read failed, falling back to powermeter: {e}")

    # Fallback: measure power from PM100D (Watts)
    try:
        power = c_double()
        pm.measPower(byref(power), TLPM_DEFAULT_CHANNEL)
        return power.value
    except Exception as e:
        print(f"Powermeter read failed: {e}")
        return 0.0

def safe_voltage(v, vmin=0, vmax=75):
    return max(vmin, min(vmax, v))

def show_heatmap(controller=None, x_voltage=None, move_to_max=False):
    ys, zs, cs = zip(*heatmap_data)

    y_unique = np.unique(ys)
    z_unique = np.unique(zs)
    y_grid = np.linspace(min(ys), max(ys), 50)
    z_grid = np.linspace(min(zs), max(zs), 50)

    Y, Z = np.meshgrid(y_grid, z_grid)
    C = np.zeros_like(Y)

    # Interpolate using nearest neighbor
    for i in range(Y.shape[0]):
        for j in range(Y.shape[1]):
            distances = [(y - Y[i, j])**2 + (z - Z[i, j])**2 for y, z in zip(ys, zs)]
            idx = np.argmin(distances)
            C[i, j] = cs[idx]

    plt.figure()
    plt.imshow(C, extent=(min(ys), max(ys), min(zs), max(zs)), origin='lower', aspect='auto', cmap='viridis')
    plt.colorbar(label='Power (W)')
    plt.xlabel('Y Voltage (V)')
    plt.ylabel('Z Voltage (V)')
    plt.title('Power Heatmap (Y-Z Plane)')
    plt.show()

    # find maximum in interpolated heatmap
    # handle NaNs just in case
    if np.all(np.isnan(C)):
        return None
    max_idx = np.unravel_index(np.nanargmax(C), C.shape)
    y_max = float(Y[max_idx])
    z_max = float(Z[max_idx])
    max_val = float(C[max_idx])

    print(f"Heatmap maximum (interpolated): Y={y_max:.2f} V, Z={z_max:.2f} V -> Power={max_val:.4e} W")

    # move stage to the interpolated maximum if requested and controller provided
    if move_to_max and (controller is not None):
        try:
            if x_voltage is None:
                # try to read current X from controller if available
                try:
                    x_voltage = controller.get_xyz_voltage()[0]
                except Exception:
                    x_voltage = None
            if x_voltage is None:
                print("X voltage not provided and could not be read from controller. Skipping move.")
            else:
                print(f"Moving stage to X={x_voltage:.2f}, Y={y_max:.2f}, Z={z_max:.2f}")
                controller.set_xyz_voltage(safe_voltage(x_voltage), safe_voltage(y_max), safe_voltage(z_max))
        except Exception as e:
            print(f"Failed to move stage to heatmap maximum: {e}")

    return (y_max, z_max, max_val)

# --- Main Execution ---
controller = Controller()
x0, y0, z0 = controller.get_xyz_voltage()
fixed_x = safe_voltage(x0)

# --- Initialize PM100D ---
pm = TLPMX()
deviceCount = c_int16()
pm.findRsrc(byref(deviceCount))
resourceName = create_string_buffer(1024)
pm.getRsrcName(0, resourceName)
pm.open(resourceName, c_bool(True), c_bool(True))

msg = create_string_buffer(1024)
pm.getCalibrationMsg(msg, TLPM_DEFAULT_CHANNEL)
print("Connected to PM100D. Calibration:", c_char_p(msg.raw).value.decode())

pm.setWavelength(c_double(635), TLPM_DEFAULT_CHANNEL)
pm.setPowerAutoRange(c_int16(1), TLPM_DEFAULT_CHANNEL)
pm.setPowerUnit(c_int16(0), TLPM_DEFAULT_CHANNEL)

print(f"Starting scan at fixed X={fixed_x:.2f} V")

# --- Andor initialization (optional) ---
# target wavelength (nm) to extract counts from the spectrum
target_wavelength = 635.0

andor_sys = None
wavelengths = None
try:
    andor_sys = andor.AndorSystem()  # uses config.yaml if present
    try:
        # setup_spectrograph() should return wavelength calibration (array of nm per pixel)
        wavelengths = andor_sys.setup_spectrograph()
        if wavelengths is not None:
            wavelengths = np.array(wavelengths)
    except Exception as e:
        print(f"Andor spectrograph setup did not return wavelengths: {e}")
except Exception as e:
    print(f"Andor initialization failed or not present: {e}")

# --- Raster Scan Settings ---
y_start, y_end, y_step = 0, 40, 2  # Adjust as needed
z_start, z_end, z_step = 0, 40, 2

heatmap_data = []

ys = np.arange(y_start, y_end + y_step, y_step)
zs = np.arange(z_start, z_end + z_step, z_step)

total_steps = len(ys) * len(zs)
step_count = 0

plt.ion()
fig = plt.figure()
line_data = []

controller.set_xyz_voltage(fixed_x, 20, 20)
input("Press Enter to start the scan...")
# --- Raster Scan Y-Z ---
for yi, y in enumerate(ys):
    z_loop = zs 
    for z in z_loop:
        y = safe_voltage(y)
        z = safe_voltage(z)
        controller.set_xyz_voltage(fixed_x, y, z)
        time.sleep(0.5)  # Let stage and power meter settle
        counts = get_counts()
        

        heatmap_data.append((y, z, counts))
        line_data.append((step_count, counts))
        print(f"Step {step_count + 1}/{total_steps}: Y={y:.2f}, Z={z:.2f} -> {counts:.4e} W")

        # live update
        steps, values = zip(*line_data)
        plt.cla()
        plt.plot(steps, values, marker='o', color='blue')
        plt.xlabel("Step")
        plt.ylabel("Power (W)")
        plt.title("Live Power vs Step")
        plt.pause(0.01)

        step_count += 1
    z_loop = zs[::-1]
    for z in z_loop:
        y = safe_voltage(y)
        z = safe_voltage(z)
        controller.set_xyz_voltage(fixed_x, y, z)
        time.sleep(0.1)


# --- Finish Up ---

# --- Move to position with maximum counts ---
if heatmap_data:
    # Prefer the interpolated maximum and command the stage there
    result = show_heatmap(controller=controller, x_voltage=fixed_x, move_to_max=True)
    if result is None:
        # fallback to sampled max if interpolation failed
        max_idx = np.argmax([c for (_, _, c) in heatmap_data])
        best_y, best_z, best_counts = heatmap_data[max_idx]
        print(f"\nMoving to sampled max counts position: Y={best_y:.2f} V, Z={best_z:.2f} V (Power={best_counts:.4e} W)")
        controller.set_xyz_voltage(fixed_x, y0, z0)
        for i in range(y0, int(best_y),10):
            controller.set_xyz_voltage(fixed_x, i, z0)
        for i in range(z0, int(best_z),10):
            controller.set_xyz_voltage(fixed_x, best_y, i)
        controller.set_xyz_voltage(fixed_x, best_y, best_z)
else:
    print("No scan data found, returning to initial position.")
    controller.set_xyz_voltage(fixed_x, y0, z0)
controller.close()
pm.close()

plt.ioff()
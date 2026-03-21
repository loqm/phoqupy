# Scientific Instrument Control API

Concise API reference for Andor cameras, MultiHarp timing devices, NanoMAX stages, and data analysis.

## General Workflow

1. To align the sample, run camera.py to grab and show frames from the Thorlabs camera.
2. To take individual time-tagged measurements (for g2, lifetime calculations):
  a. Use the MultiHarp software to collect a .ptu file
  b. Use the MultiHarpWrapper() implementation to gather and store data, using json configs to set measurement parameters
3. To scan a sample:  
  a. Use MultiHarpWrapper() to take measurements. You can configure measurements per pixel using the config system. 
  b. Use NanoMaxStage() to implement a scanning routine. 
4. To analyse measured/recorded data, use Analyser(). 

## TODO:

1. Test IRF deconvolution (data from sub-ns lifetime samples required).
2. Implement custom software markers for scanning routines.
3. Implement block-wise measurement for long measurements.
4. Sample detection using Thorlabs camera. 
5. Automatic scaling of bin times in measurements for lifetime fitting in-post. 

## AndorSystem

Controls Andor CCD cameras and Shamrock spectrographs.

### Constructor
```python
AndorSystem(config="config.yaml")
```

### Methods

#### `update_config(config=None)`
- Updates system configuration from YAML file
- **Parameters**: `config` (str, optional) - Path to config file

#### `wait_for_stabilization()`
- Blocks until CCD temperature stabilizes
- Auto-shuts down if temperature drifts

#### `setup_spectrograph()`
- Configures spectrograph wavelength and camera readout
- **Returns**: Wavelength calibration array

#### `acquire_spectrum()`
- Acquires spectrum with cosmic ray rejection
- **Returns**: Combined spectrum data (list)

#### `is_overexposed(spectrum, threshold=10000)`
- Checks for detector saturation
- **Parameters**: `spectrum` (list), `threshold` (int)
- **Returns**: bool

#### `shutdown()`
- Safe shutdown with temperature ramping

---

## MultiHarpWrapper

Interface for PicoQuant MultiHarp TCSPC devices.

### Constructor
```python
MultiHarpWrapper(silent=False, debug=False, settings_config="settings.json", 
                measurement_config="measurement.json", irf_path="./data/irf.ptu",
                output_path="./data/default.ptu")
```

### Methods

#### `connect(measMode=MeasMode.T3, refSrc=None)`
- Connects to MultiHarp device
- **Returns**: bool (success)

#### `connectFile(filename)`
- Connects to PTU file for offline analysis
- **Parameters**: `filename` (str)
- **Returns**: bool (success)

#### `update_config()`
- Reloads and applies configuration files
- **Returns**: bool (success)

#### `set_settings()`
- Applies all device settings from config
- **Returns**: bool (success)

#### `get_count_rates(loopback=False)`
- Gets photon count rates from all channels
- **Parameters**: `loopback` (bool) - Continuous display if True
- **Returns**: list of count rates (Hz)

#### `get_sync_period()`
- **Returns**: Sync period (float, seconds)

#### `measure_irf(acqTime=1000, waitFinished=True, savePTU=True)`
- Measures instrument response function
- **Parameters**: `acqTime` (int, ms), `waitFinished` (bool), `savePTU` (bool)
- **Returns**: bool (success)

#### `measure(measType="unfold", acqTime=1000, size=134217728, waitFinished=True, savePTU=False)`
- Performs measurements based on type
- **Parameters**: `measType` (str), `acqTime` (int, ms), `size` (int), `waitFinished` (bool), `savePTU` (bool)
- **Returns**: bool (success)

#### `get_data(measType="unfold")`
- Retrieves measurement data
- **Parameters**: `measType` (str)
- **Returns**: tuple (time_bins, data) as numpy arrays

---

## Analyser

Advanced data analysis for fluorescence lifetime spectroscopy.

### Constructor
```python
Analyser(silent=False, debug=False, settings_config="settings.json",
         measurement_config="measurement.json", irf_path="./data/irf.ptu")
```

### Methods

#### `get_lifetimes(readoutData, readoutBins, horizon=1000, nExp=2, deconvolve=False, tau0=None, bounds=None, method=None, maxiter=None)`
- Multi-exponential lifetime fitting using NNLS
- **Parameters**: 
  - `readoutData` (array) - Decay histogram
  - `readoutBins` (array) - Time bins (ps)
  - `horizon` (int) - Fit range
  - `nExp` (int) - Number of exponentials
  - `deconvolve` (bool) - Apply IRF deconvolution
  - `tau0` (list) - Initial guesses (ns)
  - `bounds` (tuple) - Parameter bounds
  - `method` (str) - Optimization method
  - `maxiter` (int) - Max iterations
- **Returns**: dict with `lifetimes`, `amplitudes`, `fit`, `rnorm`, `success`, `message`

#### `plot_lifetimes(horizon=1000)`
- Plots data vs fitted curve
- **Parameters**: `horizon` (int) - Display range

#### `get_g2(readoutData, readoutBins, normalized=False)`
- Placeholder for g² correlation analysis
- **Parameters**: `readoutData` (array), `readoutBins` (array), `normalized` (bool)

---

## ThorlabsCamera

Thorlabs camera control for streaming and programmatic capture.

### Constructor
```python
ThorlabsCamera(config="config.yaml", camera_serial=None, buffer_size=30)
```

### Methods

#### `connect()`
- Connects to Thorlabs camera
- **Returns**: bool (success)

#### `disconnect()`
- Disconnects camera and cleanup resources

#### `capture_frame()`
- Captures single frame programmatically
- **Returns**: numpy array or None

#### `start_daemon()`
- Starts streaming daemon in background
- **Returns**: bool (success)

#### `stop_daemon()`
- Stops streaming daemon

#### `get_current_frame()`
- Gets most recent frame from stream
- **Returns**: numpy array or None

#### `get_status()`
- Gets current system status
- **Returns**: dict with connection, streaming, fps, etc.

#### `save_frame(frame, filename=None)`
- Saves frame to disk
- **Parameters**: `frame` (array), `filename` (str, optional)
- **Returns**: bool (success)

#### `set_frame_callback(callback)`
- Sets callback function for each new frame
- **Parameters**: `callback` (function)

#### `update_config(config=None)`
- Updates configuration from YAML file
- **Parameters**: `config` (str, optional)

#### `wait_for_stabilization()`
- Waits for camera to stabilize after settings change
- **Returns**: bool (success)

#### `shutdown()`
- Complete system shutdown with cleanup

### Command Line Usage

```bash
# Single frame capture
python camera.py --capture --output snapshot.png

# Run streaming daemon
python camera.py --daemon

# Check camera status  
python camera.py --status

# Use specific camera
python camera.py --serial CAMERA_SERIAL --capture

# Verbose logging
python camera.py --daemon --verbose

# Custom config file
python camera.py --config custom_config.yaml --daemon
```

**Available Arguments:**
- `--config, -c` - Configuration file path (default: config.yaml)
- `--serial, -s` - Camera serial number
- `--daemon, -d` - Run as streaming daemon
- `--capture` - Capture single frame
- `--output, -o` - Output filename for capture
- `--status` - Show camera status
- `--kill, -k` - Kill running daemon (placeholder)
- `--verbose, -v` - Enable verbose logging

**Daemon Control:**
- Start daemon: `python camera.py --daemon`
- Stop daemon: Press `Ctrl+C` in terminal
- Monitor: Displays real-time FPS and frame count

---

## NanoMaxStage

Precision positioning control via MDT69x controller.

### Constructor
```python
NanoMaxStage(port="COM4")
```

### Methods

#### `center_stage(start, end)`
- Positions stage at center of voltage range
- **Parameters**: `start` (float), `end` (float) - Voltage limits

#### `move_to(x=None, y=None, z=None)`
- Moves to absolute positions
- **Parameters**: `x`, `y`, `z` (float, optional) - Voltage positions

#### `close()`
- Immediate shutdown (0V all axes)

#### `shutdown()`
- Gradual shutdown with voltage ramping

---

## Usage Examples

### Basic Spectroscopy
```python
andor = AndorSystem("config.yaml")
andor.wait_for_stabilization()
wavelengths = andor.setup_spectrograph()
spectrum = andor.acquire_spectrum()
if andor.is_overexposed(spectrum):
    print("Saturated!")
andor.shutdown()
```

### Lifetime Measurement
```python
mh = MultiHarpWrapper(debug=True)
if mh.connect():
    mh.set_settings()
    mh.measure_irf(acqTime=10000)
    mh.measure("histogram", acqTime=60000)
    bins, counts = mh.get_data("histogram")
    
    analyzer = Analyser()
    results = analyzer.get_lifetimes(counts, bins, nExp=2)
    analyzer.plot_lifetimes()
    print(f"Lifetimes: {results['lifetimes']} ps")
```

### Stage Positioning
```python
stage = NanoMaxStage("COM4")
stage.center_stage(0.0, 10.0)
stage.move_to(x=5.0, y=3.0)
stage.shutdown()
```

---

## Configuration Files

### Andor (YAML)
```yaml
temp_setpoint: -70.0
center_wavelength: 650.0
exposure: 1.0
acquisition_mode: "single"
fan_mode: "full"
grating: 1
filter_slot: 5
```

### MultiHarp Settings (JSON)
```json
{
  "setSyncDiv": {"div": 8},
  "setInputCFD": {"channel": 0, "level": -50, "zerox": 0},
  "setBinning": {"binning": 0},
  "setOffset": {"offset": 0}
}
```
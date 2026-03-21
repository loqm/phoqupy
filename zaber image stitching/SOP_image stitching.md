# 🔬 Zaber XY Stage Image Stitching (MIST)

Control a dual-axis Zaber stage, acquire tiled images, and stitch them into a high-resolution composite using the MIST algorithm.

---

## 🚀 Quick Start

```bash
pip install pipenv
pipenv install
pipenv shell
```
## 🧭 Workflow

1️⃣ Stage Control + Live View
```bash
python main_gui.py
```
-> Joystick-based X–Y stage control
-> Live camera feed for alignment

2️⃣ Image Acquisition
```bash
python image_stitching.py
```
-> Automated raster scan
-> Captures and saves image tiles
3️⃣ Image Stitching (MIST)

-> Edit in stitch.py:
```bash
image_folder = "path/to/images"
```
Run:
```bash
python stitch.py
```
-> Outputs stitched high-resolution image
## 📁 Project Structure
```bash
.
├── python/
│   ├── main_gui.py
│   ├── image_stitching.py
│   ├── stitch.py
│   ├── joystick.py
│   ├── tkinter_camera_live_view.py
│   └── windows_setup.py
├── dlls/
│   ├── 32_lib/
│   └── 64_lib/
├── Pipfile
├── Pipfile.lock
```
## ⚙️ Requirements
Python 3.8+
Zaber X–Y stages
Camera (USB/compatible)
Joystick controller
## ⚠️ Tips
Run scripts in order
Ensure 10–20% overlap between images
Keep stage calibrated before scanning
Avoid interrupting acquisition
## 🧪 Output
Grid of captured images
Final stitched mosaic (MIST output)
## 🛠 Troubleshooting
Issue	Fix
Stage not moving	Check connections / COM port
No camera feed	Verify drivers / index
Bad stitching	Increase overlap
## 📌 Notes
Designed for microscopy / precision imaging workflows
Optimized for large-area scans with high spatial resolution
## 🤝 Contributing

Feel free to open issues or submit pull requests for improvements.

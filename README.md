# Xsens-to-OpeNsim

![Processed Results Simulation Video](/home/gabri/APERTA/APERTA-Repos/Docker_Repos/Xsens-to-OpeNsim/Procesado.mp4)

This repository provides tools to convert kinematic data retrieved from Xsens IMU sensors into OpenSim trajectories (`.sto` files) and, optionally, MuJoCo simulation files (`.xml`). 

The repository has been restructured and modularized to provide a clear separation between common source code (`src/`) and operating system specifics (`linux/`, `windows/`).

## Installation

### 1. Requirements

Ensure you have Python 3 installed and install the base data science dependencies:

```bash
pip install -r requirements.txt
```

Additionally, interacting with OpenSim files requires the OpenSim API (`import opensim`). Review the [OpenSim documentation](https://simtk-confluence.stanford.edu/display/OpenSim/Scripting+in+Python) for installation instructions depending on your system.

### 2. MuJoCo Conversion (Optional)

If you intend to run the `convert_to_mujoco` pipeline step, you must install the custom `myoconverter` library built by the repository author:

```bash
pip install git+https://github.com/gabrinovas/myoconverter.git
```

## Structure

*   `models/`: Contains the base `.osim` models ready for calibration.
    *   `Rajagopal_WithMuscles.osim`
    *   `Rajagopal2015_opensense.osim` (Skeleton only)
    *   `Rajagopal_FreeArms_LockedLegs.osim`
*   `src/`: Modularized, reusable Python functions dealing with Xsens parsing, OpenSim operations, Simbody visualization, and MuJoCo compilation.
*   `linux/`: Configuration (`config.yaml`) and execution scripts specific to Linux environments.
*   `windows/`: Configuration (`config.yaml`) and execution scripts specific to Windows environments. **Note:** Simbody visualization is unsupported on Windows here.
*   `sensor_mapping.json`: Configuration mapping Xsens IMU IDs to OpenSim model bodies.

## Usage

1. Open the `config.yaml` specific to your operating system (`linux/config.yaml` or `windows/config.yaml`).
2. Update the `paths:` variables to point to your physical `MT_*.txt` IMU files and specify where to save the processed files. Update the `model_path:` to select which model from the `models/` directory you wish to calibrate.
3. If necessary, adjust the `sensor_mapping.json` for your specific IMU setup.
4. Run the core pipeline from the root directory of this repository:

**Linux:**
```bash
python3 linux/run_pipeline.py
```

**Windows:**
```cmd
python windows\run_pipeline.py
```

### Visualizing Results (Linux Only)
After generating `.sto` files from the pipeline, you can visually render the calibration using Simbody on Linux:

```bash
python3 linux/visualize_simbody.py
```

### Converting to MuJoCo
Convert your OpenSim models to MuJoCo format (requires `myoconverter` dependency):

**Linux:**
```bash
python3 linux/convert_to_mujoco.py
```

**Windows:**
```cmd
python windows\convert_to_mujoco.py
```
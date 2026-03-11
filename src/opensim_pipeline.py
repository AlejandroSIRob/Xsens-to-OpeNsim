import opensim as osim
import os
import yaml

def load_config_from_input(config_input):
    """Loads configuration from either a file path or a dictionary."""
    if isinstance(config_input, dict):
        return config_input
    else:
        with open(config_input, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

def run_imu_placer(config_input):
    """Runs the OpenSim IMU Placer to calibrate the model.
       config_input can be either a path (str) or a config dict."""
    
    config = load_config_from_input(config_input)
    paths = config['paths']
    os_settings = config['opensim_settings']
    
    work_dir = os.getcwd()
    model_path = os.path.join(work_dir, paths['model_path'])
    data_path = os.path.join(work_dir, paths['output_folder'], paths['output_filename'])
    geometry_path = os.path.join(work_dir, paths['geometry_path'])
    out_dir = paths['output_folder']

    # Asegurar que el directorio de salida existe
    os.makedirs(out_dir, exist_ok=True)

    if os.path.exists(geometry_path):
        osim.ModelVisualizer.addDirToGeometrySearchPaths(geometry_path)

    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}")
        return None
    if not os.path.exists(data_path):
        print(f"ERROR: Data file not found at {data_path}")
        return None

    rot_list = os_settings['sensor_to_opensim_rot']
    sensor_to_opensim_rot = osim.Vec3(rot_list[0], rot_list[1], rot_list[2])

    print(f"--- 1. Calibrating Model: {os.path.basename(model_path)} ---")
    model = osim.Model(model_path)

    imu_placer = osim.IMUPlacer()
    imu_placer.setModel(model)
    imu_placer.set_orientation_file_for_calibration(data_path)
    imu_placer.set_sensor_to_opensim_rotations(sensor_to_opensim_rot)
    imu_placer.set_base_imu_label(os_settings['base_imu_label'])
    imu_placer.set_base_heading_axis(os_settings['base_heading_axis'])
    imu_placer.run(False)  # False to not open internal visualizer

    calibrated_model_path = os.path.join(out_dir, os_settings['output_model_name'])
    model.printToXML(calibrated_model_path)
    print(f"Calibrated model saved to: {calibrated_model_path}")
    return calibrated_model_path

def run_inverse_kinematics(config_input, calibrated_model_path):
    """Runs OpenSim IMU Inverse Kinematics using a calibrated model.
       config_input can be either a path (str) or a config dict."""
    
    config = load_config_from_input(config_input)
    paths = config['paths']
    os_settings = config['opensim_settings']
    
    work_dir = os.getcwd()
    data_path = os.path.join(work_dir, paths['output_folder'], paths['output_filename'])
    out_dir = paths['output_folder']
    
    # Asegurar que el directorio de salida existe
    os.makedirs(out_dir, exist_ok=True)
    
    rot_list = os_settings['sensor_to_opensim_rot']
    sensor_to_opensim_rot = osim.Vec3(rot_list[0], rot_list[1], rot_list[2])

    print("--- 2. Computing Inverse Kinematics (IK) ---")
    if not os.path.exists(calibrated_model_path):
        print(f"ERROR: Calibrated model not found at {calibrated_model_path}")
        return False
        
    model_calibrated = osim.Model(calibrated_model_path)

    ik_tool = osim.IMUInverseKinematicsTool()
    ik_tool.setModel(model_calibrated)
    ik_tool.set_orientations_file(data_path)
    ik_tool.set_sensor_to_opensim_rotations(sensor_to_opensim_rot)
    ik_tool.set_results_directory(out_dir)  # Ahora out_dir existe seguro
    
    ik_tool.run()
    print(f"IK Finished. Results in directory: {out_dir}")
    return True

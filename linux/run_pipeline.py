import sys
import os

# Add the parent directory to the path so we can import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import xsens_parser
from src import opensim_pipeline
from src import data_utils

def main():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    
    # Load config manually to find input directory
    import yaml
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
        
    original_input_dir = config_data['paths']['input_folder']
    fixed_input_dir = os.path.join(original_input_dir + "_corrected")
    
    print("\n--- 0. Fixing Packet Counters in IMU Data ---")
    data_utils.process_folder(original_input_dir, fixed_input_dir)
    
    # Temporarily override the config to point to the fixed directory
    config_data['paths']['input_folder'] = fixed_input_dir

    print("\n--- 1. Parsing and Aligning Xsens Data ---")
    success = xsens_parser.parse_config_dict(config_data)
    
    if not success:
        print("Failed to parse Xsens data. Aborting pipeline.")
        return

    print("\n--- 2. Running OpenSim IMU Placer ---")
    calibrated_model = opensim_pipeline.run_imu_placer(config_data)
    
    if not calibrated_model:
        print("Failed to run IMU Placer. Aborting pipeline.")
        return

    print("\n--- 3. Running OpenSim Inverse Kinematics ---")
    opensim_pipeline.run_inverse_kinematics(config_data, calibrated_model)

if __name__ == "__main__":
    # To run this script, your working directory should be the root of the repository
    if not os.path.exists("linux/config.yaml"):
        print("Please run this script from the root of the repository: python linux/run_pipeline.py")
        sys.exit(1)
        
    main()

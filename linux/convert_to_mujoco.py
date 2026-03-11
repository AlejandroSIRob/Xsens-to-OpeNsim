import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import mujoco_converter

def main():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    print("\n--- Starting MuJoCo Conversion ---")
    success = mujoco_converter.run_mujoco_conversion(config_path)
    
    if not success:
        print("MuJoCo conversion failed.")
        sys.exit(1)
    
    print("MuJoCo conversion completed successfully.")

if __name__ == "__main__":
    if not os.path.exists("linux/config.yaml"):
        print("Please run this script from the root of the repository: python linux/convert_to_mujoco.py")
        sys.exit(1)
        
    main()

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import simbody_visualizer

def main():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    print("\n--- Starting Simbody Visualization ---")
    # You can adjust speed_step (e.g., 1 for slow, 10 for fast) and start_time_sec
    success = simbody_visualizer.run_simbody_visualization(config_path, speed_step=10, start_time_sec=0.0)
    
    if not success:
        print("Visualization failed.")

if __name__ == "__main__":
    if not os.path.exists("linux/config.yaml"):
        print("Please run this script from the root of the repository: python linux/visualize_simbody.py")
        sys.exit(1)
        
    main()

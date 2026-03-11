import os
import shutil
import yaml

def load_config(config_path):
    """Loads configuration from a YAML file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def run_mujoco_conversion(config_path, output_mujoco_dir=None):
    """
    Converts an OpenSim model to MuJoCo format using myoconverter.
    
    Args:
        config_path: Path to the configuration YAML file
        output_mujoco_dir: Override output directory (optional)
    """
    try:
        from myoconverter.O2MPipeline import O2MPipeline
    except ImportError:
        print("ERROR: myoconverter module is not installed.")
        print("Please install it using: pip install git+https://github.com/gabrinovas/myoconverter.git")
        return False

    config = load_config(config_path)
    paths = config['paths']
    
    work_dir = os.getcwd()
    osim_path = os.path.join(work_dir, paths['model_path'])
    geometry_folder = os.path.join(work_dir, paths['geometry_path'])
    
    # Determinar carpeta de salida
    if output_mujoco_dir is None:
        # Si hay ruta configurada en YAML, usarla (puede ser absoluta o relativa)
        if 'mujoco_output_folder' in paths:
            output_mujoco_dir = paths['mujoco_output_folder']
        else:
            # Fallback a carpeta por defecto relativa
            output_mujoco_dir = "mujoco_model"
    
    # Si la ruta no es absoluta, hacerla relativa al directorio de trabajo
    if not os.path.isabs(output_mujoco_dir):
        output_folder = os.path.join(work_dir, output_mujoco_dir)
    else:
        output_folder = output_mujoco_dir

    print(f"\n--- 4. Converting to MuJoCo: {os.path.basename(osim_path)} ---")
    print(f"Output directory: {output_folder}")

    if not os.path.exists(osim_path):
        print(f"ERROR: OpenSim model not found at {osim_path}")
        return False

    # Crear directorio de salida
    os.makedirs(output_folder, exist_ok=True)
    
    # Limpiar contenido previo si existe (pero no borrar el directorio en sí)
    if os.path.exists(output_folder):
        print(f"Cleaning existing MuJoCo output directory: {output_folder}")
        for item in os.listdir(output_folder):
            item_path = os.path.join(output_folder, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

    # Ejecutar conversión (solo kinemática)
    print("Running O2MPipeline conversion (Kinematics only)...")
    try:
        converter = O2MPipeline(
            osim_path, 
            geometry_folder, 
            output_folder, 
            steps=[1],
            force_all=True,
            skip_plotting=True
        )
        print(f"✓ Conversion completed. MuJoCo model saved to: {output_folder}")
        return True
    except Exception as e:
        print(f"ERROR during MuJoCo conversion: {e}")
        return False

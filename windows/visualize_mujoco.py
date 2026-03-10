"""
Script para visualizar trayectorias del modelo en MuJoCo (Windows)
Ejecutar desde la raíz del repositorio: python windows\visualize_mujoco.py
"""

import sys
import os
import yaml
import numpy as np
import pandas as pd
import time
import glob

# Añadir el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_config(config_path):
    """Carga la configuración desde un archivo YAML."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def find_mujoco_model(output_dir, config=None):
    """
    Busca el modelo de MuJoCo en el directorio de salida.
    Si config tiene 'mujoco_output_folder', busca primero allí.
    """
    search_paths = []
    
    # Si tenemos configuración con carpeta específica de MuJoCo
    if config and 'paths' in config and 'mujoco_output_folder' in config['paths']:
        mujoco_path = config['paths']['mujoco_output_folder']
        
        # Si es ruta absoluta, usarla directamente
        if os.path.isabs(mujoco_path):
            search_paths.append(os.path.join(mujoco_path, "*.xml"))
        else:
            # Si es relativa, combinar con directorio de trabajo
            mujoco_dir = os.path.join(os.getcwd(), mujoco_path)
            search_paths.append(os.path.join(mujoco_dir, "*.xml"))
    
    # Añadir rutas por defecto
    search_paths.extend([
        os.path.join(output_dir, "mujoco_model", "*.xml"),
        os.path.join(output_dir, "*.xml"),
        os.path.join(os.getcwd(), "mujoco_model", "*.xml")
    ])
    
    for pattern in search_paths:
        files = glob.glob(pattern)
        if files:
            return files[0]
    
    return None

def find_motion_file(output_dir):
    """
    Busca el archivo de movimiento (.mot) en el directorio de salida.
    """
    search_patterns = [
        os.path.join(output_dir, "*.mot"),
        os.path.join(output_dir, "ik_*.mot"),
        os.path.join(output_dir, "*_ik.mot")
    ]
    
    for pattern in search_patterns:
        files = glob.glob(pattern)
        if files:
            return files[0]
    
    return None

def visualize_mujoco_trajectory(config_path, mjcf_path=None, data_path=None, 
                               speed_factor=1.0, start_time=0.0, pelvis_rotation_offset=0):
    """
    Visualiza trayectorias del modelo en MuJoCo.
    """
    try:
        import mujoco
        import mujoco.viewer
    except ImportError:
        print("ERROR: mujoco no está instalado.")
        print("Instálalo con: pip install mujoco")
        return False
    
    # Cargar configuración
    config = load_config(config_path)
    paths = config['paths']
    settings = config['settings']
    sampling_rate = settings['sampling_rate']
    
    output_dir = os.path.join(os.getcwd(), paths['output_folder'])
    
    print(f"\n--- Visualizando trayectoria en MuJoCo ---")
    
    # Determinar rutas de archivos
    if mjcf_path is None:
        mjcf_path = find_mujoco_model(output_dir, config)
        if mjcf_path is None:
            print("ERROR: No se encontró el modelo de MuJoCo.")
            return False
    
    if data_path is None:
        data_path = find_motion_file(output_dir)
        if data_path is None:
            print("ERROR: No se encontró el archivo de movimiento (.mot).")
            return False
    
    print(f"Modelo MJCF: {mjcf_path}")
    print(f"Datos: {data_path}")
    print(f"Factor de velocidad: {speed_factor}")
    
    # Verificar que los archivos existen
    if not os.path.exists(mjcf_path):
        print(f"ERROR: Modelo no encontrado en {mjcf_path}")
        return False
    
    if not os.path.exists(data_path):
        print(f"ERROR: Datos no encontrados en {data_path}")
        return False
    
    try:
        # Cargar modelo de MuJoCo
        model = mujoco.MjModel.from_xml_path(mjcf_path)
        data = mujoco.MjData(model)
        
        # Cargar datos de trayectoria
        df = pd.read_csv(data_path, sep='\t', skiprows=6)
        print(f"Archivo de datos cargado: {len(df)} frames")
        
        # Crear mapeo automático de joints
        mapping = {}
        joints_found = []
        for col in df.columns:
            col_clean = col.strip()
            joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, col_clean)
            if joint_id != -1:
                mapping[col_clean] = model.jnt_qposadr[joint_id]
                joints_found.append(col_clean)
        
        print(f"Joints encontrados: {len(joints_found)}")
        
        # Obtener el vector de tiempos
        if 'time' in df.columns:
            times = df['time'].values
        else:
            times = np.arange(len(df)) / sampling_rate
        
        # Encontrar frame de inicio
        start_idx = 0
        for i, t in enumerate(times):
            if t >= start_time:
                start_idx = i
                break
        
        print(f"Iniciando en tiempo: {times[start_idx]:.2f}s")
        print("\nPresiona Ctrl+C para detener")
        print("Controles: Izq: rotar, Der: zoom, Medio: panorámica")
        
        # Loop de visualización - VERSIÓN SIMPLE Y RÁPIDA
        with mujoco.viewer.launch_passive(model, data) as viewer:
            viewer.cam.distance = 4.0
            viewer.cam.azimuth = 90
            viewer.cam.elevation = -15
            
            for i in range(start_idx, len(df)):
                row = df.iloc[i]
                
                # Actualizar posiciones articulares
                for col_name, q_index in mapping.items():
                    if col_name in row.index:
                        val = row[col_name]
                        
                        # Conversiones especiales
                        if col_name in ["pelvis_rotation", "pelvis_tilt", "pelvis_list"]:
                            if col_name == "pelvis_rotation":
                                val = np.deg2rad(val + pelvis_rotation_offset)
                            else:
                                val = np.deg2rad(val)
                        elif col_name in ["pelvis_tx", "pelvis_ty", "pelvis_tz"]:
                            # Translaciones - no convertir
                            pass
                        else:
                            # Otras articulaciones - convertir a radianes
                            val = np.deg2rad(val)
                        
                        data.qpos[q_index] = val
                
                # Avanzar simulación
                mujoco.mj_step(model, data)
                viewer.sync()
                
                # Control de velocidad simple - 0.01s = ~100fps (original)
                time.sleep(0.01 / speed_factor)
                
                # Mostrar progreso cada 100 frames
                if i % 100 == 0:
                    current_time = times[i] if i < len(times) else i/sampling_rate
                    print(f"Tiempo: {current_time:.2f}s | Frame: {i}", end='\r')
        
        print("\nVisualización completada.")
        return True
        
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Función principal."""
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    
    if not os.path.exists(config_path):
        print("ERROR: Ejecuta desde la raíz: python windows\\visualize_mujoco.py")
        sys.exit(1)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mjcf', type=str, help='Ruta al modelo MJCF')
    parser.add_argument('--data', type=str, help='Ruta al archivo .mot')
    parser.add_argument('--speed', type=float, default=1.0, help='Factor velocidad')
    parser.add_argument('--start', type=float, default=0.0, help='Tiempo inicio')
    parser.add_argument('--offset', type=float, default=0, help='Offset pelvis (grados)')
    
    args = parser.parse_args()
    
    success = visualize_mujoco_trajectory(
        config_path=config_path,
        mjcf_path=args.mjcf,
        data_path=args.data,
        speed_factor=args.speed,
        start_time=args.start,
        pelvis_rotation_offset=args.offset
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

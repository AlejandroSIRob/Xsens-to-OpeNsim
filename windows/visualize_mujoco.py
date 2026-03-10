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

# Añadir el directorio padre al path para importar módulos del repositorio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_config(config_path):
    """Carga la configuración desde un archivo YAML."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def find_mujoco_model(output_dir, base_name="Rajagopal2015_BrazosLibres_PiernasBloqueadas_cvt1.xml"):
    """
    Busca el modelo de MuJoCo en el directorio de salida.
    """
    search_patterns = [
        os.path.join(output_dir, "mujoco_model", "*.xml"),
        os.path.join(output_dir, "*.xml"),
        os.path.join(os.getcwd(), "mujoco_model", "*.xml")
    ]
    
    for pattern in search_patterns:
        files = glob.glob(pattern)
        if files:
            return files[0]
    
    # Si no encuentra, usa el nombre por defecto en el directorio actual
    default_path = os.path.join(os.getcwd(), "mujoco_model", base_name)
    if os.path.exists(default_path):
        return default_path
    
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
    
    Args:
        config_path: Ruta al archivo de configuración
        mjcf_path: Ruta al modelo MJCF de MuJoCo (si es None, se busca automáticamente)
        data_path: Ruta al archivo de datos .mot (si es None, se busca automáticamente)
        speed_factor: Factor de velocidad (1.0 = velocidad normal)
        start_time: Tiempo de inicio en segundos
        pelvis_rotation_offset: Offset de rotación para la pelvis (grados)
    """
    try:
        import mujoco
        import mujoco.viewer
    except ImportError:
        print("ERROR: mujoco no está instalado.")
        print("Instálalo con: pip install mujoco")
        return False
    
    # Cargar configuración para obtener la frecuencia de muestreo
    config = load_config(config_path)
    paths = config['paths']
    settings = config['settings']
    sampling_rate = settings['sampling_rate']  # 60.0 por defecto
    
    output_dir = os.path.join(os.getcwd(), paths['output_folder'])
    
    # Determinar rutas de archivos
    if mjcf_path is None:
        mjcf_path = find_mujoco_model(output_dir)
        if mjcf_path is None:
            print("ERROR: No se encontró el modelo de MuJoCo.")
            print("Busca el archivo XML en el directorio de salida o especifica mjcf_path.")
            return False
    
    if data_path is None:
        data_path = find_motion_file(output_dir)
        if data_path is None:
            print("ERROR: No se encontró el archivo de movimiento (.mot).")
            return False
    
    print(f"\n--- Visualizando trayectoria en MuJoCo ---")
    print(f"Modelo MJCF: {mjcf_path}")
    print(f"Datos: {data_path}")
    print(f"Frecuencia de muestreo (config): {sampling_rate} Hz")
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
        print(f"Archivo de datos cargado: {len(df)} frames, {len(df.columns)} columnas")
        
        # Crear mapeo automático de joints
        mapping = {}
        joints_found = []
        for col in df.columns:
            col_clean = col.strip()
            joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, col_clean)
            if joint_id != -1:
                mapping[col_clean] = model.jnt_qposadr[joint_id]
                joints_found.append(col_clean)
        
        print(f"Joints encontrados en el modelo: {len(joints_found)}")
        if len(joints_found) == 0:
            print("ADVERTENCIA: No se encontraron joints en el modelo.")
            print("Columnas disponibles en datos:", list(df.columns)[:10])
        
        # Obtener el vector de tiempos
        if 'time' in df.columns:
            times = df['time'].values
        else:
            # Si no hay columna time, asumimos la frecuencia de muestreo
            times = np.arange(len(df)) / sampling_rate
            print(f"Nota: Usando frecuencia de muestreo de configuración: {sampling_rate} Hz")
        
        # Calcular la frecuencia real a partir de los datos
        if len(times) > 1:
            real_freq = 1.0 / np.mean(np.diff(times))
            print(f"Frecuencia real calculada de datos: {real_freq:.2f} Hz")
            frame_time = 1.0 / real_freq
        else:
            frame_time = 1.0 / sampling_rate
            print(f"Usando frame_time = {frame_time*1000:.1f} ms (de configuración)")
        
        # Encontrar frame de inicio
        start_idx = 0
        for i, t in enumerate(times):
            if t >= start_time:
                start_idx = i
                break
        
        print(f"Iniciando en tiempo: {times[start_idx]:.2f}s (frame {start_idx})")
        print("\nPresiona Ctrl+C para detener la visualización")
        print("Controles del visor:")
        print("  - Botón izquierdo: Rotar cámara")
        print("  - Botón derecho: Zoom")
        print("  - Botón medio: Panorámica")
        
        # Loop de visualización
        with mujoco.viewer.launch_passive(model, data) as viewer:
            viewer.cam.distance = 4.0
            viewer.cam.azimuth = 90
            viewer.cam.elevation = -15
            
            frame_count = 0
            last_time = time.time()
            
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
                            # Otras articulaciones (brazos, piernas) - convertir a radianes
                            val = np.deg2rad(val)
                        
                        data.qpos[q_index] = val
                
                # Avanzar simulación
                mujoco.mj_step(model, data)
                viewer.sync()
                
                # Control de velocidad basado en la frecuencia real
                frame_count += 1
                if frame_count % 10 == 0:
                    elapsed = time.time() - last_time
                    target_time = (i - start_idx) * frame_time / speed_factor
                    if elapsed < target_time:
                        time.sleep(target_time - elapsed)
                    last_time = time.time()
                
                # Mostrar progreso
                if i % 100 == 0:
                    current_time = times[i] if i < len(times) else i/sampling_rate
                    print(f"Tiempo: {current_time:.2f}s | Frame: {i}", end='\r')
        
        print("\nVisualización completada.")
        return True
        
    except KeyboardInterrupt:
        print("\nVisualización detenida por el usuario.")
        return True
    except Exception as e:
        print(f"ERROR durante la visualización: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal del script."""
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists(config_path):
        print("ERROR: No se encuentra config.yaml")
        print("Ejecuta este script desde la raíz del repositorio:")
        print("  python windows\\visualize_mujoco.py")
        sys.exit(1)
    
    print("\n--- Visualizador de Trayectorias MuJoCo (Windows) ---")
    
    # Parámetros configurables
    import argparse
    parser = argparse.ArgumentParser(description='Visualizar trayectorias en MuJoCo')
    parser.add_argument('--mjcf', type=str, help='Ruta al modelo MJCF (opcional)')
    parser.add_argument('--data', type=str, help='Ruta al archivo .mot (opcional)')
    parser.add_argument('--speed', type=float, default=1.0, help='Factor de velocidad (defecto: 1.0)')
    parser.add_argument('--start', type=float, default=0.0, help='Tiempo de inicio en segundos')
    parser.add_argument('--offset', type=float, default=0, help='Offset de rotación de pelvis (grados)')
    
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
        print("Visualización fallida.")
        sys.exit(1)

if __name__ == "__main__":
    main()

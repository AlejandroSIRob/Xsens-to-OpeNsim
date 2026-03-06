import pandas as pd
import numpy as np
from scipy.spatial.transform import Rotation as R
import os
import glob

# =========================================================
# 1.CONFIGURACIÓN DE RUTAS (EDITAR AQUÍ)
# =========================================================

# 1. Archivos exportados del software
input_folder = r"C:\Users\alexs\Desktop\MUESTRAS\V10\XSENS" 

# 2. Guardados archivos salida
output_folder = r"C:\Users\alexs\Desktop\MUESTRAS\V10\PROCESADO-Xsens"
output_filename = 'cinematica_v10.sto'

# Frecuencia de muestreo (Xsens suele ser 60Hz o 100Hz)
TARGET_FREQ = 60.0

# ---------------------------------------------------------
# 2. MAPEO DE SENSORES (IDs -> Nombres OpenSim)
# ---------------------------------------------------------
sensor_mapping = {
    # TREN INFERIOR / TRONCO
    '10B41517': 'pelvis_imu',       # Pelvis
    '10B4151A': 'torso_imu',        # Torso 

    # TREN SUPERIOR DERECHO
    '10B4151C': 'humerus_r_imu',    # "Bíceps" (Brazo superior derecho)
    '10B4215D': 'radius_r_imu',     # "Muñeca derecha" (Antebrazo derecho)

    # TREN SUPERIOR IZQUIERDO
    '10B414FE': 'humerus_l_imu',    # "Bíceps" (Brazo superior izquierdo) 
    '10B414FF': 'radius_l_imu',     # "Muñeca izquierda" (Antebrazo izquierdo)

    # MANO DERECHA:
    '10B41515': 'hand_r_imu',       # Mano Derecha 
    
    # CABEZA
    #'10B41515': 'cranial_imu',       # Cabeza 

    # --- NUEVO: MANOS (Usando los sensores de Torso y Cabeza) ---
    # IMPORTANTE: Verifica qué ID tienes en qué mano. 
    # Si al visualizar se cruzan los brazos, intercambia estos dos nombres.
    #'10B4151A': 'hand_r_imu',       # Mano Derecha (Antes Torso)
    #'10B41515': 'hand_l_imu',       # Mano Izquierda (Antes Cabeza)
    }

# ---------------------------------------------------------
# 3. FUNCIÓN DE PROCESAMIENTO
# ---------------------------------------------------------
def process_xsens_files():
    patron = os.path.join(input_folder, "MT_*.txt")
    files = glob.glob(patron)
    
    if not files:
        print("No se encontraron archivos MT_*.txt en el directorio.")
        return

    merged_data = pd.DataFrame()
    print(f"Encontrados {len(files)} archivos. Procesando...")

    for filepath in files:
        filename = os.path.basename(filepath)
        sensor_id = next((sid for sid in sensor_mapping.keys() if sid in filename), None)
        
        if not sensor_id:
            continue
            
        col_name = sensor_mapping[sensor_id]
        print(f"-> Procesando {col_name} (ID: {sensor_id})...")
        
        # Detectar inicio de datos
        with open(filepath, 'r') as f:
            skip_rows = next(i for i, line in enumerate(f) if 'PacketCounter' in line)
        
        df = pd.read_csv(filepath, sep='\t', skiprows=skip_rows)
        
        # --- LÓGICA DE TIEMPO ---
        df['time'] = (df['PacketCounter'] - df['PacketCounter'].iloc[0]) / TARGET_FREQ
        df = df.set_index('time')
        
        # !!! CORRECCIÓN CRÍTICA !!!
        # Aseguramos que el índice esté ordenado y eliminamos duplicados si los hay
        df = df[~df.index.duplicated(keep='first')]
        df = df.sort_index()
        
        # --- LÓGICA DE CONVERSIÓN ---
        if 'Quat_q0' in df.columns:
            quats = df[['Quat_q0', 'Quat_q1', 'Quat_q2', 'Quat_q3']].values
        elif 'Roll' in df.columns:
            euler_angles = df[['Roll', 'Pitch', 'Yaw']].values
            r = R.from_euler('xyz', euler_angles, degrees=True)
            q_scipy = r.as_quat()
            quats = np.column_stack((q_scipy[:, 3], q_scipy[:, 0], q_scipy[:, 1], q_scipy[:, 2]))
        else:
            continue

        quat_strings = [f"{q[0]:.6f},{q[1]:.6f},{q[2]:.6f},{q[3]:.6f}" for q in quats]
        df_col = pd.DataFrame(data=quat_strings, index=df.index, columns=[col_name])
        
        # Unir al dataframe principal
        if merged_data.empty:
            merged_data = df_col
        else:
            # Re-ordenar merged_data antes de cada fusión por seguridad
            merged_data = merged_data.sort_index()
            merged_data = pd.merge_asof(merged_data, df_col, left_index=True, right_index=True, tolerance=0.02, direction='nearest')

    # ---------------------------------------------------------
    # 4. GUARDADO
    # ---------------------------------------------------------
    if not merged_data.empty:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            
        full_path = os.path.join(output_folder, output_filename)
        
        with open(full_path, 'w') as f:
            f.write("DataRate=60.000000\nDataType=Quaternion\nversion=3\nOpenSimVersion=4.4\nendheader\n")
            f.write("time\t" + "\t".join(merged_data.columns) + "\n")
            for t, row in merged_data.iterrows():
                f.write(f"{t:.4f}\t" + "\t".join(row.values) + "\n")
                
        print(f"\n¡ÉXITO! Archivo guardado como: {full_path}")
    else:
        print("\n[ERROR] No se generaron datos.")

if __name__ == "__main__":
    process_xsens_files()
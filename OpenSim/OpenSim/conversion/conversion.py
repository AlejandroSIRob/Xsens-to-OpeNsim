import pandas as pd
import numpy as np
from scipy.spatial.transform import Rotation as R
import os
import glob

# ---------------------------------------------------------
# 1. MAPEO DE SENSORES (IDs -> Nombres OpenSim)
# ---------------------------------------------------------
sensor_mapping = {
    # TREN INFERIOR / TRONCO
    '10B41517': 'pelvis_imu',       # Pelvis
    '10B4151A': 'torso_imu',             # TREN SUPERIOR DERECHO

    # TREN SUPERIOR DERECHO
    '10B4151C': 'humerus_r_imu',    # "Espalda derecha" (Brazo superior derecho)
    '10B4215D': 'radius_r_imu',     # "Muñeca derecha" (Antebrazo derecho)

    # TREN SUPERIOR IZQUIERDO
    '10B414FE': 'humerus_l_imu',    # "Espalda izquierda" (Brazo superior izquierdo) - [VERIFICAR ID]
    '10B414FF': 'radius_l_imu',     # "Muñeca izquierda" (Antebrazo izquierdo)

    # CABEZA
    '10B41515': 'cranial_imu'       # Cabeza - [VERIFICAR ID]
    }

# Nombre del archivo de salida
output_filename = 'xsens_converted_data.sto'

# Frecuencia de muestreo (Ajustar si es diferente, ej: 60Hz, 100Hz)
TARGET_FREQ = 60.0 

# ---------------------------------------------------------
# 2. FUNCIÓN DE PROCESAMIENTO
# ---------------------------------------------------------
def process_xsens_files():
    # Defines la carpeta correcta para tu entorno Linux
    carpeta = "/home/ubuntu/Desktop/OpenSim/conversion/CALIBRADO_MOV"

    # Unes la carpeta con el nombre del archivo
    patron = os.path.join(carpeta, "MT_*.txt")

    # Buscas los archivos
    files = glob.glob(patron)
    
    if not files:
        print(f"No se encontraron archivos MT_*.txt en el directorio: {carpeta}")
        return

    merged_data = pd.DataFrame()
    print(f"Encontrados {len(files)} archivos en {carpeta}. Procesando...")

    for filepath in files:
        # Extraer ID del nombre del archivo
        filename = os.path.basename(filepath)
        sensor_id = None
        for sid in sensor_mapping.keys():
            if sid in filename:
                sensor_id = sid
                break
        
        if not sensor_id:
            print(f"AVISO: El archivo '{filename}' no tiene un ID en el mapa. Se salta.")
            continue
            
        col_name = sensor_mapping[sensor_id]
        print(f"-> Procesando {col_name} (ID: {sensor_id})...")
        
        # Detectar inicio de datos (buscar línea 'PacketCounter')
        with open(filepath, 'r') as f:
            lines = f.readlines()
            skip_rows = 0
            for i, line in enumerate(lines):
                if 'PacketCounter' in line:
                    skip_rows = i
                    break
        
        # Cargar datos
        df = pd.read_csv(filepath, sep='\t', skiprows=skip_rows)
        
        # --- LÓGICA DE TIEMPO ---
        # Usar PacketCounter para crear un tiempo relativo constante
        df['time'] = (df['PacketCounter'] - df['PacketCounter'].iloc[0]) / TARGET_FREQ
        df = df.set_index('time')
        
        # --- LÓGICA DE CONVERSIÓN (Euler vs Quaterniones) ---
        quats = None
        
        # CASO A: El archivo YA tiene Cuaterniones (Quat_q0, etc.)
        if 'Quat_q0' in df.columns:
            # Orden Xsens: q0(w), q1(x), q2(y), q3(z)
            quats = df[['Quat_q0', 'Quat_q1', 'Quat_q2', 'Quat_q3']].values
            
        # CASO B: El archivo solo tiene Euler (Roll, Pitch, Yaw)
        elif 'Roll' in df.columns:
            euler_angles = df[['Roll', 'Pitch', 'Yaw']].values
            # Xsens Euler suele ser XYZ en grados. Convertimos a Quaterniones.
            r = R.from_euler('xyz', euler_angles, degrees=True)
            # Scipy devuelve [x, y, z, w]
            q_scipy = r.as_quat()
            # Convertir a [w, x, y, z] para OpenSim
            quats = np.column_stack((q_scipy[:, 3], q_scipy[:, 0], q_scipy[:, 1], q_scipy[:, 2]))
            
        else:
            print(f"ERROR: El archivo {filename} no tiene columnas de orientación reconocibles.")
            continue

        # Formato 'Quaternion' de archivo .sto: "w,x,y,z" en una sola celda como string
        quat_strings = []
        for q in quats:
            # q es [w, x, y, z]
            quat_strings.append(f"{q[0]:.6f},{q[1]:.6f},{q[2]:.6f},{q[3]:.6f}")
            
        df_col = pd.DataFrame(data=quat_strings, index=df.index, columns=[col_name])
        
        # Unir al dataframe principal
        if merged_data.empty:
            merged_data = df_col
        else:
            # Unir tolerando pequeñas diferencias de tiempo
            merged_data = pd.merge_asof(merged_data, df_col, left_index=True, right_index=True, tolerance=0.02, direction='nearest')

    # ---------------------------------------------------------
    # 3. GUARDAR ARCHIVO .STO
    # ---------------------------------------------------------
    if not merged_data.empty:
        with open(output_filename, 'w') as f:
            # Cabecera estándar OpenSim
            f.write("DataRate=60.000000\n")
            f.write("DataType=Quaternion\n")
            f.write("version=3\n")
            f.write("OpenSimVersion=4.4\n")
            f.write("endheader\n")
            
            # Encabezados de columnas (time + sensores)
            header = "time\t" + "\t".join(merged_data.columns) + "\n"
            f.write(header)
            
            # Datos
            for t, row in merged_data.iterrows():
                line = f"{t:.4f}\t" + "\t".join(row.values) + "\n"
                f.write(line)
                
        print(f"\n¡ÉXITO! Archivo guardado como: {os.path.abspath(output_filename)}")
        print("Copia este archivo en tu carpeta de OpenSim/OpenSense.")
    else:
        print("No se pudieron procesar datos.")

# Ejecutar el script
if __name__ == "__main__":
    process_xsens_files()

import opensim as osim
import os
import math
import time

# ================= CONFIGURACIÓN DE VELOCIDAD =================
# AUMENTA este número para ir más rápido.
# 1 = Dibuja todos los cuadros (Lento)
# 5 = Dibuja 1 de cada 5 (Rápido)
# 10 = Dibuja 1 de cada 10 (Muy Rápido)
SPEED_STEP = 10  

# Segundo donde quieres que empiece la visualización
START_TIME_SEC = 0.0 
# ==============================================================

WORK_DIR = os.getcwd()
MODEL_PATH = os.path.join(WORK_DIR, "model", "Rajagopal_Unificado.osim")
DATA_PATH = os.path.join(WORK_DIR, "xsens_converted_data.sto")
GEOMETRY_PATH = "/home/ubuntu/Desktop/OpenSim/conversion/model/Geometry"
osim.ModelVisualizer.addDirToGeometrySearchPaths(GEOMETRY_PATH)

# Configuración IMU
BASE_IMU_LABEL = "pelvis_imu"
BASE_HEADING_AXIS = "-z"
SENSOR_TO_OPENSIM_ROT = osim.Vec3(-math.pi/2, 0, 0)

OUT_DIR = "Resultados_Linux"
if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR)

# Validación de archivos
if not os.path.exists(MODEL_PATH) or not os.path.exists(DATA_PATH):
    print("ERROR: Faltan archivos (modelo o datos).")
    exit()

# ================= PASO 1: IMU PLACER =================
print(f"--- 1. Calibrando Modelo ---")
model = osim.Model(MODEL_PATH)
imu_placer = osim.IMUPlacer()
imu_placer.setModel(model)
imu_placer.set_orientation_file_for_calibration(DATA_PATH)
imu_placer.set_sensor_to_opensim_rotations(SENSOR_TO_OPENSIM_ROT)
imu_placer.set_base_imu_label(BASE_IMU_LABEL)
imu_placer.set_base_heading_axis(BASE_HEADING_AXIS)
imu_placer.run(False)

calibrated_model_path = os.path.join(OUT_DIR, "Modelo_Calibrado.osim")
model.printToXML(calibrated_model_path)
print("Modelo calibrado guardado.")

# ================= PASO 2: IK =================
print("--- 2. Calculando IK ---")
model_calibrated = osim.Model(calibrated_model_path)
ik_tool = osim.IMUInverseKinematicsTool()
ik_tool.setModel(model_calibrated)
ik_tool.set_orientations_file(DATA_PATH)
ik_tool.set_sensor_to_opensim_rotations(SENSOR_TO_OPENSIM_ROT)
ik_tool.set_results_directory(OUT_DIR)
ik_tool.run()
print("IK Finalizado.")

# ================= PASO 3: VISUALIZACIÓN OPTIMIZADA =================
print("\n--- 3. Visualizando ---")

mot_files = [f for f in os.listdir(OUT_DIR) if f.endswith(".mot")]
if not mot_files: exit()
motion_file_path = os.path.join(OUT_DIR, mot_files[0])

# Preparar visualizador
model_calibrated.setUseVisualizer(True)
state = model_calibrated.initSystem()
visualizer = model_calibrated.updVisualizer().updSimbodyVisualizer()
visualizer.setBackgroundColor(osim.Vec3(0.2, 0.2, 0.2))

# Cargar datos
table = osim.TimeSeriesTable(motion_file_path)
times = table.getIndependentColumn()
n_rows = table.getNumRows()

# --- OPTIMIZACIÓN A: MAPEO PREVIO ---
# En lugar de buscar nombres (strings) en el bucle, guardamos los objetos coordenada
print("Optimizando caché de coordenadas...")
coord_map = []
for j in range(table.getNumColumns()):
    col_name = table.getColumnLabel(j)
    if model_calibrated.getCoordinateSet().contains(col_name):
        # Guardamos la tupla: (indice_columna, objeto_coordenada)
        coord_obj = model_calibrated.updCoordinateSet().get(col_name)
        coord_map.append((j, coord_obj))

# --- OPTIMIZACIÓN B: BÚSQUEDA DE INICIO ---
start_index = 0
for k in range(n_rows):
    if times[k] >= START_TIME_SEC:
        start_index = k
        break

print(f"Iniciando en {times[start_index]:.2f}s | Saltando cada {SPEED_STEP} frames.")

# Loop Turbo
try:
    # El tercer parámetro de range es el 'step' (el salto)
    for i in range(start_index, n_rows, SPEED_STEP):
        
        # 1. Obtener fila
        row = table.getRowAtIndex(i)
        
        # 2. Actualizar coordenadas (Usando el mapa optimizado)
        for col_idx, coord_obj in coord_map:
            # Obtener valor directo (sin buscar nombres)
            val_deg = row.getElt(0, col_idx)
            coord_obj.setValue(state, math.radians(val_deg))
        
        # 3. Dibujar
        model_calibrated.realizePosition(state)
        visualizer.drawFrameNow(state)
        
        print(f"Tiempo: {times[i]:.2f} s", end='\r')
        
        # Sin sleep para máxima velocidad, o muy bajo si parpadea
        # time.sleep(0.001) 

except KeyboardInterrupt:
    print("\nDetenido.")

print("\nFin.")

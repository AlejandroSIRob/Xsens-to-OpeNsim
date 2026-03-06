import opensim as osim
import os
import sys

print("--- CARGANDO MODELO BIOMÉDICO (BRAZO) ---")

# 1. Definir rutas
home_dir = os.path.expanduser("~")
repo_folder = os.path.join(home_dir, "Desktop/opensim-models")
model_file = os.path.join(repo_folder, "Models/Arm26/arm26.osim")
geometry_folder = os.path.join(repo_folder, "Geometry")

# 2. Verificar archivos críticos
if not os.path.exists(model_file):
    print(f"ERROR CRÍTICO: No encuentro el modelo en: {model_file}")
    sys.exit(1)

if not os.path.exists(geometry_folder):
    print(f"ERROR CRÍTICO: No encuentro la carpeta de huesos en: {geometry_folder}")
    sys.exit(1)

# 3. TRUCO IMPORTANTE: Añadir la ruta de los huesos AL SISTEMA
# Esto hace que OpenSim sepa dónde buscar los archivos .vtp
print(f"Añadiendo ruta de geometría: {geometry_folder}")
osim.ModelVisualizer.addDirToGeometrySearchPaths(geometry_folder)

# 4. Cargar el Modelo
print(f"Leyendo archivo: {os.path.basename(model_file)}...")
model = osim.Model(model_file)

# 5. Activar Visualizador (Modo Simple)
# Al compilar simbody manualmente, esto invocará al ejecutable automáticamente
model.setUseVisualizer(True)

# 6. Inicializar sistema
print("Inicializando sistema (esto puede tardar unos segundos)...")
state = model.initSystem()
manager = osim.Manager(model)
state.setTime(0)
manager.initialize(state)

print("------------------------------------------------")
print("¡SIMULACIÓN EN MARCHA!")
print("Si todo ha ido bien, verás una ventana llamada 'Simbody Visualizer'")
print("con el brazo cayendo.")
print("------------------------------------------------")

# 7. Simular 4 segundos
manager.integrate(4.0)

print("Fin de la simulación.")

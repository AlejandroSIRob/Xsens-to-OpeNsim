import opensim as osim
import os
import sys

print("--- CARGANDO MODELO RAJAGOPAL (MODO ESTATUA) ---")

# 1. Definir rutas
home_dir = os.path.expanduser("~")
repo_folder = os.path.join(home_dir, "/home/ubuntu/Desktop/OpenSim/")
# Usamos el modelo Rajagopal que ya viste que funciona
model_file = os.path.join(repo_folder, "conversion/Resultados_Linux/modelo_calibrado.osim")
geometry_folder = os.path.join(repo_folder, "Geometry")

# 2. Verificar archivos
if not os.path.exists(model_file):
    print(f"ERROR CRÍTICO: No encuentro el modelo en: {model_file}")
    sys.exit(1)

# 3. Configurar geometría
print(f"Añadiendo ruta de geometría: {geometry_folder}")
osim.ModelVisualizer.addDirToGeometrySearchPaths(geometry_folder)

# 4. Cargar el Modelo
print(f"Leyendo archivo: {os.path.basename(model_file)}...")
model = osim.Model(model_file)

# --- NUEVO: BLOQUEAR ARTICULACIONES PARA QUE NO SE CAIGA ---
print("Bloqueando articulaciones (Freeze) para inspección...")
coordSet = model.getCoordinateSet()
for i in range(coordSet.getSize()):
    coord = coordSet.get(i)
    # Bloqueamos (Locked = True) para que sea una estatua
    coord.setDefaultLocked(True)
# -----------------------------------------------------------

# 5. Activar Visualizador
model.setUseVisualizer(True)

# 6. Inicializar sistema
print("Inicializando sistema...")
state = model.initSystem()
manager = osim.Manager(model)
state.setTime(0)
manager.initialize(state)

print("------------------------------------------------")
print("¡VISUALIZADOR LISTO!")
print("El modelo debería aparecer DE PIE y quieto.")
print("------------------------------------------------")

# 7. Simular (Ahora no caerá)
manager.integrate(4.0)

print("Fin de la simulación.")

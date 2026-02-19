# Xsens to OpenSim: Pipeline de Procesamiento Biomecánico



Este repositorio contiene un flujo de trabajo completo (pipeline) automatizado con Python para transformar datos cinemáticos crudos obtenidos de sensores inerciales **Xsens Awinda**, convertirlos a formatos compatibles con **OpenSim**, calibrar un modelo musculoesquelético y resolver la Cinemática Inversa (Inverse Kinematics) para visualizar el movimiento en 3D.


## ⚙️ Requisitos y Dependencias

Para ejecutar los scripts de este repositorio, necesitas:
* **Python 3.x**
* **OpenSim API para Python** (Módulo `opensim`)
* **Librerías de procesamiento numérico:** `pandas`, `numpy`, `scipy`.

## 🚀 Flujo de Trabajo (Workflow)

El procesamiento se divide en dos fases automatizadas por dos scripts principales ubicados en `OpenSim/conversion/`.

### 1. Conversión de Datos (`conversion.py` / `conversion_Linux.py`)
Este script actúa como traductor entre el hardware físico (Xsens) y el software de simulación (OpenSim).
* **Lectura de datos:** Lee múltiples archivos `.txt` generados por el MT Manager de Xsens. Detecta automáticamente el inicio de los datos omitiendo los encabezados mediante la búsqueda de la columna `PacketCounter`.
* **Mapeo de Sensores:** Utiliza un diccionario interno para asociar el MAC/ID único de cada sensor Xsens con un "Virtual IMU" en el modelo de OpenSim (ej. `10B41517` -> `pelvis_imu`).
* **Gestión del Tiempo:** Convierte los incrementos de los paquetes en una línea de tiempo continua basada en la frecuencia de muestreo (por defecto, 60 Hz).
* **Conversión de Orientación:** Es capaz de ingerir cuaterniones directos (`Quat_q0`, etc.) o ángulos de Euler (`Roll`, `Pitch`, `Yaw`), transformando estos últimos a cuaterniones usando `scipy.spatial.transform` para asegurar la compatibilidad matemática.
* **Alineación temporal:** Une los datos asíncronos de todos los sensores en un único DataFrame ordenado temporalmente usando `pd.merge_asof`, generando un archivo de salida estándar `xsens_converted_data.sto`.

### 2. Procesamiento Biomecánico (`procesado-completo.py`)
Una vez generados los cuaterniones en el archivo `.sto`, este script utiliza la API de OpenSim para realizar la simulación biomecánica.
* **Calibración (`IMUPlacer`):** Toma el modelo `Rajagopal_Unificado.osim` y calcula las rotaciones relativas (offsets) entre los sensores físicos (orientación IMU) y los huesos virtuales (orientación del cuerpo). Devuelve un nuevo modelo calibrado (`modelo_calibrado.osim`).
* **Cinemática Inversa (`IMUInverseKinematicsTool`):** Resuelve los ángulos de las articulaciones fotograma a fotograma para que el modelo digital siga la orientación dictada por los sensores inerciales. Exporta los resultados a un archivo `.mot` (motion).
* **Visualización en tiempo real:** Implementa una ventana interactiva usando `SimbodyVisualizer`. Para evitar la ralentización típica de la API visual de OpenSim, el código implementa un sistema inteligente de "salto de frames" (renderizando 1 de cada 4 fotogramas) manteniendo la reproducción fluida.

## 🔧 Personalización del Mapeo de Sensores

Si cambias la disposición física de los sensores en el sujeto (por ejemplo, mover el sensor del torso a las manos), debes editar el diccionario `sensor_mapping` dentro del archivo `conversion.py`.

Asegúrate de que la clave (`'10B4XXXX'`) coincida con tu sensor físico, y el valor (`'nombre_imu'`) coincida exactamente con el sufijo `_imu` de los cuerpos (bodies) definidos en tu archivo `.osim`.

## ▶️ Ejecución Básica

1. Coloca tus archivos `.txt` exportados de Xsens en la carpeta configurada (ej. `OpenSim/conversion/Sin-Manos`).
2. Actualiza la ruta `carpeta` dentro de `conversion.py`.
3. Ejecuta la conversión:
   ```bash
   python conversion.py
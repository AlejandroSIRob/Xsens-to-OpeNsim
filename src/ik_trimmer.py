"""
Módulo para recortar archivos de cinemática inversa (IK) en múltiples segmentos
Mantiene la estructura correcta de los archivos .mot y respeta el formato OpenSim
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union


def trim_ik_segment(
    input_path: str,
    start_time: float,
    end_time: float,
    output_path: Optional[str] = None,
    segment_name: Optional[str] = None,
    reset_time: bool = True
) -> Optional[str]:
    """
    Recorta un segmento de un archivo de cinemática inversa (.mot)
    
    Args:
        input_path: Ruta al archivo .mot original
        start_time: Tiempo de inicio en segundos (float)
        end_time: Tiempo de fin en segundos (float)
        output_path: Ruta de salida (opcional, si no se proporciona se genera automática)
        segment_name: Nombre personalizado para el segmento (opcional)
        reset_time: Si True, reinicia el tiempo a 0 en el segmento recortado
    
    Returns:
        Ruta del archivo generado o None si falló
    """
    
    # Asegurar que los tiempos son floats
    try:
        start_time = float(start_time)
        end_time = float(end_time)
    except (ValueError, TypeError) as e:
        print(f"    Error: No se pudieron convertir los tiempos a float: {start_time}, {end_time}")
        print(f"    Error: {e}")
        return None
    
    # Verificar que el archivo existe
    if not os.path.exists(input_path):
        print(f"Error: El archivo {input_path} no existe")
        return None
    
    # Validar tiempos
    if start_time >= end_time:
        print(f"    Error: Tiempo de inicio ({start_time:.3f}s) debe ser menor que tiempo de fin ({end_time:.3f}s)")
        return None
    
    nombre_original = os.path.basename(input_path)
    print(f"\n  Procesando: {nombre_original}")
    print(f"    Segmento: {start_time:.3f}s - {end_time:.3f}s")
    
    # Leer el archivo línea por línea para separar cabecera y datos
    with open(input_path, 'r') as f:
        lineas = f.readlines()
    
    # Encontrar dónde termina la cabecera
    idx_endheader = None
    for i, linea in enumerate(lineas):
        if 'endheader' in linea.lower():
            idx_endheader = i
            break
    
    if idx_endheader is None:
        print(f"    Error: No se encontró 'endheader' en {nombre_original}")
        return None
    
    # Separar cabecera y datos
    cabecera = lineas[:idx_endheader+1]
    datos_lineas = lineas[idx_endheader+1:]
    
    # Extraer nombres de columnas
    nombres_columnas = [col.strip() for col in datos_lineas[0].strip().split('\t')]
    
    # Leer los datos numéricos
    datos = []
    for linea in datos_lineas[1:]:
        if linea.strip():
            valores = linea.strip().split('\t')
            try:
                valores_float = [float(v) for v in valores]
                datos.append(valores_float)
            except ValueError as e:
                print(f"    Advertencia: No se pudo convertir línea: {e}")
                continue
    
    if not datos:
        print(f"    Error: No se pudieron leer datos numéricos")
        return None
    
    # Crear DataFrame
    df = pd.DataFrame(datos, columns=nombres_columnas)
    
    # Verificar que la columna 'time' existe
    if 'time' not in df.columns:
        print(f"    Error: No se encontró la columna 'time'")
        print(f"    Columnas disponibles: {list(df.columns)}")
        return None
    
    # Mostrar información del archivo original
    tiempo_min = float(df['time'].min())
    tiempo_max = float(df['time'].max())
    print(f"    Original: {len(df)} frames, rango {tiempo_min:.3f}-{tiempo_max:.3f}s")
    
    # Verificar que el rango solicitado está dentro del rango disponible
    if start_time < tiempo_min:
        print(f"    Advertencia: Inicio {start_time:.3f}s es anterior al inicio del archivo ({tiempo_min:.3f}s)")
        print(f"    Ajustando a {tiempo_min:.3f}s")
        start_time = tiempo_min
    
    if end_time > tiempo_max:
        print(f"    Advertencia: Fin {end_time:.3f}s es posterior al fin del archivo ({tiempo_max:.3f}s)")
        print(f"    Ajustando a {tiempo_max:.3f}s")
        end_time = tiempo_max
    
    # Filtrar por tiempo
    df_filtrado = df[(df['time'] >= start_time) & (df['time'] <= end_time)].copy()
    
    if len(df_filtrado) == 0:
        print(f"    Error: No hay datos en el rango {start_time:.3f}-{end_time:.3f}")
        return None
    
    # Reindexar timestamps desde 0 si se solicita
    if reset_time:
        df_filtrado['time'] = df_filtrado['time'] - start_time
    
    duracion = float(df_filtrado['time'].max())
    print(f"    Segmento: {len(df_filtrado)} frames, duración {duracion:.3f}s")
    
    # Determinar nombre de archivo de salida
    if output_path:
        ruta_salida = output_path
    else:
        directorio_base = Path(input_path).parent
        nombre_base = os.path.splitext(nombre_original)[0]
        
        if segment_name:
            # Limpiar nombre para evitar caracteres inválidos
            clean_name = "".join(c for c in str(segment_name) if c.isalnum() or c in "._-")
            nombre_salida = f"{clean_name}.mot"
        else:
            # Generar nombre automático
            nombre_salida = f"{nombre_base}_seg_{start_time:.1f}_{end_time:.1f}.mot"
        
        ruta_salida = directorio_base / nombre_salida
    
    # Asegurar que el directorio de salida existe
    output_dir = os.path.dirname(ruta_salida)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Escribir archivo con cabecera y datos procesados
    try:
        with open(ruta_salida, 'w') as f:
            # Escribir cabecera
            for linea in cabecera:
                # Mantener la cabecera tal cual, pero podemos actualizar la versión si es necesario
                if 'version=' in linea and not 'OpenSimVersion' in linea:
                    f.write("version=3\n")
                elif 'OpenSimVersion' in linea:
                    f.write("OpenSimVersion=4.5-2023-11-26-efcdfd3eb\n")
                else:
                    f.write(linea)
            
            # Escribir nombres de columnas
            f.write('\t'.join(nombres_columnas) + '\n')
            
            # Escribir datos con formato adecuado
            for idx, row in df_filtrado.iterrows():
                valores_formateados = []
                for col in nombres_columnas:
                    valor = row[col]
                    # Usar notación científica para valores muy pequeños
                    if abs(valor) < 1e-10 and valor != 0:
                        valores_formateados.append(f"{valor:.6e}")
                    else:
                        valores_formateados.append(f"{valor:.15f}")
                f.write('\t'.join(valores_formateados) + '\n')
        
        print(f"    ✓ Guardado: {ruta_salida}")
        return str(ruta_salida)
        
    except Exception as e:
        print(f"    Error al escribir archivo: {e}")
        return None


def trim_ik_multiple_segments(
    input_path: str,
    segments: List[Dict[str, Union[float, str]]],
    output_dir: Optional[str] = None,
    reset_time: bool = True
) -> List[str]:
    """
    Recorta múltiples segmentos de un mismo archivo IK
    
    Args:
        input_path: Ruta al archivo .mot original
        segments: Lista de diccionarios con 'start', 'end' y opcionalmente 'name'
        output_dir: Directorio de salida (opcional, por defecto mismo que el original)
        reset_time: Si True, reinicia el tiempo a 0 en cada segmento
    
    Returns:
        Lista de rutas de archivos generados
    """
    
    resultados = []
    
    for i, segment in enumerate(segments):
        # IMPORTANTE: Convertir explícitamente a float
        try:
            start_time = float(segment.get('start', 0))
            end_time = float(segment.get('end', 0))
        except (ValueError, TypeError) as e:
            print(f"Error: Segmento {i+1} - No se pudieron convertir los tiempos a float: {e}")
            print(f"  Valores recibidos: start={segment.get('start')}, end={segment.get('end')}")
            continue
        
        name = segment.get('name', f"segment_{i+1}")
        
        print(f"\n--- Procesando segmento {i+1} ---")
        print(f"  Nombre: {name}")
        print(f"  Inicio (raw): {segment.get('start')} -> float: {start_time}")
        print(f"  Fin (raw): {segment.get('end')} -> float: {end_time}")
        
        # Validar segmento
        if start_time is None or end_time is None:
            print(f"Error: Segmento {i+1} sin start_time o end_time")
            continue
        
        # Asegurar que start_time < end_time
        if start_time >= end_time:
            print(f"Error: Segmento {i+1} tiene inicio ({start_time}) >= fin ({end_time})")
            print(f"  Esto no está permitido.")
            continue  # No intercambiar automáticamente, mostrar error claro
        
        # Determinar ruta de salida
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            # Limpiar nombre para evitar caracteres inválidos
            clean_name = "".join(c for c in str(name) if c.isalnum() or c in "._-")
            output_path = os.path.join(output_dir, f"{clean_name}.mot")
        else:
            output_path = None  # Se generará automáticamente
        
        resultado = trim_ik_segment(
            input_path=input_path,
            start_time=start_time,
            end_time=end_time,
            output_path=output_path,
            segment_name=name,
            reset_time=reset_time
        )
        
        if resultado:
            resultados.append(resultado)
    
    return resultados


def trim_ik_batch(
    config_path: str,
    output_dir: Optional[str] = None,
    reset_time: bool = True
) -> Dict[str, List[str]]:
    """
    Procesa un lote de archivos según configuración JSON
    
    Formato del JSON:
    {
        "carpeta_raiz": "/ruta/base",  # Opcional
        "archivos": [
            {
                "ruta": "ruta/archivo1.mot",
                "segmentos": [
                    {"start": 0.5, "end": 2.5, "name": "movimiento1"},
                    {"start": 3.0, "end": 5.0, "name": "movimiento2"}
                ]
            }
        ]
    }
    
    Args:
        config_path: Ruta al archivo JSON de configuración
        output_dir: Directorio base de salida (opcional)
        reset_time: Si True, reinicia el tiempo a 0 en cada segmento
    
    Returns:
        Diccionario con rutas de archivos generados por archivo original
    """
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    carpeta_raiz = config.get('carpeta_raiz', None)
    resultados = {}
    
    print(f"\n{'='*60}")
    print("PROCESANDO LOTE DE ARCHIVOS IK")
    print(f"{'='*60}\n")
    
    for idx, item in enumerate(config['archivos'], 1):
        # Determinar la ruta completa del archivo
        if 'ruta' in item:
            ruta_archivo = item['ruta']
        elif 'nombre' in item and carpeta_raiz:
            ruta_archivo = os.path.join(carpeta_raiz, item['nombre'])
        else:
            print(f"Error: Elemento sin ruta válida: {item}")
            continue
        
        # Verificar que el archivo existe
        if not os.path.exists(ruta_archivo):
            print(f"Advertencia: Archivo no encontrado: {ruta_archivo}")
            continue
        
        # Obtener segmentos
        segmentos = item.get('segmentos', [])
        if not segmentos:
            print(f"Advertencia: No hay segmentos definidos para {ruta_archivo}")
            continue
        
        print(f"\n[{idx}] Archivo: {os.path.basename(ruta_archivo)}")
        print(f"    Segmentos: {len(segmentos)}")
        
        # Mostrar segmentos con sus tipos
        for s in segmentos:
            start_raw = s.get('start', '?')
            end_raw = s.get('end', '?')
            name = s.get('name', 'sin_nombre')
            print(f"      - {name}: {start_raw} (type: {type(start_raw).__name__}) - {end_raw} (type: {type(end_raw).__name__})")
        
        # Determinar directorio de salida para este archivo
        if output_dir:
            # Crear subdirectorio basado en el nombre del archivo
            nombre_base = os.path.splitext(os.path.basename(ruta_archivo))[0]
            out_dir_archivo = os.path.join(output_dir, nombre_base)
        else:
            out_dir_archivo = None
        
        # Procesar segmentos
        resultados[ruta_archivo] = trim_ik_multiple_segments(
            input_path=ruta_archivo,
            segments=segmentos,
            output_dir=out_dir_archivo,
            reset_time=reset_time
        )
    
    # Resumen final
    print(f"\n{'='*60}")
    print("RESUMEN DE PROCESAMIENTO")
    print(f"{'='*60}")
    total_archivos = len([v for v in resultados.values() if v])
    total_segmentos = sum(len(v) for v in resultados.values())
    print(f"Archivos procesados: {total_archivos}/{len(config['archivos'])}")
    print(f"Segmentos generados: {total_segmentos}")
    
    return resultados


def generate_config_from_folder(
    folder_path: str,
    start_time: float = 0.0,
    end_time: float = 1.0,
    pattern: str = "*.mot",
    output_json: str = "trim_config.json"
) -> Optional[str]:
    """
    Genera automáticamente un archivo JSON de configuración a partir de una carpeta
    
    Args:
        folder_path: Carpeta donde buscar archivos .mot
        start_time: Tiempo de inicio por defecto
        end_time: Tiempo de fin por defecto
        pattern: Patrón de búsqueda de archivos
        output_json: Ruta del archivo JSON de salida
    
    Returns:
        Ruta del archivo JSON generado o None si falló
    """
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: La carpeta {folder_path} no existe")
        return None
    
    # Buscar archivos que coincidan con el patrón
    archivos = list(folder.rglob(pattern))
    
    if not archivos:
        print(f"No se encontraron archivos con patrón '{pattern}' en {folder_path}")
        return None
    
    # Crear configuración
    config = {
        "carpeta_raiz": str(folder),
        "archivos": []
    }
    
    for archivo in archivos:
        # Obtener ruta relativa
        try:
            ruta_relativa = archivo.relative_to(folder)
        except ValueError:
            ruta_relativa = archivo
        
        # Generar nombre de segmento basado en el nombre del archivo
        nombre_base = archivo.stem
        
        config["archivos"].append({
            "nombre": str(ruta_relativa),
            "segmentos": [
                {
                    "start": float(start_time),  # Asegurar que es float
                    "end": float(end_time),      # Asegurar que es float
                    "name": nombre_base
                }
            ]
        })
    
    # Guardar JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print(f"✓ Archivo JSON generado: {output_json}")
    print(f"  Archivos encontrados: {len(archivos)}")
    print(f"  Tiempos por defecto: {start_time}s - {end_time}s")
    
    return output_json


def get_file_info(file_path: str) -> Dict:
    """
    Obtiene información de un archivo IK sin cargarlo completamente
    
    Args:
        file_path: Ruta al archivo .mot
    
    Returns:
        Diccionario con información del archivo
    """
    if not os.path.exists(file_path):
        return {'error': 'File not found'}
    
    try:
        with open(file_path, 'r') as f:
            lineas = f.readlines()
        
        # Encontrar cabecera
        idx_endheader = None
        for i, linea in enumerate(lineas):
            if 'endheader' in linea.lower():
                idx_endheader = i
                break
        
        if idx_endheader is None:
            return {'error': 'No endheader found'}
        
        # Extraer nombres de columnas
        datos_lineas = lineas[idx_endheader+1:]
        nombres_columnas = [col.strip() for col in datos_lineas[0].strip().split('\t')]
        
        # Leer primera y última fila de datos
        datos = []
        for linea in datos_lineas[1:]:
            if linea.strip():
                valores = linea.strip().split('\t')
                try:
                    datos.append([float(v) for v in valores])
                except:
                    continue
                if len(datos) >= 2:  # Solo necesitamos primero y último
                    pass
        
        if not datos:
            return {'error': 'No data found'}
        
        # Obtener primera y última fila
        primera_fila = datos[0]
        ultima_fila = datos[-1]
        
        # Encontrar índice de la columna time
        time_idx = None
        for i, col in enumerate(nombres_columnas):
            if col.strip() == 'time':
                time_idx = i
                break
        
        if time_idx is None:
            return {'error': 'No time column found'}
        
        return {
            'filename': os.path.basename(file_path),
            'num_frames': len(datos),
            'num_columns': len(nombres_columnas),
            'time_start': primera_fila[time_idx],
            'time_end': ultima_fila[time_idx],
            'duration': ultima_fila[time_idx] - primera_fila[time_idx],
            'columns': nombres_columnas[:10]  # Solo primeras 10 columnas para no saturar
        }
        
    except Exception as e:
        return {'error': str(e)}


def main():
    """Función principal para uso desde línea de comandos"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Recortador de archivos de cinemática inversa (IK)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Generar configuración desde carpeta
  python -m src.ik_trimmer --generate-config /ruta/carpeta --output config.json
  
  # Procesar desde configuración
  python -m src.ik_trimmer --config config.json --output-dir /ruta/salida
  
  # Procesar archivo individual con múltiples segmentos
  python -m src.ik_trimmer --archivo archivo.mot --segmentos "0.5-2.5:mov1" "3.0-5.0:mov2"
  
  # Obtener información del archivo
  python -m src.ik_trimmer --info archivo.mot
        """
    )
    
    parser.add_argument('--config', '-c', type=str, help='Archivo JSON de configuración')
    parser.add_argument('--archivo', '-a', type=str, help='Archivo específico a procesar')
    parser.add_argument('--segmentos', '-s', nargs='+', 
                       help='Segmentos en formato "inicio-fin:nombre" (ej: "0.5-2.5:movimiento")')
    parser.add_argument('--generate-config', '-g', type=str, 
                       help='Generar configuración desde carpeta')
    parser.add_argument('--output-dir', '-o', type=str, help='Directorio de salida')
    parser.add_argument('--output-json', type=str, default='trim_config.json',
                       help='Archivo JSON de salida para --generate-config')
    parser.add_argument('--start', type=float, default=0.0,
                       help='Tiempo de inicio por defecto (para --generate-config)')
    parser.add_argument('--end', type=float, default=1.0,
                       help='Tiempo de fin por defecto (para --generate-config)')
    parser.add_argument('--pattern', type=str, default='*.mot',
                       help='Patrón de búsqueda (para --generate-config)')
    parser.add_argument('--no-reset-time', action='store_true',
                       help='No reiniciar el tiempo a 0 en los segmentos')
    parser.add_argument('--info', type=str, help='Mostrar información del archivo')
    
    args = parser.parse_args()
    
    reset_time = not args.no_reset_time
    
    if args.info:
        # Mostrar información del archivo
        info = get_file_info(args.info)
        print("\n" + "="*60)
        print("INFORMACIÓN DEL ARCHIVO IK")
        print("="*60)
        for key, value in info.items():
            print(f"  {key}: {value}")
        print("="*60)
    
    elif args.generate_config:
        # Generar configuración desde carpeta
        generate_config_from_folder(
            folder_path=args.generate_config,
            start_time=args.start,
            end_time=args.end,
            pattern=args.pattern,
            output_json=args.output_json
        )
    
    elif args.config:
        # Procesar desde archivo JSON
        trim_ik_batch(
            config_path=args.config,
            output_dir=args.output_dir,
            reset_time=reset_time
        )
    
    elif args.archivo and args.segmentos:
        # Procesar archivo individual con segmentos
        segments = []
        for seg in args.segmentos:
            # Parsear formato "inicio-fin:nombre"
            if ':' in seg:
                tiempo_part, nombre = seg.rsplit(':', 1)
            else:
                tiempo_part, nombre = seg, None
            
            if '-' in tiempo_part:
                start_str, end_str = tiempo_part.split('-')
                try:
                    start = float(start_str)
                    end = float(end_str)
                except ValueError:
                    print(f"Error: No se pudieron convertir los tiempos en: {seg}")
                    continue
            else:
                print(f"Error: Formato inválido para segmento: {seg}")
                continue
            
            # Asegurar que start < end
            if start > end:
                print(f"Advertencia: Inicio ({start}) > fin ({end}) en segmento '{nombre}', intercambiando...")
                start, end = end, start
            
            segments.append({
                'start': start,
                'end': end,
                'name': nombre
            })
        
        trim_ik_multiple_segments(
            input_path=args.archivo,
            segments=segments,
            output_dir=args.output_dir,
            reset_time=reset_time
        )
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

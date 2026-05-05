"""
Module to trim Inverse Kinematics (IK) files into multiple segments.
Maintains the correct structure of .mot files and respects the OpenSim format.
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
    Trims a segment from an inverse kinematics (.mot) file.
    
    Args:
        input_path: Path to the original .mot file
        start_time: Start time in seconds (float)
        end_time: End time in seconds (float)
        output_path: Output path (optional, auto-generated if not provided)
        segment_name: Custom name for the segment (optional)
        reset_time: If True, resets the time to 0 in the trimmed segment
    
    Returns:
        Path to the generated file or None if it failed
    """
    
    # Ensure times are floats
    try:
        start_time = float(start_time)
        end_time = float(end_time)
    except (ValueError, TypeError) as e:
        print(f"    Error: Could not convert times to float: {start_time}, {end_time}")
        print(f"    Error: {e}")
        return None
    
    # Verify the file exists
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} does not exist")
        return None
    
    # Validate times
    if start_time >= end_time:
        print(f"    Error: Start time ({start_time:.3f}s) must be less than end time ({end_time:.3f}s)")
        return None
    
    nombre_original = os.path.basename(input_path)
    print(f"\n  Processing: {nombre_original}")
    print(f"    Segment: {start_time:.3f}s - {end_time:.3f}s")
    
    # Read the file line by line to separate header and data
    with open(input_path, 'r') as f:
        lineas = f.readlines()
    
    # Find where the header ends
    idx_endheader = None
    for i, linea in enumerate(lineas):
        if 'endheader' in linea.lower():
            idx_endheader = i
            break
    
    if idx_endheader is None:
        print(f"    Error: 'endheader' not found in {nombre_original}")
        return None
    
    # Separate header and data
    cabecera = lineas[:idx_endheader+1]
    datos_lineas = lineas[idx_endheader+1:]
    
    # Extract column names
    nombres_columnas = [col.strip() for col in datos_lineas[0].strip().split('\t')]
    
    # Read numeric data
    datos = []
    for linea in datos_lineas[1:]:
        if linea.strip():
            valores = linea.strip().split('\t')
            try:
                valores_float = [float(v) for v in valores]
                datos.append(valores_float)
            except ValueError as e:
                print(f"    Warning: Could not convert line: {e}")
                continue
    
    if not datos:
        print(f"    Error: Could not read numeric data")
        return None
    
    # Create DataFrame
    df = pd.DataFrame(datos, columns=nombres_columnas)
    
    # Verify 'time' column exists
    if 'time' not in df.columns:
        print(f"    Error: 'time' column not found")
        print(f"    Available columns: {list(df.columns)}")
        return None
    
    # Show original file information
    tiempo_min = float(df['time'].min())
    tiempo_max = float(df['time'].max())
    print(f"    Original: {len(df)} frames, range {tiempo_min:.3f}-{tiempo_max:.3f}s")
    
    # Verify the requested range is within the available range
    if start_time < tiempo_min:
        print(f"    Warning: Start {start_time:.3f}s is before file start ({tiempo_min:.3f}s)")
        print(f"    Adjusting to {tiempo_min:.3f}s")
        start_time = tiempo_min
    
    if end_time > tiempo_max:
        print(f"    Warning: End {end_time:.3f}s is after file end ({tiempo_max:.3f}s)")
        print(f"    Adjusting to {tiempo_max:.3f}s")
        end_time = tiempo_max
    
    # Filter by time
    df_filtrado = df[(df['time'] >= start_time) & (df['time'] <= end_time)].copy()
    
    if len(df_filtrado) == 0:
        print(f"    Error: No data in range {start_time:.3f}-{end_time:.3f}")
        return None
    
    # Reindex timestamps from 0 if requested
    if reset_time:
        df_filtrado['time'] = df_filtrado['time'] - start_time
    
    duracion = float(df_filtrado['time'].max())
    print(f"    Segment: {len(df_filtrado)} frames, duration {duracion:.3f}s")
    
    # Determine output file name
    if output_path:
        ruta_salida = output_path
    else:
        directorio_base = Path(input_path).parent
        nombre_base = os.path.splitext(nombre_original)[0]
        
        if segment_name:
            # Clean name to avoid invalid characters
            clean_name = "".join(c for c in str(segment_name) if c.isalnum() or c in "._-")
            nombre_salida = f"{clean_name}.mot"
        else:
            # Generate automatic name
            nombre_salida = f"{nombre_base}_seg_{start_time:.1f}_{end_time:.1f}.mot"
            
        ruta_salida = directorio_base / nombre_salida
    
    # Ensure output directory exists
    output_dir = os.path.dirname(ruta_salida)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Write file with header and processed data
    try:
        with open(ruta_salida, 'w') as f:
            # Write header
            for linea in cabecera:
                # Keep header as is, but we can update the version if needed
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
        
        print(f"    ✓ Saved: {ruta_salida}")
        return str(ruta_salida)
        
    except Exception as e:
        print(f"    Error writing file: {e}")
        return None


def trim_ik_multiple_segments(
    input_path: str,
    segments: List[Dict[str, Union[float, str]]],
    output_dir: Optional[str] = None,
    reset_time: bool = True
) -> List[str]:
    """
    Trims multiple segments from the same IK file.
    
    Args:
        input_path: Path to original .mot file
        segments: List of dictionaries with 'start', 'end' and optionally 'name'
        output_dir: Output directory (optional, default is same as original)
        reset_time: If True, resets time to 0 in each segment
    
    Returns:
        List of generated file paths
    """
    
    resultados = []
    
    for i, segment in enumerate(segments):
        # IMPORTANT: Convert explicitly to float
        try:
            start_time = float(segment.get('start', 0))
            end_time = float(segment.get('end', 0))
        except (ValueError, TypeError) as e:
            print(f"Error: Segment {i+1} - Could not convert times to float: {e}")
            print(f"  Values received: start={segment.get('start')}, end={segment.get('end')}")
            continue
        
        name = segment.get('name', f"segment_{i+1}")
        
        print(f"\n--- Processing segment {i+1} ---")
        print(f"  Name: {name}")
        print(f"  Start (raw): {segment.get('start')} -> float: {start_time}")
        print(f"  End (raw): {segment.get('end')} -> float: {end_time}")
        
        # Validate segment
        if start_time is None or end_time is None:
            print(f"Error: Segment {i+1} missing start_time or end_time")
            continue
        
        # Ensure start_time < end_time
        if start_time >= end_time:
            print(f"Error: Segment {i+1} has start ({start_time}) >= end ({end_time})")
            print(f"  This is not allowed.")
            continue  # Do not swap automatically, show clear error
        
        # Determine output path
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            # Clean name to avoid invalid characters
            clean_name = "".join(c for c in str(name) if c.isalnum() or c in "._-")
            output_path = os.path.join(output_dir, f"{clean_name}.mot")
        else:
            output_path = None  # Auto-generated
        
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
    Processes a batch of files according to JSON configuration
    
    JSON format:
    {
        "carpeta_raiz": "/ruta/base",  # Optional
        "archivos": [
            {
                "ruta": "ruta/archivo1.mot",
                "segmentos": [
                    {"start": 0.5, "end": 2.5, "name": "movement1"},
                    {"start": 3.0, "end": 5.0, "name": "movement2"}
                ]
            }
        ]
    }
    
    Args:
        config_path: Path to JSON config file
        output_dir: Base output directory (optional)
        reset_time: If True, resets time to 0 in each segment
    
    Returns:
        Dictionary with generated file paths by original file
    """
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    carpeta_raiz = config.get('carpeta_raiz', None)
    resultados = {}
    
    print(f"\n{'='*60}")
    print("PROCESSING BATCH OF IK FILES")
    print(f"{'='*60}\n")
    
    for idx, item in enumerate(config['archivos'], 1):
        # Determine full file path
        if 'ruta' in item:
            ruta_archivo = item['ruta']
        elif 'nombre' in item and carpeta_raiz:
            ruta_archivo = os.path.join(carpeta_raiz, item['nombre'])
        else:
            print(f"Error: Element without valid path: {item}")
            continue
        
        # Verify file exists
        if not os.path.exists(ruta_archivo):
            print(f"Warning: File not found: {ruta_archivo}")
            continue
        
        # Get segments
        segmentos = item.get('segmentos', [])
        if not segmentos:
            print(f"Warning: No segments defined for {ruta_archivo}")
            continue
        
        print(f"\n[{idx}] File: {os.path.basename(ruta_archivo)}")
        print(f"    Segments: {len(segmentos)}")
        
        # Show segments with types
        for s in segmentos:
            start_raw = s.get('start', '?')
            end_raw = s.get('end', '?')
            name = s.get('name', 'unnamed')
            print(f"      - {name}: {start_raw} (type: {type(start_raw).__name__}) - {end_raw} (type: {type(end_raw).__name__})")
        
        # Determine output directory for this file
        if output_dir:
            # Extract relative path (date and version) from 'nombre' if available
            rel_path = ""
            if 'nombre' in item:
                rel_path = os.path.dirname(item['nombre'])
            elif carpeta_raiz and ruta_archivo.startswith(carpeta_raiz):
                rel_path = os.path.dirname(os.path.relpath(ruta_archivo, carpeta_raiz))
            
            # Create subdirectory preserving date and version
            if rel_path:
                out_dir_archivo = os.path.join(output_dir, rel_path)
            else:
                nombre_base = os.path.splitext(os.path.basename(ruta_archivo))[0]
                out_dir_archivo = os.path.join(output_dir, nombre_base)
        else:
            out_dir_archivo = None
        
        # Process segments
        resultados[ruta_archivo] = trim_ik_multiple_segments(
            input_path=ruta_archivo,
            segments=segmentos,
            output_dir=out_dir_archivo,
            reset_time=reset_time
        )
    
    # Final summary
    print(f"\n{'='*60}")
    print("PROCESSING SUMMARY")
    print(f"{'='*60}")
    total_archivos = len([v for v in resultados.values() if v])
    total_segmentos = sum(len(v) for v in resultados.values())
    print(f"Files processed: {total_archivos}/{len(config['archivos'])}")
    print(f"Segments generated: {total_segmentos}")
    
    return resultados


def generate_config_from_folder(
    folder_path: str,
    start_time: float = 0.0,
    end_time: float = 1.0,
    pattern: str = "*.mot",
    output_json: str = "trim_config.json"
) -> Optional[str]:
    """
    Automatically generates a JSON configuration file from a folder
    
    Args:
        folder_path: Folder to search for .mot files
        start_time: Default start time
        end_time: Default end time
        pattern: File search pattern
        output_json: Output JSON file path
    
    Returns:
        Path of the generated JSON file or None if failed
    """
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: Folder {folder_path} does not exist")
        return None
    
    # Search for files matching the pattern
    archivos = list(folder.rglob(pattern))
    
    if not archivos:
        print(f"No files found with pattern '{pattern}' in {folder_path}")
        return None
    
    # Create configuration
    config = {
        "carpeta_raiz": str(folder),
        "archivos": []
    }
    
    for archivo in archivos:
        # Get relative path
        try:
            ruta_relativa = archivo.relative_to(folder)
        except ValueError:
            ruta_relativa = archivo
        
        # Generate segment name based on file name
        nombre_base = archivo.stem
        
        config["archivos"].append({
            "nombre": str(ruta_relativa),
            "segmentos": [
                {
                    "start": float(start_time),  # Ensure it is a float
                    "end": float(end_time),      # Ensure it is a float
                    "name": nombre_base
                }
            ]
        })
    
    # Save JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print(f"✓ JSON file generated: {output_json}")
    print(f"  Files found: {len(archivos)}")
    print(f"  Default timings: {start_time}s - {end_time}s")
    
    return output_json


def get_file_info(file_path: str) -> Dict:
    """
    Gets information from an IK file without fully loading it
    
    Args:
        file_path: Path to .mot file
    
    Returns:
        Dictionary with file information
    """
    if not os.path.exists(file_path):
        return {'error': 'File not found'}
    
    try:
        with open(file_path, 'r') as f:
            lineas = f.readlines()
        
        # Find header
        idx_endheader = None
        for i, linea in enumerate(lineas):
            if 'endheader' in linea.lower():
                idx_endheader = i
                break
        
        if idx_endheader is None:
            return {'error': 'No endheader found'}
        
        # Extract column names
        datos_lineas = lineas[idx_endheader+1:]
        nombres_columnas = [col.strip() for col in datos_lineas[0].strip().split('\t')]
        
        # Read first and last row of data
        datos = []
        for linea in datos_lineas[1:]:
            if linea.strip():
                valores = linea.strip().split('\t')
                try:
                    datos.append([float(v) for v in valores])
                except:
                    continue
                if len(datos) >= 2:  # Only need first and last
                    pass
        
        if not datos:
            return {'error': 'No data found'}
        
        # Get first and last row
        primera_fila = datos[0]
        ultima_fila = datos[-1]
        
        # Find index of the time column
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
            'columns': nombres_columnas[:10]  # Only first 10 columns to avoid clutter
        }
        
    except Exception as e:
        return {'error': str(e)}


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Inverse Kinematics (IK) File Trimmer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  # Generate config from folder
  python -m src.ik_trimmer --generate-config /path/to/folder --output config.json
  
  # Process from configuration
  python -m src.ik_trimmer --config config.json --output-dir /output/path
  
  # Process single file with multiple segments
  python -m src.ik_trimmer --archivo file.mot --segmentos "0.5-2.5:mov1" "3.0-5.0:mov2"
  
  # Get file info
  python -m src.ik_trimmer --info file.mot
        """
    )
    
    parser.add_argument('--config', '-c', type=str,
                       default='/home/drims/simulation_projects/config_real.json',
                       help='JSON configuration file (default: /home/drims/simulation_projects/config_real.json)')
    parser.add_argument('--archivo', '-a', type=str, help='Specific file to process')
    parser.add_argument('--segmentos', '-s', nargs='+', 
                       help='Segments in "start-end:name" format (e.g., "0.5-2.5:movement")')
    parser.add_argument('--generate-config', '-g', type=str, 
                       help='Generate configuration from folder')
    parser.add_argument('--output-dir', '-o', type=str,
                       default='/home/drims/data/dataset_processing/Inverse_Kinematics_Opensim/Segmented_Trajectory/IK_segmented_trajectory',
                       help='Output directory (default: /home/drims/data/dataset_processing/Inverse_Kinematics_Opensim/Segmented_Trajectory/IK_segmented_trajectory)')
    parser.add_argument('--output-json', type=str, default='trim_config.json',
                       help='Output JSON file for --generate-config')
    parser.add_argument('--start', type=float, default=0.0,
                       help='Default start time (for --generate-config)')
    parser.add_argument('--end', type=float, default=1.0,
                       help='Default end time (for --generate-config)')
    parser.add_argument('--pattern', type=str, default='*.mot',
                       help='Search pattern (for --generate-config)')
    parser.add_argument('--no-reset-time', action='store_true',
                       help='Do not reset time to 0 in segments')
    parser.add_argument('--info', type=str, help='Show file information')
    
    args = parser.parse_args()
    
    reset_time = not args.no_reset_time
    
    if args.info:
        # Show file information
        info = get_file_info(args.info)
        print("\n" + "="*60)
        print("IK FILE INFORMATION")
        print("="*60)
        for key, value in info.items():
            print(f"  {key}: {value}")
        print("="*60)
    
    elif args.generate_config:
        # Generate configuration from folder
        generate_config_from_folder(
            folder_path=args.generate_config,
            start_time=args.start,
            end_time=args.end,
            pattern=args.pattern,
            output_json=args.output_json
        )
    
    elif args.archivo and args.segmentos:
        # Process individual file with segments
        segments = []
        for seg in args.segmentos:
            # Parse format "start-end:name"
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
                    print(f"Error: Could not convert times in: {seg}")
                    continue
            else:
                print(f"Error: Invalid format for segment: {seg}")
                continue
            
            # Ensure start < end
            if start > end:
                print(f"Warning: Start ({start}) > end ({end}) in segment '{nombre}', swapping...")
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
    
    elif args.config:
        # Process from JSON file
        print(f"\nUsing JSON configuration file: {args.config}")
        print(f"Using output directory: {args.output_dir}")
        
        trim_ik_batch(
            config_path=args.config,
            output_dir=args.output_dir,
            reset_time=reset_time
        )
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

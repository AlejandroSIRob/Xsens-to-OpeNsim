#!/usr/bin/env python3
"""
Script para generar automáticamente configuración de recorte desde una carpeta
Ejecutar desde la raíz del repositorio: python linux/generate_trim_config.py /ruta/carpeta
"""

import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ik_trimmer import generate_config_from_folder

def main():
    parser = argparse.ArgumentParser(
        description='Generar configuración de recorte desde carpeta',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python linux/generate_trim_config.py /ruta/carpeta --output config.json
  python linux/generate_trim_config.py /ruta/carpeta --start 0.5 --end 2.5 --pattern "ik_*.mot"
        """
    )
    parser.add_argument('carpeta', type=str, help='Carpeta con archivos .mot')
    parser.add_argument('--output', '-o', type=str, default='trim_config.json',
                       help='Archivo JSON de salida')
    parser.add_argument('--start', '-s', type=float, default=0.0,
                       help='Tiempo de inicio por defecto (segundos)')
    parser.add_argument('--end', '-e', type=float, default=1.0,
                       help='Tiempo de fin por defecto (segundos)')
    parser.add_argument('--pattern', '-p', type=str, default='*.mot',
                       help='Patrón de búsqueda de archivos')
    
    args = parser.parse_args()
    
    # Verificar que la carpeta existe
    if not os.path.exists(args.carpeta):
        print(f"Error: La carpeta {args.carpeta} no existe")
        sys.exit(1)
    
    result = generate_config_from_folder(
        folder_path=args.carpeta,
        start_time=args.start,
        end_time=args.end,
        pattern=args.pattern,
        output_json=args.output
    )
    
    if result:
        print(f"\nConfiguración guardada en: {result}")
    else:
        print("\nError al generar configuración")
        sys.exit(1)

if __name__ == "__main__":
    main()

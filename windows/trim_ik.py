#!/usr/bin/env python3
"""
Script de entrada para recortar archivos de cinemática inversa (Windows)
Ejecutar desde la raíz del repositorio: python windows/trim_ik.py [opciones]
"""

import sys
import os

# Añadir el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ik_trimmer import main

if __name__ == "__main__":
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("windows/config.yaml"):
        print("Advertencia: No se encuentra windows/config.yaml")
        print("Asegúrate de ejecutar este script desde la raíz del repositorio")
    
    main()

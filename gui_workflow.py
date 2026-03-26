#!/usr/bin/env python3
"""
Interfaz gráfica unificada para el pipeline Xsens-to-OpenSim
Detecta automáticamente el sistema operativo y muestra opciones apropiadas
"""

import sys
import os
import platform
import subprocess
import yaml
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import json

# Añadir src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src import xsens_parser, opensim_pipeline, data_utils

class WorkflowGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Xsens-to-OpenSim Workflow Controller")
        self.root.geometry("850x750")
        
        # Detectar sistema operativo
        self.os_type = platform.system().lower()
        if self.os_type == "windows":
            self.config_path = os.path.join("windows", "config.yaml")
            self.is_windows = True
            self.is_linux = False
        else:  # Linux / Darwin
            self.config_path = os.path.join("linux", "config.yaml")
            self.is_linux = True
            self.is_windows = False
        
        print(f"Sistema detectado: {platform.system()} - Usando {self.config_path}")
        
        # Cargar configuración por defecto
        self.load_config()
        
        # Variables para los campos
        self.create_variables()
        
        # Crear la interfaz
        self.create_widgets()
        
    def load_config(self):
        """Carga la configuración del archivo YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar {self.config_path}:\n{e}")
            self.config = {
                'paths': {},
                'settings': {'sampling_rate': 60.0},
                'opensim_settings': {}
            }
    
    def create_variables(self):
        """Crea las variables tkinter para los campos"""
        # Paths
        self.input_folder = tk.StringVar(value=self.config['paths'].get('input_folder', ''))
        self.output_folder = tk.StringVar(value=self.config['paths'].get('output_folder', ''))
        self.output_filename = tk.StringVar(value=self.config['paths'].get('output_filename', 'kinematics_v3.sto'))
        self.mapping_file = tk.StringVar(value=self.config['paths'].get('mapping_file', 'sensor_mapping.json'))
        self.model_path = tk.StringVar(value=self.config['paths'].get('model_path', 'models/Rajagopal_WithMuscles.osim'))
        self.geometry_path = tk.StringVar(value=self.config['paths'].get('geometry_path', 'models/Geometry'))
        
        # Settings
        self.sampling_rate = tk.DoubleVar(value=self.config['settings'].get('sampling_rate', 60.0))
        
        # OpenSim settings
        self.base_imu_label = tk.StringVar(value=self.config['opensim_settings'].get('base_imu_label', 'pelvis_imu'))
        self.base_heading_axis = tk.StringVar(value=self.config['opensim_settings'].get('base_heading_axis', 'z'))
        sensor_rot = self.config['opensim_settings'].get('sensor_to_opensim_rot', [-1.57079633, 0, 0])
        self.sensor_rot_x = tk.DoubleVar(value=sensor_rot[0])
        self.sensor_rot_y = tk.DoubleVar(value=sensor_rot[1])
        self.sensor_rot_z = tk.DoubleVar(value=sensor_rot[2])
        self.output_model_name = tk.StringVar(value=self.config['opensim_settings'].get('output_model_name', 'calibrated_model.osim'))
        
        # Opciones de flujo
        self.skip_packet_fix = tk.BooleanVar(value=False)
        self.skip_parsing = tk.BooleanVar(value=False)
        self.skip_imu_placer = tk.BooleanVar(value=False)
        self.skip_ik = tk.BooleanVar(value=False)
        
        # Opciones de MuJoCo
        self.do_mujoco = tk.BooleanVar(value=True)
        self.mujoco_output = tk.StringVar(value=self.config['paths'].get('mujoco_output_folder', '/home/drims/mujoco_output_folder' if self.is_linux else 'mujoco_model'))
        
        # Opciones de visualización (dependen del SO)
        if self.is_linux:
            self.visualization_mode = tk.StringVar(value="none")
        else:
            self.visualization_mode = tk.StringVar(value="none")
        
        # Variables para recorte de IK
        self.trim_input_file = tk.StringVar(value="")
        self.trim_output_dir = tk.StringVar(value="")
        self.trim_reset_time = tk.BooleanVar(value=True)
    
    def create_widgets(self):
        """Crea los widgets de la interfaz"""
        
        # Notebook para pestañas
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Pestaña principal
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Pipeline Principal")
        self.create_main_tab(main_frame)
        
        # Pestaña de configuración
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Configuración Avanzada")
        self.create_config_tab(config_frame)
        
        # Pestaña de ejecución
        run_frame = ttk.Frame(notebook)
        notebook.add(run_frame, text="Ejecutar")
        self.create_run_tab(run_frame)
        
        # Pestaña de recorte de IK
        trim_frame = ttk.Frame(notebook)
        notebook.add(trim_frame, text="Recorte IK")
        self.create_trim_tab(trim_frame)
        
        # Barra de estado
        self.status_var = tk.StringVar(value="Listo")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_main_tab(self, parent):
        """Pestaña principal con opciones de flujo"""
        
        # Frame para rutas principales
        paths_frame = ttk.LabelFrame(parent, text="Rutas Principales", padding=10)
        paths_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(paths_frame, text="Carpeta de entrada (IMU raw):").grid(row=0, column=0, sticky='w', pady=2)
        ttk.Entry(paths_frame, textvariable=self.input_folder, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(paths_frame, text="Examinar", command=lambda: self.browse_folder(self.input_folder)).grid(row=0, column=2)
        
        ttk.Label(paths_frame, text="Carpeta de salida:").grid(row=1, column=0, sticky='w', pady=2)
        ttk.Entry(paths_frame, textvariable=self.output_folder, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(paths_frame, text="Examinar", command=lambda: self.browse_folder(self.output_folder)).grid(row=1, column=2)
        
        ttk.Label(paths_frame, text="Archivo de salida:").grid(row=2, column=0, sticky='w', pady=2)
        ttk.Entry(paths_frame, textvariable=self.output_filename, width=60).grid(row=2, column=1, padx=5)
        
        ttk.Label(paths_frame, text="Mapping file:").grid(row=3, column=0, sticky='w', pady=2)
        ttk.Entry(paths_frame, textvariable=self.mapping_file, width=60).grid(row=3, column=1, padx=5)
        ttk.Button(paths_frame, text="Examinar", command=lambda: self.browse_file(self.mapping_file, [("JSON files", "*.json")])).grid(row=3, column=2)
        
        # Frame para opciones de flujo
        flow_frame = ttk.LabelFrame(parent, text="Opciones de Flujo", padding=10)
        flow_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Checkbutton(flow_frame, text="Omitir corrección de PacketCounter", variable=self.skip_packet_fix).pack(anchor='w')
        ttk.Checkbutton(flow_frame, text="Omitir parsing de Xsens", variable=self.skip_parsing).pack(anchor='w')
        ttk.Checkbutton(flow_frame, text="Omitir IMU Placer", variable=self.skip_imu_placer).pack(anchor='w')
        ttk.Checkbutton(flow_frame, text="Omitir Inverse Kinematics", variable=self.skip_ik).pack(anchor='w')
        
        # Frame para MuJoCo
        mujoco_frame = ttk.LabelFrame(parent, text="Conversión a MuJoCo", padding=10)
        mujoco_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Checkbutton(mujoco_frame, text="Realizar conversión a MuJoCo", variable=self.do_mujoco, 
                       command=self.toggle_mujoco).pack(anchor='w')
        
        mujoco_entry_frame = ttk.Frame(mujoco_frame)
        mujoco_entry_frame.pack(fill='x', pady=5)
        ttk.Label(mujoco_entry_frame, text="Carpeta de salida MuJoCo:").pack(side='left')
        ttk.Entry(mujoco_entry_frame, textvariable=self.mujoco_output, width=50).pack(side='left', padx=5)
        ttk.Button(mujoco_entry_frame, text="Examinar", command=lambda: self.browse_folder(self.mujoco_output)).pack(side='left')
        
        # Frame para visualización (depende del SO)
        viz_frame = ttk.LabelFrame(parent, text="Visualización", padding=10)
        viz_frame.pack(fill='x', padx=10, pady=5)
        
        if self.is_linux:
            ttk.Radiobutton(viz_frame, text="No visualizar", variable=self.visualization_mode, 
                           value="none").pack(anchor='w')
            ttk.Radiobutton(viz_frame, text="Visualizar en Simbody", variable=self.visualization_mode, 
                           value="simbody").pack(anchor='w')
            ttk.Radiobutton(viz_frame, text="Visualizar en MuJoCo", variable=self.visualization_mode, 
                           value="mujoco").pack(anchor='w')
        else:  # Windows
            ttk.Radiobutton(viz_frame, text="No visualizar", variable=self.visualization_mode, 
                           value="none").pack(anchor='w')
            ttk.Radiobutton(viz_frame, text="Visualizar en MuJoCo", variable=self.visualization_mode, 
                           value="mujoco").pack(anchor='w')
            ttk.Label(viz_frame, text="(Para visualizar en Simbody/OpenSim, abre el modelo .osim directamente)").pack(anchor='w')
    
    def create_config_tab(self, parent):
        """Pestaña de configuración avanzada"""
        
        # Frame para sampling rate
        sampling_frame = ttk.LabelFrame(parent, text="Frecuencia de muestreo", padding=10)
        sampling_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(sampling_frame, text="Sampling rate (Hz):").pack(side='left')
        ttk.Entry(sampling_frame, textvariable=self.sampling_rate, width=10).pack(side='left', padx=5)
        
        # Frame para OpenSim settings
        opensim_frame = ttk.LabelFrame(parent, text="Configuración OpenSim", padding=10)
        opensim_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(opensim_frame, text="Modelo OpenSim:").grid(row=0, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.model_path, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(opensim_frame, text="Examinar", command=lambda: self.browse_file(self.model_path, [("OSIM files", "*.osim")])).grid(row=0, column=2)
        
        ttk.Label(opensim_frame, text="Carpeta Geometry:").grid(row=1, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.geometry_path, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(opensim_frame, text="Examinar", command=lambda: self.browse_folder(self.geometry_path)).grid(row=1, column=2)
        
        ttk.Label(opensim_frame, text="Base IMU:").grid(row=2, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.base_imu_label, width=30).grid(row=2, column=1, sticky='w', padx=5)
        
        ttk.Label(opensim_frame, text="Base heading axis:").grid(row=3, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.base_heading_axis, width=10).grid(row=3, column=1, sticky='w', padx=5)
        
        ttk.Label(opensim_frame, text="Sensor to OpenSim rot (rad):").grid(row=4, column=0, sticky='w', pady=2)
        rot_frame = ttk.Frame(opensim_frame)
        rot_frame.grid(row=4, column=1, sticky='w', padx=5)
        ttk.Entry(rot_frame, textvariable=self.sensor_rot_x, width=10).pack(side='left')
        ttk.Label(rot_frame, text=",").pack(side='left')
        ttk.Entry(rot_frame, textvariable=self.sensor_rot_y, width=10).pack(side='left')
        ttk.Label(rot_frame, text=",").pack(side='left')
        ttk.Entry(rot_frame, textvariable=self.sensor_rot_z, width=10).pack(side='left')
        
        ttk.Label(opensim_frame, text="Modelo calibrado:").grid(row=5, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.output_model_name, width=30).grid(row=5, column=1, sticky='w', padx=5)
    
    def create_run_tab(self, parent):
        """Pestaña de ejecución con botones y log"""
        
        # Frame para botones
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Guardar Configuración", command=self.save_config).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Ejecutar Pipeline", command=self.run_pipeline).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Limpiar Log", command=self.clear_log).pack(side='left', padx=5)
        
        # Frame para log
        log_frame = ttk.LabelFrame(parent, text="Salida del Pipeline", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Crear widget de texto para log
        self.log_text = tk.Text(log_frame, wrap='word', height=20)
        self.log_text.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Configurar colores para el log
        self.log_text.tag_config('error', foreground='red')
        self.log_text.tag_config('success', foreground='green')
        self.log_text.tag_config('info', foreground='blue')
    
    def create_trim_tab(self, parent):
        """Pestaña para recortar archivos de cinemática inversa"""
        
        # Frame para configuración
        config_frame = ttk.LabelFrame(parent, text="Configuración de Recorte", padding=10)
        config_frame.pack(fill='x', padx=10, pady=5)
        
        # Archivo de entrada
        ttk.Label(config_frame, text="Archivo IK (.mot):").grid(row=0, column=0, sticky='w', pady=2)
        ttk.Entry(config_frame, textvariable=self.trim_input_file, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(config_frame, text="Examinar", command=lambda: self.browse_file(
            self.trim_input_file, [("MOT files", "*.mot"), ("STO files", "*.sto")])).grid(row=0, column=2)
        
        # Directorio de salida
        ttk.Label(config_frame, text="Directorio salida:").grid(row=1, column=0, sticky='w', pady=2)
        ttk.Entry(config_frame, textvariable=self.trim_output_dir, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(config_frame, text="Examinar", command=lambda: self.browse_folder(self.trim_output_dir)).grid(row=1, column=2)
        
        # Checkbox para resetear tiempo
        ttk.Checkbutton(config_frame, text="Reiniciar tiempo a 0 en segmentos", 
                       variable=self.trim_reset_time).grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        
        # Frame para segmentos
        segments_frame = ttk.LabelFrame(parent, text="Segmentos a Recortar", padding=10)
        segments_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview para segmentos
        columns = ('start', 'end', 'name')
        self.trim_tree = ttk.Treeview(segments_frame, columns=columns, show='headings', height=6)
        self.trim_tree.heading('start', text='Inicio (s)')
        self.trim_tree.heading('end', text='Fin (s)')
        self.trim_tree.heading('name', text='Nombre')
        
        self.trim_tree.column('start', width=100)
        self.trim_tree.column('end', width=100)
        self.trim_tree.column('name', width=250)
        
        self.trim_tree.pack(side='left', fill='both', expand=True)
        
        # Scrollbar para treeview
        scrollbar = ttk.Scrollbar(segments_frame, orient='vertical', command=self.trim_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.trim_tree.configure(yscrollcommand=scrollbar.set)
        
        # Frame para botones de segmentos
        seg_buttons_frame = ttk.Frame(parent)
        seg_buttons_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(seg_buttons_frame, text="Agregar Segmento", 
                  command=self.add_trim_segment).pack(side='left', padx=5)
        ttk.Button(seg_buttons_frame, text="Eliminar Seleccionado", 
                  command=self.remove_trim_segment).pack(side='left', padx=5)
        ttk.Button(seg_buttons_frame, text="Limpiar Todos", 
                  command=self.clear_trim_segments).pack(side='left', padx=5)
        
        # Frame para acción
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(action_frame, text="Ejecutar Recorte", 
                  command=self.run_trim_ik).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Cargar Configuración JSON", 
                  command=self.load_trim_config).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Guardar Configuración JSON", 
                  command=self.save_trim_config).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Generar Configuración desde Carpeta", 
                  command=self.generate_trim_config_from_folder).pack(side='left', padx=5)
    
    def toggle_mujoco(self):
        """Habilita/deshabilita campos de MuJoCo"""
        pass  # No necesario por ahora
    
    def browse_folder(self, var):
        """Abrir diálogo para seleccionar carpeta"""
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)
    
    def browse_file(self, var, filetypes):
        """Abrir diálogo para seleccionar archivo"""
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            var.set(filename)
    
    def log(self, message, tag=None):
        """Añadir mensaje al log"""
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.root.update()
    
    def clear_log(self):
        """Limpiar el log"""
        self.log_text.delete(1.0, tk.END)
    
    def save_config(self):
        """Guardar la configuración actual en config.yaml"""
        try:
            # Actualizar diccionario de configuración
            self.config['paths']['input_folder'] = self.input_folder.get()
            self.config['paths']['output_folder'] = self.output_folder.get()
            self.config['paths']['output_filename'] = self.output_filename.get()
            self.config['paths']['mapping_file'] = self.mapping_file.get()
            self.config['paths']['model_path'] = self.model_path.get()
            self.config['paths']['geometry_path'] = self.geometry_path.get()
            self.config['paths']['mujoco_output_folder'] = self.mujoco_output.get()
            
            self.config['settings']['sampling_rate'] = self.sampling_rate.get()
            
            self.config['opensim_settings']['base_imu_label'] = self.base_imu_label.get()
            self.config['opensim_settings']['base_heading_axis'] = self.base_heading_axis.get()
            self.config['opensim_settings']['sensor_to_opensim_rot'] = [
                self.sensor_rot_x.get(),
                self.sensor_rot_y.get(),
                self.sensor_rot_z.get()
            ]
            self.config['opensim_settings']['output_model_name'] = self.output_model_name.get()
            
            # Guardar archivo
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            
            self.log("Configuración guardada correctamente", 'success')
            self.status_var.set("Configuración guardada")
            
        except Exception as e:
            self.log(f"Error guardando configuración: {e}", 'error')
            messagebox.showerror("Error", f"No se pudo guardar la configuración:\n{e}")
    
    def run_pipeline(self):
        """Ejecutar el pipeline en un hilo separado"""
        
        # Verificar que los directorios existen
        if not os.path.exists(self.input_folder.get()):
            messagebox.showerror("Error", "La carpeta de entrada no existe")
            return
        
        # Guardar configuración actual antes de ejecutar
        self.save_config()
        
        # Crear y empezar hilo
        thread = threading.Thread(target=self._run_pipeline_thread)
        thread.daemon = True
        thread.start()
    
    def _run_pipeline_thread(self):
        """Ejecutar el pipeline (en hilo separado)"""
        
        self.log("\n" + "="*60)
        self.log("INICIANDO PIPELINE", 'info')
        self.log(f"Sistema: {platform.system()}")
        self.log("="*60)
        
        # Crear copia de la configuración para modificarla
        config_dict = self.config.copy()
        
        # --- PASO 0: Corregir Packet Counters ---
        if not self.skip_packet_fix.get():
            self.log("\n--- 0. Corrigiendo Packet Counters ---", 'info')
            original_input_dir = self.input_folder.get()
            fixed_input_dir = original_input_dir + "_corrected"
            
            try:
                data_utils.process_folder(original_input_dir, fixed_input_dir)
                config_dict['paths']['input_folder'] = fixed_input_dir
                self.log("✓ Corrección completada", 'success')
            except Exception as e:
                self.log(f"✗ Error en corrección: {e}", 'error')
                return
        else:
            self.log("\n--- 0. Omitiendo corrección de Packet Counters ---", 'info')
        
        # --- PASO 1: Parsing Xsens ---
        if not self.skip_parsing.get():
            self.log("\n--- 1. Parseando datos Xsens ---", 'info')
            try:
                success = xsens_parser.parse_config_dict(config_dict)
                if success:
                    self.log("✓ Parsing completado", 'success')
                else:
                    self.log("✗ Error en parsing", 'error')
                    return
            except Exception as e:
                self.log(f"✗ Error en parsing: {e}", 'error')
                return
        else:
            self.log("\n--- 1. Omitiendo parsing Xsens ---", 'info')
        
        # --- PASO 2: IMU Placer ---
        calibrated_model = None
        if not self.skip_imu_placer.get():
            self.log("\n--- 2. Ejecutando IMU Placer ---", 'info')
            try:
                calibrated_model = opensim_pipeline.run_imu_placer(config_dict)
                if calibrated_model:
                    self.log(f"✓ Modelo calibrado: {calibrated_model}", 'success')
                else:
                    self.log("✗ Error en IMU Placer", 'error')
                    return
            except Exception as e:
                self.log(f"✗ Error en IMU Placer: {e}", 'error')
                return
        else:
            self.log("\n--- 2. Omitiendo IMU Placer ---", 'info')
        
        # --- PASO 3: Inverse Kinematics ---
        if not self.skip_ik.get() and calibrated_model:
            self.log("\n--- 3. Ejecutando Inverse Kinematics ---", 'info')
            try:
                success = opensim_pipeline.run_inverse_kinematics(config_dict, calibrated_model)
                if success:
                    self.log("✓ IK completado", 'success')
                else:
                    self.log("✗ Error en IK", 'error')
                    return
            except Exception as e:
                self.log(f"✗ Error en IK: {e}", 'error')
                return
        else:
            self.log("\n--- 3. Omitiendo IK ---", 'info')
        
        # --- PASO 4: Conversión a MuJoCo ---
        if self.do_mujoco.get():
            self.log("\n--- 4. Convirtiendo a MuJoCo ---", 'info')
            try:
                from src import mujoco_converter
                # Actualizar configuración con la ruta de MuJoCo
                config_dict['paths']['mujoco_output_folder'] = self.mujoco_output.get()
                success = mujoco_converter.run_mujoco_conversion(self.config_path)
                if success:
                    self.log("✓ Conversión a MuJoCo completada", 'success')
                else:
                    self.log("✗ Error en conversión a MuJoCo", 'error')
            except Exception as e:
                self.log(f"✗ Error en conversión: {e}", 'error')
        else:
            self.log("\n--- 4. Omitiendo conversión a MuJoCo ---", 'info')
        
        # --- PASO 5: Visualización ---
        viz_mode = self.visualization_mode.get()
        if viz_mode != "none":
            self.log(f"\n--- 5. Iniciando visualización ({viz_mode}) ---", 'info')
            
            try:
                if viz_mode == "simbody" and self.is_linux:
                    from src import simbody_visualizer
                    success = simbody_visualizer.run_simbody_visualization(self.config_path, speed_step=10)
                    if success:
                        self.log("✓ Visualización Simbody completada", 'success')
                    else:
                        self.log("✗ Error en visualización Simbody", 'error')
                
                elif viz_mode == "mujoco":
                    # Ejecutar visualizador MuJoCo
                    if self.is_linux:
                        script_path = os.path.join("linux", "visualize_mujoco.py")
                    else:
                        script_path = os.path.join("windows", "visualize_mujoco.py")
                    
                    self.log(f"Ejecutando: python {script_path}", 'info')
                    subprocess.Popen([sys.executable, script_path])
                    self.log("✓ Visualizador MuJoCo lanzado", 'success')
            
            except Exception as e:
                self.log(f"✗ Error en visualización: {e}", 'error')
        else:
            self.log("\n--- 5. Omitiendo visualización ---", 'info')
        
        self.log("\n" + "="*60)
        self.log("PIPELINE COMPLETADO", 'success')
        self.log("="*60)
        self.status_var.set("Pipeline completado")
    
    # ==================== MÉTODOS PARA RECORTE DE IK ====================
    
    def add_trim_segment(self):
        """Agrega un segmento a la lista"""
        # Diálogo simple para ingresar datos
        dialog = tk.Toplevel(self.root)
        dialog.title("Agregar Segmento")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrar diálogo
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 350) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="Inicio (s):").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        start_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=start_var, width=20).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="Fin (s):").grid(row=1, column=0, padx=10, pady=10, sticky='w')
        end_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=end_var, width=20).grid(row=1, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="Nombre:").grid(row=2, column=0, padx=10, pady=10, sticky='w')
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=20).grid(row=2, column=1, padx=10, pady=10)
        
        def add():
            try:
                # Convertir explícitamente a float
                start = float(start_var.get())
                end = float(end_var.get())
                if start >= end:
                    messagebox.showerror("Error", "El inicio debe ser menor que el fin")
                    return
                name = name_var.get().strip()
                if not name:
                    name = f"segment_{len(self.trim_tree.get_children())+1}"
                # Guardar como números float, no strings
                self.trim_tree.insert('', 'end', values=(start, end, name))
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Inicio y fin deben ser números válidos")
        
        def cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Agregar", command=add).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Cancelar", command=cancel).pack(side='left', padx=10)
    
    def remove_trim_segment(self):
        """Elimina el segmento seleccionado"""
        selected = self.trim_tree.selection()
        if selected:
            self.trim_tree.delete(selected)
        else:
            messagebox.showinfo("Información", "Seleccione un segmento para eliminar")
    
    def clear_trim_segments(self):
        """Limpia todos los segmentos"""
        if self.trim_tree.get_children():
            if messagebox.askyesno("Confirmar", "¿Eliminar todos los segmentos?"):
                for item in self.trim_tree.get_children():
                    self.trim_tree.delete(item)
    
    def run_trim_ik(self):
        """Ejecuta el recorte de IK"""
        from src.ik_trimmer import trim_ik_multiple_segments
        
        input_file = self.trim_input_file.get()
        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("Error", "Archivo de entrada válido requerido")
            return
        
        segments = []
        for item in self.trim_tree.get_children():
            values = self.trim_tree.item(item)['values']
            # Asegurar que start y end son floats
            try:
                start = float(values[0])
                end = float(values[1])
                name = str(values[2])
                segments.append({
                    'start': start,
                    'end': end,
                    'name': name
                })
            except (ValueError, TypeError) as e:
                self.log(f"Error en segmento: {values} - {e}", 'error')
                messagebox.showerror("Error", f"Error en segmento: {values}\n{e}")
                return
        
        if not segments:
            messagebox.showerror("Error", "Agregue al menos un segmento")
            return
        
        output_dir = self.trim_output_dir.get()
        if not output_dir:
            output_dir = None
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        reset_time = self.trim_reset_time.get()
        
        self.log("\n" + "="*60)
        self.log("INICIANDO RECORTE DE IK", 'info')
        self.log(f"Archivo: {input_file}")
        self.log(f"Segmentos: {len(segments)}")
        for seg in segments:
            self.log(f"  - {seg['name']}: {seg['start']}s - {seg['end']}s", 'info')
        self.log("="*60)
        
        def run():
            try:
                resultados = trim_ik_multiple_segments(
                    input_path=input_file,
                    segments=segments,
                    output_dir=output_dir,
                    reset_time=reset_time
                )
                if resultados:
                    self.log(f"\n✓ Recorte completado: {len(resultados)} segmentos generados", 'success')
                    for r in resultados:
                        self.log(f"  - {os.path.basename(r)}", 'success')
                    self.status_var.set(f"Recorte completado: {len(resultados)} segmentos")
                else:
                    self.log(f"\n✗ No se generaron segmentos. Verifique los tiempos.", 'error')
                    self.status_var.set("Recorte fallido - verifique tiempos")
            except Exception as e:
                self.log(f"✗ Error en recorte: {e}", 'error')
                self.status_var.set("Error en recorte")
                import traceback
                self.log(traceback.format_exc(), 'error')
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def load_trim_config(self):
        """Carga configuración de recorte desde JSON"""
        filename = filedialog.askopenfilename(
            title="Cargar configuración de recorte",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Limpiar segmentos actuales
            self.clear_trim_segments()
            
            # Buscar el archivo en la configuración
            if 'archivos' in config:
                archivos = config['archivos']
                
                if len(archivos) == 1:
                    # Un solo archivo, cargar directamente
                    archivo_config = archivos[0]
                    ruta_archivo = archivo_config.get('ruta', archivo_config.get('nombre', ''))
                    if ruta_archivo and os.path.exists(ruta_archivo):
                        self.trim_input_file.set(ruta_archivo)
                    segmentos = archivo_config.get('segmentos', [])
                else:
                    # Múltiples archivos, preguntar cuál usar
                    opciones = []
                    for i, a in enumerate(archivos):
                        nombre = a.get('nombre', a.get('ruta', f'Archivo {i+1}'))
                        opciones.append(f"{i+1}: {nombre}")
                    
                    seleccion = simpledialog.askstring(
                        "Seleccionar Archivo",
                        f"Se encontraron {len(archivos)} archivos:\n" + 
                        "\n".join(opciones) + 
                        "\n\nIngrese el número (1-{}) o deje en blanco para usar el primero:".format(len(archivos))
                    )
                    
                    if seleccion and seleccion.isdigit():
                        idx = int(seleccion) - 1
                        if 0 <= idx < len(archivos):
                            archivo_config = archivos[idx]
                        else:
                            archivo_config = archivos[0]
                    else:
                        archivo_config = archivos[0]
                    
                    ruta_archivo = archivo_config.get('ruta', archivo_config.get('nombre', ''))
                    if ruta_archivo and os.path.exists(ruta_archivo):
                        self.trim_input_file.set(ruta_archivo)
                    segmentos = archivo_config.get('segmentos', [])
            else:
                # Configuración simple
                segmentos = config.get('segmentos', [])
                if 'ruta' in config:
                    self.trim_input_file.set(config['ruta'])
                elif 'archivo' in config:
                    self.trim_input_file.set(config['archivo'])
            
            # Agregar segmentos - convertir a float explícitamente
            for seg in segmentos:
                try:
                    start = float(seg.get('start', 0))
                    end = float(seg.get('end', 1))
                    name = seg.get('name', 'segmento')
                    self.trim_tree.insert('', 'end', values=(start, end, name))
                except (ValueError, TypeError) as e:
                    self.log(f"Error cargando segmento {seg}: {e}", 'error')
            
            self.log(f"✓ Configuración cargada: {len(segmentos)} segmentos", 'success')
            self.status_var.set(f"Cargados {len(segmentos)} segmentos")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar configuración:\n{e}")
            self.log(f"Error cargando configuración: {e}", 'error')
    
    def save_trim_config(self):
        """Guarda la configuración de recorte a JSON"""
        input_file = self.trim_input_file.get()
        if not input_file:
            messagebox.showerror("Error", "Especifique un archivo de entrada")
            return
        
        segments = []
        for item in self.trim_tree.get_children():
            values = self.trim_tree.item(item)['values']
            try:
                start = float(values[0])
                end = float(values[1])
                name = str(values[2])
                segments.append({
                    'start': start,
                    'end': end,
                    'name': name
                })
            except (ValueError, TypeError) as e:
                self.log(f"Error en segmento {values}: {e}", 'error')
                messagebox.showerror("Error", f"Error en segmento {values}\n{e}")
                return
        
        if not segments:
            messagebox.showerror("Error", "No hay segmentos para guardar")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Guardar configuración de recorte",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="trim_config.json"
        )
        
        if not filename:
            return
        
        config = {
            "archivos": [
                {
                    "ruta": input_file,
                    "segmentos": segments
                }
            ]
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.log(f"✓ Configuración guardada: {filename}", 'success')
            self.status_var.set("Configuración guardada")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar configuración:\n{e}")
            self.log(f"Error guardando configuración: {e}", 'error')
    
    def generate_trim_config_from_folder(self):
        """Genera configuración de recorte desde una carpeta con archivos IK"""
        folder = filedialog.askdirectory(title="Seleccionar carpeta con archivos IK (.mot)")
        if not folder:
            return
        
        # Diálogo para tiempos por defecto
        dialog = tk.Toplevel(self.root)
        dialog.title("Configurar Tiempos por Defecto")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Tiempo de inicio (s):").grid(row=0, column=0, padx=10, pady=10)
        start_var = tk.StringVar(value="0.0")
        ttk.Entry(dialog, textvariable=start_var, width=15).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="Tiempo de fin (s):").grid(row=1, column=0, padx=10, pady=10)
        end_var = tk.StringVar(value="1.0")
        ttk.Entry(dialog, textvariable=end_var, width=15).grid(row=1, column=1, padx=10, pady=10)
        
        def generate():
            try:
                start_time = float(start_var.get())
                end_time = float(end_var.get())
                if start_time >= end_time:
                    messagebox.showerror("Error", "El inicio debe ser menor que el fin")
                    return
                dialog.destroy()
                
                # Buscar archivos .mot
                import glob
                pattern = os.path.join(folder, "*.mot")
                archivos = glob.glob(pattern)
                
                if not archivos:
                    messagebox.showinfo("Información", f"No se encontraron archivos .mot en {folder}")
                    return
                
                # Generar configuración
                config = {
                    "carpeta_raiz": folder,
                    "archivos": []
                }
                
                for archivo in archivos:
                    nombre_base = os.path.splitext(os.path.basename(archivo))[0]
                    config["archivos"].append({
                        "nombre": os.path.basename(archivo),
                        "segmentos": [
                            {
                                "start": start_time,
                                "end": end_time,
                                "name": nombre_base
                            }
                        ]
                    })
                
                # Guardar JSON
                json_filename = filedialog.asksaveasfilename(
                    title="Guardar configuración generada",
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json")],
                    initialfile="config_generated.json"
                )
                
                if json_filename:
                    with open(json_filename, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    
                    self.log(f"✓ Configuración generada: {json_filename}", 'success')
                    self.log(f"  Archivos encontrados: {len(archivos)}", 'info')
                    self.log(f"  Tiempos por defecto: {start_time}s - {end_time}s", 'info')
                    
                    # Preguntar si quiere cargar esta configuración
                    if messagebox.askyesno("Cargar Configuración", 
                                           f"¿Desea cargar esta configuración ahora?\n\n"
                                           f"Archivos: {len(archivos)}\n"
                                           f"Tiempos: {start_time}s - {end_time}s"):
                        # Cargar el primer archivo de la configuración
                        if archivos:
                            self.trim_input_file.set(archivos[0])
                            self.clear_trim_segments()
                            self.trim_tree.insert('', 'end', values=(start_time, end_time, nombre_base))
                            self.log(f"Configuración cargada con {len(archivos)} archivos disponibles", 'success')
                            self.status_var.set(f"Configuración generada y cargada")
                
            except ValueError:
                messagebox.showerror("Error", "Tiempos deben ser números válidos")
        
        ttk.Button(dialog, text="Generar", command=generate).pack(pady=10)


def main():
    root = tk.Tk()
    app = WorkflowGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

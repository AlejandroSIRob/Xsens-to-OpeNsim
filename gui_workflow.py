#!/usr/bin/env python3
"""
Unified graphical interface for the Xsens-to-OpenSim pipeline
Automatically detects the operating system and shows appropriate options
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

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src import xsens_parser, opensim_pipeline, data_utils

class WorkflowGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Xsens-to-OpenSim Workflow Controller")
        self.root.geometry("900x800")
        
        # Detect operating system
        self.os_type = platform.system().lower()
        if self.os_type == "windows":
            self.config_path = os.path.join("windows", "config.yaml")
            self.is_windows = True
            self.is_linux = False
        else:  # Linux / Darwin
            self.config_path = os.path.join("linux", "config.yaml")
            self.is_linux = True
            self.is_windows = False
        
        print(f"Detected system: {platform.system()} - Using {self.config_path}")
        
        # Load default configuration
        self.load_config()
        
        # Variables for fields
        self.create_variables()
        
        # Store loaded JSON config for batch processing
        self.loaded_json_config = None
        self.loaded_json_path = None
        
        # Create interface
        self.create_widgets()
        
    def load_config(self):
        """Loads configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load {self.config_path}:\n{e}")
            self.config = {
                'paths': {},
                'settings': {'sampling_rate': 60.0},
                'opensim_settings': {}
            }
    
    def create_variables(self):
        """Creates tkinter variables for fields"""
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
        
        # Flow options
        self.skip_packet_fix = tk.BooleanVar(value=False)
        self.skip_parsing = tk.BooleanVar(value=False)
        self.skip_imu_placer = tk.BooleanVar(value=False)
        self.skip_ik = tk.BooleanVar(value=False)
        
        # MuJoCo options
        self.do_mujoco = tk.BooleanVar(value=True)
        self.mujoco_output = tk.StringVar(value=self.config['paths'].get('mujoco_output_folder', '/home/drims/mujoco_output_folder' if self.is_linux else 'mujoco_model'))
        
        # Visualization options
        self.do_mujoco_viz = tk.BooleanVar(value=False)
        self.mujoco_viz_folder = tk.StringVar(value=self.mujoco_output.get())
        
        # IK Trimming variables
        self.trim_input_file = tk.StringVar(value="")
        self.trim_output_dir = tk.StringVar(value=self.config['paths'].get('trim_output_folder', ''))
        self.trim_config_path = tk.StringVar(value=self.config['paths'].get('trim_config_path', ''))
        self.trim_reset_time = tk.BooleanVar(value=True)
        self.batch_process_mode = tk.BooleanVar(value=True)  # Batch Mode
    
    def create_widgets(self):
        """Creates the user interface widgets"""
        
        # Notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Main Pipeline tab
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Main Pipeline")
        self.create_main_tab(main_frame)
        
        # Advanced Configuration tab
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Advanced Configuration")
        self.create_config_tab(config_frame)
        
        # IK Trimming tab
        trim_frame = ttk.Frame(notebook)
        notebook.add(trim_frame, text="IK Trimmer")
        self.create_trim_tab(trim_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_main_tab(self, parent):
        """Main tab with flow options and execution buttons"""
        
        # Frame for main paths
        paths_frame = ttk.LabelFrame(parent, text="Main Paths", padding=10)
        paths_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(paths_frame, text="Input Folder (Raw IMU):").grid(row=0, column=0, sticky='w', pady=2)
        ttk.Entry(paths_frame, textvariable=self.input_folder, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(paths_frame, text="Browse", command=lambda: self.browse_folder(self.input_folder)).grid(row=0, column=2)
        
        ttk.Label(paths_frame, text="Output Folder:").grid(row=1, column=0, sticky='w', pady=2)
        ttk.Entry(paths_frame, textvariable=self.output_folder, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(paths_frame, text="Browse", command=lambda: self.browse_folder(self.output_folder)).grid(row=1, column=2)
        
        ttk.Label(paths_frame, text="Output Filename (IK):").grid(row=2, column=0, sticky='w', pady=2)
        ttk.Entry(paths_frame, textvariable=self.output_filename, width=60).grid(row=2, column=1, padx=5)
        
        ttk.Label(paths_frame, text="Mapping File:").grid(row=3, column=0, sticky='w', pady=2)
        ttk.Entry(paths_frame, textvariable=self.mapping_file, width=60).grid(row=3, column=1, padx=5)
        ttk.Button(paths_frame, text="Browse", command=lambda: self.browse_file(self.mapping_file, [("JSON files", "*.json")])).grid(row=3, column=2)
        
        # Frame for flow options
        flow_frame = ttk.LabelFrame(parent, text="Flow Options", padding=10)
        flow_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Checkbutton(flow_frame, text="Skip PacketCounter correction", variable=self.skip_packet_fix).pack(anchor='w')
        ttk.Checkbutton(flow_frame, text="Skip Xsens parsing", variable=self.skip_parsing).pack(anchor='w')
        ttk.Checkbutton(flow_frame, text="Skip IMU Placer", variable=self.skip_imu_placer).pack(anchor='w')
        ttk.Checkbutton(flow_frame, text="Skip Inverse Kinematics", variable=self.skip_ik).pack(anchor='w')
        
        # Frame for MuJoCo Conversion
        mujoco_frame = ttk.LabelFrame(parent, text="MuJoCo Conversion", padding=10)
        mujoco_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Checkbutton(mujoco_frame, text="Perform MuJoCo Conversion", variable=self.do_mujoco, 
                       command=self.toggle_mujoco).pack(anchor='w')
        
        mujoco_entry_frame = ttk.Frame(mujoco_frame)
        mujoco_entry_frame.pack(fill='x', pady=5)
        ttk.Label(mujoco_entry_frame, text="MuJoCo Output Folder:").pack(side='left')
        self.mujoco_out_entry = ttk.Entry(mujoco_entry_frame, textvariable=self.mujoco_output, width=50)
        self.mujoco_out_entry.pack(side='left', padx=5)
        self.mujoco_out_btn = ttk.Button(mujoco_entry_frame, text="Browse", command=lambda: self.browse_folder(self.mujoco_output))
        self.mujoco_out_btn.pack(side='left')
        
        # Frame for MuJoCo Visualization
        viz_frame = ttk.LabelFrame(parent, text="Visualization Options", padding=10)
        viz_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Checkbutton(viz_frame, text="Launch MuJoCo Visualization", variable=self.do_mujoco_viz, command=self.toggle_mujoco).grid(row=0, column=0, sticky='w')
        ttk.Label(viz_frame, text="Visualization Folder:").grid(row=1, column=0, sticky='w', pady=2)
        self.mujoco_viz_entry = ttk.Entry(viz_frame, textvariable=self.mujoco_viz_folder, width=50)
        self.mujoco_viz_entry.grid(row=1, column=1, padx=5)
        self.mujoco_viz_btn = ttk.Button(viz_frame, text="Browse", command=lambda: self.browse_folder(self.mujoco_viz_folder))
        self.mujoco_viz_btn.grid(row=1, column=2)
        ttk.Button(viz_frame, text="Visualize in MuJoCo", command=self.run_mujoco_visualization).grid(row=1, column=3, padx=10)
        
        # Frame for Execution Buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save Configuration", command=self.save_config).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Execute Pipeline", command=self.run_pipeline).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear Log", command=self.clear_log).pack(side='left', padx=5)
        
        # Frame for Log output
        log_frame = ttk.LabelFrame(parent, text="Pipeline Output", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create text widget for log
        self.log_text = tk.Text(log_frame, wrap='word', height=10)
        self.log_text.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Configure colors for log
        self.log_text.tag_config('error', foreground='red')
        self.log_text.tag_config('success', foreground='green')
        self.log_text.tag_config('info', foreground='blue')
        self.log_text.tag_config('warning', foreground='orange')
        
        # Initialize toggle states
        self.toggle_mujoco()
    
    def create_config_tab(self, parent):
        """Advanced Configuration Tab"""
        
        # Frame for sampling rate
        sampling_frame = ttk.LabelFrame(parent, text="Sampling Frequency", padding=10)
        sampling_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(sampling_frame, text="Sampling Rate (Hz):").pack(side='left')
        ttk.Entry(sampling_frame, textvariable=self.sampling_rate, width=10).pack(side='left', padx=5)
        
        # Frame for OpenSim settings
        opensim_frame = ttk.LabelFrame(parent, text="OpenSim Configuration", padding=10)
        opensim_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(opensim_frame, text="OpenSim Model:").grid(row=0, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.model_path, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(opensim_frame, text="Browse", command=lambda: self.browse_file(self.model_path, [("OSIM files", "*.osim")])).grid(row=0, column=2)
        
        ttk.Label(opensim_frame, text="Geometry Folder:").grid(row=1, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.geometry_path, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(opensim_frame, text="Browse", command=lambda: self.browse_folder(self.geometry_path)).grid(row=1, column=2)
        
        ttk.Label(opensim_frame, text="Base IMU Label:").grid(row=2, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.base_imu_label, width=30).grid(row=2, column=1, sticky='w', padx=5)
        
        ttk.Label(opensim_frame, text="Base Heading Axis:").grid(row=3, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.base_heading_axis, width=10).grid(row=3, column=1, sticky='w', padx=5)
        
        ttk.Label(opensim_frame, text="Sensor to OpenSim Rot (rad):").grid(row=4, column=0, sticky='w', pady=2)
        rot_frame = ttk.Frame(opensim_frame)
        rot_frame.grid(row=4, column=1, sticky='w', padx=5)
        ttk.Entry(rot_frame, textvariable=self.sensor_rot_x, width=10).pack(side='left')
        ttk.Label(rot_frame, text=",").pack(side='left')
        ttk.Entry(rot_frame, textvariable=self.sensor_rot_y, width=10).pack(side='left')
        ttk.Label(rot_frame, text=",").pack(side='left')
        ttk.Entry(rot_frame, textvariable=self.sensor_rot_z, width=10).pack(side='left')
        
        ttk.Label(opensim_frame, text="Calibrated Model Name:").grid(row=5, column=0, sticky='w', pady=2)
        ttk.Entry(opensim_frame, textvariable=self.output_model_name, width=30).grid(row=5, column=1, sticky='w', padx=5)
    
    def create_trim_tab(self, parent):
        """IK Trimming Tab for multiple segment generation"""
        
        # Frame for operation mode
        mode_frame = ttk.LabelFrame(parent, text="Operation Mode", padding=10)
        mode_frame.pack(fill='x', padx=10, pady=5)
        
        self.batch_mode_var = tk.BooleanVar(value=True)
        ttk.Radiobutton(mode_frame, text="Single Mode (load one file and configure its segments)", 
                       variable=self.batch_mode_var, value=False, 
                       command=self.toggle_trim_mode).pack(anchor='w')
        ttk.Radiobutton(mode_frame, text="Batch Mode (process all files sequentially from JSON)", 
                       variable=self.batch_mode_var, value=True,
                       command=self.toggle_trim_mode).pack(anchor='w')
        
        # Frame for trim settings
        config_frame = ttk.LabelFrame(parent, text="Trim Configuration", padding=10)
        config_frame.pack(fill='x', padx=10, pady=5)
        
        # Input file (single mode)
        self.trim_input_frame = ttk.Frame(config_frame)
        self.trim_input_frame.pack(fill='x', pady=2)
        
        ttk.Label(self.trim_input_frame, text="IK File (.mot):").pack(side='left')
        ttk.Entry(self.trim_input_frame, textvariable=self.trim_input_file, width=50).pack(side='left', padx=5)
        ttk.Button(self.trim_input_frame, text="Browse", command=lambda: self.browse_file(
            self.trim_input_file, [("MOT files", "*.mot"), ("STO files", "*.sto")])).pack(side='left')
        
        # Loaded JSON info (batch mode)
        self.json_info_frame = ttk.Frame(config_frame)
        self.json_info_frame.pack(fill='x', pady=5)
        self.json_info_frame.pack_forget()  # Hidden initially
        
        ttk.Label(self.json_info_frame, text="JSON Config File:").pack(side='left')
        ttk.Entry(self.json_info_frame, textvariable=self.trim_config_path, width=50).pack(side='left', padx=5)
        ttk.Button(self.json_info_frame, text="Browse", command=lambda: self.browse_file(
            self.trim_config_path, [("JSON files", "*.json")])).pack(side='left', padx=2)
        ttk.Button(self.json_info_frame, text="Load JSON", command=self.load_specific_trim_config).pack(side='left', padx=2)
        
        # Output directory
        output_frame = ttk.Frame(config_frame)
        output_frame.pack(fill='x', pady=5)
        ttk.Label(output_frame, text="Output Directory:").pack(side='left')
        ttk.Entry(output_frame, textvariable=self.trim_output_dir, width=50).pack(side='left', padx=5)
        ttk.Button(output_frame, text="Browse", command=lambda: self.browse_folder(self.trim_output_dir)).pack(side='left')
        
        # Reset time checkbox
        ttk.Checkbutton(config_frame, text="Reset time to 0s for generated segments", 
                       variable=self.trim_reset_time).pack(anchor='w', pady=5)
        
        # Frame for segments
        segments_frame = ttk.LabelFrame(parent, text="Segments to Trim", padding=10)
        segments_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview for segments
        columns = ('start', 'end', 'name')
        self.trim_tree = ttk.Treeview(segments_frame, columns=columns, show='headings', height=8)
        self.trim_tree.heading('start', text='Start (s)')
        self.trim_tree.heading('end', text='End (s)')
        self.trim_tree.heading('name', text='Name')
        
        self.trim_tree.column('start', width=100)
        self.trim_tree.column('end', width=100)
        self.trim_tree.column('name', width=300)
        
        self.trim_tree.pack(side='left', fill='both', expand=True)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(segments_frame, orient='vertical', command=self.trim_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.trim_tree.configure(yscrollcommand=scrollbar.set)
        
        # Frame for segment buttons
        seg_buttons_frame = ttk.Frame(parent)
        seg_buttons_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(seg_buttons_frame, text="Add Segment", 
                  command=self.add_trim_segment).pack(side='left', padx=5)
        ttk.Button(seg_buttons_frame, text="Remove Selected", 
                  command=self.remove_trim_segment).pack(side='left', padx=5)
        ttk.Button(seg_buttons_frame, text="Clear All", 
                  command=self.clear_trim_segments).pack(side='left', padx=5)
        
        # Action frame
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill='x', padx=10, pady=10)
        
        self.load_json_btn = ttk.Button(action_frame, text="Load JSON Configuration", 
                                        command=self.load_trim_config)
        self.load_json_btn.pack(side='left', padx=5)
        
        self.save_json_btn = ttk.Button(action_frame, text="Save JSON Configuration", 
                                        command=self.save_trim_config)
        self.save_json_btn.pack(side='left', padx=5)
        
        self.generate_btn = ttk.Button(action_frame, text="Generate Configuration from Folder", 
                                       command=self.generate_trim_config_from_folder)
        self.generate_btn.pack(side='left', padx=5)
        
        self.execute_btn = ttk.Button(action_frame, text="Execute Trim", 
                                      command=self.run_trim_ik, style="Accent.TButton")
        self.execute_btn.pack(side='left', padx=5)
        
        # Style for execute button
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="green")
        
        # Initialize trim mode toggle
        self.toggle_trim_mode()
    
    def toggle_trim_mode(self):
        """Toggles between single mode and batch mode"""
        if self.batch_mode_var.get():
            # Batch mode - hide single input file selector, show JSON info
            self.trim_input_frame.pack_forget()
            self.json_info_frame.pack(fill='x', pady=5)
            # Clear current segments
            self.clear_trim_segments()
            self.trim_input_file.set("")
        else:
            # Single mode - show file selector, hide JSON info
            self.json_info_frame.pack_forget()
            self.trim_input_frame.pack(fill='x', pady=2)
            # Clear loaded JSON
            self.clear_loaded_json()
    
    def clear_loaded_json(self):
        """Clears the loaded JSON configuration"""
        self.loaded_json_config = None
        self.loaded_json_path = None
        self.trim_config_path.set("")
        self.clear_trim_segments()
        self.log("Loaded JSON configuration cleared.", 'info')
    
    def toggle_mujoco(self):
        """Enables/disables MuJoCo entry fields based on checkbox"""
        if hasattr(self, 'mujoco_out_entry') and hasattr(self, 'mujoco_out_btn'):
            state = 'normal' if self.do_mujoco.get() else 'disabled'
            self.mujoco_out_entry.config(state=state)
            self.mujoco_out_btn.config(state=state)
            
        if hasattr(self, 'mujoco_viz_entry') and hasattr(self, 'mujoco_viz_btn'):
            viz_state = 'normal' if self.do_mujoco_viz.get() else 'disabled'
            self.mujoco_viz_entry.config(state=viz_state)
            self.mujoco_viz_btn.config(state=viz_state)
            
    def run_mujoco_visualization(self):
        """Runs the MuJoCo visualizer tool"""
        self.log("\n--- Executing MuJoCo Visualizer ---", 'info')
        if not self.do_mujoco_viz.get():
            self.log("Option 'Launch MuJoCo Visualization' is disabled. Check it first.", 'warning')
            messagebox.showwarning("Warning", "Please enable 'Launch MuJoCo Visualization' first.")
            return

        viz_folder = self.mujoco_viz_folder.get()
        if not os.path.exists(viz_folder):
            self.log(f"Error: Directory {viz_folder} does not exist.", 'error')
            messagebox.showerror("Error", f"Visualization folder does not exist:\n{viz_folder}")
            return
            
        try:
            if self.is_linux:
                script_path = os.path.join("linux", "visualize_mujoco.py")
            else:
                script_path = os.path.join("windows", "visualize_mujoco.py")
            
            # Use environment variable to pass the path to visualize_mujoco.py safely
            env = os.environ.copy()
            env["MUJOCO_MODEL_DIR"] = viz_folder
            
            self.log(f"Running: python {script_path} (loading {viz_folder})", 'info')
            subprocess.Popen([sys.executable, script_path], env=env)
            self.log("✓ MuJoCo Visualizer successfully started", 'success')
        except Exception as e:
            self.log(f"✗ Error launching visualization: {e}", 'error')

    def browse_folder(self, var):
        """Open dialog to select a folder"""
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)
    
    def browse_file(self, var, filetypes):
        """Open dialog to select a file"""
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            var.set(filename)
    
    def log(self, message, tag=None):
        """Add message to the log text widget"""
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.root.update()
    
    def clear_log(self):
        """Clear the log text widget"""
        self.log_text.delete(1.0, tk.END)
    
    def save_config(self):
        """Save the current configuration to config.yaml"""
        try:
            # Update configuration dictionary
            self.config['paths']['input_folder'] = self.input_folder.get()
            self.config['paths']['output_folder'] = self.output_folder.get()
            self.config['paths']['output_filename'] = self.output_filename.get()
            self.config['paths']['mapping_file'] = self.mapping_file.get()
            self.config['paths']['model_path'] = self.model_path.get()
            self.config['paths']['geometry_path'] = self.geometry_path.get()
            self.config['paths']['mujoco_output_folder'] = self.mujoco_output.get()
            self.config['paths']['trim_config_path'] = self.trim_config_path.get()
            self.config['paths']['trim_output_folder'] = self.trim_output_dir.get()
            
            self.config['settings']['sampling_rate'] = self.sampling_rate.get()
            
            self.config['opensim_settings']['base_imu_label'] = self.base_imu_label.get()
            self.config['opensim_settings']['base_heading_axis'] = self.base_heading_axis.get()
            self.config['opensim_settings']['sensor_to_opensim_rot'] = [
                self.sensor_rot_x.get(),
                self.sensor_rot_y.get(),
                self.sensor_rot_z.get()
            ]
            self.config['opensim_settings']['output_model_name'] = self.output_model_name.get()
            
            # Save file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            
            self.log("Configuration saved successfully", 'success')
            self.status_var.set("Configuration saved")
            
        except Exception as e:
            self.log(f"Error saving configuration: {e}", 'error')
            messagebox.showerror("Error", f"Could not save configuration:\n{e}")
    
    def run_pipeline(self):
        """Execute the pipeline in a separate thread"""
        
        # Verify that input directory exists
        if not os.path.exists(self.input_folder.get()):
            messagebox.showerror("Error", "The input folder does not exist")
            return
        
        # Save current config before executing
        self.save_config()
        
        # Create and start thread
        thread = threading.Thread(target=self._run_pipeline_thread)
        thread.daemon = True
        thread.start()
    
    def _run_pipeline_thread(self):
        """Execute the pipeline (in a separate thread)"""
        
        self.log("\n" + "="*60)
        self.log("STARTING PIPELINE", 'info')
        self.log(f"System: {platform.system()}")
        self.log("="*60)
        
        # Create a copy of the configuration to modify it
        config_dict = self.config.copy()
        
        # --- STEP 0: Correct Packet Counters ---
        if not self.skip_packet_fix.get():
            self.log("\n--- 0. Correcting Packet Counters ---", 'info')
            original_input_dir = self.input_folder.get()
            fixed_input_dir = original_input_dir + "_corrected"
            
            try:
                data_utils.process_folder(original_input_dir, fixed_input_dir)
                config_dict['paths']['input_folder'] = fixed_input_dir
                self.log("✓ Correction completed", 'success')
            except Exception as e:
                self.log(f"✗ Error in correction: {e}", 'error')
                return
        else:
            self.log("\n--- 0. Skipping Packet Counters correction ---", 'info')
        
        # --- STEP 1: Xsens Parsing ---
        if not self.skip_parsing.get():
            self.log("\n--- 1. Parsing Xsens data ---", 'info')
            try:
                success = xsens_parser.parse_config_dict(config_dict)
                if success:
                    self.log("✓ Parsing completed", 'success')
                else:
                    self.log("✗ Error in parsing", 'error')
                    return
            except Exception as e:
                self.log(f"✗ Error in parsing: {e}", 'error')
                return
        else:
            self.log("\n--- 1. Skipping Xsens parsing ---", 'info')
        
        # --- STEP 2: IMU Placer ---
        calibrated_model = None
        if not self.skip_imu_placer.get():
            self.log("\n--- 2. Executing IMU Placer ---", 'info')
            try:
                calibrated_model = opensim_pipeline.run_imu_placer(config_dict)
                if calibrated_model:
                    self.log(f"✓ Calibrated model: {calibrated_model}", 'success')
                else:
                    self.log("✗ Error in IMU Placer", 'error')
                    return
            except Exception as e:
                self.log(f"✗ Error in IMU Placer: {e}", 'error')
                return
        else:
            self.log("\n--- 2. Skipping IMU Placer ---", 'info')
            calibrated_model = os.path.join(self.output_folder.get(), self.output_model_name.get())
            if not os.path.exists(calibrated_model):
                self.log(f"Warning: The specified calibrated model '{calibrated_model}' does not exist.", 'warning')
        
        # --- STEP 3: Inverse Kinematics ---
        if not self.skip_ik.get() and calibrated_model:
            self.log("\n--- 3. Executing Inverse Kinematics ---", 'info')
            try:
                success = opensim_pipeline.run_inverse_kinematics(config_dict, calibrated_model)
                if success:
                    self.log("✓ IK completed", 'success')
                else:
                    self.log("✗ Error in IK", 'error')
                    return
            except Exception as e:
                self.log(f"✗ Error in IK: {e}", 'error')
                return
        else:
            self.log("\n--- 3. Skipping IK ---", 'info')
            if not calibrated_model and not self.skip_ik.get():
                self.log("Could not run IK because calibrated_model is missing.", 'error')
        
        # --- STEP 4: MuJoCo Conversion ---
        if self.do_mujoco.get():
            self.log("\n--- 4. Converting to MuJoCo ---", 'info')
            try:
                from src import mujoco_converter
                # Update config with MuJoCo path
                config_dict['paths']['mujoco_output_folder'] = self.mujoco_output.get()
                # Pass config_dict directly to avoid reading the shared file from disk again
                success = mujoco_converter.run_mujoco_conversion(config_dict)
                if success:
                    self.log("✓ MuJoCo Conversion completed", 'success')
                else:
                    self.log("✗ Error in MuJoCo conversion", 'error')
            except Exception as e:
                self.log(f"✗ Error in conversion: {e}", 'error')
        else:
            self.log("\n--- 4. Skipping MuJoCo conversion ---", 'info')
        
        # Visualization section is handled by the dedicated button now.
        # But we remove the old inline visualization step since it's merged.
        
        self.log("\n" + "="*60)
        self.log("PIPELINE COMPLETED", 'success')
        self.log("="*60)
        self.status_var.set("Pipeline completed")
    
    # ==================== IK TRIMMING METHODS ====================
    
    def add_trim_segment(self):
        """Add a segment to the list"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Segment")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 350) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="Start (s):").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        start_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=start_var, width=20).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="End (s):").grid(row=1, column=0, padx=10, pady=10, sticky='w')
        end_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=end_var, width=20).grid(row=1, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="Name:").grid(row=2, column=0, padx=10, pady=10, sticky='w')
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=20).grid(row=2, column=1, padx=10, pady=10)
        
        def add():
            try:
                start = float(start_var.get())
                end = float(end_var.get())
                if start >= end:
                    messagebox.showerror("Error", "Start must be less than end")
                    return
                name = name_var.get().strip()
                if not name:
                    name = f"segment_{len(self.trim_tree.get_children())+1}"
                self.trim_tree.insert('', 'end', values=(start, end, name))
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Start and end must be valid numbers")
        
        def cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Add", command=add).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side='left', padx=10)
    
    def remove_trim_segment(self):
        """Remove selected segment"""
        selected = self.trim_tree.selection()
        if selected:
            self.trim_tree.delete(selected)
        else:
            messagebox.showinfo("Information", "Select a segment to remove")
    
    def clear_trim_segments(self):
        """Clear all segments"""
        for item in self.trim_tree.get_children():
            self.trim_tree.delete(item)
    
    def run_trim_ik(self):
        """Execute IK trimming based on selected mode"""
        from src.ik_trimmer import trim_ik_multiple_segments, trim_ik_batch
        
        reset_time = self.trim_reset_time.get()
        output_dir = self.trim_output_dir.get()
        if not output_dir:
            output_dir = None
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # Batch Mode
        if self.batch_mode_var.get():
            config_path = self.trim_config_path.get()
            
            if not self.loaded_json_config and config_path and os.path.exists(config_path):
                # Auto-load before running if not explicitly loaded
                if not self.load_specific_trim_config():
                    return
            
            if not self.loaded_json_config:
                messagebox.showerror("Error", "No JSON configuration loaded. Provide a valid path and click 'Load JSON'.")
                return
            
            self.log("\n" + "="*60)
            self.log("STARTING TIMING IN BATCH MODE", 'info')
            self.log(f"JSON File: {self.loaded_json_path}")
            self.log(f"Files in config: {len(self.loaded_json_config.get('archivos', []))}")
            self.log("="*60)
            
            def run_batch():
                try:
                    # Save temporary config for batch processing
                    temp_config_path = os.path.join(os.path.dirname(self.loaded_json_path), 
                                                    f"temp_batch_{os.path.basename(self.loaded_json_path)}")
                    with open(temp_config_path, 'w') as f:
                        json.dump(self.loaded_json_config, f, indent=4)
                    
                    resultados = trim_ik_batch(
                        config_path=temp_config_path,
                        output_dir=output_dir,
                        reset_time=reset_time
                    )
                    
                    # Clean temporary file
                    if os.path.exists(temp_config_path):
                        os.remove(temp_config_path)
                    
                    total_archivos = len([v for v in resultados.values() if v])
                    total_segmentos = sum(len(v) for v in resultados.values())
                    
                    self.log(f"\n✓ Batch trimming completed", 'success')
                    self.log(f"  Processed files: {total_archivos}/{len(resultados)}", 'success')
                    self.log(f"  Generated segments: {total_segmentos}", 'success')
                    self.status_var.set(f"Batch completed: {total_segmentos} segments")
                    
                except Exception as e:
                    self.log(f"✗ Error in batch trimming: {e}", 'error')
                    self.status_var.set("Error in batch trimming")
                    import traceback
                    self.log(traceback.format_exc(), 'error')
            
            thread = threading.Thread(target=run_batch)
            thread.daemon = True
            thread.start()
        
        # Single mode
        else:
            input_file = self.trim_input_file.get()
            if not input_file or not os.path.exists(input_file):
                messagebox.showerror("Error", "Valid input file required")
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
                    self.log(f"Error in segment: {values} - {e}", 'error')
                    messagebox.showerror("Error", f"Error in segment: {values}\n{e}")
                    return
            
            if not segments:
                messagebox.showerror("Error", "Add at least one segment")
                return
            
            self.log("\n" + "="*60)
            self.log("STARTING TRIMMING IN SINGLE MODE", 'info')
            self.log(f"File: {input_file}")
            self.log(f"Segments: {len(segments)}")
            for seg in segments:
                self.log(f"  - {seg['name']}: {seg['start']}s - {seg['end']}s", 'info')
            self.log("="*60)
            
            def run_individual():
                try:
                    resultados = trim_ik_multiple_segments(
                        input_path=input_file,
                        segments=segments,
                        output_dir=output_dir,
                        reset_time=reset_time
                    )
                    if resultados:
                        self.log(f"\n✓ Trimming completed: {len(resultados)} segments generated", 'success')
                        for r in resultados:
                            self.log(f"  - {os.path.basename(r)}", 'success')
                        self.status_var.set(f"Trimming completed: {len(resultados)} segments")
                    else:
                        self.log(f"\n✗ No segments generated. Check timings.", 'error')
                        self.status_var.set("Trimming failed - check timings")
                except Exception as e:
                    self.log(f"✗ Error in trimming: {e}", 'error')
                    self.status_var.set("Error in trimming")
                    import traceback
                    self.log(traceback.format_exc(), 'error')
            
            thread = threading.Thread(target=run_individual)
            thread.daemon = True
            thread.start()
    
    def load_specific_trim_config(self):
        """Loads the trim configuration specified in the UI path"""
        filename = self.trim_config_path.get()
        if not filename or not os.path.exists(filename):
            messagebox.showerror("Error", f"File not found: {filename}")
            return False
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.loaded_json_config = config
            self.loaded_json_path = filename
            
            # Show JSON Info
            archivos = config.get('archivos', [])
            total_segmentos = sum(len(a.get('segmentos', [])) for a in archivos)
            self.log(f"✓ Loaded JSON: {os.path.basename(filename)}", 'success')
            self.log(f"  Files: {len(archivos)}", 'info')
            self.log(f"  Total segments: {total_segmentos}", 'info')
            
            return True
        except Exception as e:
            self.log(f"Error loading JSON: {e}", 'error')
            messagebox.showerror("Error", f"Could not load JSON:\n{e}")
            return False

    def load_trim_config(self):
        """Loads trim configuration from JSON (button action)"""
        filename = filedialog.askopenfilename(
            title="Load Trimming Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        self.trim_config_path.set(filename)
        
        if self.load_specific_trim_config():
            config = self.loaded_json_config
            archivos = config.get('archivos', [])
            
            # If in single mode, prompt which file to load
            if not self.batch_mode_var.get():
                if len(archivos) == 1:
                    # Single file, load dirctly
                    archivo_config = archivos[0]
                    ruta_archivo = archivo_config.get('ruta', archivo_config.get('nombre', ''))
                    if ruta_archivo and os.path.exists(ruta_archivo):
                        self.trim_input_file.set(ruta_archivo)
                    else:
                        self.log(f"Warning: File not found: {ruta_archivo}", 'warning')
                    
                    segmentos = archivo_config.get('segmentos', [])
                    self.clear_trim_segments()
                    for seg in segmentos:
                        try:
                            start = float(seg.get('start', 0))
                            end = float(seg.get('end', 1))
                            name = seg.get('name', 'segmento')
                            self.trim_tree.insert('', 'end', values=(start, end, name))
                        except (ValueError, TypeError) as e:
                            self.log(f"Error loading segment {seg}: {e}", 'error')
                    
                    self.log(f"Loaded {len(segmentos)} segments for single file", 'success')
                    
                elif len(archivos) > 1:
                    # Multiple files, show selection dialog
                    opciones = []
                    for i, a in enumerate(archivos):
                        nombre = a.get('nombre', a.get('ruta', f'File {i+1}'))
                        num_seg = len(a.get('segmentos', []))
                        opciones.append(f"{i+1}: {nombre} ({num_seg} segments)")
                    
                    seleccion = simpledialog.askstring(
                        "Select File",
                        f"Found {len(archivos)} files in JSON:\n\n" + 
                        "\n".join(opciones) + 
                        "\n\nEnter number (1-{}) to load its segments:".format(len(archivos))
                    )
                    
                    if seleccion and seleccion.isdigit():
                        idx = int(seleccion) - 1
                        if 0 <= idx < len(archivos):
                            archivo_config = archivos[idx]
                            ruta_archivo = archivo_config.get('ruta', archivo_config.get('nombre', ''))
                            if ruta_archivo and os.path.exists(ruta_archivo):
                                self.trim_input_file.set(ruta_archivo)
                            else:
                                self.log(f"Warning: File not found: {ruta_archivo}", 'warning')
                            
                            segmentos = archivo_config.get('segmentos', [])
                            self.clear_trim_segments()
                            for seg in segmentos:
                                try:
                                    start = float(seg.get('start', 0))
                                    end = float(seg.get('end', 1))
                                    name = seg.get('name', 'segmento')
                                    self.trim_tree.insert('', 'end', values=(start, end, name))
                                except (ValueError, TypeError) as e:
                                    self.log(f"Error loading segment {seg}: {e}", 'error')
                            
                            self.log(f"Loaded {len(segmentos)} segments for selected file", 'success')
                        else:
                            self.log("Invalid number, no segments loaded", 'warning')
                    else:
                        self.log("No file selected, segments not loaded", 'warning')
            else:
                # Batch mode - only show info
                self.log(f"Batch mode activated. Ready to process all files.", 'info')
                self.log("Use 'Execute Trim' to process all files from JSON", 'info')
            
            self.status_var.set(f"JSON loaded: {os.path.basename(filename)}")
            
    def save_trim_config(self):
        """Saves trim configuration to JSON"""
        # Determine what to save depending on mode
        if self.batch_mode_var.get() and self.loaded_json_config:
            # Batch mode with loaded JSON, save current JSON
            if not self.loaded_json_path:
                filename = filedialog.asksaveasfilename(
                    title="Save Trimming Configuration",
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json")],
                    initialfile="trim_config.json"
                )
            else:
                filename = self.loaded_json_path
            
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.loaded_json_config, f, indent=4, ensure_ascii=False)
                    self.log(f"✓ JSON configuration saved: {filename}", 'success')
                    self.status_var.set("Configuration saved")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not save configuration:\n{e}")
        
        else:
            # Single mode - save current segments
            input_file = self.trim_input_file.get()
            if not input_file:
                messagebox.showerror("Error", "Specify an input file")
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
                    self.log(f"Error in segment {values}: {e}", 'error')
                    messagebox.showerror("Error", f"Error in segment {values}\n{e}")
                    return
            
            if not segments:
                messagebox.showerror("Error", "No segments to save")
                return
            
            filename = filedialog.asksaveasfilename(
                title="Save Trimming Configuration",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile="trim_config.json"
            )
            
            if filename:
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
                    self.log(f"✓ Configuration saved: {filename}", 'success')
                    self.status_var.set("Configuration saved")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not save configuration:\n{e}")
    
    def generate_trim_config_from_folder(self):
        """Generates trim configuration from a folder with IK files"""
        folder = filedialog.askdirectory(title="Select folder with IK files (.mot)")
        if not folder:
            return
        
        # Dialog for default times
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure Default Timings")
        dialog.geometry("300x180")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Start time (s):").grid(row=0, column=0, padx=10, pady=10)
        start_var = tk.StringVar(value="0.0")
        ttk.Entry(dialog, textvariable=start_var, width=15).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(dialog, text="End time (s):").grid(row=1, column=0, padx=10, pady=10)
        end_var = tk.StringVar(value="1.0")
        ttk.Entry(dialog, textvariable=end_var, width=15).grid(row=1, column=1, padx=10, pady=10)
        
        # Option to autoload after generation
        auto_load_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Load automatically after generation", 
                       variable=auto_load_var).grid(row=2, column=0, columnspan=2, pady=5)
        
        def generate():
            try:
                start_time = float(start_var.get())
                end_time = float(end_var.get())
                if start_time >= end_time:
                    messagebox.showerror("Error", "Start must be less than end")
                    return
                dialog.destroy()
                
                # Search .mot files
                import glob
                pattern = os.path.join(folder, "*.mot")
                archivos = glob.glob(pattern)
                
                if not archivos:
                    messagebox.showinfo("Information", f"No .mot files found in {folder}")
                    return
                
                # Generate config
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
                
                # Save JSON
                json_filename = filedialog.asksaveasfilename(
                    title="Save generated configuration",
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json")],
                    initialfile="config_generated.json"
                )
                
                if json_filename:
                    with open(json_filename, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    
                    self.log(f"✓ Configuration generated: {json_filename}", 'success')
                    self.log(f"  Files found: {len(archivos)}", 'info')
                    self.log(f"  Default timings: {start_time}s - {end_time}s", 'info')
                    
                    # Autoload if requested
                    if auto_load_var.get():
                        self.loaded_json_config = config
                        self.loaded_json_path = json_filename
                        self.json_path_label.config(text=os.path.basename(json_filename), foreground='green')
                        
                        # If in single mode, load the first file
                        if not self.batch_mode_var.get() and archivos:
                            self.trim_input_file.set(archivos[0])
                            self.clear_trim_segments()
                            self.trim_tree.insert('', 'end', values=(start_time, end_time, nombre_base))
                            self.log(f"Configuration loaded with {len(archivos)} available files", 'success')
                        
                        self.status_var.set(f"Configuration generated and loaded")
                
            except ValueError:
                messagebox.showerror("Error", "Timings must be valid numbers")
        
        ttk.Button(dialog, text="Generate", command=generate).grid(row=3, column=0, columnspan=2, pady=10)


def main():
    root = tk.Tk()
    app = WorkflowGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

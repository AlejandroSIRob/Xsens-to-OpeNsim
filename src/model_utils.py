import xml.etree.ElementTree as ET
import os

def create_custom_model(input_path, output_path):
    """Creates a custom OpenSim model with locked legs and free arms."""
    print(f"\n--- Creating custom model from: {input_path} ---")
    
    if not os.path.exists(input_path):
        print(f"ERROR: Input model not found at {input_path}")
        return None

    tree = ET.parse(input_path)
    root = tree.getroot()
    
    leg_coordinates = [
        'hip_flexion_r', 'hip_adduction_r', 'hip_rotation_r',
        'hip_flexion_l', 'hip_adduction_l', 'hip_rotation_l',
        'knee_angle_r', 'knee_angle_l',
        'knee_angle_r_beta', 'knee_angle_l_beta',
        'ankle_angle_r', 'ankle_angle_l',
        'subtalar_angle_r', 'subtalar_angle_l',
        'mtp_angle_r', 'mtp_angle_l',
        'lumbar_extension', 'lumbar_bending', 'lumbar_rotation'
    ]
    
    arm_coordinates = [
        'arm_flex_r', 'arm_add_r', 'arm_rot_r',
        'arm_flex_l', 'arm_add_l', 'arm_rot_l',
        'elbow_flex_r', 'elbow_flex_l',
        'pro_sup_r', 'pro_sup_l',
        'wrist_flex_r', 'wrist_flex_l',
        'wrist_dev_r', 'wrist_dev_l'
    ]
    
    leg_locked = []
    arm_unlocked = []
    modified_count = 0
    
    coordinate_paths = [
        './/Coordinate',
        './/JointSet//Joint//Coordinate',
        './/BodySet//Body//Joint//Coordinate',
        './/componentset//Joint//Coordinate'
    ]
    
    for path in coordinate_paths:
        coords = root.findall(path)
        for coord in coords:
            coord_name = coord.get('name')
            if coord_name:
                locked_elem = coord.find('locked')
                if locked_elem is None:
                    locked_elem = ET.SubElement(coord, 'locked')
                
                if coord_name in leg_coordinates:
                    locked_elem.text = 'true'
                    leg_locked.append(coord_name)
                    print(f"  [LOCKED]: {coord_name}")
                    modified_count += 1
                elif coord_name in arm_coordinates:
                    locked_elem.text = 'false'
                    arm_unlocked.append(coord_name)
                    print(f"  [UNLOCKED]: {coord_name}")
                    modified_count += 1
    
    print(f"\nTotal modified coordinates: {modified_count}")
    
    tree.write(output_path, encoding='UTF-8', xml_declaration=True)
    print(f"✓ Custom model saved to: {output_path}")
    
    return output_path

def verify_model(model_path):
    """Verifies the locked/unlocked state of the model."""
    print(f"\n--- Verifying model: {model_path} ---")
    
    tree = ET.parse(model_path)
    root = tree.getroot()
    coords = root.findall('.//Coordinate')
    
    leg_coords = ['hip_', 'knee_', 'ankle_', 'subtalar_', 'mtp_', 'lumbar_']
    arm_coords = ['arm_', 'elbow_', 'pro_sup_', 'wrist_']
    
    leg_error = arm_error = 0
    
    for coord in coords:
        coord_name = coord.get('name')
        if coord_name:
            locked_elem = coord.find('locked')
            if locked_elem is not None:
                is_locked = locked_elem.text.lower() == 'true'
                status_str = "LOCKED" if is_locked else "FREE"
                
                if any(leg in coord_name for leg in leg_coords):
                    if is_locked:
                        pass
                    else:
                        print(f"  [ERROR] {coord_name}: {status_str} (Should be LOCKED)")
                        leg_error += 1
                elif any(arm in coord_name for arm in arm_coords):
                    if not is_locked:
                        pass
                    else:
                        print(f"  [ERROR] {coord_name}: {status_str} (Should be FREE)")
                        arm_error += 1

    if leg_error == 0 and arm_error == 0:
        print("✓ Model verified successfully. No errors found.")
        return True
    return False

if __name__ == "__main__":
    import yaml
    
    # Load default linux config or take paths as args
    # This block allows running this script standalone if needed
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    with open("linux/config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    input_model = "models/Rajagopal2015_opensense.osim"
    output_model = "models/Rajagopal_FreeArms_LockedLegs.osim"
    
    create_custom_model(input_model, output_model)
    verify_model(output_model)

import os
import glob

def fix_packet_counter(input_file, output_file):
    """
    Reads an IMU data file and corrects the PacketCounter so that it is
    continuous after a reset (65535 -> 00000 becomes 65535 -> 65536).
    """
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    headers = []
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith('//'):
            headers.append(line)
        else:
            data_start = i
            break
    
    column_headers = lines[data_start].strip()
    data_start += 1
    
    corrected_lines = []
    accumulated_offset = 0
    prev_packet = None
    
    for line in lines[data_start:]:
        if not line.strip():
            continue
            
        parts = line.strip().split('\t')
        if len(parts) < 8:
            continue
            
        packet_counter = int(parts[0])
        
        # Detect reset
        if prev_packet is not None and packet_counter < 1000 and prev_packet > 60000:
            accumulated_offset += 65536
        
        new_packet = packet_counter + accumulated_offset
        parts[0] = str(new_packet)
        corrected_lines.append('\t'.join(parts))
        
        prev_packet = packet_counter
    
    with open(output_file, 'w') as f:
        f.writelines(headers)
        f.write(column_headers + '\n')
        for line in corrected_lines:
            f.write(line + '\n')
            
    print(f"Corrected file saved: {output_file}")

def process_folder(input_folder, output_folder):
    """Processes all .txt files in the input folder."""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created folder: {output_folder}")
    
    pattern = os.path.join(input_folder, "*.txt")
    files = glob.glob(pattern)
    
    if not files:
        print(f"No .txt files found in {input_folder}")
        return
    
    print(f"Processing {len(files)} files...")
    
    for input_file in files:
        filename = os.path.basename(input_file)
        output_file = os.path.join(output_folder, filename)
        
        try:
            fix_packet_counter(input_file, output_file)
            print(f"  {filename}: OK")
        except Exception as e:
            print(f"  ERROR processing {filename}: {e}")

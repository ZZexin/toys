import os
import shutil

# 📁 Set your working folder here
source_folder = "C:/2025_Roy Hill/PRODUCTION DATA"

# Step 1: Get all files in the folder
all_files = [f for f in os.listdir(source_folder) if os.path.isfile(os.path.join(source_folder, f))]

if not all_files:
    print("No files found.")
    exit()

# Step 2: Group files by Hole ID
hole_id_dict = {}

for file in all_files:
    # Extract the part before the first "_" or "." as the Hole ID
    base = file.split('_')[0].split('.')[0]

    if base not in hole_id_dict:
        hole_id_dict[base] = []

    hole_id_dict[base].append(file)

# Step 3: Create subfolders and move the files
for hole_id, files in hole_id_dict.items():
    hole_folder = os.path.join(source_folder, hole_id)
    os.makedirs(hole_folder, exist_ok=True)

    for file in files:
        src_path = os.path.join(source_folder, file)
        dst_path = os.path.join(hole_folder, file)
        shutil.move(src_path, dst_path)
        print(f"Moved {file} → {hole_folder}")

print("🎉 Done! All files grouped into subfolders by Hole ID.")

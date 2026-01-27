import lasio
import pandas as pd
from pathlib import Path

def process_las_file(las_file_path, output_folder):
    las_file_path = Path(las_file_path)
    las = lasio.read(str(las_file_path))
    changes = []

    # --- 1. Update MHID if needed ---
    if 'MHID' in las.params and las.params['MHID'].value.strip() == 'CBCBF':
        las.params['MHID'].value = 'CHCBF'
        changes.append("MHID updated: CBCBF → CHCBF")

    # --- 1b. Fix BIT SIZE format ---
    if 'BS' in las.params:
        bs_value = str(las.params['BS'].value).strip()
        try:
            bs_numeric = float(bs_value)
            if bs_numeric > 100:
                bs_str = str(int(bs_numeric))
                if len(bs_str) >= 3:
                    bs_fixed = bs_str[:2] + '.' + bs_str[2:]
                    las.params['BS'].value = bs_fixed
                    changes.append(f"BIT SIZE fixed: {bs_value} → {bs_fixed}")
        except ValueError:
            pass

    fluid_level = las.params['FLVL'].value if 'FLVL' in las.params else None

    # --- 2. Load curves into DataFrame ---
    df = las.df()

    # --- 3. Round numeric columns safely ---
    numeric_cols = df.select_dtypes(include='number').columns
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce').round(2)

    # --- 4. Density limits (1-5.5 g/cc) ---
    if 'DENSITY' in df.columns:
        df['DENSITY'] = df['DENSITY'].apply(lambda x: x if 1 <= x <= 5.5 else -999.25)

    # --- 5. CALIPER formatting ---
    if 'CALIPER' in df.columns:
        df['CALIPER'] = df['CALIPER'].apply(lambda x: "-999.25" if pd.isna(x) or x == -999.25 else f"{x:.1f}")

    # --- 6. RES(SG) update based on fluid level ---
    if 'RES(SG)' in df.columns and fluid_level is not None and 'DEPTH' in df.columns:
        try:
            fluid_level_float = float(fluid_level)
            df.loc[df['DEPTH'] <= fluid_level_float, 'RES(SG)'] = -999.25
            if str(fluid_level).upper() == 'DRY':
                print(f"{las_file_path.name}: RES(SG) set to -999.25 due to DRY fluid level")
        except ValueError:
            # If fluid_level is not numeric, skip numeric comparison
            if str(fluid_level).upper() == 'DRY':
                df['RES(SG)'] = -999.25
                print(f"{las_file_path.name}: RES(SG) set to -999.25 due to DRY fluid level")

    # --- 7. Rename DENSITY:1 and DENSITY:2 headers (curve headers only) ---
    for curve in las.curves:
        if curve.mnemonic == "DENSITY:1":
            curve.mnemonic = "DENSITY"
            changes.append("Curve header DENSITY:1 → DENSITY (values unchanged)")
        elif curve.mnemonic == "DENSITY:2":
            curve.mnemonic = "DENSITY"
            changes.append("Curve header DENSITY:2 → DENSITY (values unchanged)")

    # --- 8. Update LAS curves data ---
    for curve in las.curves:
        if curve.mnemonic in df.columns:
            curve.data = df[curve.mnemonic].values

    # --- 9. Ensure output folder exists ---
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    # --- 10. Write LAS normally first ---
    output_path = output_folder / las_file_path.name
    las.write(str(output_path), version=2.0, spacer="  ", data_section_header='~A', fmt="%.2f")

    # --- 11. Build ~A line with fixed spacing ---
    with open(output_path, 'r') as f:
        lines = f.readlines()

    a_index = next(i for i, line in enumerate(lines) if line.strip().upper().startswith("~A"))

    # --- 11b. Define two sets of fixed widths ---
    fixed_widths_with_gamma = {
        "DEPTH": 10,
        "GAMMA": 8,
        "GAMMA_M": 11,
        "SUSCEP": 8,
        "MAG-VECT": 14,
        "TILD": 10,
        "AZID": 7,
        "AZIMUTH": 13,
        "NDEV": 10,
        "EDEV": 6,
        "DISTANCE": 11,
        "GAMMA_D": 10,
        "CALIPER": 10,
        "DENSITY": 10,
        "RES(SG)": 10,
        "VOLTAGE": 8,
    }

    fixed_widths_no_gamma = {
        "DEPTH": 8,
        "GAMMA_M": 11,
        "SUSCEP": 8,
        "MAG-VECT": 14,
        "TILD": 10,
        "AZID": 7,
        "AZIMUTH": 13,
        "NDEV": 10,
        "EDEV": 6,
        "DISTANCE": 11,
        "GAMMA_D": 10,
        "CALIPER": 10,
        "DENSITY": 10,
        "RES(SG)": 10,
        "VOLTAGE": 8,
    }

    # Choose which widths to use depending on presence of GAMMA curve
    has_inrod_gamma = any(curve.mnemonic.upper() == 'GAMMA' for curve in las.curves)
    fixed_widths = fixed_widths_with_gamma if has_inrod_gamma else fixed_widths_no_gamma

    # Build the ~A line with 4 spaces after ~A, 2 spaces between columns
    curve_names_line = "~A" + "    "  # 4 spaces between ~A and first curve
    for i, curve in enumerate(las.curves):
        width = fixed_widths.get(curve.mnemonic, 10)
        if i == 0:
            curve_names_line += curve.mnemonic.ljust(width)
        else:
            curve_names_line += "  " + curve.mnemonic.ljust(width)

    # Replace the ~A line in the LAS file
    lines[a_index] = curve_names_line + "\n"

    # Write back updated LAS
    with open(output_path, 'w') as f:
        f.writelines(lines)

    # --- Print summary ---
    print(f"Processed LAS: {las_file_path.name}")
    print(f"~A line: {curve_names_line}")
    if changes:
        for change in changes:
            print(f"  - {change}")
    else:
        print("  - No changes applied")
    print("=" * 80)

    return las

# --- Example usage ---
if __name__ == "__main__":
    input_folder = Path(r"C:\2025_FMG IRONBRIDGE\Calibration\FIELD\2026\CALIBRATION_IBD0042_260127_2501\IBD0042_260127_2501 shifted")
    output_folder = Path(r"C:\2025_FMG IRONBRIDGE\Calibration\FIELD\2026\CALIBRATION_IBD0042_260127_2501\IBD0042_260127_2501 shifted")

    for las_file in input_folder.glob("*.las"):
        process_las_file(las_file, output_folder)

import json
import os
import pandas as pd

def run(products_json: str, output_excel: str = None) -> dict:
    print("\n" + "="*50)
    print("STEP 3: Flattening products...")
    print("="*50)

    if not os.path.exists(products_json):
        print(f"No products file found ({products_json}).")
        return {"rows": 0, "columns": 0, "df": pd.DataFrame()}

    rows = []
    with open(products_json, "r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
                # Flatten lists to strings
                row["phones"]    = ", ".join(row.get("phones", []))
                row["whatsapps"] = ", ".join(row.get("whatsapps", []))
                row["images"]    = ", ".join(row.get("images", []))
                # Flatten specs
                specs = row.pop("specifications", {}) or {}
                for k, v in specs.items():
                    row[f"spec_{k}"] = v
                row.pop("images_local_paths", None)
                rows.append(row)
            except Exception:
                pass

    df = pd.DataFrame(rows)
    print(f"Flattened {len(df)} rows, {len(df.columns)} columns")

    return {"rows": len(df), "columns": len(df.columns), "df": df}
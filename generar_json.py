import json
import os
import pandas as pd

CSV_FILE = "historico_generacion_rer.csv"
JSON_OUTPUT = "data/data.json"


def csv_a_json():
    if not os.path.exists(CSV_FILE):
        print(f"❌ No se encontró el archivo {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)
    df.columns = df.columns.str.strip()

    cols_reservadas = ["Fecha", "Intervalo"]
    centrales = [col for col in df.columns if col not in cols_reservadas]

    # Convertir fecha a datetime parseando el día primero (DD/MM/YYYY o YYYY-MM-DD)
    df["Fecha_DT"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Fecha_DT"])

    # Estandarizar a formato texto YYYY-MM-DD
    df["Fecha_ISO"] = df["Fecha_DT"].dt.strftime("%Y-%m-%d")

    fechas_iso = sorted(df["Fecha_ISO"].unique().tolist())
    intervalos = df["Intervalo"].unique().tolist()

    datos_dict = {c: {} for c in centrales}

    # Agrupar por la clave estandarizada YYYY-MM-DD
    for fecha_iso_str, grupo in df.groupby("Fecha_ISO"):
        grupo_ord = grupo.sort_values(by="Intervalo")
        key_fecha = str(fecha_iso_str).strip()

        for c in centrales:
            vals = (
                pd.to_numeric(grupo_ord[c], errors="coerce")
                .fillna(0.0)
                .astype(float)
                .tolist()
            )
            datos_dict[c][key_fecha] = vals

    json_final = {
        "intervalos": intervalos,
        "fechas": fechas_iso,
        "centrales": centrales,
        "datos": datos_dict,
    }

    os.makedirs("data", exist_ok=True)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    print(
        f"✅ JSON regenerado: {len(fechas_iso)} días procesados desde {fechas_iso[0]} hasta {fechas_iso[-1]}."
    )


if __name__ == "__main__":
    csv_a_json()

import json
import os
import pandas as pd

CSV_FILE = "historico_generacion_rer.csv"
JSON_OUTPUT = "data/data.json"


def csv_a_json():
    if not os.path.exists(CSV_FILE):
        print(f"❌ No se encontró el archivo {CSV_FILE}")
        return

    # 1. Leer CSV
    df = pd.read_csv(CSV_FILE)
    df.columns = df.columns.str.strip()

    cols_reservadas = ["Fecha", "Intervalo"]
    centrales = [col for col in df.columns if col not in cols_reservadas]

    # 2. Parseo seguro de fecha a ISO string (YYYY-MM-DD)
    df["Fecha_DT"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Fecha_DT"])
    df["Fecha_ISO"] = df["Fecha_DT"].dt.strftime("%Y-%m-%d")

    # 3. Lista de fechas ordenadas e intervalos
    fechas_iso = sorted(df["Fecha_ISO"].unique().tolist())
    intervalos = df["Intervalo"].unique().tolist()

    # 4. Construcción del diccionario de datos por Central
    datos_dict = {c: {} for c in centrales}

    # Agrupar por la fecha ISO estandarizada
    for fecha_str, grupo in df.groupby("Fecha_ISO"):
        # Asegurar orden por Intervalo
        grupo_ord = grupo.sort_values(by="Intervalo")

        for c in centrales:
            # Extraer números nativos de Python para evitar errores de serialización en JSON
            vals = (
                pd.to_numeric(grupo_ord[c], errors="coerce")
                .fillna(0.0)
                .astype(float)
                .tolist()
            )
            datos_dict[c][str(fecha_str)] = vals

    json_final = {
        "intervalos": intervalos,
        "fechas": fechas_iso,
        "centrales": centrales,
        "datos": datos_dict,
    }

    # 5. Guardar JSON en data/data.json
    os.makedirs("data", exist_ok=True)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    print(f"✅ Éxito: {len(fechas_iso)} días procesados en {JSON_OUTPUT}")
    if fechas_iso:
        print(
            f"📅 Fechas cargadas: desde {fechas_iso[0]} hasta {fechas_iso[-1]}"
        )


if __name__ == "__main__":
    csv_a_json()

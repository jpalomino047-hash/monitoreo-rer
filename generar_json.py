import json
import os
import pandas as pd

CSV_FILE = "historico_generacion_rer.csv"
JSON_OUTPUT = "data/data.json"


def csv_a_json():
    # Buscar el CSV en el directorio actual o en la carpeta raíz
    ruta_csv = (
        CSV_FILE
        if os.path.exists(CSV_FILE)
        else os.path.join("..", CSV_FILE)
    )

    if not os.path.exists(ruta_csv):
        print(f"❌ No se encontró el archivo {CSV_FILE}")
        return

    print(f"📖 Leyendo {ruta_csv}...")
    df = pd.read_csv(ruta_csv)
    df.columns = df.columns.str.strip()

    cols_reservadas = ["Fecha", "Intervalo"]
    centrales = [col for col in df.columns if col not in cols_reservadas]

    # Clean string de la columna Fecha
    df["Fecha_Clean"] = df["Fecha"].astype(str).str.strip()

    # Parseo de fechas ultra-robusto
    # Maneja tanto YYYY-MM-DD como DD/MM/YYYY y DD/MM/YY
    df["Fecha_DT"] = pd.to_datetime(
        df["Fecha_Clean"], format="mixed", dayfirst=True, errors="coerce"
    )

    # Eliminar filas donde la fecha no sea válida
    df_valid = df.dropna(subset=["Fecha_DT"]).copy()

    # Forzar formato ISO estándar YYYY-MM-DD
    df_valid["Fecha_ISO"] = df_valid["Fecha_DT"].dt.strftime("%Y-%m-%d")

    fechas_iso = sorted(df_valid["Fecha_ISO"].unique().tolist())
    intervalos = df_valid["Intervalo"].unique().tolist()

    print(f"🔍 TOTAL DE DÍAS ENCONTRADOS: {len(fechas_iso)}")
    if fechas_iso:
        print(f"📅 Primera fecha detectada: {fechas_iso[0]}")
        print(f"📅 Última fecha detectada:   {fechas_iso[-1]}")

    datos_dict = {c: {} for c in centrales}

    # Agrupar por Fecha_ISO
    for fecha_iso_str, grupo in df_valid.groupby("Fecha_ISO"):
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

    print(f"✅ Archivo exportado exitosamente a {JSON_OUTPUT}")


if __name__ == "__main__":
    csv_a_json()

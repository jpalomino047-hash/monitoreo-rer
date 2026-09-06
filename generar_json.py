import json
import os
import pandas as pd

# Detectar la carpeta donde está guardado este script (Downloads)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "historico_generacion_rer.csv")
JSON_OUTPUT = os.path.join(BASE_DIR, "data", "data.json")


def csv_a_json():
    if not os.path.exists(CSV_FILE):
        print(f"❌ No se encontró el archivo en: {CSV_FILE}")
        return

    print(f"📖 Leyendo CSV desde: {CSV_FILE}")
    df = pd.read_csv(CSV_FILE)
    df.columns = df.columns.str.strip()

    cols_reservadas = ["Fecha", "Intervalo"]
    centrales = [col for col in df.columns if col not in cols_reservadas]

    # Parseo robusto de fecha a formato ISO YYYY-MM-DD
    df["Fecha_Clean"] = df["Fecha"].astype(str).str.strip()
    df["Fecha_DT"] = pd.to_datetime(
        df["Fecha_Clean"], format="mixed", dayfirst=True, errors="coerce"
    )

    df_valid = df.dropna(subset=["Fecha_DT"]).copy()
    df_valid["Fecha_ISO"] = df_valid["Fecha_DT"].dt.strftime("%Y-%m-%d")

    fechas_iso = sorted(df_valid["Fecha_ISO"].unique().tolist())
    intervalos = df_valid["Intervalo"].unique().tolist()

    print(f"🔍 TOTAL DE DÍAS ENCONTRADOS: {len(fechas_iso)}")
    if fechas_iso:
        print(f"📅 Primera fecha: {fechas_iso[0]}")
        print(f"📅 Última fecha:   {fechas_iso[-1]}")

    datos_dict = {c: {} for c in centrales}

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

    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    print(f"✅ Archivo exportado exitosamente a: {JSON_OUTPUT}")


if __name__ == "__main__":
    csv_a_json()

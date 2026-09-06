import json
import os
import pandas as pd

CSV_FILE = "historico_generacion_rer.csv"
JSON_OUTPUT = "data/data.json"


def csv_a_json():
    if not os.path.exists(CSV_FILE):
        print(f"❌ No se encontró el archivo {CSV_FILE}")
        return

    # Leer CSV asegurando limpieza de columnas
    df = pd.read_csv(CSV_FILE)
    df.columns = df.columns.str.strip()

    cols_reservadas = ["Fecha", "Intervalo"]
    centrales = [col for col in df.columns if col not in cols_reservadas]

    # Parseo estricto de fechas (Maneja DD/MM/YYYY, YYYY-MM-DD y años con 2 dígitos)
    df["Fecha_Clean"] = df["Fecha"].astype(str).str.strip()
    df["Fecha_DT"] = pd.to_datetime(
        df["Fecha_Clean"], format="mixed", dayfirst=True, errors="coerce"
    )

    # Eliminar filas con fecha no válida
    df_valid = df.dropna(subset=["Fecha_DT"]).copy()

    # Forzar formato ISO YYYY-MM-DD con ceros a la izquierda (ej. 2026-01-01)
    df_valid["Fecha_ISO"] = df_valid["Fecha_DT"].dt.strftime("%Y-%m-%d")

    fechas_iso = sorted(df_valid["Fecha_ISO"].unique().tolist())
    intervalos = sorted(df_valid["Intervalo"].unique().tolist())

    print(
        f"✅ Días procesados: {len(fechas_iso)} | Desde: {fechas_iso[0]} Hasta: {fechas_iso[-1]}"
    )

    datos_dict = {c: {} for c in centrales}

    # Agrupar por la clave ISO estandarizada
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
            # Asegurar que siempre contenga los 48 tramos del día
            if len(vals) < 48:
                vals += [0.0] * (48 - len(vals))
            datos_dict[c][key_fecha] = vals[:48]

    json_final = {
        "intervalos": intervalos,
        "fechas": fechas_iso,
        "centrales": centrales,
        "datos": datos_dict,
    }

    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    print(f"🚀 Archivo actualizado correctamente en {JSON_OUTPUT}")


if __name__ == "__main__":
    csv_a_json()

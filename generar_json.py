import json
import os
import pandas as pd

CSV_FILE = "historico_generacion_rer.csv"
JSON_OUTPUT = "data/data.json"


def csv_a_json():
    if not os.path.exists(CSV_FILE):
        print(f"❌ No se encontró el archivo {CSV_FILE}")
        return

    # Leer CSV
    df = pd.read_csv(CSV_FILE)

    # Limpieza de columnas
    df.columns = df.columns.str.strip()

    # Columnas reservadas
    cols_reservadas = ["Fecha", "Intervalo"]
    centrales = [col for col in df.columns if col not in cols_reservadas]

    # 1. PARSEO ROBUSTO DE FECHAS (Soporta DD/MM/YYYY, YYYY-MM-DD, etc.)
    # dayfirst=True maneja fechas tipo 15/01/2026 correctamente
    df["Fecha_DT"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")

    # Eliminar filas donde la fecha no se pudo parsear
    df = df.dropna(subset=["Fecha_DT"])

    # Crear columna con formato estandarizado ISO (YYYY-MM-DD)
    df["Fecha_ISO"] = df["Fecha_DT"].dt.strftime("%Y-%m-%d")

    # Obtener fechas únicas e intervalos
    fechas_iso = sorted(df["Fecha_ISO"].unique().tolist())
    intervalos = df["Intervalo"].unique().tolist()

    # Estructurar datos por Central -> Fecha_ISO -> Lista de valores por intervalo
    datos_dict = {c: {} for c in centrales}

    # Agrupar por la fecha estandarizada
    for fecha_iso, grupo in df.groupby("Fecha_ISO"):
        # Asegurar el orden interno por Intervalo
        grupo_ordenado = grupo.sort_values(by="Intervalo")
        for c in centrales:
            valores = (
                pd.to_numeric(grupo_ordenado[c], errors="coerce")
                .fillna(0.0)
                .tolist()
            )
            datos_dict[c][fecha_iso] = valores

    # Crear objeto JSON final
    json_final = {
        "intervalos": intervalos,
        "fechas": fechas_iso,
        "centrales": centrales,
        "datos": datos_dict,
    }

    # Guardar en data/data.json
    os.makedirs("data", exist_ok=True)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    print(
        f"✅ Se actualizó exitosamente {JSON_OUTPUT} con {len(fechas_iso)} días cargados."
    )
    if fechas_iso:
        print(f"📅 Rango cargado: desde {fechas_iso[0]} hasta {fechas_iso[-1]}")


if __name__ == "__main__":
    csv_a_json()

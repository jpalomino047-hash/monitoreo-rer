import os
import json
import pandas as pd

CSV_FILE = "historico_generacion_rer.csv"
JSON_OUTPUT = "data/data.json"

def csv_a_json():
    if not os.path.exists(CSV_FILE):
        print(f"❌ No se encontró el archivo {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)
    
    # Limpieza de columnas
    df.columns = df.columns.str.strip()
    
    # Columnas reservadas
    cols_reservadas = ["Fecha", "Intervalo"]
    centrales = [col for col in df.columns if col not in cols_reservadas]
    
    # Obtener intervalos únicos ordenados (48 bloques)
    intervalos = df["Intervalo"].unique().tolist()
    
    # Obtener fechas únicas formateadas a YYYY-MM-DD para compatibilidad con JavaScript
    fechas_raw = df["Fecha"].unique()
    fechas_iso = []
    mapa_fechas = {}
    
    for f in fechas_raw:
        try:
            # Convertir DD/MM/YYYY a YYYY-MM-DD
            partes = str(f).split('/')
            if len(partes) == 3:
                f_iso = f"{partes[2]}-{partes[1].zfill(2)}-{partes[0].zfill(2)}"
            else:
                f_iso = str(f)
            fechas_iso.append(f_iso)
            mapa_fechas[f] = f_iso
        except:
            pass

    fechas_iso = sorted(list(set(fechas_iso)))

    # Estructurar datos por Central -> Fecha -> Lista de 48 valores
    datos_dict = {c: {} for c in centrales}
    
    for fecha_orig, grupo in df.groupby("Fecha"):
        fecha_key = mapa_fechas.get(fecha_orig, fecha_orig)
        for c in centrales:
            # Reemplazar valores NaN por 0.0
            valores = pd.to_numeric(grupo[c], errors='coerce').fillna(0.0).tolist()
            datos_dict[c][fecha_key] = valores

    # Crear objeto JSON final
    json_final = {
        "intervalos": intervalos,
        "fechas": fechas_iso,
        "centrales": centrales,
        "datos": datos_dict
    }

    # Guardar en data/data.json
    os.makedirs("data", exist_ok=True)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Se actualizó exitosamente {JSON_OUTPUT} con {len(fechas_iso)} días cargados.")

if __name__ == "__main__":
    csv_a_json()

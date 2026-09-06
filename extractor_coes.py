import os
import requests
import pandas as pd
from datetime import datetime, timedelta

BASE_URL = "https://www.coes.org.pe/portal/browser/download?url=Post%20Operaci%C3%B3n%2FReportes%2FIEOD"
CSV_FILE = "historico_generacion_rer.csv"
TEMP_EXCEL = "temp_ieod.xlsx"

def obtener_fecha_ayer():
    # Ayer (si se ejecuta hoy 6 de septiembre, intentará la fecha del 5)
    return datetime.now() - timedelta(days=1)

def construir_url(fecha):
    year = fecha.strftime("%Y")
    month_num = fecha.strftime("%m")
    day = fecha.strftime("%d")
    
    meses = {
        "01": "01_Enero", "02": "02_Febrero", "03": "03_Marzo", "04": "04_Abril",
        "05": "05_Mayo", "06": "06_Junio", "07": "07_Julio", "08": "08_Agosto",
        "09": "09_Setiembre", "10": "10_Octubre", "11": "11_Noviembre", "12": "12_Diciembre"
    }
    mes_folder = meses.get(month_num, f"{month_num}_")
    
    url = f"{BASE_URL}%2F{year}%2F{mes_folder}%2F{day}%2FAnexoA_{day}{month_num}.xlsx"
    return url

def descargar_excel(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=30)
    
    # Validar status HTTP y que el archivo no sea una respuesta HTML de error/redirección
    if res.status_code == 200 and not res.content.startswith(b"<!DOCTYPE html") and not res.content.startswith(b"<html"):
        with open(TEMP_EXCEL, "wb") as f:
            f.write(res.content)
        return True
    return False

def procesar_excel(fecha_obj):
    try:
        df_raw = pd.read_excel(TEMP_EXCEL, sheet_name="GENERACION RER", header=None, engine="openpyxl")
    except Exception as e:
        print(f"❌ Error al procesar la hoja 'GENERACION RER': {e}")
        return None
    
    # Fila 7 (índice 6 en Pandas): Títulos de las centrales
    row_headers = df_raw.iloc[6].values
    
    # Filtrar columnas que correspondan a centrales eólicas (C.E.) o solares (C.S.)
    valid_cols = []
    col_names = []
    
    for i, name in enumerate(row_headers):
        if pd.notna(name):
            name_str = str(name).strip()
            if name_str.startswith(("C.E.", "CE ", "C.S.", "CS ")) or name_str in ["CE", "CS"]:
                valid_cols.append(i)
                col_names.append(name_str)
                
    if not valid_cols:
        print("⚠️ No se encontraron columnas RER válidas (C.E. / C.S.) en la fila 7 del archivo.")
        return None

    # Filas 8 a 55 (índices 7 a 54): 48 valores semihorarios
    df_data = df_raw.iloc[7:55, valid_cols].copy()
    df_data.columns = col_names
    
    # Generar intervalos semihorarios (00:30, 01:00, ..., 24:00)
    intervalos = []
    for h in range(1, 49):
        minutos = h * 30
        hrs = minutos // 60
        mins = minutos % 60
        intervalos.append(f"{hrs:02d}:{mins:02d}")
        
    fecha_str = fecha_obj.strftime("%d/%m/%Y")
    
    df_final = pd.DataFrame()
    df_final["Fecha"] = [fecha_str] * 48
    df_final["Intervalo"] = intervalos
    
    for col in col_names:
        df_final[col] = pd.to_numeric(df_data[col], errors='coerce').values
        
    return df_final

def actualizar_historico(df_nuevo):
    if os.path.exists(CSV_FILE):
        df_hist = pd.read_csv(CSV_FILE)
        
        # Evitar duplicar la fecha si ya existe en el histórico
        fecha_nueva = df_nuevo["Fecha"].iloc[0]
        if "Fecha" in df_hist.columns and fecha_nueva in df_hist["Fecha"].values:
            print(f"ℹ️ La fecha {fecha_nueva} ya existe en {CSV_FILE}. No se realiza ningún cambio.")
            return
            
        df_combinado = pd.concat([df_hist, df_nuevo], ignore_index=True)
    else:
        df_combinado = df_nuevo
        
    df_combinado.to_csv(CSV_FILE, index=False)
    print(f"✅ Se agregaron exitosamente los datos al archivo {CSV_FILE}")

def main():
    fecha_target = obtener_fecha_ayer()
    url = construir_url(fecha_target)
    print(f"Descargando datos del COES para la fecha: {fecha_target.strftime('%d/%m/%Y')}...")
    print(f"URL objetivo: {url}")
    
    if descargar_excel(url):
        try:
            df_nuevo = procesar_excel(fecha_target)
            if df_nuevo is not None:
                actualizar_historico(df_nuevo)
        finally:
            if os.path.exists(TEMP_EXCEL):
                os.remove(TEMP_EXCEL)
    else:
        print(f"❌ No se pudo descargar el Excel del día {fecha_target.strftime('%d/%m/%Y')}. Es probable que el COES aún no publique dicho archivo.")

if __name__ == "__main__":
    main()

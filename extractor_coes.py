import os
import requests
import pandas as pd
from datetime import datetime, timedelta

BASE_URL = "https://www.coes.org.pe/portal/browser/download?url=Post%20Operaci%C3%B3n%2FReportes%2FIEOD"
CSV_FILE = "historico_generacion_rer.csv"
TEMP_EXCEL = "temp_ieod.xlsx"

def obtener_fecha_ayer():
    # Ayer (por ejemplo, si hoy es 2 de septiembre, descarga el del 1 de septiembre)
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
    if res.status_code == 200:
        with open(TEMP_EXCEL, "wb") as f:
            f.write(res.content)
        return True
    return False

def procesar_excel(fecha_obj):
    # Cargar pestaña GENERACION RER
    df_raw = pd.read_excel(TEMP_EXCEL, sheet_name="GENERACION RER", header=None)
    
    # Fila 7 (índice 6 en Pandas): Títulos de las centrales
    row_headers = df_raw.iloc[6].values
    
    # Filtrar columnas que sean C.E., CE, C.S. o CS
    valid_cols = []
    col_names = []
    
    for i, name in enumerate(row_headers):
        if pd.notna(name):
            name_str = str(name).strip()
            if name_str.startswith(("C.E.", "CE ", "C.S.", "CS ")) or name_str in ["CE", "CS"]:
                valid_cols.append(i)
                col_names.append(name_str)
                
    if not valid_cols:
        print("⚠️ No se encontraron columnas RER (C.E. / C.S.) en la fila 7.")
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
        
        # Evitar duplicar la fecha si ya fue cargada anteriormente
        fecha_nueva = df_nuevo["Fecha"].iloc[0]
        if "Fecha" in df_hist.columns and fecha_nueva in df_hist["Fecha"].values:
            print(f"ℹ️ La fecha {fecha_nueva} ya existe en el histórico. No se duplica.")
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
    print(f"URL: {url}")
    
    if descargar_excel(url):
        try:
            df_nuevo = procesar_excel(fecha_target)
            if df_nuevo is not None:
                actualizar_historico(df_nuevo)
        finally:
            if os.path.exists(TEMP_EXCEL):
                os.remove(TEMP_EXCEL)
    else:
        print("❌ No se pudo descargar el archivo. Es posible que aún no esté publicado en el portal del COES.")

if __name__ == "__main__":
    main()

import os
import io
import re
import zipfile
import warnings
import requests
import pandas as pd
from datetime import datetime, timedelta
from openpyxl import load_workbook

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
requests.packages.urllib3.disable_warnings()

# 1. Calcular automáticamente el día de ayer en la zona horaria de Perú (GMT-5)
hora_peru = datetime.utcnow() - timedelta(hours=5)
ayer = hora_peru - timedelta(days=1)

dia_str = ayer.strftime("%d")     
mes_num = ayer.strftime("%m")     
anio_str = ayer.strftime("%Y")    

meses_es = {
    "01": "01_Enero", "02": "02_Febrero", "03": "03_Marzo", "04": "04_Abril",
    "05": "05_Mayo", "06": "06_Junio", "07": "07_Julio", "08": "08_Agosto",
    "09": "09_Septiembre", "10": "10_Octubre", "11": "11_Noviembre", "12": "12_Diciembre"
}
mes_carpeta = meses_es[mes_num]

url = (
    f"https://www.coes.org.pe/portal/browser/download?url=Post%20Operaci%C3%B3n"
    f"%2FReportes%2FIEOD%2F{anio_str}%2F{mes_carpeta}%2F{dia_str}%2FAnexoA_{dia_str}{mes_num}.xlsx"
)

filename = f"AnexoA_{dia_str}{mes_num}.xlsx"
print(f"Fecha de procesamiento (Ayer): {ayer.strftime('%Y-%m-%d')}")
print(f"Descargando desde COES: {filename}")

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

try:
    response = requests.get(url, headers=headers, verify=False, timeout=30)
    if response.status_code != 200:
        print(f"[Error] Archivo no disponible en el servidor del COES (Status: {response.status_code}).")
        exit(0)
except Exception as e:
    print(f"[Error] Fallo crítico de conexión: {e}")
    exit(1)

content_bytes = io.BytesIO(response.content)
if not zipfile.is_zipfile(content_bytes):
    print("[Error] El archivo descargado no es un archivo Excel válido (Zip corrupted).")
    exit(0)

try:
    wb = load_workbook(filename=content_bytes, data_only=True)
    if "GENERACION RER" not in wb.sheetnames:
        print("[Error] No se encontró la pestaña 'GENERACION RER'.")
        exit(0)
    ws = wb["GENERACION RER"]
except Exception as e:
    print(f"[Error] No se pudo estructurar el Excel: {e}")
    exit(1)

fecha_formateada = ayer.strftime("%Y-%m-%d")
centrales_detectadas = {}

for col in range(1, ws.max_column + 1):
    celda_val = ws.cell(row=7, column=col).value
    if celda_val:
        texto_celda = str(celda_val).strip().upper()
        es_eolica = bool(re.search(r'\bC\.E\.|\bCE\b', texto_celda))
        es_solar = bool(re.search(r'\bC\.S\.|\bCS\b', texto_celda))
        
        if es_eolica or es_solar:
            tipo_completo = "Eólica" if es_eolica else "Solar"
            centrales_detectadas[col] = {
                'nombre': str(celda_val).strip(),
                'tipo': tipo_completo
            }

datos_dia = []
for row in range(8, 56):
    intervalo = ws.cell(row=row, column=2).value or ws.cell(row=row, column=1).value
    registro = {
        'Fecha': fecha_formateada,
        'Intervalo': str(intervalo).strip() if intervalo else f"H_{row-7}"
    }
    
    for col, info in centrales_detectadas.items():
        val = ws.cell(row=row, column=col).value
        try:
            registro[info['nombre']] = float(val) if val is not None else 0.0
        except ValueError:
            registro[info['nombre']] = 0.0
        
    datos_dia.append(registro)

df_nuevo = pd.DataFrame(datos_dia)

if not df_nuevo.empty:
    columnas_activas = ['Fecha', 'Intervalo']
    for col in df_nuevo.columns:
        if col in ['Fecha', 'Intervalo']:
            continue
        if df_nuevo[col].abs().sum() > 0.01:
            columnas_activas.append(col)
    df_nuevo = df_nuevo[columnas_activas]

csv_historico = "historico_generacion_rer.csv"

if os.path.exists(csv_historico):
    print("Actualizando archivo histórico existente...")
    df_antiguo = pd.read_csv(csv_historico)
    df_antiguo = df_antiguo[df_antiguo['Fecha'] != fecha_formateada]
    df_consolidado = pd.concat([df_antiguo, df_nuevo], ignore_index=True)
else:
    print("Creando nuevo archivo histórico...")
    df_consolidado = df_nuevo

columnas_ordenadas = ['Fecha', 'Intervalo'] + [c for c in df_consolidado.columns if c not in ['Fecha', 'Intervalo']]
df_consolidado = df_consolidado[columnas_ordenadas]

df_consolidado.to_csv(csv_historico, index=False, encoding='utf-8')
print(f"¡Éxito! Datos guardados en {csv_historico}. Filas actuales: {df_consolidado.shape[0]}")

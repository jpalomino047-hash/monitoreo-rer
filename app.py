import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Monitoreo RER - Perfil de Generación",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Monitoreo RER - Perfiles de Generación Diario")
st.markdown("Visualización superpuesta del perfil de generación diaria por central y mes.")

# -----------------------------------------------------------------------------
# CARGA Y PARSEO ROBUSTO DE DATOS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos():
    url_raw = "https://raw.githubusercontent.com/jpalomino047-hash/monitoreo-rer/main/historico_generacion_rer.csv"
    df = pd.read_csv(url_raw)
    
    # Limpiar espacios en los nombres de las columnas
    df.columns = df.columns.str.strip()
    
    # Identificar la columna de fecha/hora (asumimos la primera columna)
    col_fecha = df.columns[0]
    
    # Asegurar que la primera columna sea texto sin espacios
    df[col_fecha] = df[col_fecha].astype(str).str.strip()
    
    # Convertir todas las demás columnas (centrales) a números float
    for col in df.columns[1:]:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(',', '.').str.strip()
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # TÁCTICA PARA EXTRAER FECHA Y HORA SIN PASAR POR PD.TO_DATETIME FRÁGIL:
    # 1. Intentar parsear con dayfirst=True
    fecha_dt = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
    
    # 2. Si falló la fecha completa, creamos los componentes
    df['año'] = fecha_dt.dt.year
    df['mes_num'] = fecha_dt.dt.month
    df['dia'] = fecha_dt.dt.day
    
    # Rellenar años/meses/días si vinieron nulos intentando parsing alternativo
    if df['año'].isna().all():
        # Asumir que la columna tiene formato "DD/MM/YYYY HH:MM" o similar
        partes = df[col_fecha].str.split(' ', expand=True)
        if partes.shape[1] >= 2:
            fechas_parte = pd.to_datetime(partes[0], dayfirst=True, errors='coerce')
            df['año'] = fechas_parte.dt.year
            df['mes_num'] = fechas_parte.dt.month
            df['dia'] = fechas_parte.dt.day
            horas_parte = partes[1]
        else:
            horas_parte = df[col_fecha]
    else:
        horas_parte = fecha_dt.dt.strftime('%H:%M')

    # Convertir "H:MM" a valor decimal continuo de 0 a 24 para el eje X
    def hora_a_decimal(cadena_hora):
        try:
            cadena_hora = str(cadena_hora).strip()
            if ':' in cadena_hora:
                h, m = cadena_hora.split(':')[:2]
                val = float(h) + float(m)/60.0
                return 24.0 if (val == 0.0 and h != '0' and h != '00') else val
            return np.nan
        except:
            return np.nan

    df['hora_decimal'] = horas_parte.apply(hora_a_decimal)
    
    # Si hora_decimal sigue teniendo nulos, asignar secuencia basada en frecuencia (48 bloques/día)
    if df['hora_decimal'].isna().any():
        # Asignar un índice de 0 a 47 repetitivo para asegurar 48 intervalos por día
        df['hora_decimal'] = df.groupby(['año', 'mes_num', 'dia']).cumcount() * 0.5

    return df, col_fecha

try:
    df_raw, col_fecha = cargar_datos()
except Exception as e:
    st.error(f"Error al procesar el archivo CSV: {e}")
    st.stop()

# Lista de columnas de centrales
cols_excluir = ['año', 'mes_num', 'dia', 'hora_decimal', col_fecha]
cols_centrales = [c for c in df_raw.columns if c not in cols_excluir]

# -----------------------------------------------------------------------------
# FILTROS
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 Filtros")

# Filtrar Años válidos
años_validos = df_raw['año'].dropna().unique()
if len(años_validos) > 0:
    años_disp = sorted(años_validos.astype(int), reverse=True)
    año_sel = st.sidebar.selectbox("Año", options=años_disp)
else:
    año_sel = None

mes_map = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 
           7: 'Julio', 8: 'Agosto', 9: 'Setiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}

if año_sel:
    df_año = df_raw[df_raw['año'] == año_sel]
    meses_disp = sorted(df_año['mes_num'].dropna().unique().astype(int))
    mes_sel = st.sidebar.selectbox("Mes", options=meses_disp, format_func=lambda x: mes_map.get(x, str(x)))
else:
    mes_sel = None

central_sel = st.sidebar.selectbox("Central / Serie", options=cols_centrales)

# Filtrado final
if año_sel and mes_sel:
    df_fil = df_raw[(df_raw['año'] == año_sel) & (df_raw['mes_num'] == mes_sel)].copy()
else:
    df_fil = df_raw.copy()

# -----------------------------------------------------------------------------
# GRÁFICO
# -----------------------------------------------------------------------------
if central_sel and not df_fil.empty:

    # Métricas
    col1, col2, col3 = st.columns(3)
    pmax = df_fil[central_sel].max()
    pmed = df_fil[central_sel].mean()
    
    col1.metric("Potencia Máxima (PMAX)", f"{pmax:.2f} MW" if pd.notna(pmax) else "0.00 MW")
    col2.metric("Potencia Promedio", f"{pmed:.2f} MW" if pd.notna(pmed) else "0.00 MW")
    col3.metric("Registros en el Mes", len(df_fil))

    st.markdown("---")

    fig = go.Figure()

    # 1. Trazar perfiles por cada día
    dias = sorted(df_fil['dia'].dropna().unique())
    for d in dias:
        df_d = df_fil[df_fil['dia'] == d].sort_values('hora_decimal')
        if not df_d.empty:
            fig.add_trace(go.Scatter(
                x=df_d['hora_decimal'],
                y=df_d[central_sel],
                mode='lines',
                line=dict(width=1, color='rgba(160, 160, 160, 0.35)'),
                name=f"Día {int(d)}",
                showlegend=False,
                connectgaps=True,
                hovertemplate=f"Día {int(d)} | Hora: %{{x:.2f}}h<br>Potencia: %{{y:.2f}} MW<extra></extra>"
            ))

    # 2. Trazar Promedio Mensual
    df_prom = df_fil.groupby('hora_decimal')[central_sel].mean().reset_index().sort_values('hora_decimal')

    if not df_prom.empty:
        fig.add_trace(go.Scatter(
            x=df_prom['hora_decimal'],
            y=df_prom[central_sel],
            mode='lines+markers',
            marker=dict(size=4),
            line=dict(width=3.5, color='#0068C9'),
            name="Media Mensual",
            connectgaps=True,
            hovertemplate="<b>Media Mensual</b><br>Hora: %{x:.2f}h<br>Potencia Promedio: %{y:.2f} MW<extra></extra>"
        ))

    # Formateo visual del Eje X (00:00 a 24:00)
    tick_vals = list(range(0, 25, 2))
    tick_text = [f"{h:02d}:00" for h in range(0, 25, 2)]

    fig.update_layout(
        title=f"Perfil Diario Superpuesto - {central_sel} ({mes_map.get(mes_sel, '')} {año_sel})",
        xaxis=dict(
            title="Hora del Día",
            tickmode='array',
            tickvals=tick_vals,
            ticktext=tick_text,
            range=[-0.2, 24.2]
        ),
        yaxis=dict(title="Potencia (MW)", zeroline=True),
        template="plotly_white",
        height=550
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No hay datos disponibles para mostrar.")

# Expander de control
with st.expander("📥 Ver tabla de datos filtrada (Revisa que la columna de hora no sea None)"):
    st.dataframe(df_fil)

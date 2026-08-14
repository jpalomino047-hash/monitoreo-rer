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
# CARGA Y PARSEO DE DATOS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos():
    url_raw = "https://raw.githubusercontent.com/jpalomino047-hash/monitoreo-rer/main/historico_generacion_rer.csv"
    df = pd.read_csv(url_raw)
    
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Identificar la columna de fecha
    col_fecha = df.columns[0]
    for col in df.columns:
        if any(term in col.lower() for term in ['fecha', 'time', 'timestamp', 'date', 'hora']):
            col_fecha = col
            break

    # Parsear fechas usando el parser flexible de pandas
    df['fecha_parsed'] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['fecha_parsed'])

    # Extraer componentes
    df['año'] = df['fecha_parsed'].dt.year
    df['mes_num'] = df['fecha_parsed'].dt.month
    df['dia'] = df['fecha_parsed'].dt.day
    
    # Eje X preciso: Hora en decimal de 0.0 a 23.75
    df['hora_decimal'] = df['fecha_parsed'].dt.hour + df['fecha_parsed'].dt.minute / 60.0 + df['fecha_parsed'].dt.second / 3600.0

    # Convertir variables numéricas (removiendo comas)
    cols_excluir = ['año', 'mes_num', 'dia', 'hora_decimal', 'fecha_parsed', col_fecha]
    for col in df.columns:
        if col not in cols_excluir:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '.').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df, col_fecha

try:
    df_raw, col_fecha = cargar_datos()
except Exception as e:
    st.error(f"Error al cargar/procesar los datos: {e}")
    st.stop()

# Centrales
cols_excluir = ['año', 'mes_num', 'dia', 'hora_decimal', 'fecha_parsed', col_fecha]
cols_centrales = [c for c in df_raw.columns if c not in cols_excluir]

# -----------------------------------------------------------------------------
# FILTROS
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 Filtros")

años_disp = sorted(df_raw['año'].dropna().unique().astype(int), reverse=True)
año_sel = st.sidebar.selectbox("Año", options=años_disp)

mes_map = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 
           7: 'Julio', 8: 'Agosto', 9: 'Setiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}

df_año = df_raw[df_raw['año'] == año_sel]
meses_disp = sorted(df_año['mes_num'].dropna().unique().astype(int))
mes_sel = st.sidebar.selectbox("Mes", options=meses_disp, format_func=lambda x: mes_map.get(x, str(x)))

central_sel = st.sidebar.selectbox("Central / Serie", options=cols_centrales)

# Data filtrada del mes
df_fil = df_raw[(df_raw['año'] == año_sel) & (df_raw['mes_num'] == mes_sel)].copy()

# -----------------------------------------------------------------------------
# GRÁFICA MULTI-LÍNEA SOBRE EJE 0-24 HRS
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

    # 1. Graficar líneas delgadas por cada día del mes
    dias = sorted(df_fil['dia'].unique())
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

    # 2. Graficar Promedio Mensual (Línea azul gruesa)
    # Redondeamos la hora decimal a 2 decimales para agrupar exactamente las medias horas (0.0, 0.5, 1.0...)
    df_fil['hora_agrupar'] = df_fil['hora_decimal'].round(2)
    df_prom = df_fil.groupby('hora_agrupar')[central_sel].mean().reset_index().sort_values('hora_agrupar')

    if not df_prom.empty:
        fig.add_trace(go.Scatter(
            x=df_prom['hora_agrupar'],
            y=df_prom[central_sel],
            mode='lines+markers',
            marker=dict(size=4),
            line=dict(width=3.5, color='#0068C9'),
            name="Media Mensual",
            connectgaps=True,
            hovertemplate="<b>Media Mensual</b><br>Hora: %{x:.2f}h<br>Potencia Promedio: %{y:.2f} MW<extra></extra>"
        ))

    # Formatear el Eje X numérico (0 a 24 hrs) para mostrar las etiquetas "00:00", "02:00", etc.
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
    st.warning("No hay datos disponibles.")

with st.expander("📥 Ver tabla de datos filtrada"):
    st.dataframe(df_fil)

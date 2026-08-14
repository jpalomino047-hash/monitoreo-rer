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
# CARGA DE DATOS DESDE GITHUB
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)  # Recarga automáticamente cada hora
def cargar_datos():
    url_raw = "https://raw.githubusercontent.com/jpalomino047-hash/monitoreo-rer/main/historico_generacion_rer.csv"
    df = pd.read_csv(url_raw)
    
    # Intentar detectar la columna de fecha/hora
    col_fecha = None
    for col in df.columns:
        if any(term in col.lower() for term in ['fecha', 'time', 'timestamp', 'date', 'hora']):
            col_fecha = col
            break
            
    if col_fecha:
        df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce')
        df['año'] = df[col_fecha].dt.year
        df['mes_num'] = df[col_fecha].dt.month
        df['dia'] = df[col_fecha].dt.day
        df['hora_decimal'] = df[col_fecha].dt.hour + df[col_fecha].dt.minute / 60.0
        df['hora_str'] = df[col_fecha].dt.strftime('%H:%M')
    
    return df, col_fecha

try:
    df_raw, col_fecha = cargar_datos()
except Exception as e:
    st.error(f"Error al cargar el archivo CSV desde GitHub: {e}")
    st.stop()

# Detectar columnas de central / generación
columnas = list(df_raw.columns)
cols_excluir = ['año', 'mes_num', 'dia', 'hora_decimal', 'hora_str', col_fecha]
cols_centrales = [c for c in columnas if c not in cols_excluir]

# -----------------------------------------------------------------------------
# FILTROS EN SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 Filtros")

if 'año' in df_raw.columns and df_raw['año'].notna().any():
    años_disponibles = sorted(df_raw['año'].dropna().unique().astype(int), reverse=True)
    año_sel = st.sidebar.selectbox("Año", options=años_disponibles)
else:
    año_sel = None

mes_map = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 
           7: 'Julio', 8: 'Agosto', 9: 'Setiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}

if 'mes_num' in df_raw.columns and df_raw['mes_num'].notna().any():
    if año_sel:
        meses_disp = sorted(df_raw[df_raw['año'] == año_sel]['mes_num'].dropna().unique().astype(int))
    else:
        meses_disp = sorted(df_raw['mes_num'].dropna().unique().astype(int))
    mes_sel = st.sidebar.selectbox("Mes", options=meses_disp, format_func=lambda x: mes_map.get(x, str(x)))
else:
    mes_sel = None

# Selección de Central o Variable
if cols_centrales:
    central_sel = st.sidebar.selectbox("Central / Serie", options=cols_centrales)
else:
    central_sel = None

# Filtrado de Data
df_fil = df_raw.copy()
if año_sel is not None:
    df_fil = df_fil[df_fil['año'] == año_sel]
if mes_sel is not None:
    df_fil = df_fil[df_fil['mes_num'] == mes_sel]

# -----------------------------------------------------------------------------
# GRÁFICA SUPERPUESTA DE PERFIL DIARIO
# -----------------------------------------------------------------------------
if central_sel and 'hora_decimal' in df_fil.columns and 'dia' in df_fil.columns:
    
    # KPIs rápidos
    col1, col2, col3 = st.columns(3)
    pmax = df_fil[central_sel].max()
    pmed = df_fil[central_sel].mean()
    
    col1.metric("Potencia Máxima (PMAX)", f"{pmax:.2f}" if pd.notna(pmax) else "-")
    col2.metric("Potencia Promedio", f"{pmed:.2f}" if pd.notna(pmed) else "-")
    col3.metric("Registros del Mes", len(df_fil))

    st.markdown("---")

    fig = go.Figure()

    # Perfiles diarios individuales (líneas delgadas y tenue)
    dias = sorted(df_fil['dia'].dropna().unique())
    for dia in dias:
        df_d = df_fil[df_fil['dia'] == dia].sort_values('hora_decimal')
        fig.add_trace(go.Scatter(
            x=df_d['hora_decimal'],
            y=df_d[central_sel],
            mode='lines',
            line=dict(width=1, color='rgba(150, 150, 150, 0.35)'),
            name=f"Día {int(dia)}",
            showlegend=False,
            hoverinfo='text',
            text=[f"Día {int(dia)} | Hora: {h} | Valor: {v:.2f}" for h, v in zip(df_d['hora_str'], df_d[central_sel])]
        ))

    # Curva Promedio Mensual (Resaltada)
    df_prom = df_fil.groupby('hora_decimal')[central_sel].mean().reset_index()
    fig.add_trace(go.Scatter(
        x=df_prom['hora_decimal'],
        y=df_prom[central_sel],
        mode='lines',
        line=dict(width=3.5, color='#0068C9'),
        name="Media Mensual",
        hovertemplate="<b>Media Mensual</b><br>Hora: %{x}:00<br>Valor Promedio: %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        title=f"Perfil Diario Superpuesto - {central_sel} ({mes_map.get(mes_sel, '')} {año_sel})",
        xaxis=dict(
            title="Hora del Día",
            tickmode='array',
            tickvals=list(range(0, 25, 2)),
            ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)],
            range=[0, 23.5]
        ),
        yaxis=dict(title="Generación / Potencia", zeroline=True),
        template="plotly_white",
        height=550
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Muestra de datos sin procesar:")
    st.dataframe(df_raw.head())

# Expander para ver tabla de datos
with st.expander("📥 Ver tabla de datos filtrada"):
    st.dataframe(df_fil)

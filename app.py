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
# CARGA Y LIMPIEZA DE DATOS DESDE GITHUB
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos():
    url_raw = "https://raw.githubusercontent.com/jpalomino047-hash/monitoreo-rer/main/historico_generacion_rer.csv"
    df = pd.read_csv(url_raw)
    
    # Limpiar espacios en nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Identificar columna de fecha/hora
    col_fecha = df.columns[0]
    for col in df.columns:
        if any(term in col.lower() for term in ['fecha', 'time', 'timestamp', 'date', 'hora']):
            col_fecha = col
            break
            
    # Parsear fecha
    df[col_fecha] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
    df = df.dropna(subset=[col_fecha])
    
    # Componentes de tiempo
    df['año'] = df[col_fecha].dt.year
    df['mes_num'] = df[col_fecha].dt.month
    df['dia'] = df[col_fecha].dt.day
    
    # Generar etiqueta de hora estandarizada "HH:MM"
    df['hora_str'] = df[col_fecha].dt.strftime('%H:%M')

    # Convertir las demás columnas a numérico
    cols_excluir = ['año', 'mes_num', 'dia', 'hora_str', col_fecha]
    for col in df.columns:
        if col not in cols_excluir:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '.').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df, col_fecha

try:
    df_raw, col_fecha = cargar_datos()
except Exception as e:
    st.error(f"Error al procesar el archivo CSV: {e}")
    st.stop()

# Lista de centrales
cols_excluir = ['año', 'mes_num', 'dia', 'hora_str', col_fecha]
cols_centrales = [c for c in df_raw.columns if c not in cols_excluir]

# -----------------------------------------------------------------------------
# FILTROS LATERALES
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

# Filtrar data
df_fil = df_raw[(df_raw['año'] == año_sel) & (df_raw['mes_num'] == mes_sel)].copy()

# -----------------------------------------------------------------------------
# CONSTRUCCIÓN DEL GRÁFICO (VÍA PIVOT TABLE)
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

    # Pivotear la data: Filas = Hora, Columnas = Día
    # Esto elimina problemas de tipos flotantes en el eje X
    df_pivot = df_fil.pivot_table(index='hora_str', columns='dia', values=central_sel, aggfunc='mean')
    
    # Ordenar por hora real del día
    df_pivot.index = pd.to_datetime(df_pivot.index, format='%H:%M').time
    df_pivot = df_pivot.sort_index()
    df_pivot.index = [t.strftime('%H:%M') for t in df_pivot.index]

    fig = go.Figure()

    # 1. Trazar cada día del mes (Líneas tenues)
    for col_dia in df_pivot.columns:
        fig.add_trace(go.Scatter(
            x=df_pivot.index,
            y=df_pivot[col_dia],
            mode='lines',
            line=dict(width=1, color='rgba(180, 180, 180, 0.4)'),
            name=f"Día {int(col_dia)}",
            showlegend=False,
            connectgaps=True,
            hovertemplate=f"Día {int(col_dia)} | Hora: %{{x}}<br>Potencia: %{{y:.2f}} MW<extra></extra>"
        ))

    # 2. Trazar el Promedio Mensual (Línea azul gruesa)
    media_mensual = df_pivot.mean(axis=1)
    fig.add_trace(go.Scatter(
        x=df_pivot.index,
        y=media_mensual,
        mode='lines+markers',
        marker=dict(size=4),
        line=dict(width=3.5, color='#0068C9'),
        name="Media Mensual",
        connectgaps=True,
        hovertemplate="<b>Media Mensual</b><br>Hora: %{x}<br>Potencia Promedio: %{y:.2f} MW<extra></extra>"
    ))

    fig.update_layout(
        title=f"Perfil Diario Superpuesto - {central_sel} ({mes_map.get(mes_sel, '')} {año_sel})",
        xaxis=dict(
            title="Hora del Día",
            tickangle=-45
        ),
        yaxis=dict(title="Potencia (MW)", zeroline=True),
        template="plotly_white",
        height=550
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No hay registros válidos para el filtro seleccionado.")

# Expander para ver tabla
with st.expander("📥 Ver tabla de datos filtrada"):
    st.dataframe(df_fil)

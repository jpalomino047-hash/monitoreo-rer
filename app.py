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
# CARGA Y PROCESAMIENTO DE DATOS DESDE GITHUB
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos():
    url_raw = "https://raw.githubusercontent.com/jpalomino047-hash/monitoreo-rer/main/historico_generacion_rer.csv"
    df = pd.read_csv(url_raw)
    
    # Limpiar nombres de columnas (quitar espacios extra)
    df.columns = df.columns.str.strip()
    
    # Identificar columna de fecha/hora
    col_fecha = None
    for col in df.columns:
        if any(term in col.lower() for term in ['fecha', 'time', 'timestamp', 'date', 'hora']):
            col_fecha = col
            break
            
    if col_fecha:
        df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce')
        # Eliminar filas donde la fecha no se pudo parsear
        df = df.dropna(subset=[col_fecha])
        
        df['año'] = df[col_fecha].dt.year
        df['mes_num'] = df[col_fecha].dt.month
        df['dia'] = df[col_fecha].dt.day
        df['hora_decimal'] = df[col_fecha].dt.hour + df[col_fecha].dt.minute / 60.0
        df['hora_str'] = df[col_fecha].dt.strftime('%H:%M')

    # Convertir las demás columnas a numérico (removiendo comas por puntos)
    cols_excluir = ['año', 'mes_num', 'dia', 'hora_decimal', 'hora_str', col_fecha]
    for col in df.columns:
        if col not in cols_excluir:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df, col_fecha

try:
    df_raw, col_fecha = cargar_datos()
except Exception as e:
    st.error(f"Error al procesar el archivo CSV: {e}")
    st.stop()

# Identificar columnas de centrales
cols_excluir = ['año', 'mes_num', 'dia', 'hora_decimal', 'hora_str', col_fecha]
cols_centrales = [c for c in df_raw.columns if c not in cols_excluir]

# -----------------------------------------------------------------------------
# FILTROS EN SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 Filtros")

# Filtro de Año
if 'año' in df_raw.columns and df_raw['año'].notna().any():
    años_disp = sorted(df_raw['año'].dropna().unique().astype(int), reverse=True)
    año_sel = st.sidebar.selectbox("Año", options=años_disp)
else:
    año_sel = None

mes_map = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 
           7: 'Julio', 8: 'Agosto', 9: 'Setiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}

# Filtro de Mes
if 'mes_num' in df_raw.columns and df_raw['mes_num'].notna().any():
    if año_sel:
        df_año = df_raw[df_raw['año'] == año_sel]
        meses_disp = sorted(df_año['mes_num'].dropna().unique().astype(int))
    else:
        meses_disp = sorted(df_raw['mes_num'].dropna().unique().astype(int))
    mes_sel = st.sidebar.selectbox("Mes", options=meses_disp, format_func=lambda x: mes_map.get(x, str(x)))
else:
    mes_sel = None

# Selección de Central
if cols_centrales:
    central_sel = st.sidebar.selectbox("Central / Serie", options=cols_centrales)
else:
    central_sel = None

# Aplicar Filtrado
df_fil = df_raw.copy()
if año_sel is not None:
    df_fil = df_fil[df_fil['año'] == año_sel]
if mes_sel is not None:
    df_fil = df_fil[df_fil['mes_num'] == mes_sel]

# -----------------------------------------------------------------------------
# CONSTRUCCIÓN DE LA GRÁFICA
# -----------------------------------------------------------------------------
if central_sel and not df_fil.empty:
    
    # KPIs rápidos
    col1, col2, col3 = st.columns(3)
    pmax = df_fil[central_sel].max()
    pmed = df_fil[central_sel].mean()
    
    col1.metric("Potencia Máxima (PMAX)", f"{pmax:.2f} MW" if pd.notna(pmax) else "-")
    col2.metric("Potencia Promedio", f"{pmed:.2f} MW" if pd.notna(pmed) else "-")
    col3.metric("Registros en el Mes", len(df_fil))

    st.markdown("---")

    fig = go.Figure()

    # Si tenemos columnas de día y hora_decimal, hacemos la superposición diaria
    if 'dia' in df_fil.columns and 'hora_decimal' in df_fil.columns:
        
        # 1. Trazar cada día por separado (línea tenue)
        dias = sorted(df_fil['dia'].dropna().unique())
        for d in dias:
            df_d = df_fil[df_fil['dia'] == d].dropna(subset=[central_sel, 'hora_decimal']).sort_values('hora_decimal')
            if not df_d.empty:
                fig.add_trace(go.Scatter(
                    x=df_d['hora_decimal'],
                    y=df_d[central_sel],
                    mode='lines',
                    line=dict(width=1, color='rgba(160, 160, 160, 0.35)'),
                    name=f"Día {int(d)}",
                    showlegend=False,
                    hoverinfo='text',
                    text=[f"Día {int(d)} | Hora: {h} | Potencia: {v:.2f} MW" for h, v in zip(df_d['hora_str'], df_d[central_sel])]
                ))

        # 2. Trazar el Promedio Mensual (Línea resaltada azul)
        df_prom = df_fil.groupby('hora_decimal')[central_sel].mean().reset_index().sort_values('hora_decimal')
        if not df_prom.empty:
            fig.add_trace(go.Scatter(
                x=df_prom['hora_decimal'],
                y=df_prom[central_sel],
                mode='lines',
                line=dict(width=3.5, color='#0068C9'),
                name="Media Mensual",
                hovertemplate="<b>Media Mensual</b><br>Hora: %{x:.2f}h<br>Potencia: %{y:.2f} MW<extra></extra>"
            ))

        fig.update_layout(
            title=f"Perfil Diario Superpuesto - {central_sel} ({mes_map.get(mes_sel, '')} {año_sel})",
            xaxis=dict(
                title="Hora del Día",
                tickmode='array',
                tickvals=list(range(0, 25, 2)),
                ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)],
                range=[0, 24]
            ),
            yaxis=dict(title="Potencia (MW)", zeroline=True),
            template="plotly_white",
            height=550
        )
    else:
        # Gráfica alternativa simple si la fecha no se pudo separar por hora/día
        fig.add_trace(go.Scatter(
            y=df_fil[central_sel],
            mode='lines',
            name=central_sel
        ))
        fig.update_layout(title=f"Serie de Generación - {central_sel}")

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No hay datos disponibles para la combinación de filtros seleccionada.")

# Expander con la tabla de datos
with st.expander("📥 Ver tabla de datos filtrada"):
    st.dataframe(df_fil)

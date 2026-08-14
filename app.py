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
    
    # Limpiar espacios en nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Identificar columnas clave de tiempo
    col_fecha = df.columns[0]      # "Fecha"
    col_intervalo = df.columns[1]  # "Intervalo"
    
    # Parsear Fecha para extraer Año, Mes y Día
    fecha_dt = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
    df['año'] = fecha_dt.dt.year
    df['mes_num'] = fecha_dt.dt.month
    df['dia'] = fecha_dt.dt.day
    
    # Función para convertir intervalos ("0:30", "1:00", etc.) a número decimal (0.0 a 24.0)
    def hora_a_decimal(cadena_hora):
        try:
            cadena_hora = str(cadena_hora).strip()
            if ':' in cadena_hora:
                partes = cadena_hora.split(':')
                h = float(partes[0])
                m = float(partes[1])
                val = h + (m / 60.0)
                return 24.0 if (val == 0.0 and h != 0) else val
            return np.nan
        except:
            return np.nan

    # Extraer hora decimal desde 'Intervalo'
    df['hora_decimal'] = df[col_intervalo].apply(hora_a_decimal)

    # Fallback si falla el parseo
    if df['hora_decimal'].isna().any():
        df['hora_decimal'] = df.groupby(['año', 'mes_num', 'dia']).cumcount() * 0.5

    # Convertir a flotante SOLO las columnas de centrales
    cols_excluir_conversion = ['año', 'mes_num', 'dia', 'hora_decimal', col_fecha, col_intervalo]
    for col in df.columns:
        if col not in cols_excluir_conversion:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '.').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df, col_fecha, col_intervalo

try:
    df_raw, col_fecha, col_intervalo = cargar_datos()
except Exception as e:
    st.error(f"Error al procesar el archivo CSV: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# FILTROS LATERALES
# -----------------------------------------------------------------------------
cols_excluir = ['año', 'mes_num', 'dia', 'hora_decimal', col_fecha, col_intervalo]
cols_centrales = [c for c in df_raw.columns if c not in cols_excluir]

st.sidebar.header("🔍 Filtros")

# Filtro Año
años_validos = df_raw['año'].dropna().unique()
if len(años_validos) > 0:
    años_disp = sorted(años_validos.astype(int), reverse=True)
    año_sel = st.sidebar.selectbox("Año", options=años_disp)
else:
    año_sel = None

mes_map = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 
           7: 'Julio', 8: 'Agosto', 9: 'Setiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}

# Filtro Mes
if año_sel:
    df_año = df_raw[df_raw['año'] == año_sel]
    meses_disp = sorted(df_año['mes_num'].dropna().unique().astype(int))
    mes_sel = st.sidebar.selectbox("Mes", options=meses_disp, format_func=lambda x: mes_map.get(x, str(x)))
else:
    mes_sel = None

st.sidebar.markdown("---")

# Seleccionar Central Principal (Azul)
central_sel = st.sidebar.selectbox("Central Principal (Azul)", options=cols_centrales, index=0)

# Seleccionar Segunda Central Opcional (Naranja)
opciones_segunda = ["Ninguna (Solo Central Principal)"] + [c for c in cols_centrales if c != central_sel]
central_sel_2 = st.sidebar.selectbox("Comparar con Segunda Central (Naranja)", options=opciones_segunda, index=0)

# Filtrado de DataFrame
if año_sel and mes_sel:
    df_fil = df_raw[(df_raw['año'] == año_sel) & (df_raw['mes_num'] == mes_sel)].copy()
else:
    df_fil = df_raw.copy()

# -----------------------------------------------------------------------------
# RENDERING DE MÉTRICAS Y GRÁFICO
# -----------------------------------------------------------------------------
if central_sel and not df_fil.empty:

    # Métricas
    if central_sel_2 != "Ninguna (Solo Central Principal)":
        col1, col2, col3, col4 = st.columns(4)
        
        pmax_1 = df_fil[central_sel].max()
        pmed_1 = df_fil[central_sel].mean()
        pmax_2 = df_fil[central_sel_2].max()
        pmed_2 = df_fil[central_sel_2].mean()
        
        col1.metric(f"PMAX - {central_sel}", f"{pmax_1:.2f} MW" if pd.notna(pmax_1) else "0.00 MW")
        col2.metric(f"Promedio - {central_sel}", f"{pmed_1:.2f} MW" if pd.notna(pmed_1) else "0.00 MW")
        col3.metric(f"PMAX - {central_sel_2}", f"{pmax_2:.2f} MW" if pd.notna(pmax_2) else "0.00 MW")
        col4.metric(f"Promedio - {central_sel_2}", f"{pmed_2:.2f} MW" if pd.notna(pmed_2) else "0.00 MW")
    else:
        col1, col2, col3 = st.columns(3)
        pmax = df_fil[central_sel].max()
        pmed = df_fil[central_sel].mean()
        
        col1.metric("Potencia Máxima (PMAX)", f"{pmax:.2f} MW" if pd.notna(pmax) else "0.00 MW")
        col2.metric("Potencia Promedio", f"{pmed:.2f} MW" if pd.notna(pmed) else "0.00 MW")
        col3.metric("Registros en el Mes", len(df_fil))

    st.markdown("---")

    fig = go.Figure()
    dias = sorted(df_fil['dia'].dropna().unique())

    # 1. TRAZADO DE CENTRAL PRINCIPAL (AZUL)
    # Perfiles diarios tenues
    for d in dias:
        df_d = df_fil[df_fil['dia'] == d].sort_values('hora_decimal')
        if not df_d.empty:
            fig.add_trace(go.Scatter(
                x=df_d['hora_decimal'],
                y=df_d[central_sel],
                mode='lines',
                line=dict(width=0.8, color='rgba(0, 104, 201, 0.2)'),
                name=f"{central_sel} - Día {int(d)}",
                showlegend=False,
                connectgaps=True,
                hoverinfo='skip'
            ))

    # Media Mensual Central Principal
    df_prom1 = df_fil.groupby('hora_decimal')[central_sel].mean().reset_index().sort_values('hora_decimal')
    if not df_prom1.empty:
        fig.add_trace(go.Scatter(
            x=df_prom1['hora_decimal'],
            y=df_prom1[central_sel],
            mode='lines+markers',
            marker=dict(size=4),
            line=dict(width=3.5, color='#0068C9'),
            name=f"Media Mensual: {central_sel}",
            connectgaps=True,
            hovertemplate=f"<b>{central_sel} (Media)</b><br>Hora: %{{x:.2f}}h<br>Potencia: %{{y:.2f}} MW<extra></extra>"
        ))

    # 2. TRAZADO DE SEGUNDA CENTRAL SI FUE SELECCIONADA (NARANJA)
    if central_sel_2 != "Ninguna (Solo Central Principal)":
        # Perfiles diarios tenues en naranja
        for d in dias:
            df_d = df_fil[df_fil['dia'] == d].sort_values('hora_decimal')
            if not df_d.empty:
                fig.add_trace(go.Scatter(
                    x=df_d['hora_decimal'],
                    y=df_d[central_sel_2],
                    mode='lines',
                    line=dict(width=0.8, color='rgba(255, 127, 14, 0.2)'),
                    name=f"{central_sel_2} - Día {int(d)}",
                    showlegend=False,
                    connectgaps=True,
                    hoverinfo='skip'
                ))

        # Media Mensual Segunda Central
        df_prom2 = df_fil.groupby('hora_decimal')[central_sel_2].mean().reset_index().sort_values('hora_decimal')
        if not df_prom2.empty:
            fig.add_trace(go.Scatter(
                x=df_prom2['hora_decimal'],
                y=df_prom2[central_sel_2],
                mode='lines+markers',
                marker=dict(size=4),
                line=dict(width=3.5, color='#FF7F0E'),
                name=f"Media Mensual: {central_sel_2}",
                connectgaps=True,
                hovertemplate=f"<b>{central_sel_2} (Media)</b><br>Hora: %{{x:.2f}}h<br>Potencia: %{{y:.2f}} MW<extra></extra>"
            ))

    # Formato del Eje X (00:00, 02:00 ... 24:00)
    tick_vals = list(range(0, 25, 2))
    tick_text = [f"{h:02d}:00" for h in range(0, 25, 2)]

    titulo_graf = f"Perfil Diario - {central_sel}"
    if central_sel_2 != "Ninguna (Solo Central Principal)":
        titulo_graf += f" vs {central_sel_2}"
    titulo_graf += f" ({mes_map.get(mes_sel, '')} {año_sel})"

    fig.update_layout(
        title=titulo_graf,
        xaxis=dict(
            title="Hora del Día",
            tickmode='array',
            tickvals=tick_vals,
            ticktext=tick_text,
            range=[-0.2, 24.2]
        ),
        yaxis=dict(title="Potencia (MW)", zeroline=True),
        template="plotly_white",
        height=580,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No hay datos disponibles para mostrar.")

# Expander para inspección
with st.expander("📥 Ver tabla de datos filtrada"):
    st.dataframe(df_fil)

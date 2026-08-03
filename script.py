import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de estilo visual
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.sans-serif': 'Arial', 'font.family': 'sans-serif'})

def generar_grafico_perfil(df):
    if df.empty:
        return

    # Obtener la lista de centrales (excluyendo Fecha e Intervalo)
    centrales = [c for c in df.columns if c not in ['Fecha', 'Intervalo']]
    num_centrales = len(centrales)
    
    if num_centrales == 0:
        return

    # Definir la grilla de subgráficos
    cols = 3
    rows = (num_centrales + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(18, 4 * rows), sharex=True, sharey=False)
    axes = axes.flatten() if num_centrales > 1 else [axes]

    fechas = df['Fecha'].unique()
    ultima_fecha = max(fechas)

    for i, central in enumerate(centrales):
        ax = axes[i]
        
        # 1. Superposición de días anteriores (Perfil Histórico en Gris)
        for fecha in fechas:
            if fecha == ultima_fecha:
                continue
            df_dia = df[df['Fecha'] == fecha]
            ax.plot(df_dia['Intervalo'], df_dia[central], color='gray', alpha=0.15, linewidth=1)

        # 2. Resaltar el perfil del último día disponible
        df_ultimo = df[df['Fecha'] == ultima_fecha]
        ax.plot(
            df_ultimo['Intervalo'], 
            df_ultimo[central], 
            color='#d95f02', 
            linewidth=2.5, 
            label=f'Último día ({ultima_fecha})'
        )

        ax.set_title(f"{central}", fontsize=11, fontweight='bold')
        ax.set_ylabel("MW", fontsize=9)
        ax.tick_params(axis='x', rotation=90, labelsize=7)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(loc='upper right', fontsize=8)

    # Ocultar ejes vacíos si num_centrales no es múltiplo exacto de cols
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.suptitle("Perfil Diario de Generación RER (Superposición de Días)", fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    # Guardar imagen para el README
    plt.savefig("perfil_generacion_rer.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("Gráfico 'perfil_generacion_rer.png' generado exitosamente.")

# Llamar a la función al final del script
generar_grafico_perfil(df_consolidado)

import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de estilo visual
sns.set_theme(style="whitegrid")

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
    
    if num_centrales == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    fechas = df['Fecha'].unique()
    ultima_fecha = max(fechas)

    for i, central in enumerate(centrales):
        ax = axes[i]
        
        # 1. Perfil Histórico (días anteriores en gris)
        for fecha in fechas:
            if fecha == ultima_fecha:
                continue
            df_dia = df[df['Fecha'] == fecha]
            ax.plot(df_dia['Intervalo'], df_dia[central], color='gray', alpha=0.2, linewidth=1)

        # 2. Resaltar el último día
        df_ultimo = df[df['Fecha'] == ultima_fecha]
        ax.plot(
            df_ultimo['Intervalo'], 
            df_ultimo[central], 
            color='#d95f02', 
            linewidth=2.5, 
            label=f'Último día ({ultima_fecha})'
        )

        ax.set_title(f"{central}", fontsize=10, fontweight='bold')
        ax.set_ylabel("MW", fontsize=8)
        ax.tick_params(axis='x', rotation=90, labelsize=6)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(loc='upper right', fontsize=8)

    # Ocultar cuadros vacíos sobrantes
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.suptitle("Perfil Diario de Generación RER", fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    
    # Guardar imagen obligatoria para GitHub Actions
    plt.savefig("perfil_generacion_rer.png", dpi=200, bbox_inches='tight')
    plt.close()
    print("Gráfico 'perfil_generacion_rer.png' generado exitosamente.")

# Ejecutar la graficación con el dataframe consolidado
generar_grafico_perfil(df_consolidado)
plt.savefig("perfil_generacion_rer.png", dpi=200, bbox_inches='tight')

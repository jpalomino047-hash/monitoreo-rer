def exportar_a_json(df):
    if df is None or df.empty:
        print("[Aviso] No hay datos disponibles para exportar a JSON.")
        return

    if os.path.exists('data') and not os.path.isdir('data'):
        os.remove('data')
    os.makedirs('data', exist_ok=True)

    centrales = [c for c in df.columns if c not in ['Fecha', 'Intervalo']]

    # Normalizar fechas a YYYY-MM-DD por si vienen en formato DD/MM/YYYY
    fechas_raw = df['Fecha'].unique()
    mapa_fechas = {}
    fechas_iso = []
    for f in fechas_raw:
        partes = str(f).split('/')
        if len(partes) == 3:
            f_iso = f"{partes[2]}-{partes[1].zfill(2)}-{partes[0].zfill(2)}"
        else:
            f_iso = str(f)
        mapa_fechas[f] = f_iso
        fechas_iso.append(f_iso)

    fechas_iso = sorted(list(set(fechas_iso)))
    intervalos_unicos = list(df['Intervalo'].unique()[:48])

    estructura_json = {
        "intervalos": intervalos_unicos,
        "fechas": fechas_iso,
        "centrales": centrales,
        "datos": {c: {} for c in centrales}
    }

    for fecha_orig, df_fecha in df.groupby('Fecha'):
        fecha_key = mapa_fechas.get(fecha_orig, fecha_orig)
        for central in centrales:
            valores = pd.to_numeric(df_fecha[central], errors='coerce').fillna(0.0).tolist()
            estructura_json["datos"][central][fecha_key] = valores[:48]

    json_path = os.path.join('data', 'data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(estructura_json, f, ensure_ascii=False, indent=2)

    print(f"¡Éxito! Datos exportados para la Web en '{json_path}'.")

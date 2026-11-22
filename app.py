import streamlit as st
from datetime import datetime, date
from PIL import Image
import io
import json
import pandas as pd
from github import Github, GithubException

# ==========================================
# CONFIGURACIÓN DE GITHUB Y FUNCIONES
# ==========================================
def _repo():
    g = Github(st.secrets["GITHUB_TOKEN"])
    return g.get_repo(st.secrets["GITHUB_REPO"])

@st.cache_data(ttl=60) # Guarda en caché por 60 seg para que cargue rápido
def obtener_lista_config(ruta_archivo):
    try:
        repo = _repo()
        file = repo.get_contents(ruta_archivo)
        return json.loads(file.decoded_content.decode("utf-8"))
    except:
        return []

def guardar_envio(tipo: str, datos: dict, archivos: list) -> str:
    repo = _repo()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    conductor = (datos.get("conductor") or "sin_nombre").replace(" ", "_")
    envio_id = f"{ts}_{conductor}"

    urls = []
    for i, file_info in enumerate(archivos):
        if not file_info: continue
        ext = file_info["name"].split(".")[-1].lower() if "." in file_info["name"] else "bin"
        path = f"archivos/{tipo}/{envio_id}_{i+1}.{ext}"
        
        repo.create_file(
            path=path, message=f"archivo {envio_id} #{i+1}",
            content=file_info["data"], branch="main",
        )
        urls.append(f"https://raw.githubusercontent.com/{repo.full_name}/main/{path}")

    datos["_tipo"] = tipo
    datos["_enviado_en"] = datetime.now().isoformat(timespec="seconds")
    datos["_archivos"] = urls

    path_json = f"datos/{tipo}/{envio_id}.json"
    repo.create_file(
        path=path_json, message=f"registro {envio_id}",
        content=json.dumps(datos, ensure_ascii=False, indent=2), branch="main",
    )
    return envio_id

def obtener_todos_los_datos():
    repo = _repo()
    registros = []
    try:
        carpetas = repo.get_contents("datos")
        for carpeta in carpetas:
            if carpeta.type == "dir":
                for archivo in repo.get_contents(carpeta.path):
                    if archivo.name.endswith(".json"):
                        registros.append(json.loads(archivo.decoded_content.decode("utf-8")))
    except GithubException:
        pass 
    
    if not registros: return pd.DataFrame()
    
    df = pd.DataFrame(registros)
    if "_archivos" in df.columns:
        df["_archivos"] = df["_archivos"].apply(lambda x: " | ".join(x) if isinstance(x, list) else x)
    return df

def calcular_metricas(df):
    if df.empty: return pd.DataFrame()
    df['datetime'] = pd.to_datetime(df['fecha_envio'] + ' ' + df['hora_envio'])
    df['kilometraje'] = pd.to_numeric(df['kilometraje'], errors='coerce')

    resumen = df.groupby(['conductor', 'fecha_envio']).agg(
        KM_Inicial=('kilometraje', 'min'),
        KM_Final=('kilometraje', 'max'),
        Hora_Inicio=('datetime', 'min'),
        Hora_Fin=('datetime', 'max')
    ).reset_index()

    resumen['Total_KMs'] = resumen['KM_Final'] - resumen['KM_Inicial']
    resumen['Horas_Jornada'] = (resumen['Hora_Fin'] - resumen['Hora_Inicio']).dt.total_seconds() / 3600

    horas_trabajadas = []
    for _, row in resumen.iterrows():
        df_dia = df[(df['conductor'] == row['conductor']) & (df['fecha_envio'] == row['fecha_envio'])].sort_values('datetime')
        inicios = df_dia[df_dia['_tipo'] == 'inicio_servicio']['datetime'].tolist()
        fines = df_dia[df_dia['_tipo'] == 'fin_servicio']['datetime'].tolist()
        
        total_horas = sum((fines[i] - inicios[i]).total_seconds() / 3600 for i in range(min(len(inicios), len(fines))))
        horas_trabajadas.append(total_horas)

    resumen['Horas_Trabajadas'] = horas_trabajadas
    resumen['Horas_Disponibles'] = resumen['Horas_Jornada'] - resumen['Horas_Trabajadas']
    
    resumen = resumen[['conductor', 'fecha_envio', 'Total_KMs', 'Horas_Trabajadas', 'Horas_Disponibles', 'Horas_Jornada']]
    for col in ['Total_KMs', 'Horas_Trabajadas', 'Horas_Disponibles', 'Horas_Jornada']:
        resumen[col] = resumen[col].fillna(0).round(2)
    return resumen

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Bitácora Conductor", page_icon="🚗", layout="centered")
st.markdown("<style>.stButton button { width: 100%; font-size: 18px; padding: 14px; background-color: #1976D2; color: white; }</style>", unsafe_allow_html=True)

# Cargar listas base
lista_conductores = obtener_lista_config("config/conductores.json")
nombres_conductores = [c["nombre"] for c in lista_conductores] if lista_conductores else ["Error: Falta config/conductores.json"]
lista_clientes = obtener_lista_config("config/clientes.json") or ["Error: Falta config/clientes.json"]

with st.sidebar:
    st.header("⚙️ Menú")
    password = st.text_input("Contraseña de Administrador", type="password")
    es_admin = password == st.secrets.get("ADMIN_PASSWORD", "admin123")

# ==========================================
# VISTA 1: MODO ADMINISTRADOR
# ==========================================
if es_admin:
    st.title("📊 Panel de Administración")
    with st.spinner("Calculando métricas..."):
        df = obtener_todos_los_datos()
    
    if df.empty:
        st.warning("Aún no hay registros en el sistema.")
    else:
        df_resumen = calcular_metricas(df)
        col1, col2, col3 = st.columns(3)
        col1.metric("KMs Totales", f"{df_resumen['Total_KMs'].sum():,.1f} km")
        col2.metric("Hrs Trabajadas", f"{df_resumen['Horas_Trabajadas'].sum():,.1f} h")
        col3.metric("Hrs Disponibles", f"{df_resumen['Horas_Disponibles'].sum():,.1f} h")
        
        st.markdown("---")
        st.subheader("Resumen por Conductor y Día")
        st.dataframe(df_resumen.sort_values(by="fecha_envio", ascending=False), use_container_width=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_resumen.to_excel(writer, index=False, sheet_name='Resumen')
            df.to_excel(writer, index=False, sheet_name='Datos_Crudos')
        
        st.download_button("📥 Descargar Reporte en Excel", buffer.getvalue(), f"Reporte_Flota_{date.today()}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        
        with st.expander("Ver registros crudos (Todo el detalle)"):
            st.dataframe(df.sort_values(by="_enviado_en", ascending=False), use_container_width=True)

# ==========================================
# VISTA 2: MODO CONDUCTOR (Formularios)
# ==========================================
else:
    st.title("🚗 Bitácora de servicio")
    st.caption(f"Hoy: {date.today().strftime('%d/%m/%Y')}")
    
    tabs = st.tabs(["🚏 1. Salida", "🟢 2. Inicio", "🏁 3. Fin", "🏠 4. Llegada"])

    # Función auxiliar para capturar conductor y documento
    def selector_conductor(key_prefix):
        nombre_sel = st.selectbox("1. Nombre del Conductor *", nombres_conductores, key=f"{key_prefix}_cond")
        documento = next((c["documento"] for c in lista_conductores if c["nombre"] == nombre_sel), "")
        if documento:
            st.text_input("Documento de Identidad", value=documento, disabled=True, key=f"{key_prefix}_doc")
        return nombre_sel, documento

    def preparar_archivo(archivo_subido):
        if archivo_subido is None: return None
        if archivo_subido.type.startswith('image/'):
            img = Image.open(archivo_subido)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            nombre_base = archivo_subido.name.rsplit('.', 1)[0]
            return {"name": f"{nombre_base}.jpg", "data": buffer.getvalue()}
        return {"name": archivo_subido.name, "data": archivo_subido.getvalue()}

    def procesar_envio(tipo, datos, archivos):
        try:
            with st.spinner("Guardando datos en GitHub..."):
                envio_id = guardar_envio(tipo, datos, archivos)
            st.success(f"✅ Registro guardado. ID: `{envio_id}`")
            st.balloons()
        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")

    # --- Pestaña 1 ---
    with tabs[0]:
        st.subheader("Al salir a iniciar la jornada")
        conductor, documento = selector_conductor("t1")
        placa = st.text_input("2. Placa del vehículo *", key="t1_placa")
        km = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t1_km")
        foto = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t1_foto")
        sugerencias = st.text_area("5. Sugerencias (opcional)", key="t1_sug")
        
        if st.button("Enviar Registro de Salida", key="t1_btn"):
            if not placa or foto is None:
                st.error("⚠️ Faltan campos obligatorios o la fotografía.")
            else:
                datos = {"conductor": conductor, "documento": documento, "placa": placa, "kilometraje": km, "sugerencias": sugerencias, "fecha_envio": str(date.today()), "hora_envio": datetime.now().strftime("%H:%M:%S")}
                procesar_envio("salida_parqueadero", datos, [preparar_archivo(foto)])

    # --- Pestaña 2 ---
    with tabs[1]:
        st.subheader("Al recoger al pasajero / iniciar el servicio")
        conductor2, documento2 = selector_conductor("t2")
        placa2 = st.text_input("2. Placa del vehículo *", key="t2_placa")
        km2 = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t2_km")
        foto2 = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t2_foto")
        sugerencias2 = st.text_area("5. Sugerencias (opcional)", key="t2_sug")
        
        if st.button("Enviar Registro de Inicio", key="t2_btn"):
            if not placa2 or foto2 is None:
                st.error("⚠️ Faltan campos obligatorios o la fotografía.")
            else:
                datos2 = {"conductor": conductor2, "documento": documento2, "placa": placa2, "kilometraje": km2, "sugerencias": sugerencias2, "fecha_envio": str(date.today()), "hora_envio": datetime.now().strftime("%H:%M:%S")}
                procesar_envio("inicio_servicio", datos2, [preparar_archivo(foto2)])

    # --- Pestaña 3 ---
    with tabs[2]:
        st.subheader("Al terminar el viaje")
        conductor3, documento3 = selector_conductor("t3")
        placa3 = st.text_input("2. Placa del vehículo *", key="t3_placa")
        km3 = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t3_km")
        foto_odo3 = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t3_foto")
        pdf_planilla = st.file_uploader("5. PDF Planillas *", type=["pdf"], key="t3_pdf")
        
        cliente = st.selectbox("6. Cliente *", lista_clientes, key="t3_cliente")
        ruta = st.text_input("7. Ruta *", key="t3_ruta")
        remesa = st.text_input("8. N° Remesa *", key="t3_remesa")
        viaje = st.text_input("9. N° Viaje (Opcional)", key="t3_viaje")
        sugerencias3 = st.text_area("10. Sugerencias (Opcional)", key="t3_sug")
        
        if st.button("Enviar Registro de Fin", key="t3_btn"):
            if not placa3 or not ruta or not remesa or foto_odo3 is None or pdf_planilla is None:
                st.error("⚠️ Faltan campos de texto o archivos obligatorios.")
            else:
                datos3 = {"conductor": conductor3, "documento": documento3, "placa": placa3, "kilometraje": km3, "cliente": cliente, "ruta": ruta, "n_remesa": remesa, "n_viaje": viaje, "sugerencias": sugerencias3, "fecha_envio": str(date.today()), "hora_envio": datetime.now().strftime("%H:%M:%S")}
                archivos3 = [preparar_archivo(foto_odo3), preparar_archivo(pdf_planilla)]
                procesar_envio("fin_servicio", datos3, archivos3)

    # --- Pestaña 4 ---
    with tabs[3]:
        st.subheader("Al cerrar la jornada")
        conductor4, documento4 = selector_conductor("t4")
        placa4 = st.text_input("2. Placa del vehículo *", key="t4_placa")
        km4 = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t4_km")
        foto4 = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t4_foto")
        sugerencias4 = st.text_area("5. Sugerencias (Opcional)", key="t4_sug")
        
        if st.button("Enviar Registro de Llegada", key="t4_btn"):
            if not placa4 or foto4 is None:
                st.error("⚠️ Faltan campos obligatorios o la fotografía.")
            else:
                datos4 = {"conductor": conductor4, "documento": documento4, "placa": placa4, "kilometraje": km4, "sugerencias": sugerencias4, "fecha_envio": str(date.today()), "hora_envio": datetime.now().strftime("%H:%M:%S")}
                procesar_envio("llegada_parqueadero", datos4, [preparar_archivo(foto4)])

    st.markdown("---")
    st.caption("Hecho con Streamlit + GitHub · Añade esta página a tu pantalla de inicio 📲")

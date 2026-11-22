import streamlit as st
from datetime import datetime, date
from PIL import Image
import io
import json
from github import Github

# ==========================================
# CONFIGURACIÓN DE GITHUB (Unificado)
# ==========================================
def _repo():
    g = Github(st.secrets["GITHUB_TOKEN"])
    return g.get_repo(st.secrets["GITHUB_REPO"])

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
            path=path,
            message=f"archivo {envio_id} #{i+1}",
            content=file_info["data"],
            branch="main",
        )
        urls.append(f"https://raw.githubusercontent.com/{repo.full_name}/main/{path}")

    datos["_tipo"] = tipo
    datos["_enviado_en"] = datetime.now().isoformat(timespec="seconds")
    datos["_archivos"] = urls

    path_json = f"datos/{tipo}/{envio_id}.json"
    repo.create_file(
        path=path_json,
        message=f"registro {envio_id}",
        content=json.dumps(datos, ensure_ascii=False, indent=2),
        branch="main",
    )
    return envio_id

# ==========================================
# CONFIGURACIÓN DE LA APP
# ==========================================
st.set_page_config(
    page_title="Bitácora Conductor",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Bitácora">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#1976D2">
    <style>
      .stTextInput input, .stNumberInput input, .stTextArea textarea { font-size: 18px; padding: 10px; }
      .stButton button { width: 100%; font-size: 18px; padding: 14px; background-color: #1976D2; color: white; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚗 Bitácora de servicio")
st.caption(f"Hoy: {date.today().strftime('%d/%m/%Y')}")

tabs = st.tabs([
    "🚏 1. Salida parqueadero",
    "🟢 2. Inicio servicio",
    "🏁 3. Fin servicio",
    "🏠 4. Llegada parqueadero"
])

def preparar_archivo(archivo_subido):
    if archivo_subido is None:
        return None
    if archivo_subido.type.startswith('image/'):
        img = Image.open(archivo_subido)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
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
    conductor = st.text_input("1. Nombre del Conductor *", key="t1_cond")
    placa = st.text_input("2. Placa del vehículo *", key="t1_placa")
    km = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t1_km")
    foto = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t1_foto")
    sugerencias = st.text_area("5. Sugerencias (opcional)", key="t1_sug")
    
    if st.button("Enviar Registro de Salida", key="t1_btn"):
        if not conductor or not placa or foto is None:
            st.error("⚠️ Faltan campos obligatorios o la fotografía.")
        else:
            datos = {"conductor": conductor, "placa": placa, "kilometraje": km, "sugerencias": sugerencias, "fecha_envio": str(date.today()), "hora_envio": datetime.now().strftime("%H:%M:%S")}
            procesar_envio("salida_parqueadero", datos, [preparar_archivo(foto)])

# --- Pestaña 2 ---
with tabs[1]:
    st.subheader("Al recoger al pasajero / iniciar el servicio")
    conductor2 = st.text_input("1. Nombre del Conductor *", key="t2_cond")
    placa2 = st.text_input("2. Placa del vehículo *", key="t2_placa")
    km2 = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t2_km")
    foto2 = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t2_foto")
    sugerencias2 = st.text_area("5. Sugerencias (opcional)", key="t2_sug")
    
    if st.button("Enviar Registro de Inicio", key="t2_btn"):
        if not conductor2 or not placa2 or foto2 is None:
            st.error("⚠️ Faltan campos obligatorios o la fotografía.")
        else:
            datos2 = {"conductor": conductor2, "placa": placa2, "kilometraje": km2, "sugerencias": sugerencias2, "fecha_envio": str(date.today()), "hora_envio": datetime.now().strftime("%H:%M:%S")}
            procesar_envio("inicio_servicio", datos2, [preparar_archivo(foto2)])

# --- Pestaña 3 ---
with tabs[2]:
    st.subheader("Al terminar el viaje")
    conductor3 = st.text_input("1. Nombre del Conductor *", key="t3_cond")
    placa3 = st.text_input("2. Placa del vehículo *", key="t3_placa")
    km3 = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t3_km")
    foto_odo3 = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t3_foto")
    pdf_planilla = st.file_uploader("5. PDF Planillas *", type=["pdf"], key="t3_pdf")
    cliente = st.text_input("6. Cliente *", key="t3_cliente")
    ruta = st.text_input("7. Ruta *", key="t3_ruta")
    remesa = st.text_input("8. N° Remesa *", key="t3_remesa")
    viaje = st.text_input("9. N° Viaje (Opcional)", key="t3_viaje")
    sugerencias3 = st.text_area("10. Sugerencias (Opcional)", key="t3_sug")
    
    if st.button("Enviar Registro de Fin", key="t3_btn"):
        if not conductor3 or not placa3 or not cliente or not ruta or not remesa or foto_odo3 is None or pdf_planilla is None:
            st.error("⚠️ Faltan campos de texto o archivos obligatorios.")
        else:
            datos3 = {"conductor": conductor3, "placa": placa3, "kilometraje": km3, "cliente": cliente, "ruta": ruta, "n_remesa": remesa, "n_viaje": viaje, "sugerencias": sugerencias3, "fecha_envio": str(date.today()), "hora_envio": datetime.now().strftime("%H:%M:%S")}
            archivos3 = [preparar_archivo(foto_odo3), preparar_archivo(pdf_planilla)]
            procesar_envio("fin_servicio", datos3, archivos3)

# --- Pestaña 4 ---
with tabs[3]:
    st.subheader("Al cerrar la jornada")
    conductor4 = st.text_input("1. Nombre del Conductor *", key="t4_cond")
    placa4 = st.text_input("2. Placa del vehículo *", key="t4_placa")
    km4 = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t4_km")
    foto4 = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t4_foto")
    sugerencias4 = st.text_area("5. Sugerencias (Opcional)", key="t4_sug")
    
    if st.button("Enviar Registro de Llegada", key="t4_btn"):
        if not conductor4 or not placa4 or foto4 is None:
            st.error("⚠️ Faltan campos obligatorios o la fotografía.")
        else:
            datos4 = {"conductor": conductor4, "placa": placa4, "kilometraje": km4, "sugerencias": sugerencias4, "fecha_envio": str(date.today()), "hora_envio": datetime.now().strftime("%H:%M:%S")}
            procesar_envio("llegada_parqueadero", datos4, [preparar_archivo(foto4)])

st.markdown("---")
st.caption("Hecho con Streamlit + GitHub · Añade esta página a tu pantalla de inicio 📲")

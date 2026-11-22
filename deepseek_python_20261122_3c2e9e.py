import streamlit as st
from datetime import datetime, date
from github_utils import guardar_envio
from PIL import Image
import io

st.set_page_config(
    page_title="Bitácora Conductor",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- PWA / "Añadir a pantalla de inicio" y estilos ---
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

tabs = st.tabs(
    ["🚏 1. Salida parqueadero",
     "🟢 2. Inicio servicio",
     "🏁 3. Fin servicio",
     "🏠 4. Llegada parqueadero"]
)

# Función para comprimir imágenes y ahorrar espacio/datos
def preparar_archivo(archivo_subido):
    if archivo_subido is None:
        return None
    
    # Si es una imagen, la comprimimos
    if archivo_subido.type.startswith('image/'):
        img = Image.open(archivo_subido)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Redimensionar a máximo 1600px para que siga siendo legible pero pese poco
        img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=80)
        
        # Forzamos extensión .jpg
        nombre_base = archivo_subido.name.rsplit('.', 1)[0]
        return {"name": f"{nombre_base}.jpg", "data": buffer.getvalue()}
    
    # Si es un PDF u otro, lo enviamos tal cual
    return {"name": archivo_subido.name, "data": archivo_subido.getvalue()}

# Función auxiliar para enviar y validar
def procesar_envio(tipo, datos, archivos):
    try:
        with st.spinner("Guardando datos y archivos en GitHub..."):
            envio_id = guardar_envio(tipo, datos, archivos)
        st.success(f"✅ Registro guardado correctamente. ID: `{envio_id}`")
        st.balloons()
    except Exception as e:
        st.error(f"❌ Error al guardar: {e}")

# ==========================================
# PESTAÑA 1: Salida del parqueadero
# ==========================================
with tabs[0]:
    st.subheader("Al salir a iniciar la jornada")
    
    conductor = st.text_input("1. Nombre del Conductor *", key="t1_cond")
    placa = st.text_input("2. Placa del vehículo *", key="t1_placa")
    km = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t1_km")
    
    foto = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t1_foto")
    sugerencias = st.text_area("5. Sugerencias (opcional)", key="t1_sug")
    
    if st.button("Enviar Registro de Salida", key="t1_btn"):
        if not conductor or not placa:
            st.error("⚠️ Nombre y Placa son obligatorios.")
        elif foto is None:
            st.error("⚠️ La fotografía del odómetro es OBLIGATORIA.")
        else:
            datos = {
                "conductor": conductor, "placa": placa, "kilometraje": km,
                "sugerencias": sugerencias, "fecha_envio": str(date.today()),
                "hora_envio": datetime.now().strftime("%H:%M:%S")
            }
            archivos = [preparar_archivo(foto)]
            procesar_envio("salida_parqueadero", datos, archivos)

# ==========================================
# PESTAÑA 2: Inicio de servicio
# ==========================================
with tabs[1]:
    st.subheader("Al recoger al pasajero / iniciar el servicio")
    
    conductor2 = st.text_input("1. Nombre del Conductor *", key="t2_cond")
    placa2 = st.text_input("2. Placa del vehículo *", key="t2_placa")
    km2 = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t2_km")
    
    foto2 = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t2_foto")
    sugerencias2 = st.text_area("5. Sugerencias (opcional)", key="t2_sug")
    
    if st.button("Enviar Registro de Inicio", key="t2_btn"):
        if not conductor2 or not placa2:
            st.error("⚠️ Nombre y Placa son obligatorios.")
        elif foto2 is None:
            st.error("⚠️ La fotografía del odómetro es OBLIGATORIA.")
        else:
            datos2 = {
                "conductor": conductor2, "placa": placa2, "kilometraje": km2,
                "sugerencias": sugerencias2, "fecha_envio": str(date.today()),
                "hora_envio": datetime.now().strftime("%H:%M:%S")
            }
            archivos2 = [preparar_archivo(foto2)]
            procesar_envio("inicio_servicio", datos2, archivos2)

# ==========================================
# PESTAÑA 3: Fin de servicio
# ==========================================
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
    
    if st.button("Enviar Registro de Fin de Servicio", key="t3_btn"):
        if not conductor3 or not placa3 or not cliente or not ruta or not remesa:
            st.error("⚠️ Faltan campos de texto obligatorios (Conductor, Placa, Cliente, Ruta, Remesa).")
        elif foto_odo3 is None or pdf_planilla is None:
            st.error("⚠️ La fotografía del odómetro y el PDF de planillas son OBLIGATORIOS.")
        else:
            datos3 = {
                "conductor": conductor3, "placa": placa3, "kilometraje": km3,
                "cliente": cliente, "ruta": ruta, "n_remesa": remesa,
                "n_viaje": viaje, "sugerencias": sugerencias3,
                "fecha_envio": str(date.today()), "hora_envio": datetime.now().strftime("%H:%M:%S")
            }
            archivos3 = [
                preparar_archivo(foto_odo3),
                preparar_archivo(pdf_planilla) # Los PDFs no se comprimen, se envían tal cual
            ]
            procesar_envio("fin_servicio", datos3, archivos3)

# ==========================================
# PESTAÑA 4: Llegada al parqueadero (Completada)
# ==========================================
with tabs[3]:
    st.subheader("Al cerrar la jornada")
    
    conductor4 = st.text_input("1. Nombre del Conductor *", key="t4_cond")
    placa4 = st.text_input("2. Placa del vehículo *", key="t4_placa")
    km4 = st.number_input("3. Kilometraje del vehículo *", min_value=0.0, step=1.0, format="%.1f", key="t4_km")
    
    foto4 = st.file_uploader("4. Fotografía del odómetro *", type=["jpg", "jpeg", "png"], key="t4_foto")
    sugerencias4 = st.text_area("5. Sugerencias (Opcional)", key="t4_sug")
    
    if st.button("Enviar Registro de Llegada", key="t4_btn"):
        if not conductor4 or not placa4:
            st.error("⚠️ Nombre y Placa son obligatorios.")
        elif foto4 is None:
            st.error("⚠️ La fotografía del odómetro es OBLIGATORIA.")
        else:
            datos4 = {
                "conductor": conductor4, "placa": placa4, "kilometraje": km4,
                "sugerencias": sugerencias4, "fecha_envio": str(date.today()),
                "hora_envio": datetime.now().strftime("%H:%M:%S")
            }
            archivos4 = [preparar_archivo(foto4)]
            procesar_envio("llegada_parqueadero", datos4, archivos4)

st.markdown("---")
st.caption("Hecho con Streamlit + GitHub · Añade esta página a tu pantalla de inicio 📲")
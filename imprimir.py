import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Etiquetadora Vevor 35x25", layout="wide", initial_sidebar_state="collapsed")

# Estilos visuales TPV
st.markdown("""
    <style>
    .notranslate { translate: no !important; }
    .btn-num button { height: 80px !important; font-size: 30px !important; font-weight: bold !important; border-radius: 12px !important; }
    .main-display { background:#212529; color:#00ff00; padding:15px; border-radius:10px; text-align:center; margin-bottom:15px; border: 2px solid #444; }
    </style>
    """, unsafe_allow_html=True)

if 'busqueda' not in st.session_state: st.session_state.busqueda = ""
if 'paso' not in st.session_state: st.session_state.paso = "buscar"
if 'producto_sel' not in st.session_state: st.session_state.producto_sel = None
if 'cant_copias' not in st.session_state: st.session_state.cant_copias = ""

# --- CARGA DE DATOS DESDE GOOGLE DRIVE ---
@st.cache_data(ttl=600)
def cargar_datos():
    sheet_id = "15XnTblNUJKf1HPkNAl7c0OZ3J3td32CatZmCkFkRoOI"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return pd.read_csv(url)

try:
    df = cargar_datos()
except Exception as e:
    st.error("Error al conectar con Google Drive. Revisa los permisos de compartir.")
    st.stop()

# --- VISTA 1: BUSCADOR ---
if st.session_state.paso == "buscar":
    st.markdown(f"<div class='main-display'><h1>{st.session_state.busqueda if st.session_state.busqueda else 'ESCRIBA PRODUCTO...'}</h1></div>", unsafe_allow_html=True)
    col_teclado, col_resultados = st.columns([0.6, 0.4])
    with col_teclado:
        for fila in ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM "]:
            cols = st.columns(len(fila))
            for i, letra in enumerate(fila):
                label = "ESP" if letra == " " else letra
                if cols[i].button(label, key=f"k_{letra}", use_container_width=True):
                    st.session_state.busqueda += letra
                    st.rerun()
        c1, c2 = st.columns(2)
        if c1.button("⬅️ BORRAR", use_container_width=True): st.session_state.busqueda = st.session_state.busqueda[:-1]; st.rerun()
        if c2.button("🗑️ LIMPIAR", use_container_width=True): st.session_state.busqueda = ""; st.rerun()

    with col_resultados:
        if st.session_state.busqueda:
            filtro = df[df['Producto'].str.contains(st.session_state.busqueda, case=False, na=False)]
            for p in filtro['Producto'].head(7):
                if st.button(f"📍 {p}", key=f"res_{p}", use_container_width=True):
                    st.session_state.update({"producto_sel": p, "paso": "cantidad", "cant_copias": ""})
                    st.rerun()

# --- VISTA 2: CANTIDAD Y PDF ---
elif st.session_state.paso == "cantidad":
    info_prod = df[df['Producto'] == st.session_state.producto_sel].iloc[0]
    ahora = datetime.now()
    h_proc = float(info_prod.get('H_Desc_Proceso', 0)) if not pd.isna(info_prod.get('H_Desc_Proceso')) else 0
    h_vida = float(info_prod.get('H_Vida_Post', 0)) if not pd.isna(info_prod.get('H_Vida_Post')) else 0
    
    f_uso_dt = ahora + timedelta(hours=h_proc)
    
    # Lógica para "Ver fecha fabricante"
    usa_fecha_fab = (h_vida == 0)
    
    txt_elab = ahora.strftime('%d/%m/%y %H:%M')
    txt_uso = f_uso_dt.strftime('%d/%m/%y %H:%M')
    
    if usa_fecha_fab:
        txt_cad_display = "VER FECHA FABRICANTE"
    else:
        f_cad_dt = f_uso_dt + timedelta(hours=h_vida)
        txt_cad_display = f_cad_dt.strftime('%d/%m/%y %H:%M')

    st.subheader(f"Seleccionado: {st.session_state.producto_sel}")
    col_pre, col_num = st.columns([0.4, 0.6])
    with col_pre:
        with st.container(border=True):
            st.write(f"**ELAB:** {txt_elab}")
            st.write(f"**USO:** {txt_uso}")
            if usa_fecha_fab:
                st.warning(f"### {txt_cad_display}")
            else:
                st.error(f"### CADUCIDAD:\n{txt_cad_display}")
                
        if st.session_state.cant_copias:
            if st.button(f"📄 GENERAR {st.session_state.cant_copias} ETIQUETAS", type="primary", use_container_width=True):
                nombre_pdf = "etiqueta.pdf"
                c = canvas.Canvas(nombre_pdf, pagesize=(35*mm, 25*mm))
                for _ in range(int(st.session_state.cant_copias)):
                    # Nombre producto
                    c.setFont("Helvetica-Bold", 8)
                    c.drawString(2*mm, 21*mm, str(st.session_state.producto_sel)[:20])
                    
                    # Fechas ELAB y USO
                    c.setFont("Helvetica", 6.5)
                    c.drawString(2*mm, 17*mm, f"ELAB: {txt_elab}")
                    c.drawString(2*mm, 13.5*mm, f"USO:  {txt_uso}")
                    
                    c.setLineWidth(0.1)
                    c.line(2*mm, 12*mm, 33*mm, 12*mm)
                    
                    # Caducidad o Ver Fecha Fabricante
                    if usa_fecha_fab:
                        c.setFont("Helvetica-Bold", 7.5) # Un poco más pequeña para que quepa bien
                        c.drawString(2*mm, 6*mm, txt_cad_display)
                    else:
                        c.setFont("Helvetica-Bold", 9)
                        c.drawString(2*mm, 6*mm, f"CAD: {txt_cad_display}")
                    
                    c.showPage()
                c.save()
                with open(nombre_pdf, "rb") as f:
                    st.download_button("⬇️ DESCARGAR PDF", f, file_name=nombre_pdf, mime="application/pdf", use_container_width=True)
        if st.button("⬅️ VOLVER"): st.session_state.paso = "buscar"; st.rerun()

    with col_num:
        st.markdown(f"<div style='text-align:center; background:#eee; padding:10px; border-radius:10px;'><h1>{st.session_state.cant_copias if st.session_state.cant_copias else '0'}</h1><small>COPIAS</small></div>", unsafe_allow_html=True)
        nums = [["1","2","3"], ["4","5","6"], ["7","8","9"], ["C", "0", "⬅️"]]
        for fila_n in nums:
            cols = st.columns(3)
            for i, n in enumerate(fila_n):
                if cols[i].button(n, key=f"n_{n}", use_container_width=True):
                    if n == "⬅️": st.session_state.cant_copias = st.session_state.cant_copias[:-1]
                    elif n == "C": st.session_state.cant_copias = ""
                    else: st.session_state.cant_copias += n
                    st.rerun()

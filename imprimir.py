import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# --- CONFIGURACIÓN TPV ---
st.set_page_config(page_title="Etiquetas Papavero", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .notranslate { translate: no !important; }
    .stButton button { height: 75px !important; font-size: 25px !important; border-radius: 15px !important; }
    .main-display { background:#1e1e1e; color:#00ff00; padding:20px; border-radius:15px; text-align:center; border: 2px solid #333; }
    h1, h2, h3 { color: #333; }
    </style>
    """, unsafe_allow_html=True)

if 'busqueda' not in st.session_state: st.session_state.busqueda = ""
if 'paso' not in st.session_state: st.session_state.paso = "buscar"
if 'producto_sel' not in st.session_state: st.session_state.producto_sel = None
if 'cant_copias' not in st.session_state: st.session_state.cant_copias = ""

@st.cache_data(ttl=300)
def cargar_datos():
    sheet_id = "15XnTblNUJKf1HPkNAl7c0OZ3J3td32CatZmCkFkRoOI"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return pd.read_csv(url)

try:
    df = cargar_datos()
except:
    st.error("Error conectando con Google Drive")
    st.stop()

# --- BUSCADOR ---
if st.session_state.paso == "buscar":
    st.markdown(f"<div class='main-display'><h1>{st.session_state.busqueda if st.session_state.busqueda else 'BUSCAR PRODUCTO...'}</h1></div>", unsafe_allow_html=True)
    col_teclado, col_resultados = st.columns([0.6, 0.4])
    
    with col_teclado:
        for fila in ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM "]:
            cols = st.columns(len(fila))
            for i, letra in enumerate(fila):
                label = "ESPACIO" if letra == " " else letra
                if cols[i].button(label, key=f"k_{letra}", use_container_width=True):
                    st.session_state.busqueda += letra
                    st.rerun()
        c1, c2 = st.columns(2)
        if c1.button("⬅️ BORRAR", use_container_width=True): st.session_state.busqueda = st.session_state.busqueda[:-1]; st.rerun()
        if c2.button("🗑️ LIMPIAR", use_container_width=True): st.session_state.busqueda = ""; st.rerun()

    with col_resultados:
        if st.session_state.busqueda:
            filtro = df[df['Producto'].str.contains(st.session_state.busqueda, case=False, na=False)]
            for p in filtro['Producto'].head(6):
                if st.button(f"📍 {p}", key=f"res_{p}", use_container_width=True):
                    st.session_state.update({"producto_sel": p, "paso": "cantidad", "cant_copias": ""})
                    st.rerun()

# --- CANTIDAD Y ENVÍO ---
elif st.session_state.paso == "cantidad":
    info = df[df['Producto'] == st.session_state.producto_sel].iloc[0]
    ahora = datetime.now()
    
    # Datos de la tabla
    h_proc = float(info.get('H_Desc_Proceso', 0)) if not pd.isna(info.get('H_Desc_Proceso')) else 0
    h_vida = float(info.get('H_Vida_Post', 0)) if not pd.isna(info.get('H_Vida_Post')) else 0
    es_elaboracion = str(info.get('Tipo', '')).lower() == 'elaboracion'
    
    f_uso = ahora + timedelta(hours=h_proc)
    es_fab = (h_vida == 0)
    
    txt_elab = ahora.strftime('%d/%m/%y %H:%M')
    txt_uso = f_uso.strftime('%d/%m/%y %H:%M')
    txt_cad = "VER FECHA FABRICANTE" if es_fab else (f_uso + timedelta(hours=h_vida)).strftime('%d/%m/%y %H:%M')
    
    # Generación de Lote automático (Ej: L + día del año)
    lote_auto = f"L{ahora.timetuple().tm_yday}" if es_elaboracion else ""

    st.markdown(f"<div style='background:#f0f2f6; padding:20px; border-radius:15px; margin-bottom:10px;'><h2>{st.session_state.producto_sel}</h2></div>", unsafe_allow_html=True)
    
    col_pre, col_num = st.columns([0.4, 0.6])
    with col_pre:
        st.write(f"**ELAB:** {txt_elab}")
        if es_elaboracion: st.success(f"**LOTE:** {lote_auto}")
        st.write(f"**USO:** {txt_uso}")
        st.error(f"### {txt_cad}")
        
        if st.session_state.cant_copias:
            timestamp = ahora.strftime("%H%M%S")
            nombre_f = f"etiqueta_{timestamp}.pdf"
            c = canvas.Canvas(nombre_f, pagesize=(35*mm, 25*mm))
            for _ in range(int(st.session_state.cant_copias)):
                # Nombre producto
                c.setFont("Helvetica-Bold", 8)
                c.drawString(2*mm, 21*mm, str(st.session_state.producto_sel)[:20])
                
                # Línea de Elab y Lote
                c.setFont("Helvetica", 6.5)
                linea_elab = f"ELAB: {txt_elab}"
                if es_elaboracion: linea_elab += f"  LOT: {lote_auto}"
                c.drawString(2*mm, 17.5*mm, linea_elab)
                
                # Línea de Uso
                c.drawString(2*mm, 14*mm, f"USO:  {txt_uso}")
                
                c.setLineWidth(0.1)
                c.line(2*mm, 12.5*mm, 33*mm, 12.5*mm)
                
                # Caducidad
                c.setFont("Helvetica-Bold", 7.5 if es_fab else 9)
                c.drawString(2*mm, 6.5*mm, txt_cad if es_fab else f"CAD: {txt_cad}")
                c.showPage()
            c.save()
            
            with open(nombre_f, "rb") as f:
                st.download_button("🖨️ ENVIAR A FLASH LABEL", f, file_name=nombre_f, mime="application/pdf", use_container_width=True)
        
        if st.button("⬅️ VOLVER", use_container_width=True): st.session_state.paso = "buscar"; st.rerun()

    with col_num:
        st.markdown(f"<div style='text-align:center; background:#eee; padding:10px; border-radius:10px;'><h1>{st.session_state.cant_copias if st.session_state.cant_copias else '0'}</h1></div>", unsafe_allow_html=True)
        for f in [["1","2","3"], ["4","5","6"], ["7","8","9"], ["C","0","⬅️"]]:
            cols = st.columns(3)
            for i, n in enumerate(f):
                if cols[i].button(n, key=f"n_{n}", use_container_width=True):
                    if n == "⬅️": st.session_state.cant_copias = st.session_state.cant_copias[:-1]
                    elif n == "C": st.session_state.cant_copias = ""
                    else: st.session_state.cant_copias += n
                    st.rerun()

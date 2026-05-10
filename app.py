# ===========================================
# app.py — Wyscout Analysis (Portfolio Version)
# ===========================================
# Built originally for Cibao FC; the login gate has been removed
# so the app can be showcased without credentials.
# ===========================================

import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Wyscout Analysis",
    layout="centered",
    initial_sidebar_state="expanded"
)

# -------------------------------------------
# Router: navegación rápida entre módulos (Cibao FC Hub)
# -------------------------------------------
def _handle_go_param():
    try:
        qp = st.query_params
        go = qp.get("go", None)
    except Exception:
        qp = st.experimental_get_query_params()
        go = qp.get("go", [None])[0] if isinstance(qp.get("go"), list) else qp.get("go")

    if not go:
        return

    # === Mapeo actualizado según nombres renombrados ===
    mapping = {
        # LIGA"colectivo": "pages/1_Rendimiento_Colectivo_-_Liga.py","rival": "pages/2_Analisis_del_Rival_-_Liga.py",

        # COPA"colectivo_copa": "pages/4_Rendimiento_Colectivo_-_Copa.py","rival_copa": "pages/5_Analisis_del_Rival_-_Copa.py",
    }

    page = mapping.get(str(go).lower())
    if page:
        try:
            st.query_params.clear()
        except Exception:
            st.experimental_set_query_params()
        st.switch_page(page)

# Llamar al router lo antes posible
_handle_go_param()


# ===========================================
# HUB PAGE (CENTRO DE NAVEGACIÓN)
# ===========================================
def main_hub():
    import streamlit.components.v1 as components

    # ======== CSS GENERAL ========
    st.markdown("""<style>
        [data-testid="stSidebar"], [data-testid="stToolbar"], header[data-testid="stHeader"] {
            display: none !important;
        }
        [data-testid="stAppViewContainer"] {
            background:
              linear-gradient(rgba(10,10,10,0.75), rgba(10,10,10,0.85)),
              url("https://www.presidencia.gob.do/sites/default/files/inline-images/00449e09-428b-4cf5-9264-c9204705de13.jpeg");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }
        .hub-title {
            font-size: 2.8rem;
            font-weight: 900;
            color: #ff7b00;
            text-align: center;
            margin-top: 6vh;
            margin-bottom: 0.4rem;
            text-shadow: 0 0 10px rgba(255,123,0,0.5);
        }
        .hub-subtitle {
            text-align: center;
            color: #f0f0f0;
            font-size: 1.05rem;
            margin-bottom: 1.4rem;
        }
        div[data-testid="stSelectbox"] {
            max-width: 360px;
            margin: 0 auto 2.4rem auto;
        }
        div[data-testid="stSelectbox"] label {
            color: #ffffff !important;
            font-weight: 800 !important;
            text-align: center !important;
            display: block !important;
            margin-bottom: 0.5rem !important;
        }
        div[data-testid="stSelectbox"] > div > div {
            background-color: rgba(20,20,20,0.85) !important;
            border: 1.5px solid rgba(255,123,0,0.6) !important;
            border-radius: 14px !important;
            min-height: 56px !important;
            box-shadow: 0 6px 15px rgba(0,0,0,0.25) !important;
            transition: all 0.3s ease !important;
        }
        div[data-testid="stSelectbox"] > div > div:hover {
            background-color: rgba(255,123,0,0.15) !important;
            border-color: #ff9b25 !important;
            box-shadow: 0 0 20px rgba(255,123,0,0.4) !important;
            transform: translateY(-3px);
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            position: relative !important;
            display: flex !important;
            align-items: center !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div > div:first-child {
            width: 100% !important;
            padding-left: 44px !important;
            padding-right: 44px !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div > div:first-child * {
            text-align: center !important;
            color: #ffffff !important;
            font-weight: 800 !important;
            font-size: 0.91rem !important;
            line-height: 1 !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div > div:last-child {
            position: absolute !important;
            right: 18px !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            pointer-events: none !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] svg {
            color: #ffffff !important;
        }
        ul[data-baseweb="menu"] li {
            text-align: center !important;
            justify-content: center !important;
            font-weight: 700 !important;
        }
        ul[data-baseweb="menu"] li > div {
            justify-content: center !important;
            text-align: center !important;
            width: 100% !important;
        }
        div[data-testid="stButton"] > button {
            background-color: rgba(20,20,20,0.85) !important;
            border: 1.5px solid rgba(255,123,0,0.6) !important;
            color: #ffffff !important;
            font-weight: 800 !important;
            font-size: 0.91rem !important;
            border-radius: 14px !important;
            height: 85px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 6px 15px rgba(0,0,0,0.25) !important;
        }
        div[data-testid="stButton"] > button:hover {
            background-color: rgba(255,123,0,0.15) !important;
            border-color: #ff9b25 !important;
            color: #ff9b25 !important;
            box-shadow: 0 0 20px rgba(255,123,0,0.4) !important;
            transform: translateY(-3px);
        }
        </style>""", unsafe_allow_html=True)

    # ======== LOGO Y TITULOS ========
    st.markdown("""<div style="text-align:center; margin-top:2vh;">
            <img src="https://www.cibaofc.com/wp-content/uploads/2025/02/cropped-LOGO-CFC-5-NARANJA-BLANCO.png" width="120">
        </div>""", unsafe_allow_html=True)

    st.markdown("<div class='hub-title'>Cibao FC - Data Hub</div>", unsafe_allow_html=True)
    st.markdown("<div class='hub-subtitle'>Centro integral de análisis táctico y rendimiento basado en datos</div>", unsafe_allow_html=True)

    languages = ["Chinese","English","French","German","Italian","Portuguese","Spanish",
    ]
    st.selectbox("Seleccionar idioma",
        languages,
        index=languages.index("Spanish"),
        key="selected_language",
    )

    # ===========================================
    #                ANÁLISIS LIGA
    # ===========================================
    st.markdown("<h3 style='text-align:center; color:#ff7b00; margin-top:20px;'>ANÁLISIS LIGA</h3>", unsafe_allow_html=True)

    liga_modules = [
        ("Rendimiento Colectivo", "pages/1_Rendimiento_Colectivo_-_Liga.py"),
        ("Análisis del Rival", "pages/2_Analisis_del_Rival_-_Liga.py"),
    ]

    cols_liga = st.columns(2, gap="large")
    for i, (title, page) in enumerate(liga_modules):
        with cols_liga[i]:
            if st.button(f"**{title}**", use_container_width=True, key=f"liga_btn_{i}"):
                st.switch_page(page)

    # Separador reducido
    st.markdown("<hr style='margin-top:20px; margin-bottom:8px; opacity:0.25;'>", unsafe_allow_html=True)

    # ===========================================
    #                ANÁLISIS COPA
    # ===========================================
    st.markdown("<h3 style='text-align:center; color:#ff7b00; margin-top:5px;'>ANÁLISIS COPA</h3>", unsafe_allow_html=True)

    copa_modules = [
        ("Rendimiento Colectivo", "pages/4_Rendimiento_Colectivo_-_Copa.py"),
        ("Análisis del Rival", "pages/5_Analisis_del_Rival_-_Copa.py"),
    ]

    cols_copa = st.columns(2, gap="large")
    for i, (title, page) in enumerate(copa_modules):
        with cols_copa[i]:
            if st.button(f"**{title}**", use_container_width=True, key=f"copa_btn_{i}"):
                st.switch_page(page)
    
    # Separador reducido
    st.markdown("<hr style='margin-top:20px; margin-bottom:8px; opacity:0.25;'>", unsafe_allow_html=True)
    
    # ===========================================
    #           GESTIÓN DE DATOS
    # ===========================================
    st.markdown("<h3 style='text-align:center; color:#ff7b00; margin-top:5px;'>GESTIÓN DE DATOS</h3>", unsafe_allow_html=True)
    
    data_modules = [
        ("Upload Wyscout Data", "pages/0_Upload_Wyscout_Data.py"),
    ]
    
    cols_data = st.columns(1, gap="large")
    for i, (title, page) in enumerate(data_modules):
        with cols_data[0]:
            if st.button(f"**{title}**", use_container_width=True, key=f"data_btn_{i}"):
                st.switch_page(page)
    
            
# ===========================================
# ENTRY POINT
# ===========================================
# Login removed for portfolio showcase: render the hub directly.
main_hub()

"""
Navigation component for consistent top navigation across all pages
"""
import streamlit as st


def render_top_navigation():
    """
    Renders a top navigation bar that appears on all pages.
    Allows users to navigate between pages without going back to the hub.
    Standardized styling for consistent UX across all pages.
    Also ensures the sidebar toggle button is visible.
    """
    # CSS for navigation bar - standardized across all pages.
    # NOTE: Streamlit 1.30+ does NOT render `key` as an attribute on <button>.
    # Instead, the wrapper div gets class="st-key-<key>". So we target via
    # [class*="st-key-nav_"] button (and the inner <p> where text actually renders).
    st.markdown("""
    <style>
    /* Ensure sidebar toggle button is always visible */
    [data-testid="stSidebarCollapseButton"] {
        display: block !important;
        visibility: visible !important;
    }
    [data-testid="stSidebar"] {
        transition: transform 0.3s ease;
    }

    .top-nav-container {
        background: linear-gradient(135deg, rgba(20, 20, 25, 0.95) 0%, rgba(15, 15, 20, 0.98) 100%);
        border-bottom: 2px solid rgba(255, 140, 0, 0.3);
        padding: 0.8rem 1.5rem;
        margin: -1rem -1rem 1.5rem -1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    .nav-label {
        color: #94A3B8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 0.5rem;
        line-height: 2.5;
    }

    /* Top navigation buttons - sleek, compact, consistent across ALL pages */
    [class*="st-key-nav_"] button {
        background-color: #ff7b00 !important;
        border: 1px solid #ff7b00 !important;
        color: black !important;
        border-radius: 6px !important;
        padding: 0.4rem 0.75rem !important;
        min-height: 40px !important;
        height: 40px !important;
        line-height: 1 !important;
        width: 100% !important;
        box-sizing: border-box !important;
        transition: all 0.2s !important;
        white-space: nowrap !important;
        overflow: hidden !important;
    }
    /* The inner <p> is where text actually renders. Force compact 13px. */
    [class*="st-key-nav_"] button p {
        font-size: 13px !important;
        line-height: 1.2 !important;
        font-weight: 600 !important;
        color: black !important;
        margin: 0 !important;
        padding: 0 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    /* Home button: slightly larger emoji */
    [class*="st-key-nav_home_top"] button p {
        font-size: 16px !important;
    }
    [class*="st-key-nav_"] button:hover {
        background-color: #ff8c00 !important;
        border-color: #ff8c00 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Navigation bar using Streamlit columns and buttons
    st.markdown('<div class="top-nav-container">', unsafe_allow_html=True)
    
    # Create columns for navigation - consistent spacing
    col_home, col_spacer1, col_liga_label, col_liga1, col_liga2, col_spacer2, col_copa_label, col_copa1, col_copa2 = st.columns([1, 0.3, 0.8, 2, 2, 0.3, 0.8, 2, 2])
    
    with col_home:
        if st.button("🏠", help="Volver al Inicio", use_container_width=True, key="nav_home_top"):
            st.switch_page("app.py")
    
    with col_liga_label:
        st.markdown('<div class="nav-label">Liga:</div>', unsafe_allow_html=True)
    
    with col_liga1:
        if st.button("Rendimiento Colectivo", key="nav_liga_colectivo_top", use_container_width=True):
            st.switch_page("pages/1_Rendimiento_Colectivo_-_Liga.py")
    
    with col_liga2:
        if st.button("Análisis del Rival", key="nav_liga_rival_top", use_container_width=True):
            st.switch_page("pages/2_Analisis_del_Rival_-_Liga.py")
    
    with col_copa_label:
        st.markdown('<div class="nav-label">Copa:</div>', unsafe_allow_html=True)
    
    with col_copa1:
        if st.button("Rendimiento Colectivo", key="nav_copa_colectivo_top", use_container_width=True):
            st.switch_page("pages/4_Rendimiento_Colectivo_-_Copa.py")
    
    with col_copa2:
        if st.button("Análisis del Rival", key="nav_copa_rival_top", use_container_width=True):
            st.switch_page("pages/5_Analisis_del_Rival_-_Copa.py")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


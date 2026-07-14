import streamlit as st


def aplicar_fundo(logado=False):

    st.markdown("""
    <style>

    /* =====================================================
       FUNDO PRINCIPAL
    ===================================================== */

    .stApp{
        background:
            radial-gradient(circle at top left,#312e81 0%,transparent 35%),
            radial-gradient(circle at top right,#0ea5e9 0%,transparent 35%),
            radial-gradient(circle at bottom right,#7c3aed 0%,transparent 30%),
            linear-gradient(
                135deg,
                #010617,
                #020b24,
                #010617
            );
        color:white;
    }

    header{
        visibility:hidden;
    }

    footer{
        visibility:hidden;
    }

    .block-container{
        padding-top:2rem;
        padding-bottom:2rem;
        max-width:95%;
    }

    /* =====================================================
       SIDEBAR
    ===================================================== */

    section[data-testid="stSidebar"]{
        background:rgba(5,10,25,.95);
        border-right:1px solid rgba(255,255,255,.05);
    }

    section[data-testid="stSidebar"] *{
        color:white !important;
    }

    /* =====================================================
       INPUTS
    ===================================================== */

    .stTextInput input,
    .stNumberInput input{
        border-radius:12px;
        background:rgba(255,255,255,0.05);
        color:white;
        border:1px solid rgba(255,255,255,0.08);
    }

    .stTextInput input:focus,
    .stNumberInput input:focus{
        border:1px solid #00c8ff;
        box-shadow:0 0 10px rgba(0,200,255,.4);
    }

    /* =====================================================
       BOTÕES
    ===================================================== */

    .stButton button{
        width:100%;
        height:50px;
        border:none;
        border-radius:12px;
        color:white;
        font-weight:700;
        background:linear-gradient(
            90deg,
            #00c8ff,
            #3b82f6
        );
        transition:.3s;
    }

    .stButton button:hover{
        transform:translateY(-2px);
        box-shadow:
            0 0 20px rgba(0,200,255,.35);
    }

    /* =====================================================
       KPIs
    ===================================================== */

    div[data-testid="metric-container"]{
        background:rgba(255,255,255,.04);
        border:1px solid rgba(255,255,255,.08);
        border-radius:18px;
        padding:15px;
        backdrop-filter:blur(20px);
        box-shadow:
            0 0 20px rgba(0,0,0,.15);
    }

    div[data-testid="metric-container"] label{
        color:#9ca3af !important;
        font-size:13px !important;
    }

    div[data-testid="metric-container"] [data-testid="stMetricValue"]{
        font-size:28px !important;
        color:white !important;
    }

    /* =====================================================
       TABELAS
    ===================================================== */

    .stDataFrame{
        border-radius:20px;
        overflow:hidden;
    }

    /* =====================================================
       TABS
    ===================================================== */

    .stTabs [data-baseweb="tab"]{
        font-size:16px;
        font-weight:600;
        color:#d1d5db;
    }

    .stTabs [aria-selected="true"]{
        color:#00c8ff !important;
    }

    /* =====================================================
       RODAPÉ LUXIZ IA
    ===================================================== */

    .luxiz-footer{
        text-align:center;
        margin-top:25px;
        color:#94a3b8;
        font-size:13px;
        opacity:0.8;
    }

    /* ========================================
RODAPÉ FIXO
======================================== */

.footer-luxiz {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background: rgba(5,10,25,0.95);
    border-top: 1px solid rgba(255,255,255,0.08);
    backdrop-filter: blur(15px);
    padding: 8px 20px;
    text-align: center;
    font-size: 13px;
    color: #d1d5db;
    z-index: 999999;
}

.footer-luxiz span.online {
    color: #22c55e;
    font-weight: 700;
}

.footer-luxiz span.cloud {
    color: #38bdf8;
    font-weight: 700;
}

.footer-luxiz span.refresh {
    color: #facc15;
    font-weight: 700;
}

    </style>
    """, unsafe_allow_html=True)

def logo_header():

    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:5px;">
        <span style="font-size:32px;">✨</span>
        <span style="font-size:28px;font-weight:800;color:white;">Luxiz IA</span>
    </div>
    <div style="color:#94a3b8;font-size:15px;margin-bottom:15px;">
        Centro Inteligente de Operações
    </div>
    """, unsafe_allow_html=True)


def rodape():

    st.markdown("""
    <div class="luxiz-footer">
        Desenvolvido por Luxiz IA
    </div>
    """, unsafe_allow_html=True)

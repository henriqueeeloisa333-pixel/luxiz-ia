import streamlit as st


def aplicar_fundo(tema="escuro"):

    if tema == "claro":

        st.markdown("""
        <style>

        /* =====================================================
           FUNDO PRINCIPAL (CLARO)
        ===================================================== */

        .stApp{
            background:
                radial-gradient(circle at top left,#e0e7ff 0%,transparent 35%),
                radial-gradient(circle at top right,#bae6fd 0%,transparent 35%),
                radial-gradient(circle at bottom right,#ede9fe 0%,transparent 30%),
                linear-gradient(
                    135deg,
                    #f8fafc,
                    #f1f5f9,
                    #f8fafc
                );
            color:#111827;
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
            background:rgba(255,255,255,.95);
            border-right:1px solid rgba(0,0,0,.06);
        }

        section[data-testid="stSidebar"] *{
            color:#111827 !important;
        }

        /* =====================================================
           INPUTS
        ===================================================== */

        .stTextInput input,
        .stNumberInput input{
            border-radius:12px;
            background:rgba(0,0,0,0.03);
            color:#111827;
            border:1px solid rgba(0,0,0,0.12);
        }

        .stTextInput input:focus,
        .stNumberInput input:focus{
            border:1px solid #0284c7;
            box-shadow:0 0 10px rgba(2,132,199,.25);
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
                #0284c7,
                #2563eb
            );
            transition:.3s;
        }

        .stButton button:hover{
            transform:translateY(-2px);
            box-shadow:
                0 0 20px rgba(2,132,199,.25);
        }

        /* =====================================================
           KPIs
        ===================================================== */

        div[data-testid="metric-container"],
        div[data-testid="stMetric"]{
            background:rgba(0,0,0,.03);
            border:1px solid rgba(0,0,0,.08);
            border-radius:18px;
            padding:15px;
            backdrop-filter:blur(20px);
            box-shadow:
                0 0 15px rgba(0,0,0,.05);
        }

        div[data-testid="metric-container"] label,
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricLabel"] *{
            color:#4b5563 !important;
            font-size:13px !important;
        }

        div[data-testid="metric-container"] [data-testid="stMetricValue"],
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricValue"] *{
            font-size:28px !important;
            color:#111827 !important;
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
            color:#4b5563;
        }

        .stTabs [aria-selected="true"]{
            color:#0284c7 !important;
        }

        /* =====================================================
           RODAPÉ LUXIZ IA
        ===================================================== */

        .luxiz-footer{
            text-align:center;
            margin-top:25px;
            color:#64748b;
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
            background: rgba(255,255,255,0.95);
            border-top: 1px solid rgba(0,0,0,0.08);
            backdrop-filter: blur(15px);
            padding: 8px 20px;
            text-align: center;
            font-size: 13px;
            color: #374151;
            z-index: 999999;
        }

        .footer-luxiz span.online {
            color: #16a34a;
            font-weight: 700;
        }

        .footer-luxiz span.cloud {
            color: #0284c7;
            font-weight: 700;
        }

        .footer-luxiz span.refresh {
            color: #ca8a04;
            font-weight: 700;
        }

        /* =====================================================
           LOGO / CABEÇALHO
        ===================================================== */

        .luxiz-logo{
            text-align:left;
            margin-bottom:10px;
        }

        .luxiz-logo h1{
            font-size:2.4rem;
            font-weight:800;
            letter-spacing:.5px;
            margin:0;
            background:linear-gradient(90deg,#0284c7,#7c3aed,#0284c7);
            background-size:200% auto;
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
        }

        .luxiz-logo p{
            margin:2px 0 0 0;
            font-size:.8rem;
            font-weight:600;
            letter-spacing:2.5px;
            text-transform:uppercase;
            color:#64748b;
        }

        /* =====================================================
           RODAPÉ "DESENVOLVIDO POR"
        ===================================================== */

        .luxiz-dev-footer{
            text-align:center;
            margin-top:18px;
            padding-top:14px;
            border-top:1px solid rgba(0,0,0,.08);
        }

        .luxiz-dev-footer .marca{
            font-size:.85rem;
            font-weight:700;
            letter-spacing:.5px;
            background:linear-gradient(90deg,#0284c7,#7c3aed);
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
        }

        .luxiz-dev-footer .sub{
            font-size:.72rem;
            color:#94a3b8;
            margin-top:2px;
        }

        </style>
        """, unsafe_allow_html=True)

    else:

        st.markdown("""
        <style>

        /* =====================================================
           FUNDO PRINCIPAL (ESCURO)
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

        div[data-testid="metric-container"],
        div[data-testid="stMetric"]{
            background:rgba(255,255,255,.04);
            border:1px solid rgba(255,255,255,.08);
            border-radius:18px;
            padding:15px;
            backdrop-filter:blur(20px);
            box-shadow:
                0 0 20px rgba(0,0,0,.15);
        }

        div[data-testid="metric-container"] label,
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricLabel"] *{
            color:#9ca3af !important;
            font-size:13px !important;
        }

        div[data-testid="metric-container"] [data-testid="stMetricValue"],
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricValue"] *{
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

        /* =====================================================
           LOGO / CABEÇALHO
        ===================================================== */

        .luxiz-logo{
            text-align:left;
            margin-bottom:10px;
        }

        .luxiz-logo h1{
            font-size:2.4rem;
            font-weight:800;
            letter-spacing:.5px;
            margin:0;
            background:linear-gradient(90deg,#00c8ff,#a855f7,#00c8ff);
            background-size:200% auto;
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
        }

        .luxiz-logo p{
            margin:2px 0 0 0;
            font-size:.8rem;
            font-weight:600;
            letter-spacing:2.5px;
            text-transform:uppercase;
            color:#94a3b8;
        }

        /* =====================================================
           RODAPÉ "DESENVOLVIDO POR"
        ===================================================== */

        .luxiz-dev-footer{
            text-align:center;
            margin-top:18px;
            padding-top:14px;
            border-top:1px solid rgba(255,255,255,.08);
        }

        .luxiz-dev-footer .marca{
            font-size:.85rem;
            font-weight:700;
            letter-spacing:.5px;
            background:linear-gradient(90deg,#00c8ff,#a855f7);
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
        }

        .luxiz-dev-footer .sub{
            font-size:.72rem;
            color:#64748b;
            margin-top:2px;
        }

        </style>
        """, unsafe_allow_html=True)


# =====================================================
# LOGO / CABEÇALHO PADRÃO
# =====================================================

def logo_header(subtitulo="Centro Inteligente de Operações"):

    st.markdown(
        f"""
        <div class="luxiz-logo">
            <h1>✨ Luxiz IA</h1>
            <p>{subtitulo}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# RODAPÉ "DESENVOLVIDO POR"
# =====================================================

def rodape():

    st.markdown(
        """
        <div class="luxiz-dev-footer">
            <div class="marca">✨ Luxiz IA</div>
            <div class="sub">Centro Inteligente de Operações</div>
        </div>
        """,
        unsafe_allow_html=True
    )

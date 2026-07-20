import streamlit as st


# =====================================================
# CSS COMPARTILHADO
# (botões, inputs, sidebar, KPIs, tabelas, abas, rodapé,
# logo — igual em qualquer tela, muda só por tema)
# =====================================================

def _css_base(tema):

    if tema == "claro":

        return """
        <style>

        header{visibility:hidden;}
        footer{visibility:hidden;}

        .block-container{
            padding-top:2rem;
            padding-bottom:2rem;
            max-width:95%;
        }

        section[data-testid="stSidebar"]{
            background:rgba(255,255,255,.95);
            border-right:1px solid rgba(0,0,0,.06);
        }

        section[data-testid="stSidebar"] *{
            color:#111827 !important;
        }

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

        .stButton button{
            width:100%;
            height:50px;
            border:none;
            border-radius:12px;
            color:white;
            font-weight:700;
            background:linear-gradient(90deg,#0284c7,#2563eb);
            transition:.3s;
        }

        .stButton button:hover{
            transform:translateY(-2px);
            box-shadow:0 0 20px rgba(2,132,199,.25);
        }

        div[data-testid="metric-container"],
        div[data-testid="stMetric"]{
            background:rgba(0,0,0,.03);
            border:1px solid rgba(0,0,0,.08);
            border-radius:18px;
            padding:15px;
            backdrop-filter:blur(20px);
            box-shadow:0 0 15px rgba(0,0,0,.05);
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

        .stDataFrame{
            border-radius:20px;
            overflow:hidden;
        }

        .stTabs [data-baseweb="tab"]{
            font-size:16px;
            font-weight:600;
            color:#4b5563;
        }

        .stTabs [aria-selected="true"]{
            color:#0284c7 !important;
        }

        .luxiz-footer{
            text-align:center;
            margin-top:25px;
            color:#64748b;
            font-size:13px;
            opacity:0.8;
        }

        .footer-luxiz{
            position:fixed;
            bottom:0;
            left:0;
            width:100%;
            background:rgba(255,255,255,0.95);
            border-top:1px solid rgba(0,0,0,0.08);
            backdrop-filter:blur(15px);
            padding:8px 20px;
            text-align:center;
            font-size:13px;
            color:#374151;
            z-index:999999;
        }

        .footer-luxiz span.online{ color:#16a34a; font-weight:700; }
        .footer-luxiz span.cloud{ color:#0284c7; font-weight:700; }
        .footer-luxiz span.refresh{ color:#ca8a04; font-weight:700; }

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
        """

    return """
    <style>

    header{visibility:hidden;}
    footer{visibility:hidden;}

    .block-container{
        padding-top:2rem;
        padding-bottom:2rem;
        max-width:95%;
    }

    section[data-testid="stSidebar"]{
        background:rgba(5,10,25,.95);
        border-right:1px solid rgba(255,255,255,.05);
    }

    section[data-testid="stSidebar"] *{
        color:white !important;
    }

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

    .stButton button{
        width:100%;
        height:50px;
        border:none;
        border-radius:12px;
        color:white;
        font-weight:700;
        background:linear-gradient(90deg,#00c8ff,#3b82f6);
        transition:.3s;
    }

    .stButton button:hover{
        transform:translateY(-2px);
        box-shadow:0 0 20px rgba(0,200,255,.35);
    }

    div[data-testid="metric-container"],
    div[data-testid="stMetric"]{
        background:rgba(255,255,255,.04);
        border:1px solid rgba(255,255,255,.08);
        border-radius:18px;
        padding:15px;
        backdrop-filter:blur(20px);
        box-shadow:0 0 20px rgba(0,0,0,.15);
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

    .stDataFrame{
        border-radius:20px;
        overflow:hidden;
    }

    .stTabs [data-baseweb="tab"]{
        font-size:16px;
        font-weight:600;
        color:#d1d5db;
    }

    .stTabs [aria-selected="true"]{
        color:#00c8ff !important;
    }

    .luxiz-footer{
        text-align:center;
        margin-top:25px;
        color:#94a3b8;
        font-size:13px;
        opacity:0.8;
    }

    .footer-luxiz{
        position:fixed;
        bottom:0;
        left:0;
        width:100%;
        background:rgba(5,10,25,0.95);
        border-top:1px solid rgba(255,255,255,0.08);
        backdrop-filter:blur(15px);
        padding:8px 20px;
        text-align:center;
        font-size:13px;
        color:#d1d5db;
        z-index:999999;
    }

    .footer-luxiz span.online{ color:#22c55e; font-weight:700; }
    .footer-luxiz span.cloud{ color:#38bdf8; font-weight:700; }
    .footer-luxiz span.refresh{ color:#facc15; font-weight:700; }

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
    """


# =====================================================
# CSS DE FUNDO
# (gradiente chamativo só na tela de login;
# fundo sólido — branco ou escuro — no resto do app)
# =====================================================

def _css_fundo(tema, tela):

    if tela == "login":

        if tema == "claro":

            return """
            <style>
            .stApp{
                background:
                    radial-gradient(circle at top left,#e0e7ff 0%,transparent 35%),
                    radial-gradient(circle at top right,#bae6fd 0%,transparent 35%),
                    radial-gradient(circle at bottom right,#ede9fe 0%,transparent 30%),
                    linear-gradient(135deg,#f8fafc,#f1f5f9,#f8fafc);
                color:#111827;
            }

            .luxiz-teaser{
                display:inline-flex;
                align-items:center;
                gap:8px;
                background:rgba(255,255,255,.65);
                border:1px solid rgba(2,132,199,.25);
                border-radius:999px;
                padding:8px 18px;
                font-size:.85rem;
                color:#0369a1;
                font-weight:600;
                margin-bottom:18px;
                backdrop-filter:blur(10px);
            }

            .st-key-login-card{
                background:rgba(255,255,255,.55) !important;
                border:1px solid rgba(0,0,0,.08) !important;
                border-radius:20px !important;
                backdrop-filter:blur(20px);
                box-shadow:0 8px 32px rgba(2,132,199,.12);
                padding:8px;
            }
            </style>
            """

        return """
        <style>
        .stApp{
            background:
                radial-gradient(circle at top left,#312e81 0%,transparent 35%),
                radial-gradient(circle at top right,#0ea5e9 0%,transparent 35%),
                radial-gradient(circle at bottom right,#7c3aed 0%,transparent 30%),
                linear-gradient(135deg,#010617,#020b24,#010617);
            color:white;
        }

        .luxiz-teaser{
            display:inline-flex;
            align-items:center;
            gap:8px;
            background:rgba(255,255,255,.06);
            border:1px solid rgba(0,200,255,.3);
            border-radius:999px;
            padding:8px 18px;
            font-size:.85rem;
            color:#7dd3fc;
            font-weight:600;
            margin-bottom:18px;
            backdrop-filter:blur(10px);
        }

        .st-key-login-card{
            background:rgba(255,255,255,.05) !important;
            border:1px solid rgba(255,255,255,.1) !important;
            border-radius:20px !important;
            backdrop-filter:blur(20px);
            box-shadow:0 8px 32px rgba(0,0,0,.35);
            padding:8px;
        }
        </style>
        """

    # Fundo sólido para o restante do app (Início, Dashboard,
    # Remanejamento, SAC, Administrativo) — sem gradiente chamativo.

    if tema == "claro":

        return """
        <style>
        .stApp{
            background:#f8fafc;
            color:#111827;
        }
        </style>
        """

    return """
    <style>
    .stApp{
        background:#0b1120;
        color:white;
    }
    </style>
    """


# =====================================================
# FUNÇÃO PRINCIPAL
# =====================================================

def aplicar_fundo(tema="escuro", tela="app"):
    """
    tema: "claro" ou "escuro"
    tela: "login" (fundo com gradiente chamativo) ou
          "app" (fundo sólido, sem gradiente) — usado em
          todas as telas depois do login.
    """

    st.markdown(
        _css_base(tema),
        unsafe_allow_html=True
    )

    st.markdown(
        _css_fundo(tema, tela),
        unsafe_allow_html=True
    )


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

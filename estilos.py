import streamlit as st
import contextlib
import time
import base64
import os

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# =====================================================
# FUSO HORÁRIO (conversão UTC -> Campo Grande)
# =====================================================
# Todo horário gravado no banco (CURRENT_TIMESTAMP do Postgres) fica
# em UTC. Isso é o correto — o servidor e o banco já têm o relógio
# certo via NTP, não é um problema de sincronização. O que precisa
# acontecer é converter esse horário UTC para o fuso local sempre
# que ele for exibido na tela. Use estas duas funções em vez de
# lidar com timezone "na mão" em cada página.

FUSO_PADRAO = ZoneInfo("America/Campo_Grande")


def horario_local(momento):
    """
    Converte um datetime vindo do banco (gravado em UTC, geralmente
    sem timezone/"ingênuo") para o horário de Campo Grande. Se já
    vier com timezone, só faz a conversão direto. Devolve None se
    `momento` for None.
    """

    if momento is None:
        return None

    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)

    return momento.astimezone(FUSO_PADRAO)


def agora_local():
    """Horário atual já no fuso de Campo Grande (para relógios/rodapé)."""

    return datetime.now(FUSO_PADRAO)


# =====================================================
# INTENSIDADE DE COR DOS CARTÕES (por tema)
# =====================================================
# As cores dos cartões (rgba de fundo + borda em hex) foram
# pensadas pro tema escuro — nesse fundo bem escuro, uma opacidade
# baixa (tipo 0.14/0.16) já contrasta bem. No tema claro, a mesma
# opacidade em cima de fundo branco quase some. Esta função pega
# o rgba "original" (pensado pro escuro) e, só quando o tema atual
# for "claro", aumenta a opacidade — no escuro devolve sem mexer.
# Uso: cor_fundo = estilos.cor_fundo_cartao("rgba(59,130,246,0.16)")

import re as _re


def cor_fundo_cartao(cor_fundo_original, multiplicador=1.8, teto=0.42):

    if st.session_state.get("tema") != "claro":
        return cor_fundo_original

    correspondencia = _re.match(
        r"rgba\((\d+),(\d+),(\d+),([\d.]+)\)",
        cor_fundo_original
    )

    if not correspondencia:
        return cor_fundo_original

    r, g, b, alfa = correspondencia.groups()

    nova_alfa = min(float(alfa) * multiplicador, teto)

    return f"rgba({r},{g},{b},{nova_alfa:.2f})"


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
        header [data-testid="collapsedControl"]{
            visibility:visible !important;
        }
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

        /* =====================================================
           WIDGETS NATIVOS (select, multiselect, checkbox, toggle,
           calendário do date_input, popover) — o config.toml fixa
           theme.base="dark" pro Streamlit (é global, vale pra
           todo mundo, não dá pra trocar por sessão), então esses
           componentes NÃO seguem sozinhos o toggle claro/escuro
           do Luxiz IA. Sem este bloco, eles ficam sempre com a
           cara do tema escuro do Streamlit, mesmo com o app no
           tema claro — é esse o bug do "campo preto".
           ===================================================== */

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div{
            background:rgba(0,0,0,0.03) !important;
            border-color:rgba(0,0,0,0.12) !important;
            color:#111827 !important;
        }

        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div{
            color:#111827 !important;
        }

        div[data-baseweb="select"] svg{
            fill:#111827 !important;
        }

        ul[data-baseweb="menu"],
        div[data-baseweb="popover"]{
            background:#ffffff !important;
        }

        li[data-baseweb="menu-item"]{
            background:#ffffff !important;
            color:#111827 !important;
        }

        li[data-baseweb="menu-item"]:hover{
            background:rgba(2,132,199,.12) !important;
        }

        label[data-baseweb="checkbox"] span,
        label[data-baseweb="radio"] span{
            color:#111827 !important;
        }

        div[data-baseweb="calendar"],
        div[data-baseweb="calendar"] *{
            background:#ffffff !important;
            color:#111827 !important;
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

        div[class*="st-key-toggle_tema"]{
            position:fixed;
            bottom:2px;
            left:18px;
            z-index:1000000;
            width:auto;
        }
        div[class*="st-key-toggle_tema"] label{
            gap:.35rem;
        }

        .luxiz-logo{
            display:flex;
            align-items:center;
            gap:0;
            margin-bottom:10px;
        }

        .luxiz-logo-icon{
            width:52px;
            height:52px;
            min-width:52px;
            border-radius:14px;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:1.5rem;
            background:linear-gradient(135deg,#0284c7,#7c3aed);
            box-shadow:0 6px 18px rgba(2,132,199,.35);
        }

        .luxiz-logo-imagem{
            height:76px;
            width:auto;
            display:block;
            filter:drop-shadow(0 4px 14px rgba(2,132,199,.35));
        }

        .luxiz-logo-texto{
            margin-left:-12px;
        }

        .luxiz-logo-texto h1{
            font-size:2rem;
            font-weight:800;
            letter-spacing:.3px;
            margin:0;
            line-height:1.1;
            background:linear-gradient(90deg,#0284c7,#7c3aed,#0284c7);
            background-size:200% auto;
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
        }

        .luxiz-logo-texto p{
            margin:3px 0 0 0;
            font-size:.72rem;
            font-weight:600;
            letter-spacing:2px;
            text-transform:uppercase;
            color:#64748b;
            white-space:nowrap;
        }

        .luxiz-teaser-wrap{
            display:flex;
            align-items:center;
            justify-content:flex-start;
            height:100%;
            min-height:52px;
        }

        .luxiz-dev-footer{
            text-align:center;
            margin-top:18px;
            padding-top:14px;
            border-top:1px solid rgba(0,0,0,.08);
        }

        .luxiz-dev-footer .marca{
            display:flex;
            align-items:center;
            justify-content:center;
            gap:0;
            font-size:.85rem;
            font-weight:700;
            letter-spacing:.5px;
            background:linear-gradient(90deg,#0284c7,#7c3aed);
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
        }

        .luxiz-dev-footer-logo{
            height:20px;
            width:auto;
            display:block;
            margin-right:-4px;
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
    header [data-testid="collapsedControl"]{
        visibility:visible !important;
    }
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

    /* Mesma explicação do bloco claro, espelhada — garante o
       inverso também (se um dia o config.toml mudar pra base
       claro, esses widgets continuam obedecendo o toggle). */

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div{
        background:rgba(255,255,255,0.05) !important;
        border-color:rgba(255,255,255,0.08) !important;
        color:white !important;
    }

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div{
        color:white !important;
    }

    div[data-baseweb="select"] svg{
        fill:white !important;
    }

    ul[data-baseweb="menu"],
    div[data-baseweb="popover"]{
        background:#0b1220 !important;
    }

    li[data-baseweb="menu-item"]{
        background:#0b1220 !important;
        color:white !important;
    }

    li[data-baseweb="menu-item"]:hover{
        background:rgba(0,200,255,.12) !important;
    }

    label[data-baseweb="checkbox"] span,
    label[data-baseweb="radio"] span{
        color:white !important;
    }

    div[data-baseweb="calendar"],
    div[data-baseweb="calendar"] *{
        background:#0b1220 !important;
        color:white !important;
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

    div[class*="st-key-toggle_tema"]{
        position:fixed;
        bottom:2px;
        left:18px;
        z-index:1000000;
        width:auto;
    }
    div[class*="st-key-toggle_tema"] label{
        gap:.35rem;
    }

    .luxiz-logo{
        display:flex;
        align-items:center;
        gap:0;
        margin-bottom:10px;
    }

    .luxiz-logo-icon{
        width:52px;
        height:52px;
        min-width:52px;
        border-radius:14px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        background:linear-gradient(135deg,#00c8ff,#a855f7);
        box-shadow:0 6px 18px rgba(0,200,255,.35);
    }

    .luxiz-logo-imagem{
        height:76px;
        width:auto;
        display:block;
        filter:drop-shadow(0 4px 14px rgba(0,200,255,.35));
    }

    .luxiz-logo-texto{
        margin-left:-12px;
    }

    .luxiz-logo-texto h1{
        font-size:2rem;
        font-weight:800;
        letter-spacing:.3px;
        margin:0;
        line-height:1.1;
        background:linear-gradient(90deg,#00c8ff,#a855f7,#00c8ff);
        background-size:200% auto;
        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
        background-clip:text;
    }

    .luxiz-logo-texto p{
        margin:3px 0 0 0;
        font-size:.72rem;
        font-weight:600;
        letter-spacing:2px;
        text-transform:uppercase;
        color:#94a3b8;
        white-space:nowrap;
    }

    .luxiz-teaser-wrap{
        display:flex;
        align-items:center;
        justify-content:flex-start;
        height:100%;
        min-height:52px;
    }

    .luxiz-dev-footer{
        text-align:center;
        margin-top:18px;
        padding-top:14px;
        border-top:1px solid rgba(255,255,255,.08);
    }

    .luxiz-dev-footer .marca{
        display:flex;
        align-items:center;
        justify-content:center;
        gap:0;
        font-size:.85rem;
        font-weight:700;
        letter-spacing:.5px;
        background:linear-gradient(90deg,#00c8ff,#a855f7);
        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
        background-clip:text;
    }

    .luxiz-dev-footer-logo{
        height:20px;
        width:auto;
        display:block;
        margin-right:-4px;
    }

    .luxiz-dev-footer .sub{
        font-size:.72rem;
        color:#64748b;
        margin-top:2px;
    }

    /* =====================================================
       AVISO CENTRAL "LUXIZ IA" (carregando / sucesso)
       Sempre com o mesmo visual (escuro translúcido), para não
       depender do tema claro/escuro — é uma camada por cima de
       tudo, some sozinha, e nunca bloqueia cliques por baixo.
       ===================================================== */

    @keyframes luxizGirar{
        to{ transform:rotate(360deg); }
    }

    @keyframes luxizOverlayEntra{
        from{ opacity:0; transform:translateY(10px) scale(.94); }
        to{ opacity:1; transform:translateY(0) scale(1); }
    }

    @keyframes luxizOverlayVidaCurta{
        0%{   opacity:0; transform:translateY(10px) scale(.94); }
        6%{   opacity:1; transform:translateY(0) scale(1); }
        90%{  opacity:1; transform:translateY(0) scale(1); }
        100%{ opacity:0; transform:translateY(-8px) scale(.97); }
    }

    @keyframes luxizCheckPulso{
        0%{   transform:scale(.6); opacity:0; }
        55%{  transform:scale(1.15); opacity:1; }
        100%{ transform:scale(1); opacity:1; }
    }

    .luxiz-overlay{
        position:fixed;
        inset:0;
        width:100vw;
        height:100vh;
        display:flex;
        align-items:center;
        justify-content:center;
        z-index:3000000;
        pointer-events:none;
    }

    .luxiz-overlay-card{
        pointer-events:none;
        min-width:280px;
        max-width:90vw;
        padding:34px 46px;
        border-radius:1.25rem;
        text-align:center;
        background:linear-gradient(180deg, rgba(15,20,36,.96), rgba(8,11,22,.96));
        border:1.5px solid rgba(56,189,248,.35);
        box-shadow:
            0 28px 70px rgba(0,0,0,.55),
            0 0 0 1px rgba(255,255,255,.04),
            0 0 46px rgba(56,189,248,.16);
        backdrop-filter:blur(14px);
        animation:luxizOverlayEntra .25s ease;
    }

    .luxiz-overlay-sucesso .luxiz-overlay-card{
        border-color:rgba(34,197,94,.45);
        box-shadow:
            0 28px 70px rgba(0,0,0,.55),
            0 0 0 1px rgba(255,255,255,.04),
            0 0 46px rgba(34,197,94,.20);
        animation:luxizOverlayVidaCurta 4.5s ease forwards;
    }

    .luxiz-overlay-spinner{
        width:40px;
        height:40px;
        margin:0 auto 16px;
        border-radius:50%;
        border:4px solid rgba(255,255,255,.14);
        border-top-color:#38bdf8;
        animation:luxizGirar .75s linear infinite;
    }

    .luxiz-overlay-check{
        width:52px;
        height:52px;
        margin:0 auto 12px;
        border-radius:50%;
        background:rgba(34,197,94,.16);
        border:2px solid #22c55e;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.7rem;
        line-height:1;
        box-shadow:0 0 22px rgba(34,197,94,.35);
        animation:luxizCheckPulso .4s ease;
    }

    .luxiz-overlay-titulo{
        display:flex;
        align-items:center;
        justify-content:center;
        gap:8px;
        margin-bottom:8px;
    }

    .luxiz-overlay-logo{
        width:24px;
        height:24px;
        object-fit:contain;
    }

    .luxiz-overlay-titulo-texto{
        font-size:1.25rem;
        font-weight:800;
        letter-spacing:.4px;
        background:linear-gradient(90deg,#00c8ff,#a855f7);
        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
        background-clip:text;
    }

    .luxiz-overlay-texto{
        font-size:1.08rem;
        color:#f1f5f9;
        line-height:1.45;
        font-weight:500;
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
            @keyframes luxizBgFloat{
                0%,100%{ background-position:0% 0%,100% 0%,100% 100%,0% 0%; }
                50%{ background-position:12% 8%,88% 6%,88% 92%,0% 0%; }
            }

            @keyframes luxizReflexoVidro{
                0%{ left:-60%; }
                100%{ left:130%; }
            }

            .stApp{
                background:
                    radial-gradient(circle at top left,#e0e7ff 0%,transparent 35%),
                    radial-gradient(circle at top right,#bae6fd 0%,transparent 35%),
                    radial-gradient(circle at bottom right,#ede9fe 0%,transparent 30%),
                    linear-gradient(135deg,#f8fafc,#f1f5f9,#f8fafc);
                background-size:160% 160%,160% 160%,160% 160%,100% 100%;
                animation:luxizBgFloat 16s ease-in-out infinite;
                color:#111827;
            }

            .luxiz-teaser{
                display:inline-block;
                text-align:center;
                line-height:1.5;
                max-width:440px;
                background:rgba(255,255,255,.65);
                border:1px solid rgba(2,132,199,.25);
                border-radius:18px;
                padding:12px 22px;
                font-size:.85rem;
                color:#0369a1;
                font-weight:600;
                margin-bottom:0;
                backdrop-filter:blur(10px);
            }

            .st-key-login-card{
                position:relative;
                overflow:hidden;
                background:rgba(255,255,255,.55) !important;
                border:1px solid rgba(0,0,0,.08) !important;
                border-radius:20px !important;
                backdrop-filter:blur(20px);
                box-shadow:0 8px 32px rgba(2,132,199,.12);
                padding:8px;
            }

            /* Leve reflexo de vidro: uma faixa fina de brilho que
               atravessa o card de login devagar, num loop contínuo,
               como o reflexo natural sobre um vidro. */
            .st-key-login-card::before{
                content:"";
                position:absolute;
                top:0;
                left:-60%;
                width:35%;
                height:100%;
                background:linear-gradient(115deg, transparent, rgba(255,255,255,.35), transparent);
                transform:skewX(-18deg);
                animation:luxizReflexoVidro 5.5s ease-in-out infinite;
                pointer-events:none;
                z-index:1;
            }
            </style>
            """

        return """
        <style>
        @keyframes luxizBgFloat{
            0%,100%{ background-position:0% 0%,100% 0%,100% 100%,0% 0%; }
            50%{ background-position:12% 8%,88% 6%,88% 92%,0% 0%; }
        }

        @keyframes luxizReflexoVidro{
            0%{ left:-60%; }
            100%{ left:130%; }
        }

        .stApp{
            background:
                radial-gradient(circle at top left,#312e81 0%,transparent 35%),
                radial-gradient(circle at top right,#0ea5e9 0%,transparent 35%),
                radial-gradient(circle at bottom right,#7c3aed 0%,transparent 30%),
                linear-gradient(135deg,#010617,#020b24,#010617);
            background-size:160% 160%,160% 160%,160% 160%,100% 100%;
            animation:luxizBgFloat 16s ease-in-out infinite;
            color:white;
        }

        .luxiz-teaser{
            display:inline-block;
            text-align:center;
            line-height:1.5;
            max-width:440px;
            background:rgba(255,255,255,.06);
            border:1px solid rgba(0,200,255,.3);
            border-radius:18px;
            padding:12px 22px;
            font-size:.85rem;
            color:#7dd3fc;
            font-weight:600;
            margin-bottom:0;
            backdrop-filter:blur(10px);
        }

        .st-key-login-card{
            position:relative;
            overflow:hidden;
            background:rgba(255,255,255,.05) !important;
            border:1px solid rgba(255,255,255,.1) !important;
            border-radius:20px !important;
            backdrop-filter:blur(20px);
            box-shadow:0 8px 32px rgba(0,0,0,.35);
            padding:8px;
        }

        /* Leve reflexo de vidro: uma faixa fina de brilho que
           atravessa o card de login devagar, num loop contínuo,
           como o reflexo natural sobre um vidro. */
        .st-key-login-card::before{
            content:"";
            position:absolute;
            top:0;
            left:-60%;
            width:35%;
            height:100%;
            background:linear-gradient(115deg, transparent, rgba(255,255,255,.22), transparent);
            transform:skewX(-18deg);
            animation:luxizReflexoVidro 5.5s ease-in-out infinite;
            pointer-events:none;
            z-index:1;
        }
        </style>
        """

    # Fundo suave para a tela Início — um efeito bem mais discreto que
    # o do login (blobs de baixa opacidade, deslocamento lento), só
    # pra dar vida à tela inicial sem chamar tanta atenção quanto o
    # gradiente do login nem ficar chapado como o fundo sólido do app.

    if tela == "inicio":

        if tema == "claro":

            return """
            <style>
            @keyframes luxizBgSuave{
                0%,100%{ background-position:0% 0%,100% 0%,100% 100%,0% 0%; }
                50%{ background-position:8% 6%,92% 4%,90% 94%,0% 0%; }
            }

            .stApp{
                background:
                    radial-gradient(circle at 12% 18%, rgba(99,102,241,.07) 0%, transparent 42%),
                    radial-gradient(circle at 88% 12%, rgba(14,165,233,.07) 0%, transparent 42%),
                    radial-gradient(circle at 78% 92%, rgba(168,85,247,.06) 0%, transparent 38%),
                    #f8fafc;
                background-size:170% 170%,170% 170%,170% 170%,100% 100%;
                animation:luxizBgSuave 30s ease-in-out infinite;
                color:#111827;
            }
            </style>
            """

        return """
        <style>
        @keyframes luxizBgSuave{
            0%,100%{ background-position:0% 0%,100% 0%,100% 100%,0% 0%; }
            50%{ background-position:8% 6%,92% 4%,90% 94%,0% 0%; }
        }

        .stApp{
            background:
                radial-gradient(circle at 12% 18%, rgba(59,130,246,.12) 0%, transparent 42%),
                radial-gradient(circle at 88% 12%, rgba(139,92,246,.12) 0%, transparent 42%),
                radial-gradient(circle at 78% 92%, rgba(14,165,233,.09) 0%, transparent 38%),
                #0b1120;
            background-size:170% 170%,170% 170%,170% 170%,100% 100%;
            animation:luxizBgSuave 30s ease-in-out infinite;
            color:white;
        }
        </style>
        """

    # Fundo sólido para o restante do app (Dashboard, Remanejamento,
    # SAC, Administrativo etc.) — sem gradiente chamativo.

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
    tela: "login" (fundo com gradiente chamativo), "inicio" (fundo
          com efeito suave de blobs, usado só na tela Início) ou
          "app" (fundo sólido, sem gradiente) — usado nas demais
          telas depois do login.
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

def marca_desenvolvedor_login():
    """
    Mensagem discreta em um canto da tela de login, com um leve
    efeito de brilho passando sobre "Luxiz IA" — só usada na tela
    de login.
    """

    st.markdown(
        """
        <style>
        @keyframes luxizBrilhoTexto{
            0%{ background-position:-120% 0; }
            100%{ background-position:220% 0; }
        }

        .luxiz-marca-dev{
            position:fixed;
            left:18px;
            top:12px;
            font-size:.72rem;
            font-weight:600;
            color:rgba(148,163,184,.85);
            letter-spacing:.2px;
            z-index:1000000;
            pointer-events:none;
        }

        .luxiz-marca-dev-nome{
            background:linear-gradient(
                90deg,
                #7dd3fc 0%,
                #ffffff 18%,
                #a855f7 36%,
                #7dd3fc 54%
            );
            background-size:300% 100%;
            -webkit-background-clip:text;
            background-clip:text;
            -webkit-text-fill-color:transparent;
            animation:luxizBrilhoTexto 3.2s linear infinite;
            font-weight:800;
        }
        </style>
        <div class="luxiz-marca-dev">
            desenvolvido por <span class="luxiz-marca-dev-nome">Luxiz IA</span>
        </div>
        """,
        unsafe_allow_html=True
    )


@st.cache_data
def _logo_base64():
    """
    Lê o arquivo da logo (assets/luxiz_logo.png, na raiz do projeto)
    e devolve em base64, para embutir direto no HTML sem depender
    de servir arquivo estático. Cacheado — só lê o arquivo uma vez.
    """

    caminho = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "assets",
        "luxiz_logo.png"
    )

    with open(caminho, "rb") as arquivo:
        return base64.b64encode(arquivo.read()).decode()


@st.cache_data
def _favicon_base64():
    """
    Lê o arquivo assets/favicon.png e devolve em base64 — usado como
    marca nos avisos centrais de processamento/sucesso, no lugar do
    antigo "✨" em texto.
    """

    caminho = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "assets",
        "favicon.png"
    )

    with open(caminho, "rb") as arquivo:
        return base64.b64encode(arquivo.read()).decode()


def _titulo_overlay_html():
    """
    HTML do título "Luxiz IA" usado nos avisos centrais, com o
    favicon.png no lugar do emoji "✨".
    """

    favicon_b64 = _favicon_base64()

    return (
        '<div class="luxiz-overlay-titulo">'
        f'<img class="luxiz-overlay-logo" src="data:image/png;base64,{favicon_b64}" alt="Luxiz IA">'
        '<span class="luxiz-overlay-titulo-texto">Luxiz IA</span>'
        '</div>'
    )


def logo_header(subtitulo="Centro Inteligente de Operações"):

    logo_b64 = _logo_base64()

    st.markdown(
        f"""
        <div class="luxiz-logo">
            <img class="luxiz-logo-imagem" src="data:image/png;base64,{logo_b64}" alt="Luxiz IA">
            <div class="luxiz-logo-texto">
                <h1>Luxiz IA</h1>
                <p>{subtitulo}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# CABEÇALHO DE PÁGINA (animado, leve — só CSS)
# =====================================================
# Usado no lugar de st.title()+st.caption() em cada aba, pra dar
# uma entrada suave (fade + slide), um ícone com leve balanço e
# uma barrinha de destaque com brilho correndo — tudo via CSS,
# sem nenhum JS, então não pesa a aba.

def cabecalho_pagina(icone, titulo, subtitulo, cor="#3b82f6"):

    st.markdown(
        f"""
        <style>
        @keyframes luxizFadeUp {{
            from {{ opacity:0; transform:translateY(12px); }}
            to {{ opacity:1; transform:translateY(0); }}
        }}
        @keyframes luxizFloat {{
            0%, 100% {{ transform:translateY(0) rotate(0deg); }}
            50% {{ transform:translateY(-5px) rotate(-4deg); }}
        }}
        @keyframes luxizShimmerBar {{
            0% {{ background-position:0% 50%; }}
            100% {{ background-position:200% 50%; }}
        }}
        .luxiz-page-header{{
            display:flex;
            align-items:center;
            gap:16px;
            animation:luxizFadeUp .45s ease;
        }}
        .luxiz-page-header-icon{{
            width:54px;
            height:54px;
            min-width:54px;
            border-radius:16px;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:1.55rem;
            background:linear-gradient(135deg, {cor}, {cor}99);
            box-shadow:0 6px 18px {cor}55;
            animation:luxizFloat 3.2s ease-in-out infinite;
        }}
        .luxiz-page-header-texto h1{{
            font-size:1.85rem;
            font-weight:800;
            margin:0;
            line-height:1.15;
        }}
        .luxiz-page-header-texto p{{
            margin:.2rem 0 0 0;
            font-size:.92rem;
            opacity:.7;
        }}
        .luxiz-page-header-bar{{
            height:3px;
            width:100%;
            margin-top:14px;
            border-radius:999px;
            background:linear-gradient(90deg, {cor}, transparent, {cor});
            background-size:200% auto;
            animation:luxizShimmerBar 3s linear infinite;
            opacity:.55;
        }}
        </style>
        <div class="luxiz-page-header">
            <div class="luxiz-page-header-icon">{icone}</div>
            <div class="luxiz-page-header-texto">
                <h1>{titulo}</h1>
                <p>{subtitulo}</p>
            </div>
        </div>
        <div class="luxiz-page-header-bar"></div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# RODAPÉ "DESENVOLVIDO POR"
# =====================================================

def rodape():

    logo_b64 = _logo_base64()

    st.markdown(
        f"""
        <div class="luxiz-dev-footer">
            <div class="marca">
                <img class="luxiz-dev-footer-logo" src="data:image/png;base64,{logo_b64}" alt="Luxiz IA">
                Luxiz IA
            </div>
            <div class="sub">Centro Inteligente de Operações</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# AVISO CENTRAL "LUXIZ IA" (carregando / sucesso)
# =====================================================
# Substitui st.spinner (cantinho da tela, passava despercebido)
# e st.toast (sumia rápido demais / em local que ninguém olhava)
# por um aviso bem no centro da tela, sempre com a marca
# "✨ Luxiz IA" — um enquanto a ação está rodando, outro
# confirmando o que foi feito, sumindo sozinho.

@contextlib.contextmanager
def mostrar_processando(mensagem):
    """
    Uso: with estilos.mostrar_processando("atualizando..."):
             banco.fazer_algo()
    Mostra o aviso central enquanto o bloco roda e some assim
    que ele termina (sozinho, sem precisar de rerun).
    """

    marcador = st.empty()

    marcador.markdown(
        f"""
        <div class="luxiz-overlay">
            <div class="luxiz-overlay-card">
                <div class="luxiz-overlay-spinner"></div>
                {_titulo_overlay_html()}
                <div class="luxiz-overlay-texto">{mensagem}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    try:
        yield
    finally:
        marcador.empty()


def notificar_sucesso(mensagem):
    """
    Guarda uma mensagem para ser exibida, centralizada na tela,
    assim que a página recarregar (chamar logo antes do
    st.rerun() que normalmente já vem depois de salvar algo).
    """

    st.session_state["_luxiz_notificacao"] = mensagem


def exibir_notificacao_pendente():
    """
    Mostra (uma única vez, sumindo sozinha) a mensagem de sucesso
    deixada por notificar_sucesso(), se houver alguma. Chamada no
    topo de cada página/fragmento que executa ações.
    """

    mensagem = st.session_state.pop("_luxiz_notificacao", None)

    if not mensagem:
        return

    st.markdown(
        f"""
        <div class="luxiz-overlay luxiz-overlay-sucesso">
            <div class="luxiz-overlay-card">
                <div class="luxiz-overlay-check">✅</div>
                {_titulo_overlay_html()}
                <div class="luxiz-overlay-texto">{mensagem}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# AVISO DA ATUALIZAÇÃO AUTOMÁTICA (em fases)
# =====================================================
# Usado só na aba Administrativo: como agora ela não recarrega
# tudo na hora que alguém adiciona/exclui algo (isso deixava a
# aba lenta), quem avisa que os dados foram atualizados é a
# atualização automática (a cada 120s). Esse aviso mostra as
# fases "Lendo dados" -> "Atualizando dados" -> "Concluído com
# sucesso" só quando é de fato essa atualização de fundo — se o
# recarregamento foi por causa de um clique (adicionar, excluir,
# editar), não faz sentido atrasar a pessoa com esse aviso, já
# que o próprio clique já mostrou seu aviso de "processando" e o
# toast de sucesso.

@contextlib.contextmanager
def mostrar_atualizacao_automatica(segundos_entre_ciclos=120):
    """
    Uso: with estilos.mostrar_atualizacao_automatica():
             administrativo.render()
    """

    agora = time.time()

    ultima_execucao = st.session_state.get(
        "_luxiz_ultima_leitura_admin"
    )

    st.session_state["_luxiz_ultima_leitura_admin"] = agora

    # Só trata como "atualização automática de fundo" se já tinha
    # passado tempo suficiente desde a última vez — um clique
    # (adicionar/excluir/editar) recarrega de novo bem mais rápido
    # que isso, então não entra nessa condição.
    eh_atualizacao_de_fundo = (
        ultima_execucao is not None
        and (agora - ultima_execucao) >= (segundos_entre_ciclos - 30)
    )

    if not eh_atualizacao_de_fundo:

        yield
        return

    marcador = st.empty()

    def _mostrar_fase(texto, concluido=False):

        icone_fase = (
            '<div class="luxiz-overlay-check">✅</div>'
            if concluido else
            '<div class="luxiz-overlay-spinner"></div>'
        )

        classe_extra = " luxiz-overlay-sucesso" if concluido else ""

        marcador.markdown(
            f"""
            <div class="luxiz-overlay{classe_extra}">
                <div class="luxiz-overlay-card">
                    {icone_fase}
                    {_titulo_overlay_html()}
                    <div class="luxiz-overlay-texto">{texto}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    _mostrar_fase("Lendo dados...")
    time.sleep(.5)

    try:
        yield
    finally:
        _mostrar_fase("Atualizando dados...")
        time.sleep(.5)

        _mostrar_fase("Concluído com sucesso", concluido=True)
        time.sleep(1.1)

        marcador.empty()
import base64
import random
from functools import lru_cache

import streamlit as st


# =====================================================
# EFEITO DE FUNDO DA TELA DE LOGIN
# =====================================================
# Camadas (de trás para frente):
#   1. gradiente base (estilos._css_login)
#   2. aurora (manchas de luz flutuando) + grade sutil
#   3. estrelas cintilantes (SVG) e partículas subindo
#   4. conteúdo (card de login)

LARGURA, ALTURA = 1600, 760


def _anim(animado, texto):
    return texto if animado else ""


def _brilhos(animado):
    rnd = random.Random(7)
    pontos = []
    for _ in range(64):
        x, y = rnd.randint(10, 1590), rnd.randint(10, 520)
        r = round(rnd.uniform(.9, 2.4), 1)
        cor = rnd.choice(["#e0f7ff", "#7dd3fc", "#38bdf8", "#bae6fd"])
        pulso = _anim(
            animado,
            f'<animate attributeName="opacity" values=".12;.95;.12" '
            f'dur="{round(rnd.uniform(2.4, 6.5), 1)}s" begin="-{round(rnd.uniform(0, 6), 1)}s" '
            f'repeatCount="indefinite"/>'
        )
        pontos.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{cor}" opacity=".5">{pulso}</circle>')
    return "".join(pontos)


def montar_cena(tema="escuro", animado=True):

    opacidade_geral = ".55" if tema == "claro" else "1"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {LARGURA} {ALTURA}" preserveAspectRatio="xMidYMax meet">
<g opacity="{opacidade_geral}">
{_brilhos(animado)}
</g>
</svg>"""


@lru_cache(maxsize=None)
def _uri_cena(tema, animado):

    svg = montar_cena(tema, animado)

    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


def aplicar(tema):

    if tema == "claro":
        brilho_chao = "rgba(2,132,199,.10)"
        ponto_1 = "rgba(14,165,233,.45)"
        ponto_2 = "rgba(99,102,241,.35)"
        ponto_3 = "rgba(56,189,248,.50)"
        aurora_1 = "rgba(56,189,248,.30)"
        aurora_2 = "rgba(99,102,241,.26)"
        aurora_3 = "rgba(168,85,247,.20)"
        grade = "rgba(15,23,42,.045)"
    else:
        brilho_chao = "rgba(34,211,238,.14)"
        ponto_1 = "rgba(224,247,255,.75)"
        ponto_2 = "rgba(56,189,248,.85)"
        ponto_3 = "rgba(125,211,252,.80)"
        aurora_1 = "rgba(34,211,238,.26)"
        aurora_2 = "rgba(99,102,241,.34)"
        aurora_3 = "rgba(168,85,247,.26)"
        grade = "rgba(148,163,184,.07)"

    css = """
    <style>
    @keyframes luxizParticulasSubir {
        from { background-position: 0 0; }
        to   { background-position: 0 -420px; }
    }
    @keyframes luxizParticulasBrilho {
        0%, 100% { opacity: .40; }
        50%      { opacity: 1; }
    }
    @keyframes lxAurora1 {
        0%,100% { transform: translate(0,0) scale(1); }
        50%     { transform: translate(8vw,6vh) scale(1.18); }
    }
    @keyframes lxAurora2 {
        0%,100% { transform: translate(0,0) scale(1.1); }
        50%     { transform: translate(-9vw,8vh) scale(.92); }
    }
    @keyframes lxAurora3 {
        0%,100% { transform: translate(0,0) scale(1); }
        50%     { transform: translate(-5vw,-8vh) scale(1.2); }
    }

    /* o conteúdo fica acima das camadas de efeito */
    [data-testid="stAppViewContainer"] {
        position: relative;
        z-index: 1;
    }

    /* aurora + grade (z-index negativo: fica atrás do conteúdo,
       mas na frente do gradiente de fundo) */
    .lx-aurora {
        position: fixed;
        inset: 0;
        z-index: -1;
        pointer-events: none;
        overflow: hidden;
    }
    .lx-aurora span {
        position: absolute;
        border-radius: 50%;
        filter: blur(90px);
        will-change: transform;
    }
    .lx-aurora .lx-b1 {
        width: 46vw; height: 46vw; left: -12vw; top: -18vw;
        background: __AURORA_1__;
        animation: lxAurora1 22s ease-in-out infinite;
    }
    .lx-aurora .lx-b2 {
        width: 52vw; height: 52vw; right: -16vw; top: 6vh;
        background: __AURORA_2__;
        animation: lxAurora2 28s ease-in-out infinite;
    }
    .lx-aurora .lx-b3 {
        width: 40vw; height: 40vw; left: 22vw; bottom: -24vw;
        background: __AURORA_3__;
        animation: lxAurora3 25s ease-in-out infinite;
    }
    .lx-aurora .lx-grid {
        position: absolute;
        inset: 0;
        background-image:
            linear-gradient(__GRADE__ 1px, transparent 1px),
            linear-gradient(90deg, __GRADE__ 1px, transparent 1px);
        background-size: 56px 56px;
        -webkit-mask-image: radial-gradient(ellipse 70% 60% at 50% 45%, #000 20%, transparent 78%);
        mask-image: radial-gradient(ellipse 70% 60% at 50% 45%, #000 20%, transparent 78%);
    }

    /* cena (SVG animado) ancorada na base da tela */
    .stApp::before {
        content: "";
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        height: 100vh;
        z-index: 0;
        pointer-events: none;
        background-image:
            url("__CENA_ANIMADA__"),
            radial-gradient(70% 34% at 50% 100%, __BRILHO_CHAO__, transparent 70%);
        background-repeat: no-repeat, no-repeat;
        background-position: center bottom, center bottom;
        background-size: max(100vw, 900px) auto, 100% 100%;
    }

    /* partículas de luz subindo devagar */
    .stApp::after {
        content: "";
        position: fixed;
        inset: 0;
        z-index: 0;
        pointer-events: none;
        background-image:
            radial-gradient(2px 2px at 24px 34px,   __PONTO_1__, transparent 100%),
            radial-gradient(1.5px 1.5px at 96px 150px, __PONTO_2__, transparent 100%),
            radial-gradient(2.5px 2.5px at 180px 66px, __PONTO_3__, transparent 100%),
            radial-gradient(1.5px 1.5px at 262px 212px, __PONTO_1__, transparent 100%),
            radial-gradient(2px 2px at 338px 118px,  __PONTO_2__, transparent 100%),
            radial-gradient(1.5px 1.5px at 64px 268px, __PONTO_1__, transparent 100%),
            radial-gradient(2.5px 2.5px at 214px 322px, __PONTO_3__, transparent 100%),
            radial-gradient(1.5px 1.5px at 372px 300px, __PONTO_2__, transparent 100%),
            radial-gradient(2px 2px at 130px 380px, __PONTO_1__, transparent 100%),
            radial-gradient(1.5px 1.5px at 300px 30px, __PONTO_3__, transparent 100%);
        background-size: 420px 420px;
        animation:
            luxizParticulasSubir 60s linear infinite,
            luxizParticulasBrilho 7s ease-in-out infinite;
    }

    /* "reduzir movimento": tudo parado */
    @media (prefers-reduced-motion: reduce) {
        .lx-aurora span { animation: none; }
        .stApp::before {
            background-image:
                url("__CENA_ESTATICA__"),
                radial-gradient(70% 34% at 50% 100%, __BRILHO_CHAO__, transparent 70%);
        }
        .stApp::after { animation: none; }
    }
    </style>
    """

    for marcador, valor in {
        "__CENA_ANIMADA__": _uri_cena(tema, True),
        "__CENA_ESTATICA__": _uri_cena(tema, False),
        "__BRILHO_CHAO__": brilho_chao,
        "__PONTO_1__": ponto_1,
        "__PONTO_2__": ponto_2,
        "__PONTO_3__": ponto_3,
        "__AURORA_1__": aurora_1,
        "__AURORA_2__": aurora_2,
        "__AURORA_3__": aurora_3,
        "__GRADE__": grade,
    }.items():
        css = css.replace(marcador, valor)

    st.markdown(css, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="lx-aurora">
            <div class="lx-grid"></div>
            <span class="lx-b1"></span>
            <span class="lx-b2"></span>
            <span class="lx-b3"></span>
        </div>
        """,
        unsafe_allow_html=True
    )

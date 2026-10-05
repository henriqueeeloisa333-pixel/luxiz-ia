import base64
import random
from functools import lru_cache

import streamlit as st


# =====================================================
# EFEITO DE FUNDO DA TELA DE LOGIN: "CÉU NEON"
# =====================================================
# Cena em estilo holograma (linhas ciano brilhantes sobre o fundo
# azul-escuro), toda desenhada em SVG vetorial — original, feita para
# o Luxiz IA: um avião cruza o céu da esquerda para a direita, some
# e volta a aparecer, com brilhos cintilando ao fundo.
#
# Animações (dentro do próprio SVG, sem JavaScript):
#   - o avião atravessa a tela devagar e oscila de leve;
#   - pontinhos de luz cintilam no céu.
#
# Como se encaixa no estilos.py: o gradiente do login está em
# .stApp (veja _css_fundo, tela == "login"). A cena é o pseudo-
# elemento ::before do próprio .stApp (logo acima do gradiente) e as
# partículas são o ::after; o conteúdo (stAppViewContainer) sobe um
# nível para ficar por cima. O card de login continua 100% clicável.
# O CSS só é injetado nas telas de login/troca de senha; ao entrar no
# sistema ele deixa de ser enviado e o efeito some sozinho. Para quem
# usa "reduzir movimento" no sistema, a cena aparece parada.

LARGURA, ALTURA = 1600, 760

FAIXA_AVIAO = 120     # topo do avião (céu)
MARGEM = 60           # folga para o avião nascer/sumir fora da tela

DURACAO_AVIAO = 80    # segundos para atravessar a tela
FASE_AVIAO = 34       # já começa a meio caminho quando a tela abre


def _anim(animado, texto):
    return texto if animado else ""


def _viajar(animado, peca, x_min, x_max, dur, fase=0, x_parado=0):
    """Faz a peça atravessar a tela da esquerda para a direita.

    x_min / x_max: extensão da peça (já na escala final) em relação à
    sua origem; servem para ela nascer e sumir totalmente fora da tela.
    x_parado: posição usada quando o movimento está desligado.
    """
    if not animado:
        return f'<g transform="translate({x_parado},0)">{peca}</g>'

    x_ini = round(-x_max - MARGEM)
    x_fim = round(LARGURA - x_min + MARGEM)
    voo = (
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="{x_ini} 0;{x_fim} 0" dur="{dur}s" begin="-{fase}s" '
        f'repeatCount="indefinite"/>'
    )
    return f'<g>{voo}{peca}</g>'


def _aviao(animado):
    c = (
        '<path class="v" d="M0 40Q10 29 62 27L190 25Q236 27 252 40Q236 53 190 55L62 53Q10 51 0 40Z"/>'
        '<path class="v" d="M112 42L66 100L102 100L176 44Z"/>'
        '<path class="v" d="M122 36L98 4L120 4L166 34Z"/>'
        '<path class="v" d="M22 34L2 -6L32 -6L66 30Z"/>'
        '<path class="v" d="M34 46L12 66L38 66L64 48Z"/>'
        '<path class="v" d="M118 66Q118 58 130 58H156Q166 58 166 66Q166 74 156 74H130Q118 74 118 66Z"/>'
        '<path class="d" d="M222 32Q236 32 244 38"/>'
        + "".join(f'<circle class="f" cx="{x}" cy="38" r="2"/>' for x in range(80, 214, 13))
        + '<path d="M-260 40H-6" stroke="url(#rastro)" stroke-width="2" fill="none"/>'
    )
    oscila = _anim(
        animado,
        '<animateTransform attributeName="transform" type="translate" '
        'values="0 0;0 -9;0 0" dur="7s" repeatCount="indefinite"/>'
    )
    escala = .95
    peca = f'<g transform="translate(0,{FAIXA_AVIAO}) scale({escala})"><g>{oscila}{c}</g></g>'
    # o rastro vai até x = -260 e o corpo até x = 252 (coordenadas locais)
    return _viajar(
        animado, peca, -260 * escala, 252 * escala,
        DURACAO_AVIAO, FASE_AVIAO, x_parado=1000,
    )


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

    if tema == "claro":
        linha, detalhe, preenche = "#0284c7", "#38bdf8", "rgba(2,132,199,.05)"
        opacidade_geral = ".8"
    else:
        linha, detalhe, preenche = "#22d3ee", "#a5f3fc", "rgba(34,211,238,.06)"
        opacidade_geral = "1"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {LARGURA} {ALTURA}" preserveAspectRatio="xMidYMax meet">
<defs>
<style>
.v{{fill:{preenche};stroke:{linha};stroke-linejoin:round;stroke-linecap:round}}
.d{{fill:none;stroke:{detalhe};stroke-width:1.2;stroke-linecap:round;stroke-linejoin:round;opacity:.8}}
.f{{fill:{detalhe}}}
</style>
<linearGradient id="rastro" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{linha}" stop-opacity="0"/><stop offset="1" stop-color="{linha}" stop-opacity=".7"/></linearGradient>
</defs>
<g opacity="{opacidade_geral}">
{_brilhos(animado)}
{_aviao(animado)}
</g>
</svg>"""


@lru_cache(maxsize=None)
def _uri_cena(tema, animado):

    svg = montar_cena(tema, animado)

    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


def aplicar(tema):

    if tema == "claro":
        brilho_chao = "rgba(2,132,199,.14)"
        ponto_1 = "rgba(14,165,233,.55)"
        ponto_2 = "rgba(99,102,241,.45)"
        ponto_3 = "rgba(56,189,248,.60)"
    else:
        brilho_chao = "rgba(34,211,238,.16)"
        ponto_1 = "rgba(224,247,255,.75)"
        ponto_2 = "rgba(56,189,248,.85)"
        ponto_3 = "rgba(125,211,252,.80)"

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

    /* o conteúdo fica acima das duas camadas de efeito */
    [data-testid="stAppViewContainer"] {
        position: relative;
        z-index: 1;
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

    /* "reduzir movimento": cena parada e sem partículas animadas */
    @media (prefers-reduced-motion: reduce) {
        .stApp::before {
            background-image:
                url("__CENA_ESTATICA__"),
                radial-gradient(70% 34% at 50% 100%, __BRILHO_CHAO__, transparent 70%);
        }
        .stApp::after {
            animation: none;
        }
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
    }.items():
        css = css.replace(marcador, valor)

    st.markdown(css, unsafe_allow_html=True)

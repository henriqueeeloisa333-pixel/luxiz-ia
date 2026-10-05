import base64
import random
from functools import lru_cache

import streamlit as st


# =====================================================
# EFEITO DE FUNDO DA TELA DE LOGIN: "CENTRAL LOGÍSTICA NEON"
# =====================================================
# Cena em estilo holograma (linhas ciano brilhantes sobre o fundo
# azul-escuro), toda desenhada em SVG vetorial — original, feita para
# o Luxiz IA: dois caminhões, um trem com contêineres, um navio
# cargueiro e um avião cruzando o céu, com brilhos cintilando.
#
# Animações (dentro do próprio SVG, sem JavaScript):
#   - o avião atravessa a tela devagar;
#   - os caminhões e o trem deslizam de leve, as rodas giram;
#   - o navio balança com as ondas;
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

import random

LARGURA, ALTURA, CHAO = 1600, 520, 478


def _costelas(x0, x1, passo, y0, y1):
    return "".join(f"M{x} {y0}V{y1}" for x in range(x0, x1, passo))


def _anim(animado, texto):
    return texto if animado else ""


def _no_chao(tx, escala, conteudo):
    ty = round(CHAO * (1 - escala), 2)
    return f'<g transform="translate({tx},{ty}) scale({escala})">{conteudo}</g>'


def _deriva(animado, dx, dur, atraso=0):
    return _anim(
        animado,
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="0 0;{dx} 0;0 0" dur="{dur}s" begin="{atraso}s" repeatCount="indefinite"/>'
    )


def _roda(x):
    return f'<use xlink:href="#roda" x="{x}" y="461"/>'


def _caminhao_a(animado):
    c = (
        '<path class="d" d="M0 440H336"/>'
        '<path class="v" d="M0 440V398Q0 388 12 386L62 380L84 330Q88 322 98 322H160V440Z"/>'
        '<path class="v" d="M90 334H150V374H76Z"/>'
        '<path class="d" d="M10 396V432M20 392V432M30 390V432M40 388V432"/>'
        '<path class="d" d="M2 404h10v10h-10z"/>'
        '<path class="d" d="M168 322V266M176 322V266M165 266H179"/>'
        '<path class="v" d="M176 290H336V432H176Z"/>'
        f'<path class="d" d="{_costelas(192, 336, 16, 290, 432)}"/>'
        + _roda(46) + _roda(200) + _roda(238) + _roda(288) + _roda(322)
    )
    return f'<g>{_deriva(animado, 9, 12)}{c}</g>'


def _caminhao_b(animado):
    c = (
        '<path class="d" d="M0 440H350"/>'
        '<path class="v" d="M0 440V340Q0 326 14 324H78Q90 324 94 334L106 372V440Z"/>'
        '<path class="v" d="M12 336H78L90 366H12Z"/>'
        '<path class="d" d="M50 366V436M56 394H70"/>'
        '<path class="d" d="M2 410h10v10h-10z"/>'
        '<path class="v" d="M116 296H350V436H116Z"/>'
        f'<path class="d" d="{_costelas(134, 350, 18, 296, 436)}M116 366H350"/>'
        + _roda(36) + _roda(150) + _roda(188) + _roda(304) + _roda(340)
    )
    return f'<g>{_deriva(animado, -8, 10, 1)}{c}</g>'


def _trem(animado):
    c = (
        '<path class="d" d="M0 440H452"/>'
        '<path class="v" d="M0 440V382Q0 368 12 362L40 348V318H150V348H212V440Z"/>'
        '<path class="v" d="M52 326H92V346H52Z"/>'
        '<path class="v" d="M104 330H138V346H104Z"/>'
        '<path class="d" d="M156 318V300M166 318V300M176 318V300M186 318V300M154 300H190"/>'
        f'<path class="d" d="{_costelas(120, 206, 10, 360, 432)}"/>'
        '<path class="d" d="M2 384h8v10h-8zM212 436H234"/>'
        '<path class="v" d="M234 424H452V440H234Z"/>'
        '<path class="v" d="M240 346H446V422H240Z"/>'
        f'<path class="d" d="{_costelas(254, 446, 14, 346, 422)}"/>'
        '<path class="v" d="M240 268H446V344H240Z"/>'
        f'<path class="d" d="{_costelas(254, 446, 14, 268, 344)}"/>'
        + _roda(34) + _roda(66) + _roda(150) + _roda(184)
        + _roda(262) + _roda(292) + _roda(396) + _roda(426)
    )
    return f'<g>{_deriva(animado, 12, 14, 2)}{c}</g>'


def _navio(animado):
    onda = "M-30 478" + "".join(
        f"Q{x + 15} 470 {x + 30} 478" if i == 0 else f"T{x + 30} 478"
        for i, x in enumerate(range(-30, 620, 30))
    )
    cont = ""
    for i, altura in enumerate([3, 3, 4, 4, 4, 3, 3, 2, 2]):
        x = 156 + 36 * i
        for r in range(altura):
            y = 428 - 26 * (r + 1)
            cont += f"M{x} {y}h32v26h-32z"
    janelas = "".join(
        f"M{x} {y}h7v6h-7z"
        for y in (360, 374, 388, 402) for x in range(34, 106, 12)
    )
    casco = (
        '<path class="v" d="M10 428H504L532 402L490 476H44Z"/>'
        '<path class="v" d="M26 428V350H112V428Z"/>'
        f'<path class="d" d="{janelas}"/>'
        '<path class="v" d="M36 350V322H102V350Z"/>'
        '<path class="d" d="M44 334H94M70 322V288M58 300H82M64 288H76"/>'
        '<path class="v" d="M118 428V382H140V428Z"/>'
        '<path class="d" d="M118 394H140"/>'
        f'<path class="c" d="{cont}"/>'
    )
    balanco = _anim(
        animado,
        '<animateTransform attributeName="transform" type="translate" '
        'values="0 0;0 4;0 0" dur="5s" repeatCount="indefinite"/>'
    )
    mar = _anim(
        animado,
        '<animateTransform attributeName="transform" type="translate" '
        'values="0 0;30 0" dur="4s" repeatCount="indefinite"/>'
    )
    return f'<g><g>{balanco}{casco}</g><g class="onda"><g>{mar}<path class="d" d="{onda}"/></g></g></g>'


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
    voo = _anim(
        animado,
        '<animateTransform attributeName="transform" type="translate" '
        'values="-340 0;1900 0" dur="80s" begin="-34s" repeatCount="indefinite"/>'
    )
    oscila = _anim(
        animado,
        '<animateTransform attributeName="transform" type="translate" '
        'values="0 0;0 -9;0 0" dur="7s" repeatCount="indefinite"/>'
    )
    posicao = f'<g transform="translate(0,120) scale(.95)"><g>{oscila}{c}</g></g>'
    # sem animação (movimento reduzido) o avião fica parado na região visível
    if animado:
        return f'<g>{voo}{posicao}</g>'
    return f'<g transform="translate(1000,0)">{posicao}</g>'


def _brilhos(animado):
    rnd = random.Random(7)
    pontos = []
    for _ in range(56):
        x, y = rnd.randint(10, 1590), rnd.randint(10, 430)
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
        linha, detalhe, preenche, ponto = "#0284c7", "#38bdf8", "rgba(2,132,199,.05)", "#0ea5e9"
        opacidade_geral, halo, halo_largura = ".8", ".10", 6
    else:
        linha, detalhe, preenche, ponto = "#22d3ee", "#a5f3fc", "rgba(34,211,238,.06)", "#bae6fd"
        opacidade_geral, halo, halo_largura = "1", ".16", 8

    roda_giro = _anim(
        animado,
        '<animateTransform attributeName="transform" type="rotate" '
        'from="0" to="360" dur="6s" repeatCount="indefinite"/>'
    )

    veiculos = (
        _no_chao(20, .88, _caminhao_a(animado))
        + _no_chao(334, .88, _caminhao_b(animado))
        + _no_chao(652, .85, _trem(animado))
        + _no_chao(1058, 1, _navio(animado))
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {LARGURA} {ALTURA}" preserveAspectRatio="xMidYMax meet">
<defs>
<style>
.v{{fill:{preenche};stroke:{linha};stroke-linejoin:round;stroke-linecap:round}}
.c{{fill:{preenche};stroke:{linha};stroke-width:1.1;stroke-linejoin:round}}
.d{{fill:none;stroke:{detalhe};stroke-width:1.2;stroke-linecap:round;stroke-linejoin:round;opacity:.8}}
.f{{fill:{detalhe}}}
</style>
<linearGradient id="rastro" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{linha}" stop-opacity="0"/><stop offset="1" stop-color="{linha}" stop-opacity=".7"/></linearGradient>
<radialGradient id="chao" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{linha}" stop-opacity=".30"/><stop offset="1" stop-color="{linha}" stop-opacity="0"/></radialGradient>
<g id="roda"><g>{roda_giro}<circle class="v" r="17"/><circle class="d" r="9"/><path class="d" d="M0 -9V9M-9 0H9M-6.4 -6.4L6.4 6.4M-6.4 6.4L6.4 -6.4"/></g></g>
<g id="veic" stroke-width="2">{veiculos}</g>
</defs>
<g opacity="{opacidade_geral}">
<ellipse cx="800" cy="486" rx="790" ry="30" fill="url(#chao)"/>
{_brilhos(animado)}
{_aviao(animado)}
<use xlink:href="#veic" stroke-width="{halo_largura}" opacity="{halo}"/>
<use xlink:href="#veic"/>
<path d="M0 478H1600" stroke="{linha}" stroke-opacity=".35" stroke-width="1"/>
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

    /* cena logística (SVG animado) ancorada na base da tela */
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

import base64
import math
import random
from functools import lru_cache

import streamlit as st


# =====================================================
# EFEITO DE FUNDO DA TELA DE LOGIN: "CENTRAL LOGÍSTICA NEON"
# =====================================================
# Cena em estilo holograma (linhas ciano brilhantes sobre o fundo
# azul-escuro), toda desenhada em SVG vetorial — original, feita para
# o Luxiz IA, dividida em três faixas:
#
#   EM CIMA    -> o avião cruza o céu;
#   NO MEIO    -> o trem passa pela estrada;
#   EMBAIXO    -> um operador de capacete anda carregando uma caixa.
#
# Cada um atravessa a tela de um lado ao outro, some, e depois volta
# a aparecer — cada um no seu próprio ritmo, sem sincronia com os
# outros. O avião e o personagem vão da esquerda para a direita; o
# trem (desenhado virado para a esquerda) vai da direita para a
# esquerda.
#
# Animações (dentro do próprio SVG, sem JavaScript):
#   - o avião, o trem e o personagem atravessam a tela;
#   - as rodas do trem giram; o personagem balança as pernas e o
#     corpo sobe e desce a cada passo, na mesma velocidade em que
#     avança (para não parecer que escorrega);
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

LARGURA, ALTURA, CHAO = 1600, 760, 478

# CHAO = linha do chão desenhada DENTRO do trem (coordenadas locais).
# Abaixo, onde cada faixa fica na cena (coordenadas da tela).
FAIXA_AVIAO = 120     # topo do avião (céu)
FAIXA_ESTRADA = 500   # trilho do trem
FAIXA_PISO = 740      # chão onde o personagem anda

MARGEM = 60           # folga para o veículo nascer/sumir fora da tela

# Trem: passa, some por um tempo e volta.
CICLO_TREM = 90       # segundos
FASE_TREM = 25        # já começa a meio caminho quando a tela abre
JANELA_TREM = (0.02, 0.63)

# Personagem: passa, some por um tempo e volta.
CICLO_PERSONAGEM = 60  # segundos
FASE_PERSONAGEM = 15


def _costelas(x0, x1, passo, y0, y1):
    return "".join(f"M{x} {y0}V{y1}" for x in range(x0, x1, passo))


def _anim(animado, texto):
    return texto if animado else ""


def _no_chao(escala, chao, conteudo, x=0):
    """Posiciona o veículo (escalado) com as rodas apoiadas em `chao`."""
    ty = round(chao - CHAO * escala, 2)
    return f'<g transform="translate({x},{ty}) scale({escala})">{conteudo}</g>'


def _travessia(x_ini, x_fim, dur, fase=0, janela=None):
    """Animação de ir de x_ini até x_fim e recomeçar.

    Sem `janela`, atravessa o ciclo inteiro (e reaparece logo em
    seguida). Com `janela=(a, b)`, só se move entre as frações a e b
    do ciclo e fica fora da tela no resto do tempo.
    """
    if janela is None:
        valores, tempos = f"{x_ini} 0;{x_fim} 0", ""
    else:
        a, b = janela
        valores = f"{x_ini} 0;{x_ini} 0;{x_fim} 0;{x_fim} 0"
        tempos = f' keyTimes="0;{a};{b};1"'
    return (
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="{valores}"{tempos} dur="{dur}s" begin="-{fase}s" '
        f'repeatCount="indefinite"/>'
    )


def _viajar(animado, peca, x_min, x_max, sentido, dur, fase=0, janela=None, x_parado=0):
    """Faz a peça atravessar a tela de ponta a ponta.

    x_min / x_max: extensão da peça (já na escala final) em relação à
    sua origem; servem para ela nascer e sumir totalmente fora da tela.
    sentido: 1 = esquerda -> direita, -1 = direita -> esquerda.
    x_parado: posição usada quando o movimento está desligado.
    """
    if not animado:
        return f'<g transform="translate({x_parado},0)">{peca}</g>'

    esquerda = round(-x_max - MARGEM)
    direita = round(LARGURA - x_min + MARGEM)
    x_ini, x_fim = (esquerda, direita) if sentido > 0 else (direita, esquerda)
    return f'<g>{_travessia(x_ini, x_fim, dur, fase, janela)}{peca}</g>'


def _roda(x):
    return f'<use xlink:href="#roda" x="{x}" y="461"/>'


# -----------------------------------------------------
# MEIO: trem (virado para a esquerda)
# -----------------------------------------------------
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
    escala = .85
    peca = _no_chao(escala, FAIXA_ESTRADA, c)
    return _viajar(
        animado, peca, 0, 452 * escala, -1,
        CICLO_TREM, FASE_TREM, JANELA_TREM, x_parado=360,
    )


# -----------------------------------------------------
# EMBAIXO: personagem andando com uma caixa (virado para a direita)
# -----------------------------------------------------
def _personagem(animado):
    escala = 1.3
    amplitude = 20      # graus que cada perna balança para frente/para trás
    volta = 2.4         # segundos de uma passada completa (as duas pernas)
    meia = volta / 2
    comp_perna = 66     # comprimento da perna (coordenadas locais)

    # velocidade em que os pés "andam" no chão, para o corpo avançar
    # no mesmo ritmo das pernas (sem patinar)
    passo = 2 * comp_perna * escala * math.sin(math.radians(amplitude))
    velocidade = passo / meia
    queda = round(comp_perna * (1 - math.cos(math.radians(amplitude))), 1)

    suave = 'calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" keyTimes="0;.5;1"'

    def perna(fase, angulo_parado):
        giro = _anim(
            animado,
            f'<animateTransform attributeName="transform" type="rotate" '
            f'values="-{amplitude};{amplitude};-{amplitude}" {suave} '
            f'dur="{volta}s" begin="-{fase}s" repeatCount="indefinite"/>'
        )
        # parado (movimento reduzido): uma perna à frente e outra atrás
        return (
            f'<g transform="translate(0,-{comp_perna})">'
            f'<g transform="rotate({angulo_parado})">{giro}'
            f'<path class="v" d="M-5 0H5L4 60H15Q16 66 12 66H-4Z"/></g></g>'
        )

    # o corpo desce um pouquinho quando as pernas abrem e sobe quando
    # elas se cruzam (duas vezes por passada)
    balanco = _anim(
        animado,
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="0 {queda};0 0;0 {queda}" {suave} '
        f'dur="{meia}s" repeatCount="indefinite"/>'
    )

    cabeca = (
        '<circle class="v" cx="1" cy="-134" r="12"/>'
        '<path class="d" d="M1 -122V-118"/>'
        '<path class="v" d="M-12 -137Q-12 -153 1 -153Q14 -153 14 -137Z"/>'
        '<path class="d" d="M-12 -137H20"/>'
        '<circle class="f" cx="7" cy="-132" r="1.6"/>'
    )

    tronco = (
        '<path class="v" d="M-14 -118H14L11 -64H-11Z"/>'
        '<path class="d" d="M-12 -102H12M-11.5 -92H11.5"/>'
    )

    caixa = (
        '<path class="v" d="M16 -108h44v42h-44z"/>'
        '<path class="v" d="M16 -108l6 -7h44l-6 7z"/>'
        '<path class="v" d="M60 -108l6 -7v42l-6 7z"/>'
        '<path class="d" d="M34 -108V-66M42 -108V-66M34 -108l6 -7M42 -108l6 -7"/>'
        '<path class="d" d="M47 -90h9v9h-9z"/>'
    )

    braco = (
        '<path class="v" d="M5.6 -115.7L15.6 -93.7L8.4 -90.4L-1.6 -112.4Z"/>'
        '<path class="v" d="M14.3 -94.7L42.3 -70.7L37.7 -65.3L9.7 -89.3Z"/>'
        '<circle class="v" cx="12" cy="-92" r="4"/>'
        '<circle class="v" cx="40" cy="-68" r="4.5"/>'
    )

    corpo = (
        perna(meia, 18)      # perna de trás
        + tronco
        + perna(0, -18)      # perna da frente
        + cabeca
        + caixa
        + braco
    )

    # parado, o corpo já fica na altura de "pernas abertas" (pés no chão)
    ajuste = "" if animado else f' transform="translate(0,{queda})"'
    peca = (
        f'<g transform="translate(0,{FAIXA_PISO}) scale({escala})">'
        f'<g{ajuste}>{balanco}{corpo}</g></g>'
    )

    # extensão do desenho (com as pernas abertas e a caixa na frente)
    x_min, x_max = -30 * escala, 70 * escala

    # janela de tempo calculada pela velocidade do passo: quanto mais
    # rápido o passo, mais cedo ele chega ao outro lado
    distancia = LARGURA - x_min + x_max + 2 * MARGEM
    fim = min(0.98, 0.02 + distancia / velocidade / CICLO_PERSONAGEM)

    return _viajar(
        animado, peca, x_min, x_max, 1,
        CICLO_PERSONAGEM, FASE_PERSONAGEM, (0.02, round(fim, 3)), x_parado=700,
    )


# -----------------------------------------------------
# EM CIMA: avião (virado para a direita)
# -----------------------------------------------------
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
        animado, peca, -260 * escala, 252 * escala, 1,
        80, 34, x_parado=1000,
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
        linha, detalhe, preenche, ponto = "#0284c7", "#38bdf8", "rgba(2,132,199,.05)", "#0ea5e9"
        opacidade_geral, halo, halo_largura = ".8", ".10", 6
    else:
        linha, detalhe, preenche, ponto = "#22d3ee", "#a5f3fc", "rgba(34,211,238,.06)", "#bae6fd"
        opacidade_geral, halo, halo_largura = "1", ".16", 8

    # as rodas giram para trás (anti-horário) porque o trem anda para
    # a esquerda; 2,4 s por volta acompanha a velocidade dele
    roda_giro = _anim(
        animado,
        '<animateTransform attributeName="transform" type="rotate" '
        'from="360" to="0" dur="2.4s" repeatCount="indefinite"/>'
    )

    veiculos = _trem(animado) + _personagem(animado)

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
<ellipse cx="800" cy="{FAIXA_PISO + 8}" rx="790" ry="30" fill="url(#chao)"/>
{_brilhos(animado)}
{_aviao(animado)}
<use xlink:href="#veic" stroke-width="{halo_largura}" opacity="{halo}"/>
<use xlink:href="#veic"/>
<path d="M0 {FAIXA_ESTRADA}H{LARGURA}" stroke="{linha}" stroke-opacity=".35" stroke-width="1"/>
<path d="M0 {FAIXA_PISO}H{LARGURA}" stroke="{linha}" stroke-opacity=".35" stroke-width="1"/>
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

import base64
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
#   NO MEIO    -> caminhões e o trem passam pela estrada;
#   EMBAIXO    -> o navio cargueiro navega sobre as ondas.
#
# Cada veículo atravessa a tela de um lado ao outro, some, e depois
# volta a aparecer — cada um no seu próprio ritmo, sem sincronia com
# os outros. Os da estrada (caminhões e trem) saem da direita para a
# esquerda, na direção em que estão virados, e passam um de cada vez
# (cada um tem a sua "janela" de tempo), então nunca se sobrepõem.
#
# Animações (dentro do próprio SVG, sem JavaScript):
#   - o avião, o navio, os caminhões e o trem atravessam a tela;
#   - as rodas giram, o navio balança e as ondas correm;
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

# CHAO = linha do chão desenhada DENTRO de cada veículo (coordenadas
# locais). Abaixo, onde cada faixa fica na cena (coordenadas da tela).
FAIXA_AVIAO = 120     # topo do avião (céu)
FAIXA_ESTRADA = 500   # chão da estrada (caminhões e trem)
FAIXA_MAR = 740       # linha d'água do navio

MARGEM = 60           # folga para o veículo nascer/sumir fora da tela

# Estrada: um ciclo compartilhado; cada veículo usa uma fatia (janela)
# diferente do ciclo, então passam um de cada vez.
CICLO_ESTRADA = 200   # segundos
FASE_ESTRADA = 25     # começa já com o primeiro caminhão a meio caminho
JANELA_CAMINHAO_A = (0.02, 0.27)
JANELA_TREM = (0.36, 0.64)
JANELA_CAMINHAO_B = (0.70, 0.95)


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

    Sem `janela`, o veículo atravessa o ciclo inteiro (e reaparece logo
    em seguida). Com `janela=(a, b)`, ele só se move entre as frações
    a e b do ciclo e fica fora da tela no resto do tempo.
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
# MEIO: estrada (caminhões e trem, virados para a esquerda)
# -----------------------------------------------------
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
    escala = .88
    peca = _no_chao(escala, FAIXA_ESTRADA, c)
    return _viajar(
        animado, peca, 0, 336 * escala, -1,
        CICLO_ESTRADA, FASE_ESTRADA, JANELA_CAMINHAO_A, x_parado=20,
    )


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
    escala = .88
    peca = _no_chao(escala, FAIXA_ESTRADA, c)
    return _viajar(
        animado, peca, 0, 350 * escala, -1,
        CICLO_ESTRADA, FASE_ESTRADA, JANELA_CAMINHAO_B, x_parado=790,
    )


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
        CICLO_ESTRADA, FASE_ESTRADA, JANELA_TREM, x_parado=360,
    )


# -----------------------------------------------------
# EMBAIXO: mar e navio (virado para a direita)
# -----------------------------------------------------
def _mar(animado):
    # ondas ocupam a largura toda e correm sem parar; o deslocamento é
    # de um período inteiro (60), então o laço não dá "pulo"
    y = FAIXA_MAR
    onda = f"M-60 {y}Q-45 {y - 8} -30 {y}" + "".join(
        f"T{x} {y}" for x in range(0, LARGURA + 120, 30)
    )
    corre = _anim(
        animado,
        '<animateTransform attributeName="transform" type="translate" '
        'values="0 0;60 0" dur="8s" repeatCount="indefinite"/>'
    )
    return f'<g class="onda"><g>{corre}<path class="d" d="{onda}"/></g></g>'


def _navio(animado):
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
    peca = _no_chao(1, FAIXA_MAR, f"<g>{balanco}{casco}</g>")
    return _viajar(animado, peca, 0, 532, 1, 110, 40, x_parado=1000)


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

    # as rodas giram para trás (anti-horário) porque caminhões e trem
    # andam para a esquerda; 2,4 s por volta acompanha a velocidade
    roda_giro = _anim(
        animado,
        '<animateTransform attributeName="transform" type="rotate" '
        'from="360" to="0" dur="2.4s" repeatCount="indefinite"/>'
    )

    veiculos = (
        _caminhao_a(animado)
        + _trem(animado)
        + _caminhao_b(animado)
        + _navio(animado)
        + _mar(animado)
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
<ellipse cx="800" cy="{FAIXA_MAR + 8}" rx="790" ry="30" fill="url(#chao)"/>
{_brilhos(animado)}
{_aviao(animado)}
<use xlink:href="#veic" stroke-width="{halo_largura}" opacity="{halo}"/>
<use xlink:href="#veic"/>
<path d="M0 {FAIXA_ESTRADA}H{LARGURA}" stroke="{linha}" stroke-opacity=".35" stroke-width="1"/>
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

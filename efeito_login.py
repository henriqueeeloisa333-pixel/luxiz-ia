import streamlit as st


# =====================================================
# EFEITO DE FUNDO DA TELA DE LOGIN (aurora + partículas)
# =====================================================
# Duas camadas animadas só com CSS, sem JavaScript, nas cores da
# marca (ciano -> roxo):
#   - "Aurora": manchas de luz grandes e suaves que derivam devagar.
#   - "Partículas": pontinhos de luz que sobem lentamente e cintilam,
#     lembrando pontos de dados/rastreio de uma operação logística.
#
# Como se encaixa no estilos.py: o gradiente do login está em
# .stApp (veja _css_fundo, tela == "login"). As duas camadas são os
# pseudo-elementos ::before e ::after do próprio .stApp — ficam logo
# acima do gradiente — e o conteúdo (stAppViewContainer) sobe um
# nível para ficar por cima delas. Assim o card de login continua
# 100% clicável. O CSS só é injetado nas telas de login/troca de
# senha; ao entrar no sistema, ele deixa de ser enviado e o efeito
# some sozinho.

def aplicar(tema):

    if tema == "claro":
        mistura = "normal"
        opacidade_aurora = ".55"
        cor_a = "rgba(14,165,233,.30)"
        cor_b = "rgba(168,85,247,.28)"
        cor_c = "rgba(99,102,241,.26)"
        cor_d = "rgba(56,189,248,.24)"
        ponto_1 = "rgba(99,102,241,.55)"
        ponto_2 = "rgba(14,165,233,.65)"
        ponto_3 = "rgba(168,85,247,.55)"
    else:
        mistura = "screen"
        opacidade_aurora = "1"
        cor_a = "rgba(0,200,255,.34)"
        cor_b = "rgba(168,85,247,.32)"
        cor_c = "rgba(59,130,246,.30)"
        cor_d = "rgba(124,58,237,.26)"
        ponto_1 = "rgba(255,255,255,.70)"
        ponto_2 = "rgba(0,200,255,.85)"
        ponto_3 = "rgba(168,85,247,.80)"

    css = """
    <style>
    @keyframes luxizAuroraMover {
        0%   { transform: translate3d(0,0,0) rotate(0deg) scale(1); }
        50%  { transform: translate3d(3%,-4%,0) rotate(7deg) scale(1.12); }
        100% { transform: translate3d(0,0,0) rotate(0deg) scale(1); }
    }
    @keyframes luxizParticulasSubir {
        from { background-position: 0 0; }
        to   { background-position: 0 -420px; }
    }
    @keyframes luxizParticulasBrilho {
        0%, 100% { opacity: .45; }
        50%      { opacity: 1; }
    }

    /* o conteúdo fica acima das duas camadas de efeito */
    [data-testid="stAppViewContainer"] {
        position: relative;
        z-index: 1;
    }

    .stApp::before {
        content: "";
        position: fixed;
        inset: -25%;
        z-index: 0;
        pointer-events: none;
        opacity: __OPACIDADE_AURORA__;
        mix-blend-mode: __MISTURA__;
        will-change: transform;
        background:
            radial-gradient(38% 34% at 22% 28%, __COR_A__, transparent 70%),
            radial-gradient(34% 32% at 78% 22%, __COR_B__, transparent 70%),
            radial-gradient(42% 38% at 68% 82%, __COR_C__, transparent 70%),
            radial-gradient(30% 28% at 18% 80%, __COR_D__, transparent 70%);
        animation: luxizAuroraMover 26s ease-in-out infinite;
    }

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
            luxizParticulasSubir 45s linear infinite,
            luxizParticulasBrilho 6s ease-in-out infinite;
    }

    @media (prefers-reduced-motion: reduce) {
        .stApp::before,
        .stApp::after {
            animation: none;
        }
    }
    </style>
    """

    for marcador, valor in {
        "__OPACIDADE_AURORA__": opacidade_aurora,
        "__MISTURA__": mistura,
        "__COR_A__": cor_a,
        "__COR_B__": cor_b,
        "__COR_C__": cor_c,
        "__COR_D__": cor_d,
        "__PONTO_1__": ponto_1,
        "__PONTO_2__": ponto_2,
        "__PONTO_3__": ponto_3,
    }.items():
        css = css.replace(marcador, valor)

    st.markdown(css, unsafe_allow_html=True)

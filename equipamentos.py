import streamlit as st
import banco
import estilos
import re
from collections import defaultdict


def gerar_chave_css(texto):

    return re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        texto
    ).strip('-').lower()


CORES_LOCAL = {
    "Remanejamento": ("rgba(6,182,212,0.14)", "#06b6d4"),
    "Fracionado": ("rgba(168,85,247,0.14)", "#a855f7"),
}

COR_LOCAL_PADRAO = ("rgba(100,116,139,0.14)", "#64748b")


def render():

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    estilos.cabecalho_pagina(
        "🧰",
        "Equipamentos",
        "Responsáveis por hidráulicos e carrinhos, e carrinhos fixos por local.",
        cor="#0ea5e9"
    )

    st.divider()

    responsaveis_hidraulicos = banco.ler_responsaveis_hidraulicos(armazem_id_atual)
    responsaveis_carrinhos = banco.ler_responsaveis_carrinhos(armazem_id_atual)
    carrinhos_fixos = banco.ler_carrinhos_fixos(armazem_id_atual)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("🔧 Responsáveis (Hidráulicos)", len(responsaveis_hidraulicos))

    with c2:
        st.metric("🛒 Responsáveis (Carrinhos)", len(responsaveis_carrinhos))

    with c3:
        st.metric("📍 Carrinhos Fixos", len(carrinhos_fixos))

    st.divider()

    # =====================================================
    # RESPONSÁVEIS POR HIDRÁULICOS
    # =====================================================

    st.subheader("🔧 Responsáveis por Hidráulicos")

    if not responsaveis_hidraulicos:

        st.info(
            "Nenhum responsável cadastrado ainda. Cadastre no Administrativo, "
            "na aba 🧰 Equipamentos."
        )

    else:

        cols = st.columns(3)

        for indice, item in enumerate(responsaveis_hidraulicos):

            chave_card = f"card-resp-hid-{item['id']}-{gerar_chave_css(item['nome'])}"

            st.markdown(
                f"""
                <style>
                .st-key-{chave_card} {{
                    background:rgba(59,130,246,0.12) !important;
                    border:2px solid #3b82f6 !important;
                    border-radius:0.7rem;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )

            with cols[indice % 3]:

                with st.container(border=True, key=chave_card):

                    st.markdown(f"**{item['nome']}**")
                    st.caption(f"🔧 Hidráulico {item['numero']}")

    st.info("📅 Não esquecer de preencher o Checklist toda Sexta-Feira")

    st.divider()

    # =====================================================
    # RESPONSÁVEIS POR CARRINHOS
    # =====================================================

    st.subheader("🛒 Responsáveis por Carrinhos")

    if not responsaveis_carrinhos:

        st.info(
            "Nenhum responsável cadastrado ainda. Cadastre no Administrativo, "
            "na aba 🧰 Equipamentos."
        )

    else:

        cols = st.columns(3)

        for indice, item in enumerate(responsaveis_carrinhos):

            chave_card = f"card-resp-car-{item['id']}-{gerar_chave_css(item['nome'])}"

            st.markdown(
                f"""
                <style>
                .st-key-{chave_card} {{
                    background:rgba(34,197,94,0.12) !important;
                    border:2px solid #22c55e !important;
                    border-radius:0.7rem;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )

            with cols[indice % 3]:

                with st.container(border=True, key=chave_card):

                    st.markdown(f"**{item['nome']}**")
                    st.caption(f"🛒 Carrinho {item['numero']}")

    st.info("📅 Não esquecer de preencher o Checklist toda Sexta-Feira")

    st.divider()

    # =====================================================
    # CARRINHOS FIXOS POR LOCAL
    # =====================================================

    st.subheader("📍 Carrinhos Fixos por Local")

    st.caption(
        "Carrinhos que já ficam disponíveis fixos em cada local, "
        "sem precisar de remanejamento."
    )

    if not carrinhos_fixos:

        st.info(
            "Nenhum carrinho fixo cadastrado ainda."
        )

    else:

        por_local = defaultdict(list)

        for item in carrinhos_fixos:
            por_local[item["local"]].append(item["numero"])

        cols = st.columns(min(len(por_local), 3) or 1)

        for indice, local in enumerate(sorted(por_local.keys())):

            numeros = por_local[local]

            cor_fundo, cor_borda = CORES_LOCAL.get(local, COR_LOCAL_PADRAO)

            chave_card = f"card-local-{gerar_chave_css(local)}"

            st.markdown(
                f"""
                <style>
                .st-key-{chave_card} {{
                    background:{cor_fundo} !important;
                    border:2px solid {cor_borda} !important;
                    border-radius:0.8rem;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )

            with cols[indice % len(cols)]:

                with st.container(border=True, key=chave_card):

                    st.markdown(f"### 📍 {local}")

                    st.caption(f"{len(numeros)} carrinho(s) fixo(s)")

                    chips_html = "".join(
                        f"""
                        <span style="
                            display:inline-block;
                            background:{cor_borda};
                            color:white;
                            padding:.25rem .7rem;
                            border-radius:999px;
                            font-size:.8rem;
                            font-weight:700;
                            margin:.2rem .25rem .2rem 0;
                        ">Carrinho {numero}</span>
                        """
                        for numero in numeros
                    )

                    st.markdown(chips_html, unsafe_allow_html=True)

    st.divider()

    st.caption(
        "Luxiz IA • Equipamentos"
    )
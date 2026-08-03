import streamlit as st
import banco
import estilos
import re
from datetime import date


DIAS_SEMANA = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
]

COR_FUNDO_FIXO = "rgba(168,85,247,0.14)"
COR_BORDA_FIXO = "#a855f7"

COR_FUNDO_ROTATIVO = "rgba(6,182,212,0.14)"
COR_BORDA_ROTATIVO = "#06b6d4"


def gerar_chave_css(texto):

    return re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        texto
    ).strip('-').lower()


def gerar_escala_rotativa(pessoas, atividades_rotativas):

    """
    Gera a escala da semana atual (Segunda a Sexta) para as atividades
    do tipo "rotativo", sem precisar guardar nada no banco: para cada
    atividade e cada dia da semana, a pessoa responsável é calculada
    por rodízio (round-robin), deslocado pelo número da semana do ano
    — assim, toda semana o rodízio avança sozinho.
    """

    if not pessoas or not atividades_rotativas:
        return {}

    numero_semana = date.today().isocalendar()[1]

    escala = {}

    for indice_atividade, atividade in enumerate(atividades_rotativas):

        dias_da_atividade = []

        for indice_dia, dia in enumerate(DIAS_SEMANA):

            indice_pessoa = (
                indice_atividade + indice_dia + numero_semana
            ) % len(pessoas)

            dias_da_atividade.append(
                (dia, pessoas[indice_pessoa])
            )

        escala[atividade] = dias_da_atividade

    return escala


def render():

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    estilos.cabecalho_pagina(
        "🔄",
        "Atividades Fim de Expediente Rotativo",
        "Rodízio automático de quem faz cada atividade, de Segunda a Sexta.",
        cor="#06b6d4"
    )

    st.divider()

    pessoas = [
        nome for _, nome in banco.listar_pessoas_rotativo(armazem_id_atual)
    ]

    atividades_cadastradas = banco.listar_atividades_rotativo(armazem_id_atual)

    if not atividades_cadastradas:

        st.info(
            "Cadastre pessoas e atividades no Administrativo para o "
            "rodízio ser gerado automaticamente."
        )
        return

    atividades_fixas = [
        (nome, pessoa_fixa)
        for _, nome, tipo, pessoa_fixa in atividades_cadastradas
        if tipo == "fixo"
    ]

    nomes_atividades_rotativas = [
        nome
        for _, nome, tipo, pessoa_fixa in atividades_cadastradas
        if tipo != "fixo"
    ]

    if nomes_atividades_rotativas and not pessoas:

        st.warning(
            "Há atividades rotativas cadastradas, mas nenhuma pessoa "
            "no rodízio ainda. Cadastre as pessoas no Administrativo."
        )

    numero_semana = date.today().isocalendar()[1]

    dia_semana_hoje = date.today().weekday()

    dia_hoje = (
        DIAS_SEMANA[dia_semana_hoje]
        if dia_semana_hoje < 5
        else None
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("👥 Pessoas no rodízio", len(pessoas))

    with c2:
        st.metric("🧹 Atividades", len(atividades_cadastradas))

    with c3:
        st.metric("📅 Semana", numero_semana)

    st.divider()

    if not dia_hoje:

        st.info(
            "Hoje é fim de semana — a escala abaixo é referente aos "
            "dias úteis (Segunda a Sexta)."
        )

    escala_rotativa = gerar_escala_rotativa(
        pessoas,
        nomes_atividades_rotativas
    )

    cards = []

    for nome_atividade, pessoa_fixa in atividades_fixas:

        cards.append(
            ("fixo", nome_atividade, pessoa_fixa, None)
        )

    for nome_atividade, dias_da_atividade in escala_rotativa.items():

        cards.append(
            ("rotativo", nome_atividade, None, dias_da_atividade)
        )

    cols = st.columns(3)

    for indice, (tipo, nome_atividade, pessoa_fixa, dias_da_atividade) in enumerate(cards):

        eh_fixo = tipo == "fixo"

        cor_fundo = estilos.cor_fundo_cartao(COR_FUNDO_FIXO if eh_fixo else COR_FUNDO_ROTATIVO)
        cor_borda = COR_BORDA_FIXO if eh_fixo else COR_BORDA_ROTATIVO
        emblema = "📌" if eh_fixo else "🔄"

        chave_card = f"card-rot-{gerar_chave_css(nome_atividade)}"

        st.markdown(
            f"""
            <style>
            .st-key-{chave_card} {{
                background-color: {cor_fundo} !important;
                border: 2px solid {cor_borda} !important;
                border-radius: 0.8rem;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

        with cols[indice % 3]:

            with st.container(border=True, key=chave_card):

                st.markdown(
                    f"""
                    <div style="
                        width:52px;height:52px;border-radius:50%;
                        background:{cor_borda};
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.5rem;margin-bottom:.4rem;
                        box-shadow:0 0 14px {cor_borda}88;
                    ">{emblema}</div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"### {nome_atividade}"
                )

                if eh_fixo:

                    st.markdown(
                        f"""
                        <span style="
                            background:{cor_borda};
                            color:white;
                            padding:.15rem .6rem;
                            border-radius:999px;
                            font-size:.72rem;
                            font-weight:700;
                            letter-spacing:.3px;
                        ">FIXO</span>
                        """,
                        unsafe_allow_html=True
                    )

                    st.write("")

                    st.markdown(
                        f"👤 Responsável fixo: **{pessoa_fixa or 'Não informado'}**"
                    )

                else:

                    st.markdown(
                        f"""
                        <span style="
                            background:{cor_borda};
                            color:white;
                            padding:.15rem .6rem;
                            border-radius:999px;
                            font-size:.72rem;
                            font-weight:700;
                            letter-spacing:.3px;
                        ">RODÍZIO</span>
                        """,
                        unsafe_allow_html=True
                    )

                    st.write("")

                    if dia_hoje:

                        responsavel_hoje = dict(dias_da_atividade)[dia_hoje]

                        st.markdown(
                            f"👤 Hoje _{dia_hoje}_: **{responsavel_hoje}**"
                        )

                    else:

                        st.caption(
                            "Sem responsável hoje (fim de semana)."
                        )

                    with st.popover("📅 Ver escala da semana"):

                        st.caption(
                            f"Escala de '{nome_atividade}' — semana {numero_semana}:"
                        )

                        for dia, pessoa in dias_da_atividade:

                            if dia == dia_hoje:

                                st.markdown(
                                    f"**➡️ {dia}: {pessoa}**"
                                )

                            else:

                                st.caption(
                                    f"{dia}: {pessoa}"
                                )

    st.divider()

    st.caption(
        "Luxiz IA • Rodízio de Fim de Expediente"
    )
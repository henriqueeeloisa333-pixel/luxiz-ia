import streamlit as st
import banco
import estilos
import re

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def gerar_chave_css(texto):

    return re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        texto
    ).strip('-').lower()


def render():

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    estilos.cabecalho_pagina(
        "⚡",
        "Central de Remanejamento",
        "Monitoramento operacional das prioridades em tempo real.",
        cor="#f59e0b"
    )

    st.divider()

    itens = banco.ler_remanejamentos(armazem_id_atual)

    alta = 0
    media = 0
    normal = 0

    for item in itens:

        prioridade = item.get(
            "prioridade",
            "Normal"
        )

        prioridade = prioridade.strip().capitalize()

        if prioridade == "Alta":
            alta += 1

        elif prioridade == "Média":
            media += 1

        else:
            normal += 1

    # =====================================================
    # SELO DE PRIORIDADE (CSS do efeito suave, injetado 1x)
    # =====================================================
    # Um "ping" suave e contínuo no selo do lado direito de
    # cada card, preenchendo o espaço vago sem chamar atenção
    # demais — a cor do brilho vem de --pulso-cor, definida
    # individualmente em cada selo (via style inline).

    st.markdown(
        """
        <style>
        @keyframes luxizPulsoSuave {
            0%   { box-shadow: 0 0 0 0 var(--pulso-cor); }
            70%  { box-shadow: 0 0 0 14px rgba(0,0,0,0); }
            100% { box-shadow: 0 0 0 0 rgba(0,0,0,0); }
        }
        .luxiz-selo-prioridade {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.7rem;
            margin: 4px auto 0;
            animation: luxizPulsoSuave 2.6s ease-in-out infinite;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # PRIORIDADES
    # =====================================================

    if not itens:

        st.success(
            "Nenhuma prioridade operacional cadastrada."
        )

    else:

        cols = st.columns(3)

        for indice, item in enumerate(itens):

            prioridade = item.get(
                "prioridade",
                "Normal"
            )

            prioridade = prioridade.strip().capitalize()

            with cols[indice % 3]:

                if prioridade == "Alta":

                    cor_fundo = "rgba(220,38,38,0.16)"
                    cor_borda = "#dc2626"
                    rotulo_status = "🚨 PRIORIDADE ALTA"
                    tipo_alerta = "error"
                    progresso = 100
                    descricao = "Execução imediata recomendada."
                    emblema_selo = "🚨"

                elif prioridade == "Média":

                    cor_fundo = "rgba(245,158,11,0.16)"
                    cor_borda = "#f59e0b"
                    rotulo_status = "⚠️ PRIORIDADE MÉDIA"
                    tipo_alerta = "warning"
                    progresso = 60
                    descricao = "Monitoramento operacional ativo."
                    emblema_selo = "⚠️"

                else:

                    cor_fundo = "rgba(34,197,94,0.16)"
                    cor_borda = "#22c55e"
                    rotulo_status = "✅ PRIORIDADE NORMAL"
                    tipo_alerta = "success"
                    progresso = 30
                    descricao = "Fluxo operacional dentro do esperado."
                    emblema_selo = "✅"

                chave_card = f"card-reman-{item['id']}-{gerar_chave_css(item['nome'])}"

                st.markdown(
                    f"""
                    <style>
                    .st-key-{chave_card} {{
                        background-color: {cor_fundo} !important;
                        border: 2px solid {cor_borda} !important;
                        border-radius: 0.6rem;
                    }}
                    </style>
                    """,
                    unsafe_allow_html=True
                )

                with st.container(border=True, key=chave_card):

                    col_conteudo, col_selo = st.columns([4, 1])

                    with col_conteudo:

                        if tipo_alerta == "error":

                            st.error(rotulo_status)

                        elif tipo_alerta == "warning":

                            st.warning(rotulo_status)

                        else:

                            st.success(rotulo_status)

                        st.markdown(
                            f"### ⚡ {item['nome']}"
                        )

                        st.caption(
                            descricao
                        )

                        if item.get("criado_por"):

                            st.caption(
                                f"👤 Criado por {item['criado_por']}"
                            )

                    with col_selo:

                        st.markdown(
                            f"""
                            <div class="luxiz-selo-prioridade" style="
                                background:{cor_borda}22;
                                border:2px solid {cor_borda};
                                --pulso-cor:{cor_borda}77;
                            ">{emblema_selo}</div>
                            """,
                            unsafe_allow_html=True
                        )

                    st.progress(
                        progresso
                    )

    st.divider()

    # =====================================================
    # TOTAIS (agora logo abaixo dos cards)
    # =====================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "📦 Total",
            len(itens)
        )

    with c2:
        st.metric(
            "🔴 Alta",
            alta
        )

    with c3:
        st.metric(
            "🟠 Média",
            media
        )

    with c4:
        st.metric(
            "🟢 Normal",
            normal
        )

    st.divider()

    # =====================================================
    # RESUMO
    # =====================================================

    st.subheader(
        "Resumo Operacional"
    )

    if alta > 0:

        st.error(
            f"Existem {alta} prioridade(s) alta(s) aguardando execução."
        )

    elif media > 0:

        st.warning(
            f"Existem {media} prioridade(s) média(s) em monitoramento."
        )

    elif normal > 0:

        st.info(
            "Operação operando dentro da normalidade."
        )

    else:

        st.success(
            "Nenhuma prioridade pendente."
        )

    st.divider()

    # =====================================================
    # HISTÓRICO
    # =====================================================

    with st.popover("🕒 Histórico de Remanejamentos"):

        historico = banco.ler_historico_remanejamento(armazem_id_atual)

        if historico:

            for item, prioridade, data_hora, usuario_item in historico:

                data_utc = data_hora.replace(
                    tzinfo=timezone.utc
                )

                horario_local = data_utc.astimezone(
                    ZoneInfo("America/Campo_Grande")
                )

                if prioridade == "Alta":
                    emoji = "🔴"

                elif prioridade == "Média":
                    emoji = "🟡"

                else:
                    emoji = "🟢"

                responsavel = usuario_item or "desconhecido"

                st.caption(
                    f"{emoji} {item} | {prioridade} | "
                    f"{horario_local.strftime('%d/%m/%Y %H:%M:%S')} | "
                    f"por {responsavel}"
                )

        else:

            st.info(
                "Nenhum histórico encontrado."
            )
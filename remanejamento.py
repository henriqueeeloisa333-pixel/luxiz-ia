import streamlit as st
import banco

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def render():

    st.title("⚡ Central de Remanejamento")

    st.caption(
        "Monitoramento operacional das prioridades em tempo real."
    )

    st.divider()

    itens = banco.ler_remanejamentos()

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

    st.subheader("🕒 Últimos Remanejamentos")

    historico = banco.ler_historico_remanejamento()

    if historico:

        for item, prioridade, data_hora in historico:

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

            st.caption(
                f"{emoji} {item} | {prioridade} | "
                f"{horario_local.strftime('%d/%m/%Y %H:%M:%S')}"
            )

    else:

        st.info(
            "Nenhum histórico encontrado."
        )

    st.divider()

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

                with st.container(border=True):

                    if prioridade == "Alta":

                        st.error(
                            "🚨 PRIORIDADE ALTA"
                        )

                        progresso = 100
                        descricao = "Execução imediata recomendada."

                    elif prioridade == "Média":

                        st.warning(
                            "⚠️ PRIORIDADE MÉDIA"
                        )

                        progresso = 60
                        descricao = "Monitoramento operacional ativo."

                    else:

                        st.success(
                            "✅ PRIORIDADE NORMAL"
                        )

                        progresso = 30
                        descricao = "Fluxo operacional dentro do esperado."

                    st.markdown(
                        f"### ⚡ {item['nome']}"
                    )

                    st.caption(
                        descricao
                    )

                    st.progress(
                        progresso
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
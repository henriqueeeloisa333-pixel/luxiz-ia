import streamlit as st
import banco
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter


def render():

    banco.inicializar_banco()

    st.title("😊 Central SAC Luxiz IA")

    st.caption(
        "Monitoramento inteligente de reclamações e metas"
    )

    st.divider()

    dados = banco.ler_historico_sac()

    if not dados:

        st.info(
            "Nenhum dado cadastrado ainda."
        )
        return

    tema = st.session_state.get("tema", "escuro")
    cor_fonte = "white" if tema == "escuro" else "#111827"

    df = pd.DataFrame(
        dados,
        columns=[
            "Mês",
            "Reclamações",
            "Meta",
            "Atualizado por",
            "Atualizado em"
        ]
    )

    ultimo = df.iloc[-1]

    reclamacoes = int(
        ultimo["Reclamações"]
    )

    meta = int(
        ultimo["Meta"]
    )

    margem = meta - reclamacoes

    # ==================================
    # KPIs
    # ==================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "📢 Índice Logístico",
            reclamacoes
        )

    with c2:
        st.metric(
            "🎯 Meta",
            meta
        )

    with c3:
        st.metric(
            "📊 Margem",
            margem
        )

    with c4:

        if reclamacoes <= meta:
            st.metric(
                "✅ Status",
                "Positivo"
            )
        else:
            st.metric(
                "🚨 Status",
                "Acima"
            )

    st.divider()

    # ==================================
    # EVOLUÇÃO MENSAL
    # ==================================

    st.subheader(
        "Evolução Mensal"
    )

    fig = px.line(
        df,
        x="Mês",
        y=[
            "Reclamações",
            "Meta"
        ],
        markers=True
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=cor_fonte,
        height=500,
        legend_title="Indicadores"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ==================================
    # COMPARATIVOS
    # ==================================

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            "Comparativo Atual"
        )

        fig_bar = go.Figure()

        fig_bar.add_trace(
            go.Bar(
                name="Reclamações",
                x=["Atual"],
                y=[reclamacoes]
            )
        )

        fig_bar.add_trace(
            go.Bar(
                name="Meta",
                x=["Atual"],
                y=[meta]
            )
        )

        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=cor_fonte,
            barmode="group",
            height=350
        )

        st.plotly_chart(
            fig_bar,
            use_container_width=True
        )

    with col2:

        st.subheader(
            "Indicador de Meta"
        )

        percentual = 0

        if meta > 0:
            percentual = (
                reclamacoes / meta
            ) * 100

        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=percentual,
                number={
                    "suffix": "%"
                },
                gauge={
                    "axis": {
                        "range": [0, 200]
                    },
                    "bar": {
                        "color": "#00c8ff"
                    }
                }
            )
        )

        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=cor_fonte,
            height=350
        )

        st.plotly_chart(
            fig_gauge,
            use_container_width=True
        )

    st.divider()

    # ==================================
    # HISTÓRICO
    # ==================================

    st.subheader(
        "Histórico de Resultados"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # ==================================
    # RESUMO IA
    # ==================================

    st.subheader(
        "Análise Inteligente"
    )

    if reclamacoes <= meta:

        st.success(
            f"""
Excelente resultado.

O SAC está dentro da meta estabelecida,
com margem de {margem} ocorrências.
"""
        )

    elif reclamacoes <= meta + 5:

        st.warning(
            """
Atenção.

O SAC está próximo do limite permitido.
Recomenda-se acompanhamento.
"""
        )

    else:

        st.error(
            """
Alerta crítico.

O número de reclamações ultrapassou
significativamente a meta.
"""
        )

    st.divider()

    # ==================================
    # ANÁLISE TÉCNICA
    # ==================================

    st.subheader(
        "🔍 Análise Técnica"
    )

    st.caption(
        "Ocorrências registradas por pessoa."
    )

    usuario_atual = st.session_state.get("usuario", "")

    nome_restrito = None

    if usuario_atual.startswith("Separador.") or usuario_atual.startswith("Conferente."):

        nome_restrito = usuario_atual.split(".", 1)[1].strip().title()

    registros = banco.ler_analise_tecnica()

    por_pessoa = {}

    for registro in registros:

        vinculos = registro.get("vinculos_notificados") or []

        if not vinculos and registro.get("nome"):

            # Compatibilidade com registros antigos, criados antes
            # da remoção do campo Nome.
            vinculos = [
                {
                    "nome": registro["nome"],
                    "papel": "Responsável"
                }
            ]

        # Deduplica por nome dentro do mesmo registro: mesmo que o
        # mesmo nome apareça em papéis diferentes (ex: Nome e
        # Separador iguais, salvos antes da correção), esse
        # registro conta só 1 vez para essa pessoa.
        nomes_ja_contados_neste_registro = set()

        for vinculo in vinculos:

            nome_normalizado = vinculo["nome"].strip().title()

            if nome_normalizado in nomes_ja_contados_neste_registro:
                continue

            nomes_ja_contados_neste_registro.add(nome_normalizado)

            entrada = dict(registro)
            entrada["papel_nesta_ocorrencia"] = vinculo["papel"]

            por_pessoa.setdefault(
                nome_normalizado,
                []
            ).append(entrada)

    if nome_restrito:

        por_pessoa = {
            nome: erros for nome, erros in por_pessoa.items()
            if nome == nome_restrito
        }

    if not por_pessoa:

        if nome_restrito:

            st.info(
                "Nenhuma ocorrência registrada para você ainda."
            )

        else:

            st.info(
                "Nenhum registro de análise técnica ainda."
            )

    else:

        nomes = sorted(
            por_pessoa.keys()
        )

        cols = st.columns(3)

        for indice, nome in enumerate(nomes):

            erros_pessoa = por_pessoa[nome]

            total_erros = len(erros_pessoa)

            contagem_tipos = Counter(
                erro["tipo_erro"] for erro in erros_pessoa
            )

            tipo_mais_comum, qtd_mais_comum = contagem_tipos.most_common(1)[0]

            with cols[indice % 3]:

                with st.container(border=True):

                    st.markdown(
                        f"### 👤 {nome}"
                    )

                    st.metric(
                        "Total de Erros",
                        total_erros
                    )

                    st.warning(
                        f"📌 Ponto de melhoria: **{tipo_mais_comum}** "
                        f"({qtd_mais_comum}x). Recomenda-se reforço nesse ponto."
                    )

                    with st.popover(
                        "📋 Saber mais"
                    ):

                        st.caption(
                            f"Histórico de ocorrências de {nome}:"
                        )

                        erros_ordenados = sorted(
                            erros_pessoa,
                            key=lambda e: e["data_erro"],
                            reverse=True
                        )

                        with st.container(height=250):

                            for erro in erros_ordenados:

                                st.caption(
                                    f"• {erro['tipo_erro']} — "
                                    f"{erro['data_erro'].strftime('%d/%m/%Y')} "
                                    f"({erro['papel_nesta_ocorrencia']})"
                                )

                                if erro.get("descricao"):

                                    st.caption(
                                        f"   ↳ _{erro['descricao']}_"
                                    )

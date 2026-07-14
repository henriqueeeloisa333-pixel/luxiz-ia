import streamlit as st
import banco
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


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

    df = pd.DataFrame(
        dados,
        columns=[
            "Mês",
            "Reclamações",
            "Meta"
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
        font_color="white",
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
            font_color="white",
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

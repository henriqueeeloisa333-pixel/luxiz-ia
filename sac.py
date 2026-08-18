import streamlit as st
import banco
import estilos
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from collections import Counter


def gerar_chave_css(texto):

    return re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        texto
    ).strip('-').lower()


def render():

    banco.inicializar_banco()

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    estilos.cabecalho_pagina(
        "😊",
        "Central SAC Luxiz IA",
        "Monitoramento inteligente de reclamações e metas",
        cor="#22c55e"
    )

    st.divider()

    dados = banco.ler_historico_sac(armazem_id_atual)

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

    # "Atualizado em" vem do banco em UTC (CURRENT_TIMESTAMP do
    # Postgres). Convertemos para o horário de Campo Grande antes de
    # exibir na tabela — senão o horário aparece com ~4h de diferença.

    df["Atualizado em"] = df["Atualizado em"].apply(
        lambda momento: (
            estilos.horario_local(momento).strftime("%d/%m/%Y %H:%M")
            if momento else ""
        )
    )

    # "Mês" vem do banco como texto "AAAA-MM" (ex: "2026-07").
    # Se deixarmos esse texto ir direto pro eixo X do gráfico, o
    # Plotly tenta "adivinhar" que é uma data e, com poucos pontos,
    # cria um eixo quebrado (aquele "23:59:59.9995" sem sentido).
    # Aqui a gente converte pra um rótulo fixo tipo "Jul/2026" e
    # trata o eixo como categoria, não como data.

    MESES_ABREVIADOS = [
        "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez"
    ]

    def formatar_mes(mes_ano_texto):

        try:
            ano, mes = mes_ano_texto.split("-")
            return f"{MESES_ABREVIADOS[int(mes) - 1]}/{ano}"

        except Exception:
            return mes_ano_texto

    df["Mês"] = df["Mês"].apply(formatar_mes)

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

    cor_grade = "rgba(255,255,255,.08)" if tema == "escuro" else "rgba(0,0,0,.08)"

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Mês"],
            y=df["Reclamações"],
            name="Reclamações",
            mode="lines+markers",
            line=dict(color="#f97316", width=3),
            marker=dict(size=8),
            fill="tozeroy",
            fillcolor="rgba(249,115,22,0.12)",
            hovertemplate="%{x}<br>Reclamações: %{y}<extra></extra>"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Mês"],
            y=df["Meta"],
            name="Meta",
            mode="lines+markers",
            line=dict(color="#38bdf8", width=3, dash="dash"),
            marker=dict(size=8),
            hovertemplate="%{x}<br>Meta: %{y}<extra></extra>"
        )
    )

    fig.update_xaxes(
        type="category",
        title=None,
        gridcolor=cor_grade
    )

    fig.update_yaxes(
        title=None,
        gridcolor=cor_grade,
        rangemode="tozero"
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=cor_fonte,
        height=420,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title=None
        ),
        margin=dict(t=40, l=10, r=10, b=10)
    )

    st.plotly_chart(
        fig,
        width='stretch'
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
            width='stretch'
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
            width='stretch'
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
        width='stretch',
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

    # Antes: comparava exato o nome depois do prefixo do login (ex.:
    # "Alexandre") com o nome salvo no registro. Como o nome salvo
    # agora pode vir completo pelo Perfil (ex.: "Alexandre Vasques"),
    # essa comparação exata deixava de bater. Agora só guardamos QUE
    # o acesso é restrito — quem bate com quem é decidido mais abaixo
    # por banco.pessoa_pertence_ao_usuario (nome/sobrenome/perfil).
    acesso_restrito_sac = (
        usuario_atual.startswith("Separador.")
        or usuario_atual.startswith("Conferente.")
    )

    registros_todos = banco.ler_analise_tecnica(armazem_id_atual)

    # Os cards de Análise Técnica zeram no começo de cada mês — só
    # contam as ocorrências do mês atual. O histórico completo
    # continua acessível de outras formas (ex.: Administrativo),
    # este filtro afeta só os cards mostrados aqui.
    hoje_local = estilos.agora_local().date()

    registros = [
        registro for registro in registros_todos
        if registro["data_erro"].year == hoje_local.year
        and registro["data_erro"].month == hoje_local.month
    ]

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

            # Antes: vinculo["nome"].strip().title() — isso deixava
            # "Alexandre" e "Alexandre Vasques" em cards separados.
            # Agora usa o Perfil (quando existir) para juntar os dois
            # num card só, já com o nome completo certo.
            nome_normalizado = banco.normalizar_nome_pessoa(
                vinculo["nome"], armazem_id_atual
            )

            if nome_normalizado in nomes_ja_contados_neste_registro:
                continue

            nomes_ja_contados_neste_registro.add(nome_normalizado)

            entrada = dict(registro)
            entrada["papel_nesta_ocorrencia"] = vinculo["papel"]

            por_pessoa.setdefault(
                nome_normalizado,
                []
            ).append(entrada)

    if acesso_restrito_sac:

        por_pessoa = {
            nome: erros for nome, erros in por_pessoa.items()
            if banco.pessoa_pertence_ao_usuario(
                nome, usuario_atual, armazem_id_atual
            )
        }

    if not por_pessoa:

        if acesso_restrito_sac:

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

                if total_erros <= 1:

                    cor_fundo = "rgba(34,197,94,0.16)"
                    cor_borda = "#22c55e"
                    rotulo_status = "✅ Poucas ocorrências"

                elif total_erros <= 3:

                    cor_fundo = "rgba(245,158,11,0.16)"
                    cor_borda = "#f59e0b"
                    rotulo_status = "⚠️ Atenção"

                else:

                    cor_fundo = "rgba(220,38,38,0.16)"
                    cor_borda = "#dc2626"
                    rotulo_status = "🚨 Reforço necessário"

                chave_card = f"card-analise-{gerar_chave_css(nome)}"

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

                with st.container(border=True, key=chave_card):

                    st.markdown(
                        f"""
                        <div style="
                            width:52px;height:52px;border-radius:50%;
                            background:{cor_borda};
                            display:flex;align-items:center;justify-content:center;
                            font-size:1.5rem;margin-bottom:.4rem;
                            box-shadow:0 0 14px {cor_borda}88;
                        ">👤</div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"### {nome}"
                    )

                    if cor_borda == "#22c55e":
                        st.success(rotulo_status)
                    elif cor_borda == "#f59e0b":
                        st.warning(rotulo_status)
                    else:
                        st.error(rotulo_status)

                    st.metric(
                        "Total de Erros",
                        total_erros
                    )

                    st.markdown(
                        f"""
                        <div style="
                            background:{cor_borda}22;
                            border-left:4px solid {cor_borda};
                            padding:.5rem .7rem;
                            border-radius:.4rem;
                            font-size:.85rem;
                        ">
                        📌 Ponto de melhoria: <strong>{tipo_mais_comum}</strong>
                        ({qtd_mais_comum}x). Recomenda-se reforço nesse ponto.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.write("")

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

                                chamado_erro = erro.get("chamado")

                                st.caption(
                                    f"• {erro['tipo_erro']} — "
                                    f"{erro['data_erro'].strftime('%d/%m/%Y')} "
                                    f"({erro['papel_nesta_ocorrencia']})"
                                    + (f" • Chamado {chamado_erro}" if chamado_erro else "")
                                )

                                if erro.get("descricao"):

                                    st.caption(
                                        f"   ↳ _{erro['descricao']}_"
                                    )

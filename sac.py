import html
import math
import re
from collections import Counter

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import banco
import estilos


def gerar_chave_css(texto):

    return re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        texto
    ).strip('-').lower()


# =====================================================
# VISUAL (cores, CSS e peças reutilizáveis)
# =====================================================

COR_OK = "#22c55e"
COR_ATENCAO = "#f59e0b"
COR_CRITICO = "#ef4444"
COR_NEUTRA = "#94a3b8"
COR_META = "#38bdf8"

CSS_SAC = """
<style>
div[class*="st-key-sac-painel"]{
    background:linear-gradient(150deg, rgba(148,163,184,.10), rgba(148,163,184,.03)) !important;
    border:1px solid rgba(148,163,184,.28) !important;
    border-radius:1.1rem !important;
    box-shadow:0 8px 22px rgba(0,0,0,.12);
}
.lx-sac-linha{
    transition:transform .15s ease;
}
.lx-sac-linha:hover{
    transform:translateX(3px);
}
</style>
"""


def _situacao(reclamacoes, meta):
    """Devolve (cor, rótulo curto) seguindo a mesma regra da Análise Inteligente."""

    if reclamacoes <= meta:
        return COR_OK, "Positivo"

    if reclamacoes <= meta + 5:
        return COR_ATENCAO, "Acima"

    return COR_CRITICO, "Acima"


def _kpi_html(rotulo, valor, subtexto, cor, icone):

    return (
        f'<div style="background:linear-gradient(150deg,{cor}1f,{cor}08);'
        f'border:1px solid {cor}45;border-radius:1rem;padding:1rem 1.1rem;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-size:.7rem;font-weight:800;letter-spacing:.5px;'
        f'text-transform:uppercase;opacity:.7;">{rotulo}</span>'
        f'<span style="font-size:1.3rem;">{icone}</span></div>'
        f'<div style="font-size:2.1rem;font-weight:800;color:{cor};'
        f'line-height:1.1;margin-top:.3rem;">{valor}</div>'
        f'<div style="font-size:.74rem;opacity:.75;margin-top:.25rem;">{subtexto}</div>'
        '</div>'
    )


def _anel_svg(proporcao, texto_centro, texto_baixo, cor):

    raio = 42
    circunferencia = 2 * math.pi * raio

    proporcao = max(0.0, min(proporcao, 1.0))

    deslocamento = circunferencia * (1 - proporcao)

    return (
        '<svg width="150" height="150" viewBox="0 0 100 100" '
        'style="display:block;margin:0 auto;">'
        f'<circle cx="50" cy="50" r="{raio}" fill="none" stroke="{cor}" '
        'stroke-opacity=".18" stroke-width="9"/>'
        f'<circle cx="50" cy="50" r="{raio}" fill="none" stroke="{cor}" '
        'stroke-width="9" stroke-linecap="round" '
        f'stroke-dasharray="{circunferencia:.1f}" '
        f'stroke-dashoffset="{deslocamento:.1f}" '
        'transform="rotate(-90 50 50)"/>'
        f'<text x="50" y="49" text-anchor="middle" dominant-baseline="middle" '
        f'font-size="22" font-weight="800" fill="{cor}">{texto_centro}</text>'
        f'<text x="50" y="68" text-anchor="middle" font-size="7.5" '
        f'fill="currentColor" fill-opacity=".6">{texto_baixo}</text>'
        '</svg>'
    )


def _barra_horizontal(rotulo, valor, maximo, cor):

    largura = max(0.0, min(valor / maximo * 100, 100)) if maximo else 0

    return (
        '<div style="margin-top:.7rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'font-size:.78rem;margin-bottom:.25rem;">'
        f'<span style="opacity:.8;">{rotulo}</span>'
        f'<span style="font-weight:800;color:{cor};">{valor}</span></div>'
        f'<div style="height:9px;border-radius:999px;background:{cor}22;overflow:hidden;">'
        f'<div style="width:{largura:.1f}%;height:100%;border-radius:999px;'
        f'background:linear-gradient(90deg,{cor}99,{cor});"></div></div>'
        '</div>'
    )


def _card_meta_html(reclamacoes, meta, margem, mes_rotulo):

    cor, rotulo = _situacao(reclamacoes, meta)

    percentual = (reclamacoes / meta * 100) if meta > 0 else 0

    maximo = max(reclamacoes, meta, 1)

    if margem >= 0:
        texto_margem = f"Margem de {margem} ocorrência(s) até a meta"
    else:
        texto_margem = f"{abs(margem)} ocorrência(s) acima da meta"

    return (
        '<div style="padding:.2rem .2rem .4rem .2rem;">'
        f'<div style="text-align:center;font-size:.72rem;opacity:.6;margin-bottom:.4rem;">{mes_rotulo}</div>'
        f'{_anel_svg(percentual / 100, f"{percentual:.0f}%", "da meta utilizada", cor)}'
        f'<div style="text-align:center;margin-top:.7rem;">'
        f'<span style="display:inline-block;font-size:.76rem;font-weight:800;'
        f'padding:.25rem .8rem;border-radius:999px;background:{cor}26;color:{cor};'
        f'border:1px solid {cor}66;">{rotulo}</span></div>'
        f'{_barra_horizontal("Reclamações", reclamacoes, maximo, cor)}'
        f'{_barra_horizontal("Meta", meta, maximo, COR_META)}'
        f'<div style="margin-top:.9rem;font-size:.78rem;opacity:.75;text-align:center;">{texto_margem}</div>'
        '</div>'
    )


def _historico_html(df):

    grade = (
        "grid-template-columns:110px 110px 90px 90px 150px minmax(190px,1fr);"
    )

    cabecalho = (
        f'<div style="display:grid;{grade}gap:.9rem;padding:0 1rem .4rem 1rem;'
        'font-size:.66rem;font-weight:800;letter-spacing:.5px;'
        'text-transform:uppercase;opacity:.55;">'
        '<div>Mês</div><div>Reclamações</div><div>Meta</div>'
        '<div>Margem</div><div>Situação</div><div>Atualizado</div></div>'
    )

    linhas = ""

    for _, linha in df.iloc[::-1].iterrows():

        reclamacoes = int(linha["Reclamações"])
        meta = int(linha["Meta"])

        margem = meta - reclamacoes

        if meta <= 0 and reclamacoes > 0:
            cor, rotulo = COR_NEUTRA, "— sem meta"
        else:
            cor, rotulo = _situacao(reclamacoes, meta)
            rotulo = ("✅ " if cor == COR_OK else "⚠️ " if cor == COR_ATENCAO else "🚨 ") + rotulo

        cor_margem = COR_OK if margem >= 0 else COR_CRITICO

        por = linha["Atualizado por"]
        por_texto = html.escape(str(por)) if pd.notna(por) and por else "—"

        quando = linha["Atualizado em"] or "—"

        linhas += (
            f'<div class="lx-sac-linha" style="display:grid;{grade}gap:.9rem;'
            'align-items:center;padding:.65rem 1rem;margin-bottom:.45rem;'
            f'border-radius:.9rem;background:linear-gradient(100deg,{cor}12,{cor}05 60%);'
            f'border:1px solid {cor}30;border-left:5px solid {cor};">'
            f'<div style="font-weight:800;">{html.escape(str(linha["Mês"]))}</div>'
            f'<div style="font-weight:800;font-size:1.05rem;color:{cor};">{reclamacoes}</div>'
            f'<div style="font-weight:700;color:{COR_META};">{meta}</div>'
            f'<div style="font-weight:700;color:{cor_margem};">{margem:+d}</div>'
            f'<div><span style="display:inline-block;font-size:.72rem;font-weight:800;'
            f'padding:.2rem .65rem;border-radius:999px;background:{cor}26;color:{cor};'
            f'border:1px solid {cor}66;white-space:nowrap;">{rotulo}</span></div>'
            f'<div style="font-size:.76rem;opacity:.75;">{por_texto}'
            f'<br><span style="opacity:.8;">{html.escape(str(quando))}</span></div>'
            '</div>'
        )

    return (
        '<div style="overflow-x:auto;">'
        '<div style="min-width:780px;max-height:430px;overflow-y:auto;padding-right:.3rem;">'
        f'{cabecalho}{linhas}</div></div>'
    )


def _banner(cor, icone, titulo, texto):

    return (
        f'<div style="display:flex;align-items:center;gap:.9rem;'
        f'background:linear-gradient(120deg,{cor}22,{cor}08);'
        f'border:1px solid {cor}55;border-left:5px solid {cor};'
        'border-radius:.9rem;padding:1rem 1.2rem;">'
        f'<div style="font-size:1.9rem;">{icone}</div>'
        '<div>'
        f'<div style="font-weight:800;font-size:1.05rem;color:{cor};">{titulo}</div>'
        f'<div style="font-size:.9rem;opacity:.85;margin-top:.15rem;">{texto}</div>'
        '</div></div>'
    )


def _legenda_evolucao_html():

    def chip(cor, texto):
        return (
            f'<span style="display:inline-flex;align-items:center;gap:.35rem;'
            f'font-size:.74rem;opacity:.85;margin-right:1rem;">'
            f'<span style="width:11px;height:11px;border-radius:3px;background:{cor};'
            f'display:inline-block;"></span>{texto}</span>'
        )

    return (
        '<div style="margin:-.2rem 0 .2rem 0;">'
        f'{chip(COR_OK, "Dentro da meta")}'
        f'{chip(COR_ATENCAO, "Até 5 acima")}'
        f'{chip(COR_CRITICO, "Muito acima")}'
        f'{chip(COR_NEUTRA, "Mês sem meta")}'
        f'<span style="display:inline-flex;align-items:center;gap:.35rem;'
        f'font-size:.74rem;opacity:.85;">'
        f'<span style="width:18px;border-top:3px dashed {COR_META};display:inline-block;"></span>'
        'Meta</span></div>'
    )


def _figura_evolucao(df, cor_fonte, cor_grade):

    reclamacoes = [int(v) for v in df["Reclamações"]]
    metas = [int(v) for v in df["Meta"]]

    cores_barras = []

    for valor, meta in zip(reclamacoes, metas):

        if meta <= 0:
            cores_barras.append(COR_NEUTRA)
        else:
            cores_barras.append(_situacao(valor, meta)[0])

    topo = max(reclamacoes + metas + [1]) * 1.22

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["Mês"],
            y=reclamacoes,
            name="Reclamações",
            marker=dict(color=cores_barras),
            text=reclamacoes,
            textposition="outside",
            cliponaxis=False,
            customdata=metas,
            hovertemplate=(
                "%{x}<br>Reclamações: %{y}<br>Meta: %{customdata}<extra></extra>"
            ),
            showlegend=False
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Mês"],
            y=metas,
            name="Meta",
            mode="lines+markers",
            line=dict(color=COR_META, width=3, dash="dash"),
            marker=dict(size=9, line=dict(width=2, color="#0b1224")),
            hovertemplate="%{x}<br>Meta: %{y}<extra></extra>",
            showlegend=False
        )
    )

    fig.update_xaxes(
        type="category",
        title=None,
        showgrid=False
    )

    fig.update_yaxes(
        title=None,
        gridcolor=cor_grade,
        rangemode="tozero",
        range=[0, topo],
        zeroline=False
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=cor_fonte,
        height=380,
        bargap=0.38,
        hovermode="x unified",
        margin=dict(t=20, l=10, r=10, b=10)
    )

    return fig


# =====================================================
# CARD DA PESSOA (Análise Técnica)
# =====================================================

def _corpo_card_pessoa_html(nome, total_erros, contagem_tipos, cor, rotulo_status, ultima_data):

    tipo_mais_comum, qtd_mais_comum = contagem_tipos.most_common(1)[0]

    barras = ""

    for tipo, qtd in contagem_tipos.most_common(3):

        barras += _barra_horizontal(
            html.escape(str(tipo)),
            qtd,
            qtd_mais_comum,
            cor
        )

    rodape = (
        f'📅 Última ocorrência: {ultima_data.strftime("%d/%m/%Y")}'
        if ultima_data else "Sem data registrada"
    )

    return (
        # cabeçalho
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:.6rem;flex-wrap:wrap;">'
        '<div style="display:flex;align-items:center;gap:.75rem;min-width:0;">'
        f'<div style="width:52px;height:52px;border-radius:50%;flex-shrink:0;'
        f'background:linear-gradient(135deg,{cor},{cor}aa);display:flex;'
        'align-items:center;justify-content:center;font-size:1.5rem;'
        f'box-shadow:0 0 16px {cor}66;">👤</div>'
        f'<div style="font-size:1.2rem;font-weight:800;line-height:1.2;">{html.escape(nome)}</div>'
        '</div>'
        f'<span style="font-size:.74rem;font-weight:800;padding:.25rem .7rem;'
        f'border-radius:999px;background:{cor}26;color:{cor};border:1px solid {cor}66;'
        f'white-space:nowrap;">{rotulo_status}</span>'
        '</div>'

        # total de erros
        '<div style="display:flex;align-items:center;gap:1rem;margin-top:1rem;">'
        f'<div style="background:{cor}14;border:1px solid {cor}45;border-radius:.9rem;'
        'padding:.55rem 1rem;text-align:center;min-width:96px;">'
        f'<div style="font-size:.64rem;font-weight:800;letter-spacing:.4px;'
        f'text-transform:uppercase;color:{cor};">Total de erros</div>'
        f'<div style="font-size:2.2rem;font-weight:800;line-height:1.1;">{total_erros}</div></div>'
        '<div style="font-size:.78rem;opacity:.75;">no mês atual</div>'
        '</div>'

        # distribuição por tipo
        '<div style="margin-top:.9rem;font-size:.66rem;font-weight:800;'
        'letter-spacing:.5px;text-transform:uppercase;opacity:.55;">Por tipo de erro</div>'
        f'{barras}'

        # ponto de melhoria
        f'<div style="margin-top:1rem;background:{cor}18;border-left:4px solid {cor};'
        'padding:.55rem .8rem;border-radius:.5rem;font-size:.84rem;">'
        f'📌 Ponto de melhoria: <strong>{html.escape(str(tipo_mais_comum))}</strong> '
        f'({qtd_mais_comum}x). Recomenda-se reforço nesse ponto.</div>'

        # rodapé
        f'<div style="height:1px;background:{cor}33;margin:.9rem 0 .6rem 0;"></div>'
        f'<div style="font-size:.74rem;opacity:.7;">{rodape}</div>'
    )


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
    #
    # Meses que só têm chamados na Análise Técnica (sem meta salva)
    # chegam com atualizado_em = None, e o pandas converte esse None
    # em NaT. "if momento" não barra o NaT, por isso usamos
    # pd.notna() aqui.

    df["Atualizado em"] = df["Atualizado em"].apply(
        lambda momento: (
            estilos.horario_local(momento).strftime("%d/%m/%Y %H:%M")
            if pd.notna(momento) else ""
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

    st.markdown(CSS_SAC, unsafe_allow_html=True)

    ultimo = df.iloc[-1]

    reclamacoes = int(
        ultimo["Reclamações"]
    )

    meta = int(
        ultimo["Meta"]
    )

    margem = meta - reclamacoes

    cor_situacao, rotulo_situacao = _situacao(reclamacoes, meta)

    mes_rotulo = str(ultimo["Mês"])

    # variação em relação ao mês anterior
    if len(df) >= 2:

        anterior = df.iloc[-2]

        variacao = reclamacoes - int(anterior["Reclamações"])

        if variacao > 0:
            sub_indice = f"▲ +{variacao} vs {anterior['Mês']}"
        elif variacao < 0:
            sub_indice = f"▼ {variacao} vs {anterior['Mês']}".replace("-", "−")
        else:
            sub_indice = f"► igual a {anterior['Mês']}"

    else:

        sub_indice = mes_rotulo

    # ==================================
    # KPIs
    # ==================================

    kpis = [
        _kpi_html("Índice logístico", reclamacoes, sub_indice, "#f97316", "📢"),
        _kpi_html("Meta", meta, f"definida para {mes_rotulo}", COR_META, "🎯"),
        _kpi_html(
            "Margem",
            f"{margem:+d}",
            "ocorrências até a meta" if margem >= 0 else "acima da meta",
            COR_OK if margem >= 0 else COR_CRITICO,
            "📊"
        ),
        _kpi_html(
            "Status",
            rotulo_situacao,
            "dentro da meta" if reclamacoes <= meta else "meta ultrapassada",
            cor_situacao,
            "✅" if reclamacoes <= meta else "🚨"
        ),
    ]

    for coluna, kpi in zip(st.columns(4), kpis):

        with coluna:
            st.markdown(kpi, unsafe_allow_html=True)

    st.write("")

    # ==================================
    # EVOLUÇÃO MENSAL + META DO MÊS
    # ==================================

    cor_grade = "rgba(255,255,255,.08)" if tema == "escuro" else "rgba(0,0,0,.08)"

    col_grafico, col_meta = st.columns([2, 1])

    with col_grafico:

        with st.container(border=True, key="sac-painel-evolucao"):

            st.subheader(
                "Evolução Mensal"
            )

            st.markdown(_legenda_evolucao_html(), unsafe_allow_html=True)

            st.plotly_chart(
                _figura_evolucao(df, cor_fonte, cor_grade),
                width='stretch',
                config={"displayModeBar": False}
            )

    with col_meta:

        with st.container(border=True, key="sac-painel-meta"):

            st.subheader(
                "Indicador de Meta"
            )

            st.markdown(
                _card_meta_html(reclamacoes, meta, margem, mes_rotulo),
                unsafe_allow_html=True
            )

    st.write("")

    # ==================================
    # HISTÓRICO
    # ==================================

    st.subheader(
        "Histórico de Resultados"
    )

    st.markdown(
        _historico_html(df),
        unsafe_allow_html=True
    )

    st.divider()

    # ==================================
    # RESUMO IA
    # ==================================

    st.subheader(
        "Análise Inteligente"
    )

    if reclamacoes <= meta:

        st.markdown(
            _banner(
                COR_OK, "🏆", "Excelente resultado",
                f"O SAC está dentro da meta estabelecida, com margem de "
                f"{margem} ocorrência(s)."
            ),
            unsafe_allow_html=True
        )

    elif reclamacoes <= meta + 5:

        st.markdown(
            _banner(
                COR_ATENCAO, "⚠️", "Atenção",
                "O SAC está próximo do limite permitido. "
                "Recomenda-se acompanhamento."
            ),
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            _banner(
                COR_CRITICO, "🚨", "Alerta crítico",
                "O número de reclamações ultrapassou significativamente a meta."
            ),
            unsafe_allow_html=True
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

            if total_erros <= 1:

                cor = COR_OK
                rotulo_status = "✅ Poucas ocorrências"

            elif total_erros <= 3:

                cor = COR_ATENCAO
                rotulo_status = "⚠️ Atenção"

            else:

                cor = COR_CRITICO
                rotulo_status = "🚨 Reforço necessário"

            ultima_data = max(
                (erro["data_erro"] for erro in erros_pessoa),
                default=None
            )

            chave_card = f"card-analise-{gerar_chave_css(nome)}"

            st.markdown(
                f"""
                <style>
                .st-key-{chave_card} {{
                    background: linear-gradient(150deg, {cor}22, {cor}08 70%) !important;
                    border: 1px solid {cor}55 !important;
                    border-top: 4px solid {cor} !important;
                    border-radius: 1.1rem !important;
                    box-shadow: 0 10px 26px {cor}22;
                    transition: transform .18s ease;
                }}
                .st-key-{chave_card}:hover {{
                    transform: translateY(-3px);
                }}
                </style>
                """,
                unsafe_allow_html=True
            )

            with cols[indice % 3]:

                with st.container(border=True, key=chave_card):

                    st.markdown(
                        _corpo_card_pessoa_html(
                            nome,
                            total_erros,
                            contagem_tipos,
                            cor,
                            rotulo_status,
                            ultima_data
                        ),
                        unsafe_allow_html=True
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

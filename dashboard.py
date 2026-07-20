import streamlit as st
import banco
import pandas as pd
import re


def gerar_chave_css(texto):

    return re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        texto
    ).strip('-').lower()


# =====================================================
# TENDÊNCIA
# =====================================================

def gerar_tendencia(historico):

    if len(historico) < 2:
        return "➡️", "Sem histórico"

    atual = historico[0][0]
    anterior = historico[1][0]

    if atual > anterior:
        return "⬆️", "Melhorando"

    elif atual < anterior:
        return "⬇️", "Em queda"

    return "➡️", "Estável"


# =====================================================
# DASHBOARD
# =====================================================

def render():

    RUAS = [
        "Rua 01",
        "Rua 02",
        "Rua 03",
        "Rua 04",
        "Rua 05",
        "Rua 06",
        "Rua 07",
        "Rua 35&32",
        "Rua 33&34"
    ]

    notas = banco.ler_notas()
    duplas = banco.ler_duplas()

    st.title("📊 Dashboard Operacional")

    st.caption(
        "Monitoramento inteligente das equipes em tempo real."
    )

    st.divider()

    # =====================================================
    # KPIs
    # =====================================================

    media = round(sum(notas.values()) / len(notas), 2) if notas else 0

    excelencia = len(
        [n for n in notas.values() if n >= 4.8]
    )

    alertas = len(
        [n for n in notas.values() if n < 3]
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("📍 Ruas", len(RUAS))

    with c2:
        st.metric("⭐ Média Geral", media)

    with c3:
        st.metric("🏆 Excelência", excelencia)

    with c4:
        st.metric("🚨 Alertas", alertas)

    st.divider()

    # =====================================================
    # PAINEL OPERACIONAL
    # =====================================================

    st.subheader("🚨 Painel Operacional")

    for i in range(0, len(RUAS), 3):

        cols = st.columns(3)

        for j in range(3):

            if i + j >= len(RUAS):
                continue

            rua = RUAS[i + j]

            nota = notas.get(
                rua,
                0.0
            )

            dupla = duplas.get(
                rua,
                "Sem dupla cadastrada"
            )

            historico = banco.ler_historico_rua(
                rua,
                5
            )

            seta, tendencia = gerar_tendencia(
                historico
            )

            with cols[j]:

                if nota >= 4.8:

                    cor_fundo = "rgba(59,130,246,0.16)"
                    cor_borda = "#3b82f6"
                    rotulo_status = "🏆 Excelência"
                    tipo_alerta = "info"

                elif nota >= 4:

                    cor_fundo = "rgba(34,197,94,0.16)"
                    cor_borda = "#22c55e"
                    rotulo_status = "✅ Bom desempenho"
                    tipo_alerta = "success"

                elif nota >= 3:

                    cor_fundo = "rgba(245,158,11,0.16)"
                    cor_borda = "#f59e0b"
                    rotulo_status = "⚠️ Atenção"
                    tipo_alerta = "warning"

                else:

                    cor_fundo = "rgba(220,38,38,0.16)"
                    cor_borda = "#dc2626"
                    rotulo_status = "🚨 Crítico"
                    tipo_alerta = "error"

                chave_card = f"card-dash-{gerar_chave_css(rua)}"

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

                    st.markdown(
                        f"### 📍 {rua} {seta}"
                    )

                    st.caption(
                        f"👥 {dupla}"
                    )

                    if tipo_alerta == "success":

                        st.success(rotulo_status)

                    elif tipo_alerta == "info":

                        st.info(rotulo_status)

                    elif tipo_alerta == "warning":

                        st.warning(rotulo_status)

                    else:

                        st.error(rotulo_status)

                    st.metric(
                        "Nota Atual",
                        f"{nota:.1f}"
                    )

                    st.progress(
                        nota / 5
                    )

                    if historico:

                        ultimo_usuario = historico[0][3]

                        if ultimo_usuario:

                            st.caption(
                                f"👤 Última atualização por {ultimo_usuario}"
                            )

                        if tendencia == "Em queda":

                            st.warning(
                                "📉 Notas em queda para a dupla."
                            )

                        elif tendencia == "Melhorando":

                            st.success(
                                "📈 Notas em alta para a dupla."
                            )

                        elif tendencia == "Estável":

                            st.caption(
                                "➡️ Notas estáveis para a dupla."
                            )

                        else:

                            st.caption(
                                "🕐 Ainda sem tendência (poucas atualizações)."
                            )

                    else:

                        st.info(
                            "Aguardando histórico suficiente."
                        )

    st.divider()

    # =====================================================
    # RANKING DAS EQUIPES
    # =====================================================

    st.subheader("🏆 Ranking das Equipes")

    ranking = []

    for rua in RUAS:

        ranking.append(
            {
                "Rua": rua,
                "Nota": notas.get(rua, 0),
                "Equipe": duplas.get(rua, "-")
            }
        )

    df = pd.DataFrame(ranking)

    df = df.sort_values(
        by="Nota",
        ascending=False
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # =====================================================
    # TOP 3 EQUIPES
    # =====================================================

    st.subheader("🥇 Top 3 Equipes")

    top3 = df.head(3)

    c1, c2, c3 = st.columns(3)

    colunas = [
        c1,
        c2,
        c3
    ]

    medalhas = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for idx, (_, row) in enumerate(top3.iterrows()):

        with colunas[idx]:

            st.metric(
                f"{medalhas[idx]} {row['Rua']}",
                f"{row['Nota']:.1f}",
                row["Equipe"]
            )

    st.divider()

    # =====================================================
    # RESUMO INTELIGENTE
    # =====================================================

    st.subheader("🧠 Resumo Inteligente")

    if media >= 4.8:

        st.success(
            """
Sistema operando em nível de excelência.

As equipes apresentam desempenho acima
do padrão esperado.
"""
        )

    elif media >= 4:

        st.info(
            """
Operação dentro dos parâmetros esperados.

Manter acompanhamento contínuo.
"""
        )

    elif media >= 3:

        st.warning(
            """
Existem equipes que necessitam atenção.

Recomenda-se acompanhamento operacional.
"""
        )

    else:

        st.error(
            """
Necessária intervenção operacional imediata.

Existem indicadores críticos em operação.
"""
        )

    st.divider()

    st.caption(
        "Luxiz IA • Dashboard Operacional • Sprint 1"
    )

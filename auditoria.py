import streamlit as st
import banco
import estilos
import re
from collections import Counter


# =====================================================
# EMBLEMAS POR FUNÇÃO
# =====================================================

BADGES_FUNCAO = {
    "Conferente": "🔎",
    "Empilhador": "🏗️",
    "Assistente Logístico": "📦",
}

PREFIXOS_RESTRITOS = (
    "Conferente.",
    "Empilhador.",
    "Assistente.",
    "Recebimento."
)


def gerar_chave_css(texto):

    return re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        texto
    ).strip('-').lower()


def definir_visual(aproveitamento, total_pessoa):

    if not total_pessoa:

        return (
            "rgba(148,163,184,0.12)",
            "#64748b",
            "⏳ Sem dados"
        )

    if aproveitamento >= 90:

        return (
            "rgba(59,130,246,0.16)",
            "#3b82f6",
            "🏆 Excelência"
        )

    if aproveitamento >= 75:

        return (
            "rgba(34,197,94,0.16)",
            "#22c55e",
            "✅ Bom desempenho"
        )

    if aproveitamento >= 50:

        return (
            "rgba(245,158,11,0.16)",
            "#f59e0b",
            "⚠️ Atenção"
        )

    return (
        "rgba(220,38,38,0.16)",
        "#dc2626",
        "🚨 Crítico"
    )


def render():

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    estilos.cabecalho_pagina(
        "🎯",
        "Auditoria de Atividades",
        "Acompanhamento de acertos e erros por pessoa, registrados pela auditoria operacional.",
        cor="#ec4899"
    )

    st.divider()

    registros = banco.ler_auditoria(armazem_id_atual)

    # =====================================================
    # RESTRIÇÃO DE VISÃO (mesmo esquema do SAC/Análise Técnica)
    # =====================================================

    usuario_atual = st.session_state.get("usuario", "")

    nome_restrito = None

    if usuario_atual.startswith(PREFIXOS_RESTRITOS):

        nome_restrito = usuario_atual.split(".", 1)[1].strip().title()

    # =====================================================
    # AGRUPA POR PESSOA
    # =====================================================

    por_pessoa = {}

    for registro in registros:

        nome_normalizado = registro["nome"].strip().title()

        por_pessoa.setdefault(
            nome_normalizado,
            []
        ).append(registro)

    if nome_restrito:

        por_pessoa = {
            nome: regs for nome, regs in por_pessoa.items()
            if nome == nome_restrito
        }

    # =====================================================
    # KPIs GERAIS
    # =====================================================

    total_acertos_geral = sum(r["qtd_acertos"] or 0 for r in registros)
    total_erros_geral = sum(r["qtd_erros"] or 0 for r in registros)
    total_geral = total_acertos_geral + total_erros_geral

    aproveitamento_geral = (
        (total_acertos_geral / total_geral) * 100
        if total_geral else 0
    )

    if not nome_restrito:

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("👥 Pessoas Auditadas", len(por_pessoa))

        with c2:
            st.metric("✅ Acertos", total_acertos_geral)

        with c3:
            st.metric("❌ Erros", total_erros_geral)

        with c4:
            st.metric("📊 Aproveitamento", f"{aproveitamento_geral:.0f}%")

        st.divider()

    # =====================================================
    # CARDS POR PESSOA
    # =====================================================

    if not por_pessoa:

        if nome_restrito:

            st.info(
                "Nenhum registro de auditoria encontrado para você ainda."
            )

        else:

            st.info(
                "Nenhum registro de auditoria cadastrado ainda."
            )

        return

    nomes = sorted(por_pessoa.keys())

    cols = st.columns(3)

    for indice, nome in enumerate(nomes):

        registros_pessoa = por_pessoa[nome]

        total_acertos = sum(r["qtd_acertos"] or 0 for r in registros_pessoa)
        total_erros = sum(r["qtd_erros"] or 0 for r in registros_pessoa)
        total_pessoa = total_acertos + total_erros

        aproveitamento = (
            (total_acertos / total_pessoa) * 100
            if total_pessoa else 0
        )

        contagem_funcoes = Counter(
            r["funcao"] for r in registros_pessoa if r.get("funcao")
        )

        funcao_principal = (
            contagem_funcoes.most_common(1)[0][0]
            if contagem_funcoes else None
        )

        emblema = BADGES_FUNCAO.get(funcao_principal, "🧑")

        cor_fundo, cor_borda, rotulo_status = definir_visual(
            aproveitamento,
            total_pessoa
        )

        chave_card = f"card-audit-{gerar_chave_css(nome)}"

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
                        width:56px;height:56px;border-radius:50%;
                        background:{cor_borda};
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.6rem;margin-bottom:.4rem;
                        box-shadow:0 0 14px {cor_borda}88;
                    ">{emblema}</div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"### {nome}"
                )

                st.caption(
                    funcao_principal or "Função não informada"
                )

                if total_pessoa:

                    if cor_borda == "#3b82f6":
                        st.info(rotulo_status)
                    elif cor_borda == "#22c55e":
                        st.success(rotulo_status)
                    elif cor_borda == "#f59e0b":
                        st.warning(rotulo_status)
                    else:
                        st.error(rotulo_status)

                else:

                    st.caption(rotulo_status)

                col_a, col_b = st.columns(2)

                with col_a:
                    st.metric("✅ Acertos", total_acertos)

                with col_b:
                    st.metric("❌ Erros", total_erros)

                st.progress(
                    aproveitamento / 100 if total_pessoa else 0
                )

                if total_pessoa:

                    st.caption(
                        f"**{aproveitamento:.0f}%** de aproveitamento"
                    )

                else:

                    st.caption(
                        "Sem dados suficientes."
                    )

                with st.popover("📋 Saber mais"):

                    st.caption(
                        f"Histórico de {nome}:"
                    )

                    registros_ordenados = sorted(
                        registros_pessoa,
                        key=lambda r: r["data_atividade"],
                        reverse=True
                    )

                    with st.container(height=250):

                        for registro in registros_ordenados:

                            badge_linha = BADGES_FUNCAO.get(
                                registro.get("funcao"),
                                ""
                            )

                            st.caption(
                                f"{badge_linha} {registro.get('funcao', '')} • "
                                f"{registro['data_atividade'].strftime('%d/%m/%Y')} • "
                                f"✅ {registro['qtd_acertos']} / "
                                f"❌ {registro['qtd_erros']}"
                            )

                            if registro.get("descricao"):

                                st.caption(
                                    f"   ↳ _{registro['descricao']}_"
                                )

    st.divider()

    st.caption(
        "Luxiz IA • Auditoria de Atividades"
    )
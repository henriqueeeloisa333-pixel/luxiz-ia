import html
import math
import re
from collections import Counter

import streamlit as st
import banco
import estilos


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
            estilos.cor_fundo_cartao("rgba(148,163,184,0.12)"),
            "#64748b",
            "⏳ Sem dados"
        )

    if aproveitamento >= 90:

        return (
            estilos.cor_fundo_cartao("rgba(59,130,246,0.16)"),
            "#3b82f6",
            "🏆 Excelência"
        )

    if aproveitamento >= 75:

        return (
            estilos.cor_fundo_cartao("rgba(34,197,94,0.16)"),
            "#22c55e",
            "✅ Bom desempenho"
        )

    if aproveitamento >= 50:

        return (
            estilos.cor_fundo_cartao("rgba(245,158,11,0.16)"),
            "#f59e0b",
            "⚠️ Atenção"
        )

    return (
        estilos.cor_fundo_cartao("rgba(220,38,38,0.16)"),
        "#dc2626",
        "🚨 Crítico"
    )


# =====================================================
# CARD DA PESSOA (visual profissional)
# =====================================================

COR_ACERTO = "#22c55e"
COR_ERRO = "#ef4444"


def _visual_card(aproveitamento, total_pessoa):

    if not total_pessoa:
        return "#64748b", "⏳ Sem dados"

    if aproveitamento >= 90:
        return "#3b82f6", "🏆 Excelência"

    if aproveitamento >= 75:
        return "#22c55e", "✅ Bom desempenho"

    if aproveitamento >= 50:
        return "#f59e0b", "⚠️ Atenção"

    return "#ef4444", "🚨 Crítico"


def _anel_svg(proporcao, texto_centro, texto_baixo, cor):

    raio = 42
    circunferencia = 2 * math.pi * raio

    proporcao = max(0.0, min(proporcao, 1.0))

    deslocamento = circunferencia * (1 - proporcao)

    return (
        '<svg width="108" height="108" viewBox="0 0 100 100" '
        'style="flex-shrink:0;">'
        f'<circle cx="50" cy="50" r="{raio}" fill="none" stroke="{cor}" '
        'stroke-opacity=".18" stroke-width="9"/>'
        f'<circle cx="50" cy="50" r="{raio}" fill="none" stroke="{cor}" '
        'stroke-width="9" stroke-linecap="round" '
        f'stroke-dasharray="{circunferencia:.1f}" '
        f'stroke-dashoffset="{deslocamento:.1f}" '
        'transform="rotate(-90 50 50)"/>'
        f'<text x="50" y="50" text-anchor="middle" dominant-baseline="middle" '
        f'font-size="25" font-weight="800" fill="{cor}">{texto_centro}</text>'
        f'<text x="50" y="71" text-anchor="middle" font-size="8.5" '
        f'fill="currentColor" fill-opacity=".6">{texto_baixo}</text>'
        '</svg>'
    )


def _sparkline_svg(valores, cor):

    if len(valores) < 2:
        return ""

    largura, altura, margem = 130, 40, 6

    minimo, maximo = min(valores), max(valores)

    if maximo - minimo < 0.01:
        minimo, maximo = minimo - 5, maximo + 5

    pontos = []

    for indice, valor in enumerate(valores):

        x = margem + indice * (largura - 2 * margem) / (len(valores) - 1)

        y = altura - margem - (valor - minimo) / (maximo - minimo) * (altura - 2 * margem)

        pontos.append((x, y))

    linha = " ".join(f"{x:.1f},{y:.1f}" for x, y in pontos)

    area = f"{pontos[0][0]:.1f},{altura} {linha} {pontos[-1][0]:.1f},{altura}"

    bolinhas = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3.6 if k == len(pontos) - 1 else 2.2}" '
        f'fill="{cor}"/>'
        for k, (x, y) in enumerate(pontos)
    )

    return (
        f'<svg width="{largura}" height="{altura}" '
        f'viewBox="0 0 {largura} {altura}" style="display:block;">'
        f'<polygon points="{area}" fill="{cor}" fill-opacity=".14"/>'
        f'<polyline points="{linha}" fill="none" stroke="{cor}" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        f'{bolinhas}</svg>'
    )


def _tile(rotulo, valor, cor):

    return (
        f'<div style="flex:1;min-width:92px;background:{cor}14;'
        f'border:1px solid {cor}45;border-radius:.8rem;padding:.5rem .75rem;">'
        f'<div style="font-size:.66rem;font-weight:800;letter-spacing:.4px;'
        f'text-transform:uppercase;color:{cor};">{rotulo}</div>'
        f'<div style="font-size:1.55rem;font-weight:800;line-height:1.15;">{valor}</div>'
        '</div>'
    )


def _corpo_card_html(
    nome, funcao, emblema, acertos, erros, aproveitamento,
    cor, rotulo_status, serie, qtd_registros, ultima_data
):

    total = acertos + erros

    if total:
        proporcao = aproveitamento / 100
        centro = f"{aproveitamento:.0f}%"
    else:
        proporcao = 0
        centro = "—"

    # tendência entre as duas últimas auditorias
    if len(serie) >= 2:

        delta = serie[-1] - serie[-2]

        if delta >= 2:
            cor_tend, chip_tend = "#22c55e", f"▲ +{delta:.0f} pts na última"
        elif delta <= -2:
            cor_tend, chip_tend = "#ef4444", f"▼ −{abs(delta):.0f} pts na última"
        else:
            cor_tend, chip_tend = "#94a3b8", "► estável"

    else:

        cor_tend, chip_tend = "#94a3b8", "🕐 sem tendência ainda"

    sparkline = _sparkline_svg(serie, cor)

    sparkline_html = (
        '<div style="margin-top:.5rem;">'
        f'{sparkline}'
        '<div style="font-size:.66rem;opacity:.55;margin-top:.1rem;">'
        f'aproveitamento das últimas {len(serie)} auditorias</div></div>'
        if sparkline else ""
    )

    if total:
        barra_html = (
            '<div style="margin-top:1rem;">'
            '<div style="display:flex;height:9px;border-radius:999px;'
            f'overflow:hidden;background:{COR_ERRO};">'
            f'<div style="width:{aproveitamento:.1f}%;background:{COR_ACERTO};"></div>'
            '</div>'
            '<div style="display:flex;justify-content:space-between;'
            'font-size:.68rem;opacity:.65;margin-top:.25rem;">'
            f'<span>{acertos} acerto(s)</span><span>{erros} erro(s)</span></div>'
            '</div>'
        )
    else:
        barra_html = ""

    if ultima_data:
        rodape = (
            f'📅 Última auditoria: {ultima_data.strftime("%d/%m/%Y")}'
            f' · {qtd_registros} registro(s)'
        )
    else:
        rodape = "Nenhuma auditoria registrada"

    return (
        # cabeçalho
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:.6rem;flex-wrap:wrap;">'
        '<div style="display:flex;align-items:center;gap:.75rem;min-width:0;">'
        f'<div style="width:52px;height:52px;border-radius:50%;flex-shrink:0;'
        f'background:linear-gradient(135deg,{cor},{cor}aa);display:flex;'
        'align-items:center;justify-content:center;font-size:1.5rem;'
        f'box-shadow:0 0 16px {cor}66;">{emblema}</div>'
        '<div style="min-width:0;">'
        f'<div style="font-size:1.2rem;font-weight:800;line-height:1.2;">{html.escape(nome)}</div>'
        f'<div style="font-size:.8rem;opacity:.7;margin-top:.1rem;">{html.escape(funcao or "Função não informada")}</div>'
        '</div></div>'
        f'<span style="font-size:.74rem;font-weight:800;padding:.25rem .7rem;'
        f'border-radius:999px;background:{cor}26;color:{cor};border:1px solid {cor}66;'
        f'white-space:nowrap;">{rotulo_status}</span>'
        '</div>'

        # anel + acertos/erros
        '<div style="display:flex;align-items:center;gap:1rem;margin-top:1rem;flex-wrap:wrap;">'
        f'{_anel_svg(proporcao, centro, "aproveitamento", cor)}'
        '<div style="flex:1;min-width:150px;">'
        '<div style="display:flex;gap:.6rem;flex-wrap:wrap;">'
        f'{_tile("✅ Acertos", acertos, COR_ACERTO)}'
        f'{_tile("❌ Erros", erros, COR_ERRO)}'
        '</div>'
        f'<div style="margin-top:.6rem;"><span style="display:inline-block;font-size:.72rem;'
        f'font-weight:700;padding:.2rem .6rem;border-radius:999px;'
        f'background:{cor_tend}1f;color:{cor_tend};border:1px solid {cor_tend}55;">'
        f'{chip_tend}</span></div>'
        '</div></div>'

        f'{barra_html}'
        f'{sparkline_html}'

        # rodapé
        f'<div style="height:1px;background:{cor}33;margin:.9rem 0 .6rem 0;"></div>'
        f'<div style="font-size:.74rem;opacity:.7;">{rodape}</div>'
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

    # Antes: extraía "nome_restrito" do login (ex.: "Alexandre") e
    # comparava exato com o nome do registro. Como o nome do
    # registro agora pode vir completo pelo Perfil (ex.: "Alexandre
    # Vasques"), essa comparação exata deixava de bater. Agora só
    # guardamos QUE o acesso é restrito — quem bate com quem é
    # decidido mais abaixo por banco.pessoa_pertence_ao_usuario.
    acesso_restrito_auditoria = usuario_atual.startswith(PREFIXOS_RESTRITOS)

    # =====================================================
    # AGRUPA POR PESSOA
    # =====================================================

    por_pessoa = {}

    for registro in registros:

        # Antes: registro["nome"].strip().title() — isso deixava
        # "Alexandre" e "Alexandre Vasques" em cards separados. Agora
        # usa o Perfil (quando existir) para juntar os dois num card
        # só, já com o nome completo certo.
        nome_normalizado = banco.normalizar_nome_pessoa(
            registro["nome"], armazem_id_atual
        )

        por_pessoa.setdefault(
            nome_normalizado,
            []
        ).append(registro)

    if acesso_restrito_auditoria:

        por_pessoa = {
            nome: regs for nome, regs in por_pessoa.items()
            if banco.pessoa_pertence_ao_usuario(
                nome, usuario_atual, armazem_id_atual
            )
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

    if not acesso_restrito_auditoria:

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

        if acesso_restrito_auditoria:

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

        cor, rotulo_status = _visual_card(
            aproveitamento,
            total_pessoa
        )

        registros_cronologicos = sorted(
            registros_pessoa,
            key=lambda r: r["data_atividade"]
        )

        # aproveitamento de cada auditoria, da mais antiga para a mais nova
        serie = []

        for r in registros_cronologicos:

            acertos_r = r["qtd_acertos"] or 0
            erros_r = r["qtd_erros"] or 0

            if acertos_r + erros_r > 0:
                serie.append(acertos_r / (acertos_r + erros_r) * 100)

        serie = serie[-6:]

        chave_card = f"card-audit-{gerar_chave_css(nome)}"

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
                    _corpo_card_html(
                        nome,
                        funcao_principal,
                        emblema,
                        total_acertos,
                        total_erros,
                        aproveitamento,
                        cor,
                        rotulo_status,
                        serie,
                        len(registros_pessoa),
                        registros_cronologicos[-1]["data_atividade"]
                        if registros_cronologicos else None
                    ),
                    unsafe_allow_html=True
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

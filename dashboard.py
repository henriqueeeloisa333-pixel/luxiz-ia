import html
import math

import streamlit as st
import banco
import estilos
import avaliacoes
import pandas as pd
import re

from datetime import timezone
from zoneinfo import ZoneInfo


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
# CARD DAS RUAS (visual profissional)
# =====================================================

CSS_CARD_RUA = """
<style>
.lx-rua-card{
    border-radius:1.1rem;
    overflow:hidden;
    margin-bottom:1rem;
    transition:transform .18s ease, box-shadow .18s ease;
}
.lx-rua-card:hover{
    transform:translateY(-3px);
}
</style>
"""

PALETA_AVATARES = ["#3b82f6", "#a855f7", "#ec4899", "#06b6d4"]


def _nivel_nota(nota):

    if nota >= 4.8:
        return "#3b82f6", "🏆 Excelência"

    if nota >= 4:
        return "#22c55e", "✅ Bom desempenho"

    if nota >= 3:
        return "#f59e0b", "⚠️ Atenção"

    return "#ef4444", "🚨 Crítico"


def _fmt1(valor):

    return f"{valor:.1f}".replace(".", ",")


def _iniciais(nome):

    partes = nome.split()

    if len(partes) >= 2:
        return (partes[0][0] + partes[1][0]).upper()

    return nome[:2].upper()


def _avatares_html(dupla):

    partes = avaliacoes._partes_da_dupla(dupla)

    if not partes:

        return (
            '<span style="opacity:.6;font-size:.82rem;">'
            'Sem dupla cadastrada</span>'
        )

    avatares = ""

    for indice, nome in enumerate(partes[:3]):

        cor = PALETA_AVATARES[indice % len(PALETA_AVATARES)]

        avatares += (
            f'<div style="width:30px;height:30px;border-radius:50%;'
            f'background:{cor};color:#fff;display:flex;align-items:center;'
            'justify-content:center;font-size:.7rem;font-weight:800;'
            'border:2px solid rgba(15,23,42,.45);flex-shrink:0;'
            f'margin-left:{0 if indice == 0 else -8}px;">'
            f'{html.escape(_iniciais(nome))}</div>'
        )

    return (
        '<div style="display:flex;align-items:center;gap:.6rem;min-width:0;">'
        f'<div style="display:flex;align-items:center;">{avatares}</div>'
        f'<div style="font-size:.85rem;opacity:.85;min-width:0;'
        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
        f'{html.escape(dupla)}</div></div>'
    )


def _anel_svg(nota, cor):

    raio = 42
    circunferencia = 2 * math.pi * raio

    proporcao = max(0.0, min(nota / 5, 1.0))

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
        f'font-size="27" font-weight="800" fill="{cor}">{_fmt1(nota)}</text>'
        '<text x="50" y="71" text-anchor="middle" font-size="9" '
        'fill="currentColor" fill-opacity=".6">de 5,0</text>'
        '</svg>'
    )


def _sparkline_svg(valores, cor):

    if len(valores) < 2:
        return ""

    largura, altura, margem = 130, 40, 6

    minimo, maximo = min(valores), max(valores)

    if maximo - minimo < 0.01:
        minimo, maximo = minimo - 0.5, maximo + 0.5

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


def _card_rua_html(rua, nota, dupla, historico, posicao, total):

    cor, rotulo_status = _nivel_nota(nota)

    # histórico vem do mais novo para o mais antigo
    valores = [
        float(item[0]) for item in reversed(historico)
        if item[0] is not None
    ]

    if len(valores) >= 2:

        delta = valores[-1] - valores[-2]

        if delta > 0.04:
            cor_tend, chip_tend = "#22c55e", f"▲ +{_fmt1(delta)} em alta"
        elif delta < -0.04:
            cor_tend, chip_tend = "#ef4444", f"▼ {_fmt1(delta).replace('-', '−')} em queda"
        else:
            cor_tend, chip_tend = "#94a3b8", "► estável"

    else:

        cor_tend, chip_tend = "#94a3b8", "🕐 sem tendência ainda"

    sparkline = _sparkline_svg(valores, cor)

    sparkline_html = (
        '<div style="margin-top:.55rem;">'
        f'{sparkline}'
        f'<div style="font-size:.66rem;opacity:.55;margin-top:.1rem;">'
        f'últimas {len(valores)} notas</div></div>'
        if sparkline else ""
    )

    rodape = "Aguardando a primeira atualização"

    if historico and historico[0][3]:

        rodape = f"👤 {html.escape(str(historico[0][3]))}"

        data_ultima = historico[0][2]

        if data_ultima:

            horario_local = data_ultima.replace(
                tzinfo=timezone.utc
            ).astimezone(
                ZoneInfo("America/Campo_Grande")
            )

            rodape += f" · {horario_local.strftime('%d/%m/%Y %H:%M')}"

    return (
        f'<div class="lx-rua-card" style="'
        f'background:linear-gradient(150deg,{cor}22,{cor}08 70%);'
        f'border:1px solid {cor}55;box-shadow:0 10px 26px {cor}22;">'
        f'<div style="height:4px;background:linear-gradient(90deg,{cor},{cor}55);"></div>'
        '<div style="padding:1.05rem 1.2rem 1rem 1.2rem;">'

        # cabeçalho: rua + posição no ranking
        '<div style="display:flex;justify-content:space-between;'
        'align-items:center;gap:.6rem;">'
        '<div style="display:flex;align-items:center;gap:.65rem;">'
        f'<div style="width:38px;height:38px;border-radius:11px;background:{cor}26;'
        'display:flex;align-items:center;justify-content:center;font-size:1.15rem;">📍</div>'
        f'<div style="font-size:1.3rem;font-weight:800;line-height:1.1;">{html.escape(rua)}</div>'
        '</div>'
        '<div style="font-size:.7rem;font-weight:800;letter-spacing:.3px;'
        'padding:.22rem .6rem;border-radius:999px;background:rgba(148,163,184,.16);'
        f'border:1px solid rgba(148,163,184,.3);white-space:nowrap;">🏅 {posicao}º de {total}</div>'
        '</div>'

        # dupla
        f'<div style="margin-top:.85rem;">{_avatares_html(dupla)}</div>'

        # nota + status + tendência
        '<div style="display:flex;align-items:center;gap:1rem;margin-top:1rem;flex-wrap:wrap;">'
        f'{_anel_svg(nota, cor)}'
        '<div style="flex:1;min-width:140px;">'
        f'<div style="display:inline-block;font-size:.78rem;font-weight:800;'
        f'padding:.28rem .75rem;border-radius:999px;background:{cor}26;color:{cor};'
        f'border:1px solid {cor}66;">{rotulo_status}</div>'
        f'<div style="margin-top:.5rem;"><span style="display:inline-block;font-size:.74rem;'
        f'font-weight:700;padding:.2rem .6rem;border-radius:999px;'
        f'background:{cor_tend}1f;color:{cor_tend};border:1px solid {cor_tend}55;">'
        f'{chip_tend}</span></div>'
        f'{sparkline_html}'
        '</div></div>'

        # rodapé
        f'<div style="height:1px;background:{cor}33;margin:1rem 0 .7rem 0;"></div>'
        f'<div style="font-size:.74rem;opacity:.7;">{rodape}</div>'
        '</div></div>'
    )


# =====================================================
# DASHBOARD
# =====================================================

def render():

    estilos.exibir_notificacao_pendente()

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    RUAS = banco.listar_ruas(armazem_id_atual)

    notas = banco.ler_notas(armazem_id_atual)
    duplas = banco.ler_duplas(armazem_id_atual)

    estilos.cabecalho_pagina(
        "📊",
        "Dashboard Operacional",
        "Monitoramento inteligente das equipes em tempo real.",
        cor="#3b82f6"
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
    # AVALIAÇÕES DE RUAS (autoavaliação + conferência)
    # =====================================================
    # Separador/Conferente: pedem a avaliação da rua que organizaram.
    # Gestão/Fundador: aprovam ou ajustam a nota (com motivo).
    # Para os demais perfis, essa seção não aparece.

    avaliacoes.render(armazem_id_atual)

    # =====================================================
    # PAINEL OPERACIONAL
    # =====================================================

    st.subheader("🚨 Painel Operacional")

    st.markdown(CSS_CARD_RUA, unsafe_allow_html=True)

    ordem_ranking = sorted(
        RUAS,
        key=lambda nome_rua: notas.get(nome_rua, 0),
        reverse=True
    )

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

            dupla = duplas.get(rua) or ""

            historico = banco.ler_historico_rua(
                rua,
                armazem_id_atual,
                5
            )

            with cols[j]:

                st.markdown(
                    _card_rua_html(
                        rua,
                        nota,
                        dupla,
                        historico,
                        ordem_ranking.index(rua) + 1,
                        len(RUAS)
                    ),
                    unsafe_allow_html=True
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
        width='stretch',
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

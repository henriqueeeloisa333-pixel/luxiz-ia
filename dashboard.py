import html
import math

import streamlit as st
import banco
import estilos
import avaliacoes
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
# RANKING E PÓDIO (visual profissional)
# =====================================================

MEDALHAS_PODIO = {
    1: ("#facc15", "🥇"),
    2: ("#cbd5e1", "🥈"),
    3: ("#d97706", "🥉"),
}

CSS_RANKING = """
<style>
.lx-rank-row{
    transition:transform .15s ease;
}
.lx-rank-row:hover{
    transform:translateX(3px);
}
</style>
"""

GRADE_RANKING = (
    "grid-template-columns:56px 130px minmax(190px,1.3fr) "
    "minmax(200px,1.5fr) 150px;"
)


def _ranking_html(ordenadas, notas, duplas, posicoes):

    cabecalho = (
        f'<div style="display:grid;{GRADE_RANKING}gap:.9rem;'
        'padding:0 1rem .4rem 1rem;font-size:.66rem;font-weight:800;'
        'letter-spacing:.5px;text-transform:uppercase;opacity:.55;">'
        '<div>Pos.</div><div>Rua</div><div>Equipe</div>'
        '<div>Desempenho</div><div>Situação</div></div>'
    )

    linhas = ""

    for rua in ordenadas:

        nota = notas.get(rua, 0.0)

        dupla = duplas.get(rua) or ""

        cor, rotulo = _nivel_nota(nota)

        posicao = posicoes[rua]

        if posicao in MEDALHAS_PODIO:

            cor_pos, emblema = MEDALHAS_PODIO[posicao]
            tamanho_emblema = "1.25rem"

        else:

            cor_pos, emblema = "#64748b", f"{posicao}º"
            tamanho_emblema = ".82rem"

        proporcao = max(0.0, min(nota / 5 * 100, 100))

        linhas += (
            f'<div class="lx-rank-row" style="display:grid;{GRADE_RANKING}'
            'gap:.9rem;align-items:center;padding:.7rem 1rem;margin-bottom:.5rem;'
            'border-radius:.9rem;'
            f'background:linear-gradient(100deg,{cor_pos}14,{cor}08 60%);'
            f'border:1px solid {cor}30;border-left:5px solid {cor_pos};">'

            f'<div style="width:40px;height:40px;border-radius:50%;'
            f'background:{cor_pos}22;border:2px solid {cor_pos};display:flex;'
            'align-items:center;justify-content:center;font-weight:800;'
            f'font-size:{tamanho_emblema};">{emblema}</div>'

            f'<div style="font-weight:800;font-size:1rem;">📍 {html.escape(rua)}</div>'

            f'<div>{_avatares_html(dupla)}</div>'

            '<div style="display:flex;align-items:center;gap:.7rem;">'
            f'<div style="flex:1;height:9px;border-radius:999px;background:{cor}22;overflow:hidden;">'
            f'<div style="width:{proporcao:.1f}%;height:100%;border-radius:999px;'
            f'background:linear-gradient(90deg,{cor}99,{cor});"></div></div>'
            f'<div style="font-weight:800;font-size:1.05rem;color:{cor};'
            f'min-width:34px;text-align:right;">{_fmt1(nota)}</div>'
            '</div>'

            f'<div><span style="display:inline-block;font-size:.72rem;font-weight:800;'
            f'padding:.22rem .65rem;border-radius:999px;background:{cor}26;color:{cor};'
            f'border:1px solid {cor}66;white-space:nowrap;">{rotulo}</span></div>'

            '</div>'
        )

    return (
        '<div style="overflow-x:auto;">'
        f'<div style="min-width:760px;">{cabecalho}{linhas}</div></div>'
    )


def _podio_html(top):
    """top: lista de (rua, nota, dupla) já ordenada, no máximo 3 itens."""

    alturas = {1: 86, 2: 60, 3: 42}

    colunas = ""

    # ordem visual de um pódio: 2º, 1º, 3º
    for lugar in (2, 1, 3):

        if lugar > len(top):
            continue

        rua, nota, dupla = top[lugar - 1]

        cor, medalha = MEDALHAS_PODIO[lugar]

        coroa = (
            '<div style="font-size:1.6rem;line-height:1;margin-bottom:.25rem;">👑</div>'
            if lugar == 1 else
            '<div style="height:1.85rem;"></div>'
        )

        brilho = 34 if lugar == 1 else 18

        colunas += (
            '<div style="flex:1;min-width:210px;max-width:320px;'
            'display:flex;flex-direction:column;">'
            f'<div style="text-align:center;">{coroa}</div>'

            f'<div style="background:linear-gradient(160deg,{cor}26,{cor}08 70%);'
            f'border:1px solid {cor}66;border-bottom:none;border-radius:1rem 1rem 0 0;'
            f'padding:1.1rem 1rem;text-align:center;box-shadow:0 0 {brilho}px {cor}33;">'

            f'<div style="width:60px;height:60px;margin:0 auto;border-radius:50%;'
            f'background:{cor}26;border:2px solid {cor};display:flex;align-items:center;'
            f'justify-content:center;font-size:1.9rem;box-shadow:0 0 18px {cor}66;">{medalha}</div>'

            f'<div style="font-size:1.3rem;font-weight:800;margin-top:.6rem;">'
            f'📍 {html.escape(rua)}</div>'

            f'<div style="display:flex;justify-content:center;margin-top:.55rem;">'
            f'{_avatares_html(dupla)}</div>'

            f'<div style="display:inline-block;margin-top:.8rem;background:{cor};'
            'color:#1f2937;font-weight:800;font-size:.95rem;padding:.3rem .85rem;'
            f'border-radius:999px;">⭐ {_fmt1(nota)}</div>'
            '</div>'

            f'<div style="height:{alturas[lugar]}px;'
            f'background:linear-gradient(180deg,{cor}55,{cor}1a);'
            f'border:1px solid {cor}66;border-top:none;border-radius:0 0 .8rem .8rem;'
            'display:flex;align-items:center;justify-content:center;'
            f'font-size:2.2rem;font-weight:900;color:{cor};">{lugar}º</div>'
            '</div>'
        )

    return (
        '<div style="display:flex;justify-content:center;align-items:flex-end;'
        f'gap:1rem;flex-wrap:wrap;">{colunas}</div>'
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

    # posição com empate: ruas com a mesma nota dividem a mesma colocação
    posicoes = {
        nome_rua: 1 + sum(
            1 for outra in RUAS
            if notas.get(outra, 0) > notas.get(nome_rua, 0)
        )
        for nome_rua in RUAS
    }

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
                        posicoes[rua],
                        len(RUAS)
                    ),
                    unsafe_allow_html=True
                )

    st.divider()

    # =====================================================
    # RANKING DAS EQUIPES
    # =====================================================

    st.subheader("🏆 Ranking das Equipes")

    if not RUAS:

        st.info("Nenhuma rua cadastrada ainda.")

    else:

        st.markdown(CSS_RANKING, unsafe_allow_html=True)

        st.markdown(
            _ranking_html(ordem_ranking, notas, duplas, posicoes),
            unsafe_allow_html=True
        )

    st.divider()

    # =====================================================
    # TOP 3 EQUIPES
    # =====================================================

    st.subheader("🥇 Top 3 Equipes")

    top3 = [
        (nome_rua, notas.get(nome_rua, 0.0), duplas.get(nome_rua) or "")
        for nome_rua in ordem_ranking
        if notas.get(nome_rua, 0) > 0
    ][:3]

    if top3:

        st.markdown(
            _podio_html(top3),
            unsafe_allow_html=True
        )

    else:

        st.info("Ainda não há notas lançadas para montar o pódio.")

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

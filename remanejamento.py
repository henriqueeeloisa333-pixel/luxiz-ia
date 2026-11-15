import html

import streamlit as st
import banco
import estilos
import re

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def gerar_chave_css(texto):

    return re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        texto
    ).strip('-').lower()


DIAS_SEMANA_ABREV = [
    "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"
]


def agendamento_esta_ativo(agendamento, agora):

    """
    Decide se uma doca/prioridade agendada deve estar no painel
    NESTE exato momento, olhando o dia da semana (0=Segunda ...
    6=Domingo, igual ao weekday() do Python) e a janela de horário
    cadastrada. Cobre também janelas que passam da meia-noite
    (ex.: 22:00 às 02:00).
    """

    if agora.weekday() not in (agendamento["dias_semana"] or []):
        return False

    hora_atual = agora.time()
    inicio = agendamento["hora_inicio"]
    fim = agendamento["hora_fim"]

    if inicio <= fim:
        return inicio <= hora_atual < fim

    return hora_atual >= inicio or hora_atual < fim


def descricao_janela(agendamento):

    dias = sorted(agendamento["dias_semana"] or [])

    if dias == [0, 1, 2, 3, 4]:
        texto_dias = "Seg a Sex"

    elif dias == list(range(7)):
        texto_dias = "Todos os dias"

    else:
        texto_dias = ", ".join(DIAS_SEMANA_ABREV[d] for d in dias)

    return (
        f"⏰ {agendamento['hora_inicio'].strftime('%H:%M')} às "
        f"{agendamento['hora_fim'].strftime('%H:%M')} • {texto_dias}"
    )


def janela_horario(agendamento):

    # Versão enxuta (só o horário, sem os dias da semana) usada no
    # card do painel — os dias ficam só na tela de administração,
    # onde faz sentido conferir o que foi configurado.

    return (
        f"⏰ {agendamento['hora_inicio'].strftime('%H:%M')} às "
        f"{agendamento['hora_fim'].strftime('%H:%M')}"
    )


# =====================================================
# CARDS DO PAINEL (visual profissional)
# =====================================================

CSS_REMANEJAMENTO = """
<style>
@keyframes luxizPulsoSuave {
    0%   { box-shadow: 0 0 0 0 var(--pulso-cor); }
    70%  { box-shadow: 0 0 0 14px rgba(0,0,0,0); }
    100% { box-shadow: 0 0 0 0 rgba(0,0,0,0); }
}
.lx-reman-card {
    border-radius: 1.1rem;
    overflow: hidden;
    margin-bottom: 1rem;
    transition: transform .18s ease;
}
.lx-reman-card:hover {
    transform: translateY(-3px);
}
.lx-reman-selo {
    width: 58px;
    height: 58px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
}
.lx-reman-selo.pulsa {
    animation: luxizPulsoSuave 2.6s ease-in-out infinite;
}
</style>
"""

CONFIG_PRIORIDADE = {
    "Alta": {
        "cor": "#ef4444",
        "emblema": "🚨",
        "rotulo": "PRIORIDADE ALTA",
        "descricao": "Execução imediata recomendada.",
        "nivel": 3,
        "pulsa": True,
    },
    "Média": {
        "cor": "#f59e0b",
        "emblema": "⚠️",
        "rotulo": "PRIORIDADE MÉDIA",
        "descricao": "Monitoramento operacional ativo.",
        "nivel": 2,
        "pulsa": True,
    },
    "Normal": {
        "cor": "#22c55e",
        "emblema": "✅",
        "rotulo": "PRIORIDADE NORMAL",
        "descricao": "Fluxo operacional dentro do esperado.",
        "nivel": 1,
        "pulsa": False,
    },
}

ORDEM_PRIORIDADE = {"Alta": 0, "Média": 1, "Normal": 2}


def _normalizar_prioridade(item):

    prioridade = (item.get("prioridade") or "Normal").strip().capitalize()

    return prioridade if prioridade in CONFIG_PRIORIDADE else "Normal"


def _card_remanejamento_html(item, prioridade):

    config = CONFIG_PRIORIDADE[prioridade]

    cor = config["cor"]

    # medidor de urgência: 3 segmentos, preenchidos conforme o nível
    segmentos = "".join(
        f'<div style="flex:1;height:7px;border-radius:999px;'
        f'background:{cor if posicao < config["nivel"] else cor + "26"};"></div>'
        for posicao in range(3)
    )

    agendado_html = ""

    if item.get("agendado"):

        agendado_html = (
            '<div style="margin-top:.7rem;display:flex;align-items:center;'
            'gap:.5rem;flex-wrap:wrap;">'
            '<span style="background:#8b5cf6;color:#fff;padding:.18rem .65rem;'
            'border-radius:999px;font-size:.7rem;font-weight:800;'
            'letter-spacing:.3px;">⏰ AGENDADO</span>'
            f'<span style="font-size:.78rem;opacity:.8;">{html.escape(item["janela"])}</span>'
            '</div>'
        )

    criado_html = (
        f'👤 Criado por {html.escape(str(item["criado_por"]))}'
        if item.get("criado_por") else "👤 Criado pelo sistema"
    )

    classe_selo = "lx-reman-selo pulsa" if config["pulsa"] else "lx-reman-selo"

    return (
        f'<div class="lx-reman-card" style="'
        f'background:linear-gradient(150deg,{cor}22,{cor}08 70%);'
        f'border:1px solid {cor}55;box-shadow:0 10px 26px {cor}22;">'
        f'<div style="height:4px;background:linear-gradient(90deg,{cor},{cor}55);"></div>'
        '<div style="padding:1.05rem 1.2rem 1rem 1.2rem;">'

        '<div style="display:flex;align-items:center;gap:1rem;">'
        f'<div class="{classe_selo}" style="background:{cor}22;'
        f'border:2px solid {cor};--pulso-cor:{cor}77;">{config["emblema"]}</div>'
        '<div style="min-width:0;flex:1;">'
        f'<span style="display:inline-block;font-size:.7rem;font-weight:800;'
        f'letter-spacing:.5px;padding:.22rem .7rem;border-radius:999px;'
        f'background:{cor}26;color:{cor};border:1px solid {cor}66;">'
        f'{config["rotulo"]}</span>'
        f'<div style="font-size:1.4rem;font-weight:800;line-height:1.15;margin-top:.4rem;">'
        f'⚡ {html.escape(item["nome"])}</div>'
        f'<div style="font-size:.8rem;opacity:.7;margin-top:.15rem;">{config["descricao"]}</div>'
        '</div></div>'

        f'{agendado_html}'

        '<div style="margin-top:1rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'font-size:.66rem;font-weight:800;letter-spacing:.4px;'
        'text-transform:uppercase;opacity:.6;margin-bottom:.3rem;">'
        f'<span>Nível de urgência</span><span style="color:{cor};opacity:1;">'
        f'{config["nivel"]}/3</span></div>'
        f'<div style="display:flex;gap:.3rem;">{segmentos}</div>'
        '</div>'

        f'<div style="height:1px;background:{cor}33;margin:.9rem 0 .6rem 0;"></div>'
        f'<div style="font-size:.74rem;opacity:.7;">{criado_html}</div>'
        '</div></div>'
    )


def _kpi(icone, rotulo, valor, cor):

    return (
        f'<div style="background:{cor}14;border:1px solid {cor}40;'
        'border-radius:.9rem;padding:.75rem .9rem;text-align:center;">'
        f'<div style="font-size:1.3rem;">{icone}</div>'
        f'<div style="font-size:1.5rem;font-weight:800;color:{cor};'
        f'margin-top:.1rem;">{valor}</div>'
        f'<div style="font-size:.74rem;opacity:.75;margin-top:.1rem;">{rotulo}</div>'
        '</div>'
    )


def _banner(cor, icone, titulo, texto):

    return (
        f'<div style="display:flex;align-items:center;gap:.9rem;'
        f'background:linear-gradient(120deg,{cor}22,{cor}08);'
        f'border:1px solid {cor}55;border-left:5px solid {cor};'
        'border-radius:.9rem;padding:.9rem 1.1rem;">'
        f'<div style="font-size:1.7rem;">{icone}</div>'
        '<div>'
        f'<div style="font-weight:800;color:{cor};">{titulo}</div>'
        f'<div style="font-size:.88rem;opacity:.85;margin-top:.1rem;">{texto}</div>'
        '</div></div>'
    )


def render():

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    estilos.cabecalho_pagina(
        "⚡",
        "Central de Remanejamento",
        "Monitoramento operacional das prioridades em tempo real.",
        cor="#f59e0b"
    )

    st.divider()

    _fragmento_painel(armazem_id_atual)

    st.divider()

    # =====================================================
    # HISTÓRICO
    # =====================================================

    with st.popover("🕒 Histórico de Remanejamentos"):

        historico = banco.ler_historico_remanejamento(armazem_id_atual)

        if historico:

            for item, prioridade, data_hora, usuario_item in historico:

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

                responsavel = usuario_item or "desconhecido"

                st.caption(
                    f"{emoji} {item} | {prioridade} | "
                    f"{horario_local.strftime('%d/%m/%Y %H:%M:%S')} | "
                    f"por {responsavel}"
                )

        else:

            st.info(
                "Nenhum histórico encontrado."
            )


# =====================================================
# PAINEL (fragmento com auto-atualização, para as docas
# agendadas entrarem/saírem sozinhas sem precisar recarregar
# a página inteira)
# =====================================================

@st.fragment(run_every=60)
def _fragmento_painel(armazem_id_atual):

    itens_manuais = [
        {**item, "id": f"man{item['id']}"}
        for item in banco.ler_remanejamentos(armazem_id_atual)
    ]

    agendados = banco.ler_remanejamentos_agendados(armazem_id_atual)

    agora = estilos.agora_local()

    itens_agendados_ativos = [
        {
            "id": f"ag{agendamento['id']}",
            "nome": agendamento["nome"],
            "prioridade": agendamento["prioridade"],
            "criado_por": agendamento["criado_por"],
            "agendado": True,
            "janela": janela_horario(agendamento)
        }
        for agendamento in agendados
        if agendamento_esta_ativo(agendamento, agora)
    ]

    itens = itens_manuais + itens_agendados_ativos

    # Alta primeiro, depois Média, depois Normal (a ordem original
    # entre itens da mesma prioridade é mantida)
    itens.sort(
        key=lambda item: ORDEM_PRIORIDADE[_normalizar_prioridade(item)]
    )

    alta = 0
    media = 0
    normal = 0

    for item in itens:

        prioridade = _normalizar_prioridade(item)

        if prioridade == "Alta":
            alta += 1

        elif prioridade == "Média":
            media += 1

        else:
            normal += 1

    st.markdown(CSS_REMANEJAMENTO, unsafe_allow_html=True)

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

            with cols[indice % 3]:

                st.markdown(
                    _card_remanejamento_html(
                        item,
                        _normalizar_prioridade(item)
                    ),
                    unsafe_allow_html=True
                )

    st.divider()

    # =====================================================
    # TOTAIS (logo abaixo dos cards)
    # =====================================================

    kpis = [
        _kpi("📦", "Total", len(itens), "#3b82f6"),
        _kpi("🔴", "Alta", alta, "#ef4444"),
        _kpi("🟠", "Média", media, "#f59e0b"),
        _kpi("🟢", "Normal", normal, "#22c55e"),
    ]

    for coluna, kpi_html in zip(st.columns(4), kpis):

        with coluna:
            st.markdown(kpi_html, unsafe_allow_html=True)

    st.divider()

    # =====================================================
    # RESUMO
    # =====================================================

    st.subheader(
        "Resumo Operacional"
    )

    if alta > 0:

        st.markdown(
            _banner(
                "#ef4444", "🚨", "Atenção imediata",
                f"Existem {alta} prioridade(s) alta(s) aguardando execução."
            ),
            unsafe_allow_html=True
        )

    elif media > 0:

        st.markdown(
            _banner(
                "#f59e0b", "⚠️", "Em monitoramento",
                f"Existem {media} prioridade(s) média(s) em monitoramento."
            ),
            unsafe_allow_html=True
        )

    elif normal > 0:

        st.markdown(
            _banner(
                "#3b82f6", "ℹ️", "Operação normal",
                "Operação operando dentro da normalidade."
            ),
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            _banner(
                "#22c55e", "✅", "Tudo em dia",
                "Nenhuma prioridade pendente."
            ),
            unsafe_allow_html=True
        )

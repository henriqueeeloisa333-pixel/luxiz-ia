import html
import re

import streamlit as st

import banco
import estilos


DIAS_SEMANA = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
]

DIAS_ABREVIADOS = ["Seg", "Ter", "Qua", "Qui", "Sex"]

COR_FIXO = "#a855f7"
COR_ROTATIVO = "#06b6d4"
COR_PESSOAS = "#6366f1"
COR_ATIVIDADES = "#10b981"
COR_SEMANA = "#f59e0b"
COR_HOJE = "#ec4899"


# =====================================================
# APOIO
# =====================================================

def gerar_chave_css(texto):

    return re.sub(
        r'[^a-zA-Z0-9]+',
        '-',
        texto
    ).strip('-').lower()


def _html(texto):
    """
    Envia HTML ao Streamlit sem recuo nem linhas em branco: o Markdown
    trata linhas com 4+ espaços (ou depois de uma linha vazia) como
    bloco de código.
    """

    st.markdown(
        re.sub(r"\s*\n\s*", " ", texto.strip()),
        unsafe_allow_html=True
    )


def _iniciais(nome):

    partes = [p for p in re.split(r"[\s&]+", nome or "") if p]

    return "".join(p[0].upper() for p in partes[:2]) or "?"


def gerar_escala_rotativa(pessoas, atividades_rotativas, hoje=None):

    """
    Gera a escala da semana atual (Segunda a Sexta) para as atividades
    do tipo "rotativo", sem precisar guardar nada no banco: para cada
    atividade e cada dia da semana, a pessoa responsável é calculada
    por rodízio (round-robin), deslocado pelo número da semana do ano
    — assim, toda semana o rodízio avança sozinho.
    """

    if not pessoas or not atividades_rotativas:
        return {}

    hoje = hoje or estilos.agora_local().date()

    numero_semana = hoje.isocalendar()[1]

    escala = {}

    for indice_atividade, atividade in enumerate(atividades_rotativas):

        dias_da_atividade = []

        for indice_dia, dia in enumerate(DIAS_SEMANA):

            indice_pessoa = (
                indice_atividade + indice_dia + numero_semana
            ) % len(pessoas)

            dias_da_atividade.append(
                (dia, pessoas[indice_pessoa])
            )

        escala[atividade] = dias_da_atividade

    return escala


# =====================================================
# VISUAL
# =====================================================

def _css_rotativo():

    return """
    <style>

    /* iframes de altura zero (scripts de rede/tema) não ocupam espaço */
    iframe[height="0"]{ display:none !important; }
    .stElementContainer:has(> iframe[height="0"]){ display:none !important; }

    /* ---------- títulos de seção ---------- */
    .lxr-secao{
        display:flex;
        align-items:center;
        gap:.6rem;
        margin:1.4rem 0 .7rem 0;
    }
    .lxr-secao-barra{
        width:5px;
        height:22px;
        border-radius:999px;
        background:linear-gradient(180deg,#06b6d4,#6366f1);
    }
    .lxr-secao-titulo{
        font-size:1.05rem;
        font-weight:800;
        letter-spacing:.2px;
    }
    .lxr-secao-sub{
        font-size:.78rem;
        opacity:.65;
        margin-left:.2rem;
    }

    /* ---------- indicadores ---------- */
    .lxr-kpis{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
        gap:.8rem;
        margin:.3rem 0 .4rem 0;
    }
    .lxr-kpi{
        border-radius:1rem;
        padding:.85rem 1rem;
    }
    .lxr-kpi-topo{
        display:flex;
        align-items:center;
        justify-content:space-between;
    }
    .lxr-kpi-rotulo{
        font-size:.7rem;
        font-weight:800;
        letter-spacing:.5px;
        text-transform:uppercase;
        opacity:.75;
    }
    .lxr-kpi-valor{
        font-size:1.9rem;
        font-weight:800;
        line-height:1.15;
        margin-top:.15rem;
    }
    .lxr-kpi-sub{
        font-size:.72rem;
        opacity:.65;
        margin-top:.1rem;
    }

    /* ---------- cartões de "hoje" (altura igual) ---------- */
    .lxr-grid{
        display:grid;
        grid-template-columns:repeat(auto-fill,minmax(270px,1fr));
        gap:.9rem;
    }
    .lxr-card{
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        gap:.9rem;
        min-height:158px;
        border-radius:1.1rem;
        padding:1rem 1.1rem;
        transition:transform .18s ease, box-shadow .18s ease;
    }
    .lxr-card:hover{
        transform:translateY(-3px);
    }
    .lxr-card-topo{
        display:flex;
        align-items:center;
        justify-content:space-between;
    }
    .lxr-ico{
        width:40px;
        height:40px;
        border-radius:12px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.2rem;
    }
    .lxr-badge{
        color:#ffffff;
        padding:.16rem .65rem;
        border-radius:999px;
        font-size:.68rem;
        font-weight:800;
        letter-spacing:.5px;
    }
    .lxr-nome{
        font-size:1.02rem;
        font-weight:800;
        line-height:1.3;
    }
    .lxr-resp{
        display:flex;
        align-items:center;
        gap:.6rem;
        padding:.5rem .65rem;
        border-radius:.8rem;
        background:rgba(127,127,127,.10);
    }
    .lxr-av{
        flex-shrink:0;
        width:32px;
        height:32px;
        border-radius:50%;
        display:flex;
        align-items:center;
        justify-content:center;
        color:#ffffff;
        font-size:.72rem;
        font-weight:800;
    }
    .lxr-resp-rotulo{
        font-size:.64rem;
        font-weight:700;
        letter-spacing:.4px;
        text-transform:uppercase;
        opacity:.6;
    }
    .lxr-resp-nome{
        font-size:.9rem;
        font-weight:700;
        line-height:1.25;
    }

    /* ---------- tabela da escala da semana ---------- */
    .lxr-tabela-wrap{
        overflow-x:auto;
        border-radius:1rem;
        border:1px solid rgba(127,127,127,.25);
    }
    .lxr-tabela{
        width:100%;
        border-collapse:collapse;
        font-size:.86rem;
        min-width:640px;
    }
    .lxr-tabela th{
        padding:.7rem .8rem;
        text-align:left;
        font-size:.72rem;
        font-weight:800;
        letter-spacing:.5px;
        text-transform:uppercase;
        background:rgba(127,127,127,.12);
        border-bottom:1px solid rgba(127,127,127,.25);
    }
    .lxr-tabela th.lxr-hoje{
        background:rgba(236,72,153,.22);
        color:#ec4899;
    }
    .lxr-tabela td{
        padding:.65rem .8rem;
        border-bottom:1px solid rgba(127,127,127,.15);
        vertical-align:middle;
    }
    .lxr-tabela tr:last-child td{
        border-bottom:none;
    }
    .lxr-tabela td.lxr-hoje{
        background:rgba(236,72,153,.10);
        font-weight:700;
    }
    .lxr-tabela td.lxr-ativ{
        font-weight:700;
        min-width:210px;
    }
    .lxr-tabela td.lxr-fixo-linha{
        font-weight:600;
    }
    .lxr-mini-badge{
        display:inline-block;
        color:#ffffff;
        padding:.08rem .5rem;
        border-radius:999px;
        font-size:.62rem;
        font-weight:800;
        letter-spacing:.4px;
        margin-left:.4rem;
        vertical-align:middle;
    }
    .lxr-tabela tr.lxr-separador td{
        padding:.45rem .8rem;
        font-size:.68rem;
        font-weight:800;
        letter-spacing:.6px;
        text-transform:uppercase;
        opacity:.7;
        background:rgba(127,127,127,.07);
    }

    </style>
    """


def _titulo_secao(titulo, subtitulo=""):

    sub_html = (
        f'<span class="lxr-secao-sub">{html.escape(subtitulo)}</span>'
        if subtitulo else ""
    )

    _html(
        f"""
        <div class="lxr-secao">
            <div class="lxr-secao-barra"></div>
            <div class="lxr-secao-titulo">{html.escape(titulo)}</div>
            {sub_html}
        </div>
        """
    )


def _mostrar_kpis(cartoes):
    """
    cartoes: lista de (icone, rotulo, valor, cor, subtitulo)
    """

    html_cartoes = "".join(
        f"""
        <div class="lxr-kpi" style="
            background:{cor}14;
            border:1px solid {cor}45;
            box-shadow:0 6px 18px {cor}12;
        ">
            <div class="lxr-kpi-topo">
                <span class="lxr-kpi-rotulo">{html.escape(rotulo)}</span>
                <span>{icone}</span>
            </div>
            <div class="lxr-kpi-valor" style="color:{cor};">{html.escape(str(valor))}</div>
            <div class="lxr-kpi-sub">{html.escape(subtitulo)}</div>
        </div>
        """
        for icone, rotulo, valor, cor, subtitulo in cartoes
    )

    _html(f'<div class="lxr-kpis">{html_cartoes}</div>')


def _html_cartao_hoje(tipo, nome_atividade, responsavel):

    eh_fixo = tipo == "fixo"

    cor = COR_FIXO if eh_fixo else COR_ROTATIVO
    emblema = "📌" if eh_fixo else "🔄"
    rotulo_badge = "FIXO" if eh_fixo else "RODÍZIO"

    rotulo_resp = "Responsável fixo" if eh_fixo else "Responsável hoje"

    if responsavel:

        avatar = (
            f'<div class="lxr-av" style="background:{cor};">'
            f'{html.escape(_iniciais(responsavel))}</div>'
        )

        nome_resp = html.escape(responsavel)

    else:

        avatar = (
            '<div class="lxr-av" style="background:rgba(127,127,127,.5);">—</div>'
        )

        nome_resp = "Sem responsável hoje"

    return f"""
    <div class="lxr-card" style="
        background:{cor}12;
        border:1px solid {cor}50;
        box-shadow:0 8px 22px {cor}14;
    ">
        <div class="lxr-card-topo">
            <div class="lxr-ico" style="background:{cor}26;">{emblema}</div>
            <span class="lxr-badge" style="background:{cor};">{rotulo_badge}</span>
        </div>
        <div class="lxr-nome">{html.escape(nome_atividade)}</div>
        <div class="lxr-resp">
            {avatar}
            <div>
                <div class="lxr-resp-rotulo">{rotulo_resp}</div>
                <div class="lxr-resp-nome">{nome_resp}</div>
            </div>
        </div>
    </div>
    """


def _html_tabela_escala(escala_rotativa, atividades_fixas, indice_hoje):

    cabecalho = "".join(
        f'<th class="{"lxr-hoje" if indice == indice_hoje else ""}">'
        f'{DIAS_ABREVIADOS[indice]}'
        f'{" • hoje" if indice == indice_hoje else ""}</th>'
        for indice in range(5)
    )

    linhas = ""

    if escala_rotativa:

        linhas += (
            '<tr class="lxr-separador"><td colspan="6">🔄 Atividades em rodízio</td></tr>'
        )

        for nome_atividade, dias_da_atividade in escala_rotativa.items():

            celulas = "".join(
                f'<td class="{"lxr-hoje" if indice == indice_hoje else ""}">'
                f'{html.escape(pessoa)}</td>'
                for indice, (_, pessoa) in enumerate(dias_da_atividade)
            )

            linhas += (
                f'<tr><td class="lxr-ativ">{html.escape(nome_atividade)}'
                f'<span class="lxr-mini-badge" style="background:{COR_ROTATIVO};">'
                f'RODÍZIO</span></td>{celulas}</tr>'
            )

    if atividades_fixas:

        linhas += (
            '<tr class="lxr-separador"><td colspan="6">📌 Atividades fixas</td></tr>'
        )

        for nome_atividade, pessoa_fixa in atividades_fixas:

            linhas += (
                f'<tr><td class="lxr-ativ">{html.escape(nome_atividade)}'
                f'<span class="lxr-mini-badge" style="background:{COR_FIXO};">'
                f'FIXO</span></td>'
                f'<td class="lxr-fixo-linha" colspan="5">'
                f'👤 {html.escape(pessoa_fixa or "Não informado")} · todos os dias'
                f'</td></tr>'
            )

    return f"""
    <div class="lxr-tabela-wrap">
        <table class="lxr-tabela">
            <thead>
                <tr><th>Atividade</th>{cabecalho}</tr>
            </thead>
            <tbody>{linhas}</tbody>
        </table>
    </div>
    """


# =====================================================
# PÁGINA
# =====================================================

def render():

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    _html(_css_rotativo())

    estilos.cabecalho_pagina(
        "🔄",
        "Atividades Fim de Expediente Rotativo",
        "Rodízio automático de quem faz cada atividade, de Segunda a Sexta.",
        cor="#06b6d4"
    )

    st.write("")

    pessoas = [
        nome for _, nome in banco.listar_pessoas_rotativo(armazem_id_atual)
    ]

    atividades_cadastradas = banco.listar_atividades_rotativo(armazem_id_atual)

    if not atividades_cadastradas:

        st.info(
            "Cadastre pessoas e atividades no Administrativo para o "
            "rodízio ser gerado automaticamente."
        )
        return

    atividades_fixas = [
        (nome, pessoa_fixa)
        for _, nome, tipo, pessoa_fixa in atividades_cadastradas
        if tipo == "fixo"
    ]

    nomes_atividades_rotativas = [
        nome
        for _, nome, tipo, pessoa_fixa in atividades_cadastradas
        if tipo != "fixo"
    ]

    if nomes_atividades_rotativas and not pessoas:

        st.warning(
            "Há atividades rotativas cadastradas, mas nenhuma pessoa "
            "no rodízio ainda. Cadastre as pessoas no Administrativo."
        )

    # Usa o fuso de Campo Grande (o servidor roda em UTC e, à noite,
    # já estaria um dia adiantado).
    hoje = estilos.agora_local().date()

    numero_semana = hoje.isocalendar()[1]

    indice_hoje = hoje.weekday() if hoje.weekday() < 5 else None

    dia_hoje = DIAS_SEMANA[indice_hoje] if indice_hoje is not None else None

    escala_rotativa = gerar_escala_rotativa(
        pessoas,
        nomes_atividades_rotativas,
        hoje
    )

    # =====================================================
    # INDICADORES
    # =====================================================

    _mostrar_kpis([
        ("👥", "Pessoas no rodízio", len(pessoas), COR_PESSOAS, "participam da escala"),
        (
            "🧹", "Atividades", len(atividades_cadastradas), COR_ATIVIDADES,
            f"{len(atividades_fixas)} fixa(s) · {len(nomes_atividades_rotativas)} em rodízio"
        ),
        ("📅", "Semana", numero_semana, COR_SEMANA, f"do ano de {hoje.year}"),
        (
            "📍", "Hoje",
            DIAS_ABREVIADOS[indice_hoje] if indice_hoje is not None else "Folga",
            COR_HOJE,
            hoje.strftime("%d/%m/%Y")
        ),
    ])

    if not dia_hoje:

        st.info(
            "Hoje é fim de semana — a escala abaixo é referente aos "
            "dias úteis (Segunda a Sexta)."
        )

    # =====================================================
    # HOJE
    # =====================================================

    _titulo_secao(
        "Responsáveis de hoje",
        dia_hoje or "fim de semana"
    )

    cartoes_html = ""

    for nome_atividade, dias_da_atividade in escala_rotativa.items():

        responsavel_hoje = (
            dict(dias_da_atividade)[dia_hoje] if dia_hoje else None
        )

        cartoes_html += _html_cartao_hoje(
            "rotativo", nome_atividade, responsavel_hoje
        )

    for nome_atividade, pessoa_fixa in atividades_fixas:

        cartoes_html += _html_cartao_hoje(
            "fixo", nome_atividade, pessoa_fixa
        )

    _html(f'<div class="lxr-grid">{cartoes_html}</div>')

    # =====================================================
    # ESCALA DA SEMANA
    # =====================================================

    _titulo_secao(
        "Escala da semana",
        f"semana {numero_semana} · o dia de hoje fica destacado"
    )

    _html(_html_tabela_escala(escala_rotativa, atividades_fixas, indice_hoje))

    st.write("")

    st.caption(
        "Luxiz IA • Rodízio de Fim de Expediente"
    )

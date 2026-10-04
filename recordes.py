import base64
import html
import re
from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import streamlit as st

import banco


# ==================================================
# REGRAS DOS RANKINGS
# ==================================================
# SAC: pontuação = número de chamados (cards da Análise Técnica)
#      vinculados ao nome da pessoa como Separador ou Conferente.
#      QUANTO MENOS, MELHOR. Quem não tem nenhum chamado fica em 1º
#      (empatado) e vai descendo conforme chamados entram no nome.
#
# Auditoria: pontuação = acertos - erros (maior é melhor). Em caso de
#      empate, quem tem menos erros fica na frente.
#
# Dashboard: as 3 ruas com maior nota no fechamento do mês escolhido
#      (o mês fechado mais recente aparece por padrão).

MEDALHAS = {1: "🥇", 2: "🥈", 3: "🥉"}
CORES_POSICAO = {1: "#f59e0b", 2: "#94a3b8", 3: "#f97316"}
COR_NEUTRA = "#64748b"

# Cores de cada medalha: (fita A, fita B, aro claro, aro médio, aro escuro,
# face clara, face média, face escura, cor do número)
ESTILOS_MEDALHA = {
    1: ("#dc2626", "#991b1b", "#fff6bf", "#f5c518", "#a87400",
        "#ffe98a", "#f2b705", "#b8860b", "#6b4600"),
    2: ("#2563eb", "#1e3a8a", "#ffffff", "#cfd6de", "#6b7787",
        "#f8fafc", "#c3cad3", "#8190a1", "#3f4a59"),
    3: ("#16a34a", "#14532d", "#ffd9b0", "#cd7f32", "#6e3a14",
        "#f4bd88", "#cd7f32", "#8a4b1c", "#4f270c"),
}


def _svg_para_img(svg, altura, alt):
    """
    O SVG vai como imagem (data URI), igual à logo do app: funciona
    em qualquer versão do Streamlit sem depender de HTML inline.
    """

    codificado = base64.b64encode(svg.encode("utf-8")).decode()

    return (
        f'<img src="data:image/svg+xml;base64,{codificado}" alt="{alt}" '
        f'style="height:{altura}px;width:auto;display:block;flex-shrink:0;">'
    )


@lru_cache(maxsize=None)
def _medalha_html(posicao, altura=46):
    """Medalha metálica com fita, aro, brilho e o número da posição."""

    (fita_a, fita_b, aro_1, aro_2, aro_3,
     face_1, face_2, face_3, cor_num) = ESTILOS_MEDALHA[posicao]

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 84">
<defs>
<linearGradient id="fitaA" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{fita_a}"/><stop offset="1" stop-color="{fita_b}"/></linearGradient>
<linearGradient id="fitaB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{fita_b}"/><stop offset="1" stop-color="{fita_a}"/></linearGradient>
<linearGradient id="aro" x1="0.15" y1="0" x2="0.85" y2="1"><stop offset="0" stop-color="{aro_1}"/><stop offset="0.5" stop-color="{aro_2}"/><stop offset="1" stop-color="{aro_3}"/></linearGradient>
<radialGradient id="face" cx="0.38" cy="0.32" r="0.85"><stop offset="0" stop-color="{face_1}"/><stop offset="0.55" stop-color="{face_2}"/><stop offset="1" stop-color="{face_3}"/></radialGradient>
<filter id="sombra" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="2" stdDeviation="1.8" flood-color="#000" flood-opacity="0.45"/></filter>
</defs>
<polygon points="14,0 30,0 38,34 24,38" fill="url(#fitaA)"/>
<polygon points="34,0 50,0 40,38 26,34" fill="url(#fitaB)"/>
<polygon points="24,0 30,0 33,14 27,16" fill="#ffffff" opacity="0.18"/>
<g filter="url(#sombra)">
<circle cx="32" cy="56" r="24" fill="url(#aro)"/>
<circle cx="32" cy="56" r="24" fill="none" stroke="{aro_3}" stroke-width="0.8" opacity="0.7"/>
<circle cx="32" cy="56" r="19" fill="url(#face)"/>
<circle cx="32" cy="56" r="19" fill="none" stroke="{aro_3}" stroke-width="1.2" opacity="0.55"/>
<circle cx="32" cy="56" r="16.2" fill="none" stroke="{aro_1}" stroke-width="0.7" opacity="0.7"/>
<path d="M17 50 A17 17 0 0 1 36 39 A21 21 0 0 0 17 50 Z" fill="#ffffff" opacity="0.42"/>
<text x="32" y="64.5" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="900" fill="{cor_num}" stroke="{aro_1}" stroke-width="0.4" stroke-opacity="0.6">{posicao}</text>
</g>
</svg>"""

    return _svg_para_img(svg, altura, f"{posicao}º lugar")


@lru_cache(maxsize=None)
def _taca_html(altura=64):
    """Taça dourada com alças, haste, base e brilho."""

    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 80">
<defs>
<linearGradient id="copo" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#b8860b"/><stop offset="0.28" stop-color="#ffe98a"/><stop offset="0.55" stop-color="#f5c518"/><stop offset="1" stop-color="#a87400"/></linearGradient>
<linearGradient id="haste" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#a87400"/><stop offset="0.45" stop-color="#ffe98a"/><stop offset="1" stop-color="#8a5e00"/></linearGradient>
<linearGradient id="base" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7a4a10"/><stop offset="1" stop-color="#3f2406"/></linearGradient>
<filter id="sombra" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.45"/></filter>
</defs>
<g filter="url(#sombra)">
<path d="M18 14 H8 C6 30 12 38 22 40" fill="none" stroke="url(#haste)" stroke-width="4.2" stroke-linecap="round"/>
<path d="M54 14 H64 C66 30 60 38 50 40" fill="none" stroke="url(#haste)" stroke-width="4.2" stroke-linecap="round"/>
<path d="M16 8 H56 V26 C56 42 47 52 36 52 C25 52 16 42 16 26 Z" fill="url(#copo)"/>
<rect x="16" y="6" width="40" height="5" rx="2.5" fill="#ffe98a"/>
<rect x="31" y="50" width="10" height="13" fill="url(#haste)"/>
<ellipse cx="36" cy="52" rx="8" ry="2.6" fill="#a87400"/>
<rect x="24" y="62" width="24" height="6" rx="1.5" fill="url(#haste)"/>
<rect x="19" y="67" width="34" height="9" rx="2.5" fill="url(#base)"/>
<rect x="19" y="67" width="34" height="2" rx="1" fill="#ffffff" opacity="0.22"/>
<polygon points="36,17 38.6,24 46,24.4 40.2,29 42.2,36.4 36,32.2 29.8,36.4 31.8,29 26,24.4 33.4,24" fill="#fff6bf" opacity="0.92"/>
<path d="M21 14 C20 28 24 38 31 44 C25 36 24 26 25 14 Z" fill="#ffffff" opacity="0.42"/>
</g>
</svg>"""

    return _svg_para_img(svg, altura, "Taça")


# Valores que aparecem em planilhas/cadastros no lugar de um nome
VALORES_SEM_NOME = {"", "-", "—", "não", "nao", "n/a", "na"}

# Funções que entram no ranking do SAC (prefixo do login -> rótulo)
PREFIXOS_SAC = ("Separador.", "Conferente.")


# ==================================================
# APOIO
# ==================================================

def _chave(nome):

    return banco._normalizar_texto(nome)


def _nome_valido(texto):

    return bool(texto) and texto.strip().lower() not in VALORES_SEM_NOME


def _rotulo_mes(ano, mes):

    return f"{banco.MESES_PT[mes - 1]} de {ano}"


def _meses_dos_dados(datas):

    return sorted(
        {(d.year, d.month) for d in datas if d},
        reverse=True
    )


def _mes_atual():

    agora = datetime.now(ZoneInfo("America/Campo_Grande"))

    return (agora.year, agora.month)


def _seletor_periodo(meses, chave_widget):
    """
    O mês atual vem selecionado por padrão (mesmo que ainda não tenha
    nenhum registro), então as posições se ajustam sozinhas conforme
    chamados/auditorias entram no mês. Depois vêm os meses anteriores
    com dados e, por último, "Todo o período".
    """

    atual = _mes_atual()

    anteriores = [m for m in meses if m != atual]

    def _rotulo(m):

        if m is None:
            return "Todo o período"

        if m == atual:
            return f"{_rotulo_mes(*m)} (mês atual)"

        return _rotulo_mes(*m)

    return st.selectbox(
        "Período",
        [atual] + anteriores + [None],
        format_func=_rotulo,
        key=chave_widget
    )


def _fotos_por_nome(armazem_id):

    return {
        _chave(banco.nome_completo_perfil(p)): p["foto"]
        for p in banco.ler_perfis(armazem_id)
        if p.get("foto")
    }


def _roster(armazem_id, prefixos):
    """
    Todos os colaboradores cadastrados (logins com os prefixos dados),
    já com o nome do Perfil (nome + sobrenome) quando existir. É isso
    que garante que quem ainda não tem nenhum chamado apareça no
    ranking, em 1º lugar.
    """

    perfis = {p["usuario"]: p for p in banco.ler_perfis(armazem_id)}

    roster = {}

    for _, usuario, _, _ in banco.listar_usuarios(armazem_id):

        if not usuario:
            continue

        prefixo = next((p for p in prefixos if usuario.startswith(p)), None)

        if not prefixo:
            continue

        perfil = perfis.get(usuario)

        nome = (
            banco.nome_completo_perfil(perfil)
            if perfil
            else usuario.split(".", 1)[1].strip().title()
        )

        if not nome:
            continue

        roster.setdefault(_chave(nome), {
            "nome": nome,
            "funcao": prefixo.rstrip("."),
            "foto": perfil.get("foto") if perfil else None,
        })

    return roster


def _avatar_html(nome, foto, tamanho=44):

    if foto:

        return (
            f'<img src="{foto}" style="width:{tamanho}px;height:{tamanho}px;'
            'border-radius:50%;object-fit:cover;flex-shrink:0;">'
        )

    iniciais = "".join(p[0].upper() for p in nome.split()[:2]) or "?"

    return (
        f'<div style="width:{tamanho}px;height:{tamanho}px;border-radius:50%;'
        'flex-shrink:0;background:linear-gradient(135deg,#3b82f6,#a855f7);'
        'display:flex;align-items:center;justify-content:center;color:white;'
        f'font-weight:800;font-size:.85rem;">{html.escape(iniciais)}</div>'
    )


def _chip(texto, cor):

    return (
        f'<span style="background:{cor}1f;color:{cor};border:1px solid {cor}55;'
        'padding:.2rem .65rem;border-radius:999px;font-size:.76rem;'
        f'font-weight:800;white-space:nowrap;">{texto}</span>'
    )


def _linha_ranking(posicao, nome, foto, subtitulo, chips, e_voce):

    cor = CORES_POSICAO.get(posicao, COR_NEUTRA)

    if posicao in MEDALHAS:
        selo = (
            '<div style="display:flex;justify-content:center;">'
            f'{_medalha_html(posicao, 46)}</div>'
        )
    else:
        selo = (
            f'<div style="font-weight:800;font-size:1.05rem;text-align:center;'
            f'opacity:.75;">{posicao}º</div>'
        )

    marca_voce = (
        ' <span style="background:#00c8ff22;color:#00c8ff;border:1px solid #00c8ff66;'
        'padding:.05rem .5rem;border-radius:999px;font-size:.68rem;'
        'font-weight:800;margin-left:.3rem;">Você</span>'
        if e_voce else ""
    )

    destaque = "box-shadow:0 0 0 2px #00c8ff55;" if e_voce else ""

    return (
        f'<div style="display:grid;grid-template-columns:50px 46px minmax(0,1fr) auto;'
        f'align-items:center;gap:.9rem;background:{cor}10;border:1px solid {cor}40;'
        f'border-radius:1rem;padding:.7rem 1rem;margin-bottom:.5rem;{destaque}">'
        f'{selo}'
        f'{_avatar_html(nome, foto)}'
        '<div style="min-width:0;">'
        f'<div style="font-weight:800;font-size:.98rem;overflow:hidden;'
        f'text-overflow:ellipsis;white-space:nowrap;">{html.escape(nome)}{marca_voce}</div>'
        f'<div style="font-size:.74rem;opacity:.65;margin-top:.1rem;">{html.escape(subtitulo)}</div>'
        '</div>'
        '<div style="display:flex;gap:.4rem;flex-wrap:wrap;justify-content:flex-end;">'
        f'{"".join(chips)}'
        '</div>'
        '</div>'
    )


def _kpi(icone, rotulo, valor, cor):

    return (
        f'<div style="background:{cor}14;border:1px solid {cor}40;'
        'border-radius:.9rem;padding:.7rem .9rem;text-align:center;">'
        f'<div style="font-size:1.3rem;">{icone}</div>'
        f'<div style="font-size:1.25rem;font-weight:800;color:{cor};'
        f'margin-top:.1rem;">{valor}</div>'
        f'<div style="font-size:.72rem;opacity:.75;margin-top:.1rem;">{rotulo}</div>'
        '</div>'
    )


def _mostrar_kpis(kpis):

    for coluna, kpi_html in zip(st.columns(len(kpis)), kpis):

        with coluna:
            st.markdown(kpi_html, unsafe_allow_html=True)

    st.write("")


def _atribuir_posicoes(itens, chave_empate):
    """
    Posição "densa": empatados dividem a mesma posição e o próximo
    grupo recebe a posição seguinte (1, 1, 1, 2, 2, 3, 4...). Assim
    sempre existem 🥈 e 🥉 depois do(s) líder(es), mesmo quando muita
    gente está empatada em 1º. `itens` já vem ordenado.
    """

    posicoes = []
    posicao_atual = 0

    for indice, item in enumerate(itens):

        if indice == 0 or chave_empate(item) != chave_empate(itens[indice - 1]):
            posicao_atual += 1

        posicoes.append(posicao_atual)

    return posicoes


def _plural(quantidade, singular, plural):

    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _render_minha_posicao(ranking, usuario, armazem_id, mensagem_sem_posicao):
    """
    Visão do colaborador (Separador, Conferente, Recebimento...): só a
    posição dele e quantas pessoas estão acima e abaixo. Nenhum nome,
    número de chamados, acerto ou erro de colega aparece.
    """

    minha = next(
        (
            posicao
            for posicao, pessoa in ranking
            if banco.pessoa_pertence_ao_usuario(pessoa["nome"], usuario, armazem_id)
        ),
        None
    )

    if minha is None:

        st.info(mensagem_sem_posicao)
        return

    acima = sum(1 for posicao, _ in ranking if posicao < minha)
    abaixo = sum(1 for posicao, _ in ranking if posicao > minha)
    empatados = sum(1 for posicao, _ in ranking if posicao == minha) - 1

    cor = CORES_POSICAO.get(minha, "#00c8ff")

    if minha in MEDALHAS:
        selo = _medalha_html(minha, 92)
    else:
        selo = (
            f'<div style="width:84px;height:84px;border-radius:50%;flex-shrink:0;'
            f'background:{cor}22;border:3px solid {cor};display:flex;'
            f'align-items:center;justify-content:center;font-weight:800;'
            f'font-size:1.9rem;color:{cor};">{minha}º</div>'
        )

    linha_empate = (
        f'<div style="font-size:.78rem;opacity:.65;margin-top:.45rem;">'
        f'Você divide essa posição com {_plural(empatados, "colega", "colegas")}.</div>'
        if empatados > 0 else ""
    )

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;'
        f'background:{cor}12;border:1px solid {cor}55;border-radius:1.2rem;'
        f'padding:1.5rem 1.8rem;margin-top:.5rem;">'
        f'{selo}'
        '<div>'
        '<div style="font-size:.72rem;font-weight:800;letter-spacing:.5px;'
        'text-transform:uppercase;opacity:.65;">Sua posição</div>'
        f'<div style="font-size:2.2rem;font-weight:800;color:{cor};line-height:1.15;">'
        f'{minha}º lugar</div>'
        '<div style="font-size:1rem;margin-top:.45rem;">'
        f'👆 <b>{_plural(acima, "colaborador", "colaboradores")}</b> acima de você'
        ' &nbsp;·&nbsp; '
        f'👇 <b>{_plural(abaixo, "colaborador", "colaboradores")}</b> abaixo'
        '</div>'
        f'{linha_empate}'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "🔒 Por privacidade, você vê apenas a sua própria posição. A lista "
        "completa fica disponível só para a Gestão e o Fundador."
    )


# ==================================================
# RANKING DO SAC
# ==================================================

def calcular_ranking_sac(armazem_id, periodo):

    chamados = banco.ler_analise_tecnica(armazem_id)

    if periodo:
        chamados = [
            c for c in chamados
            if c["data_erro"]
            and (c["data_erro"].year, c["data_erro"].month) == periodo
        ]

    roster = _roster(armazem_id, PREFIXOS_SAC)
    fotos = _fotos_por_nome(armazem_id)

    pessoas = {
        chave: {
            "nome": dados["nome"],
            "funcao": dados["funcao"],
            "foto": dados["foto"],
            "chamados": 0,
            "ultimo": None,
        }
        for chave, dados in roster.items()
    }

    for chamado in chamados:

        # cada chamado conta uma vez por pessoa, mesmo que ela seja
        # Separador e Conferente do mesmo chamado
        envolvidos = {}

        for campo in ("separador", "conferente"):

            texto = chamado.get(campo)

            if _nome_valido(texto):

                nome = banco.normalizar_nome_pessoa(texto, armazem_id)
                envolvidos[_chave(nome)] = nome

        for chave, nome in envolvidos.items():

            pessoa = pessoas.setdefault(chave, {
                "nome": nome,
                "funcao": "—",
                "foto": fotos.get(chave),
                "chamados": 0,
                "ultimo": None,
            })

            pessoa["chamados"] += 1

            if chamado["data_erro"] and (
                pessoa["ultimo"] is None or chamado["data_erro"] > pessoa["ultimo"]
            ):
                pessoa["ultimo"] = chamado["data_erro"]

    ordenados = sorted(
        pessoas.values(),
        key=lambda p: (p["chamados"], p["nome"].lower())
    )

    posicoes = _atribuir_posicoes(ordenados, lambda p: p["chamados"])

    return list(zip(posicoes, ordenados)), len(chamados)


def _linha_sac(posicao, pessoa, e_voce, detalhado):
    """
    detalhado=True (Gestão/Fundador, ou a própria pessoa): mostra a
    situação de chamados. Para os demais, aparece SÓ a posição e o
    nome — ninguém vê se um colega tem chamados nem quantos.
    """

    chips = []
    subtitulo = pessoa["funcao"]

    if detalhado:

        if pessoa["chamados"] == 0:

            chips.append(_chip("✅ Sem chamados", "#22c55e"))

        else:

            plural = "chamado" if pessoa["chamados"] == 1 else "chamados"
            chips.append(_chip(f'{pessoa["chamados"]} {plural}', "#f59e0b"))

            if pessoa["ultimo"]:
                subtitulo = (
                    f'{pessoa["funcao"]} · último chamado em '
                    f'{pessoa["ultimo"].strftime("%d/%m/%Y")}'
                )

    return _linha_ranking(
        posicao,
        pessoa["nome"],
        pessoa["foto"],
        subtitulo,
        chips,
        e_voce
    )


def _render_sac(armazem_id, usuario, ve_tudo):

    st.caption(
        "Pontuação = chamados da Análise Técnica vinculados ao nome da "
        "pessoa. **Quanto menos, melhor.** Quem não tem nenhum fica em 1º "
        "lugar e vai descendo conforme chamados entram no nome."
    )

    chamados = banco.ler_analise_tecnica(armazem_id)

    meses = _meses_dos_dados(c["data_erro"] for c in chamados)

    periodo = _seletor_periodo(meses, "rec_sac_periodo")

    ranking, total_chamados = calcular_ranking_sac(armazem_id, periodo)

    if not ranking:

        st.info("Nenhum colaborador (Separador ou Conferente) cadastrado ainda.")
        return

    # Colaboradores: só a própria posição.
    if not ve_tudo:

        _render_minha_posicao(
            ranking,
            usuario,
            armazem_id,
            "O ranking do SAC considera os Separadores e Conferentes — "
            "você não participa dele."
        )
        return

    # Gestão e Fundador: lista completa.
    sem_chamados = sum(1 for _, p in ranking if p["chamados"] == 0)

    _mostrar_kpis([
        _kpi("👥", "Colaboradores no ranking", str(len(ranking)), "#3b82f6"),
        _kpi("✅", "Sem nenhum chamado", str(sem_chamados), "#22c55e"),
        _kpi("📋", "Chamados no período", str(total_chamados), "#f59e0b"),
    ])

    st.markdown(
        "".join(
            _linha_sac(
                posicao,
                pessoa,
                banco.pessoa_pertence_ao_usuario(pessoa["nome"], usuario, armazem_id),
                detalhado=True
            )
            for posicao, pessoa in ranking
        ),
        unsafe_allow_html=True
    )


# ==================================================
# RANKING DA AUDITORIA
# ==================================================

def calcular_ranking_auditoria(armazem_id, periodo, funcao):

    registros = banco.ler_auditoria(armazem_id)

    if periodo:
        registros = [
            r for r in registros
            if r["data_atividade"]
            and (r["data_atividade"].year, r["data_atividade"].month) == periodo
        ]

    if funcao != "Todas":
        registros = [r for r in registros if r["funcao"] == funcao]

    fotos = _fotos_por_nome(armazem_id)

    pessoas = {}

    # ler_auditoria já vem do registro mais recente para o mais antigo,
    # então a primeira função vista é a mais recente da pessoa
    for registro in registros:

        nome = banco.normalizar_nome_pessoa(registro["nome"], armazem_id)

        if not nome:
            continue

        chave = _chave(nome)

        pessoa = pessoas.setdefault(chave, {
            "nome": nome,
            "funcao": registro["funcao"],
            "foto": fotos.get(chave),
            "acertos": 0,
            "erros": 0,
        })

        pessoa["acertos"] += registro["qtd_acertos"] or 0
        pessoa["erros"] += registro["qtd_erros"] or 0

    for pessoa in pessoas.values():

        total = pessoa["acertos"] + pessoa["erros"]

        pessoa["pontuacao"] = pessoa["acertos"] - pessoa["erros"]
        pessoa["aproveitamento"] = (
            pessoa["acertos"] / total * 100 if total else 0
        )

    ordenados = sorted(
        pessoas.values(),
        key=lambda p: (-p["pontuacao"], p["erros"], p["nome"].lower())
    )

    posicoes = _atribuir_posicoes(
        ordenados,
        lambda p: (p["pontuacao"], p["erros"])
    )

    return list(zip(posicoes, ordenados))


def _linha_auditoria(posicao, pessoa, e_voce, detalhado):
    """
    detalhado=True (Gestão/Fundador, ou a própria pessoa): mostra
    acertos, erros, aproveitamento e pontos. Para os demais, só
    acertos e pontos — os erros dos colegas não aparecem.
    """

    chips = [_chip(f'✅ {pessoa["acertos"]}', "#22c55e")]

    if detalhado:
        chips.append(_chip(f'❌ {pessoa["erros"]}', "#ef4444"))
        chips.append(_chip(f'{pessoa["aproveitamento"]:.0f}%', "#3b82f6"))

    chips.append(_chip(f'⭐ {pessoa["pontuacao"]} pts', "#f59e0b"))

    return _linha_ranking(
        posicao,
        pessoa["nome"],
        pessoa["foto"],
        pessoa["funcao"],
        chips,
        e_voce
    )


def _render_auditoria(armazem_id, usuario, ve_tudo):

    st.caption(
        "Pontuação = acertos − erros. Quem acerta mais e erra menos fica "
        "na frente; em caso de empate, vence quem tem menos erros."
    )

    registros = banco.ler_auditoria(armazem_id)

    meses = _meses_dos_dados(r["data_atividade"] for r in registros)

    funcoes = sorted({r["funcao"] for r in registros if r["funcao"]})

    col_periodo, col_funcao = st.columns(2)

    with col_periodo:
        periodo = _seletor_periodo(meses, "rec_aud_periodo")

    with col_funcao:
        funcao = st.selectbox(
            "Função",
            ["Todas"] + funcoes,
            key="rec_aud_funcao"
        )

    ranking = calcular_ranking_auditoria(armazem_id, periodo, funcao)

    if not ranking:

        st.info("Nenhum registro de auditoria para esse filtro.")
        return

    # Colaboradores: só a própria posição.
    if not ve_tudo:

        _render_minha_posicao(
            ranking,
            usuario,
            armazem_id,
            "Você ainda não tem registros de auditoria para esse filtro, "
            "então não aparece neste ranking."
        )
        return

    # Gestão e Fundador: lista completa.
    total_acertos = sum(p["acertos"] for _, p in ranking)
    total_erros = sum(p["erros"] for _, p in ranking)

    _mostrar_kpis([
        _kpi("👥", "Colaboradores no ranking", str(len(ranking)), "#3b82f6"),
        _kpi("✅", "Acertos no período", str(total_acertos), "#22c55e"),
        _kpi("❌", "Erros no período", str(total_erros), "#ef4444"),
    ])

    st.markdown(
        "".join(
            _linha_auditoria(
                posicao,
                pessoa,
                banco.pessoa_pertence_ao_usuario(pessoa["nome"], usuario, armazem_id),
                detalhado=True
            )
            for posicao, pessoa in ranking
        ),
        unsafe_allow_html=True
    )


# ==================================================
# TOP 3 DO DASHBOARD (por mês)
# ==================================================

@st.cache_data(ttl=300, show_spinner=False)
def ler_top3_do_mes(armazem_id, ano, mes):
    """
    Pódio (até 3 ruas) com a nota que cada rua tinha no fechamento
    (último dia) do mês escolhido — mesma regra do pódio da tela
    inicial, só que para qualquer mês.
    """

    data_fechamento = banco._ultimo_dia_do_mes(ano, mes)

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT DISTINCT ON (rua)
            rua,
            nota,
            dupla
        FROM historico_notas
        WHERE armazem_id = %s
        AND (data_atualizacao AT TIME ZONE 'UTC' AT TIME ZONE 'America/Campo_Grande')::date <= %s
        ORDER BY rua, data_atualizacao DESC
        """, (armazem_id, data_fechamento))

        dados = cursor.fetchall()

    finally:
        banco.liberar(conn)

    ranking = [
        {
            "rua": linha[0],
            "nota": float(linha[1]),
            "dupla": linha[2] or "Sem dupla",
        }
        for linha in dados
        if linha[1] is not None and linha[1] > 0
    ]

    ranking.sort(key=lambda item: item["nota"], reverse=True)

    return ranking[:3], data_fechamento


@st.cache_data(ttl=300, show_spinner=False)
def _primeiro_mes_com_historico(armazem_id):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT MIN(
            (data_atualizacao AT TIME ZONE 'UTC' AT TIME ZONE 'America/Campo_Grande')::date
        )
        FROM historico_notas
        WHERE armazem_id = %s
        """, (armazem_id,))

        primeira_data = cursor.fetchone()[0]

    finally:
        banco.liberar(conn)

    return (primeira_data.year, primeira_data.month) if primeira_data else None


def _meses_disponiveis_dashboard(armazem_id):

    ultimo = banco._mes_fechado_mais_recente()

    primeiro = _primeiro_mes_com_historico(armazem_id) or (ultimo.year, ultimo.month)

    meses = []

    ano, mes = ultimo.year, ultimo.month

    # do mês fechado mais recente voltando até o primeiro com histórico
    while (ano, mes) >= primeiro:

        meses.append((ano, mes))

        mes -= 1

        if mes == 0:
            mes = 12
            ano -= 1

    return meses or [(ultimo.year, ultimo.month)]


# Separadores comuns ao digitar uma dupla: "João & Maria", "João e Maria",
# "João/Maria", "João, Maria", "João + Maria", "João - Maria"
_SEPARADOR_DUPLA = re.compile(r"\s*(?:&|/|\+|,|;|\s-\s|\s[eE]\s)\s*")


def _pessoas_da_dupla(texto_dupla, armazem_id):
    """
    Quebra o texto da dupla em nomes e procura o Perfil de cada um
    (nome, sobrenome ou nome completo — se mais de uma pessoa bater,
    não arrisca e cai nas iniciais). Devolve [(nome, foto), ...].
    """

    if not texto_dupla or texto_dupla.strip().lower() in VALORES_SEM_NOME | {"sem dupla"}:
        return []

    pessoas = []

    for parte in _SEPARADOR_DUPLA.split(texto_dupla):

        parte = parte.strip()

        if not parte:
            continue

        perfil = banco.encontrar_perfil_por_nome(parte, armazem_id)

        if perfil:
            pessoas.append((banco.nome_completo_perfil(perfil), perfil.get("foto")))
        else:
            pessoas.append((parte.title(), None))

    return pessoas


def _avatares_dupla(pessoas, cor):

    if not pessoas:
        return ""

    avatares = "".join(
        f'<div style="margin-left:{0 if indice == 0 else -12}px;'
        f'border:3px solid {cor};border-radius:50%;line-height:0;'
        f'background:#0b1120;">{_avatar_html(nome, foto, 58)}</div>'
        for indice, (nome, foto) in enumerate(pessoas)
    )

    return (
        '<div style="display:flex;justify-content:center;margin-top:.8rem;">'
        f'{avatares}</div>'
    )


def _card_podio(posicao, item, armazem_id):

    cor = CORES_POSICAO[posicao]

    pessoas = _pessoas_da_dupla(item["dupla"], armazem_id)

    nomes = (
        " &amp; ".join(html.escape(nome) for nome, _ in pessoas)
        if pessoas else html.escape(item["dupla"])
    )

    # o 1º lugar leva a taça ao lado da medalha
    if posicao == 1:
        topo = (
            '<div style="display:flex;justify-content:center;align-items:flex-end;gap:.7rem;">'
            f'{_taca_html(84)}{_medalha_html(1, 92)}'
            '</div>'
        )
    else:
        topo = (
            '<div style="display:flex;justify-content:center;">'
            f'{_medalha_html(posicao, 92)}</div>'
        )

    return (
        f'<div style="background:{cor}14;border:1px solid {cor}55;'
        'border-radius:1.1rem;padding:1.3rem 1rem;text-align:center;height:100%;">'
        f'{topo}'
        f'<div style="font-weight:800;font-size:1.1rem;margin-top:.6rem;">'
        f'{html.escape(item["rua"])}</div>'
        f'<div style="font-size:2.2rem;font-weight:800;color:{cor};'
        f'margin-top:.2rem;line-height:1.1;">{item["nota"]:.1f}</div>'
        f'{_avatares_dupla(pessoas, cor)}'
        f'<div style="font-size:.82rem;opacity:.8;margin-top:.5rem;font-weight:600;">'
        f'{nomes}</div>'
        '</div>'
    )


def _render_dashboard(armazem_id):

    meses = _meses_disponiveis_dashboard(armazem_id)

    st.caption(
        "As 3 ruas com as melhores notas no fechamento do mês. Por "
        "padrão aparece o último mês fechado — use a busca para ver "
        "os meses anteriores."
    )

    escolhido = st.selectbox(
        "Mês",
        meses,
        format_func=lambda m: _rotulo_mes(*m),
        key="rec_dash_mes"
    )

    top3, data_fechamento = ler_top3_do_mes(armazem_id, *escolhido)

    st.markdown(
        f"##### 🏆 Top 3 de {_rotulo_mes(*escolhido)}"
    )

    st.caption(
        f"Notas no fechamento de {data_fechamento.strftime('%d/%m/%Y')}."
    )

    if not top3:

        st.info("Não há notas registradas no Dashboard até o fechamento desse mês.")
        return

    colunas = st.columns(3)

    for indice, item in enumerate(top3):

        with colunas[indice]:

            st.markdown(
                _card_podio(indice + 1, item, armazem_id),
                unsafe_allow_html=True
            )


# ==================================================
# QUADRO DE MEDALHAS
# ==================================================
# Regra: no FECHAMENTO de cada mês, quem fica em 1º, 2º e 3º lugar
# recebe 🥇, 🥈 e 🥉 em cada ranking:
#   - SAC: posições do ranking de chamados daquele mês (só conta se o
#     mês teve pelo menos um chamado — mês sem nenhum chamado não é
#     competição);
#   - Auditoria: posições do ranking (função "Todas") daquele mês;
#   - Dashboard: as 3 ruas do pódio do mês; a medalha vai para cada
#     pessoa da dupla da rua.
# Empatados no mesmo lugar recebem a mesma medalha.
#
# As medalhas são GRAVADAS no banco quando o mês fecha (tabelas
# criadas sozinhas abaixo), então ficam fixas: uma medalha conquistada
# não some se um registro antigo for editado ou apagado depois. O
# mês em andamento ainda não vale — só os meses fechados.
#
# Visão: cada colaborador vê só as suas medalhas; Gestão e Fundador
# veem o quadro completo.

CATEGORIAS_MEDALHA = {
    "sac": ("😊", "SAC"),
    "auditoria": ("🎯", "Auditoria"),
    "dashboard": ("📊", "Dashboard"),
}

NOMES_MEDALHA = {1: "Ouro", 2: "Prata", 3: "Bronze"}


@st.cache_resource(show_spinner=False)
def _garantir_tabelas_recordes():

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recordes_medalhas (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            mes_ref DATE NOT NULL,
            categoria TEXT NOT NULL
                CHECK (categoria IN ('sac', 'auditoria', 'dashboard')),
            chave TEXT NOT NULL,
            nome TEXT NOT NULL,
            posicao INTEGER NOT NULL CHECK (posicao BETWEEN 1 AND 3),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (armazem_id, mes_ref, categoria, chave)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recordes_fechamentos (
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            categoria TEXT NOT NULL,
            mes_ref DATE NOT NULL,
            fechado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (armazem_id, categoria, mes_ref)
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recordes_medalhas_armazem ON recordes_medalhas (armazem_id)")

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    return True


def _meses_entre(primeiro, ultimo):

    meses = []

    ano, mes = primeiro

    while (ano, mes) <= ultimo:

        meses.append((ano, mes))

        mes += 1

        if mes == 13:
            mes = 1
            ano += 1

    return meses


def _primeiro_mes(datas):

    datas = [d for d in datas if d]

    if not datas:
        return None

    primeira = min(datas)

    return (primeira.year, primeira.month)


def _calcular_medalhas_do_mes(armazem_id, categoria, ano, mes):
    """Devolve [(chave, nome, posicao 1..3), ...] do mês (já fechado)."""

    entradas = []

    if categoria == "sac":

        ranking, total_chamados = calcular_ranking_sac(armazem_id, (ano, mes))

        if total_chamados > 0:
            entradas = [
                (_chave(p["nome"]), p["nome"], posicao)
                for posicao, p in ranking
                if posicao <= 3
            ]

    elif categoria == "auditoria":

        ranking = calcular_ranking_auditoria(armazem_id, (ano, mes), "Todas")

        entradas = [
            (_chave(p["nome"]), p["nome"], posicao)
            for posicao, p in ranking
            if posicao <= 3
        ]

    else:

        top3, _ = ler_top3_do_mes(armazem_id, ano, mes)

        for indice, item in enumerate(top3):

            for nome, _foto in _pessoas_da_dupla(item["dupla"], armazem_id):
                entradas.append((_chave(nome), nome, indice + 1))

    return entradas


def _fechar_meses_pendentes(armazem_id):
    """
    Concede e grava as medalhas dos meses já fechados que ainda não
    foram processados. Na primeira vez, processa todo o histórico
    existente; depois, só o mês que acabou de fechar.
    """

    _garantir_tabelas_recordes()

    fechado = banco._mes_fechado_mais_recente()
    ultimo = (fechado.year, fechado.month)

    primeiros = {
        "sac": _primeiro_mes(
            c["data_erro"] for c in banco.ler_analise_tecnica(armazem_id)
        ),
        "auditoria": _primeiro_mes(
            r["data_atividade"] for r in banco.ler_auditoria(armazem_id)
        ),
        "dashboard": _primeiro_mes_com_historico(armazem_id),
    }

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT categoria, mes_ref
        FROM recordes_fechamentos
        WHERE armazem_id = %s
        """, (armazem_id,))

        feitos = {(cat, (mes.year, mes.month)) for cat, mes in cursor.fetchall()}

    finally:
        banco.liberar(conn)

    pendentes = [
        (categoria, mes)
        for categoria, primeiro in primeiros.items()
        if primeiro
        for mes in _meses_entre(primeiro, ultimo)
        if (categoria, mes) not in feitos
    ]

    if not pendentes:
        return 0

    # calcula tudo ANTES de abrir a conexão de escrita
    resultados = [
        (
            categoria,
            mes,
            _calcular_medalhas_do_mes(armazem_id, categoria, *mes)
        )
        for categoria, mes in pendentes
    ]

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        for categoria, (ano, mes), entradas in resultados:

            mes_ref = date(ano, mes, 1)

            for chave, nome, posicao in entradas:

                cursor.execute("""
                INSERT INTO recordes_medalhas
                    (armazem_id, mes_ref, categoria, chave, nome, posicao)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (armazem_id, mes_ref, categoria, chave) DO NOTHING
                """, (armazem_id, mes_ref, categoria, chave, nome, posicao))

            cursor.execute("""
            INSERT INTO recordes_fechamentos (armazem_id, categoria, mes_ref)
            VALUES (%s, %s, %s)
            ON CONFLICT (armazem_id, categoria, mes_ref) DO NOTHING
            """, (armazem_id, categoria, mes_ref))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    ler_medalhas.clear()

    return len(pendentes)


@st.cache_data(ttl=120, show_spinner=False)
def _verificar_fechamentos(armazem_id):

    try:
        return _fechar_meses_pendentes(armazem_id)
    except Exception as erro:
        print(f"⚠️ Recordes: falha ao fechar meses: {erro}", flush=True)
        return -1


@st.cache_data(ttl=60, show_spinner=False)
def ler_medalhas(armazem_id):

    _garantir_tabelas_recordes()

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT categoria, mes_ref, chave, nome, posicao
        FROM recordes_medalhas
        WHERE armazem_id = %s
        ORDER BY mes_ref DESC, categoria ASC, posicao ASC
        """, (armazem_id,))

        eventos = [
            {
                "categoria": linha[0],
                "mes_ref": linha[1],
                "chave": linha[2],
                "nome": linha[3],
                "posicao": linha[4],
            }
            for linha in cursor.fetchall()
        ]

    finally:
        banco.liberar(conn)

    return eventos


def _novo_acumulador(nome):

    return {
        "nome": nome,
        "total": {1: 0, 2: 0, 3: 0},
        "por_categoria": {c: {1: 0, 2: 0, 3: 0} for c in CATEGORIAS_MEDALHA},
        "eventos": [],
    }


def _somar_evento(acumulador, evento):

    acumulador["total"][evento["posicao"]] += 1
    acumulador["por_categoria"][evento["categoria"]][evento["posicao"]] += 1
    acumulador["eventos"].append(evento)


def _agregar_por_pessoa(eventos):

    pessoas = {}

    for evento in eventos:

        acumulador = pessoas.setdefault(
            evento["chave"],
            _novo_acumulador(evento["nome"])
        )

        _somar_evento(acumulador, evento)

    return pessoas


def _chip_medalha(posicao, quantidade):

    cor = CORES_POSICAO[posicao]

    return (
        f'<span style="display:inline-flex;align-items:center;gap:.3rem;'
        f'background:{cor}1f;border:1px solid {cor}55;border-radius:999px;'
        f'padding:.1rem .65rem .1rem .4rem;font-weight:800;font-size:.82rem;'
        f'color:{cor};white-space:nowrap;">'
        f'{_medalha_html(posicao, 26)}×{quantidade}</span>'
    )


def _render_minhas_medalhas(pessoas, usuario, armazem_id):

    minha = _novo_acumulador("")

    for pessoa in pessoas.values():

        if banco.pessoa_pertence_ao_usuario(pessoa["nome"], usuario, armazem_id):

            for evento in pessoa["eventos"]:
                _somar_evento(minha, evento)

    total_medalhas = sum(minha["total"].values())

    blocos = "".join(
        '<div style="text-align:center;min-width:92px;">'
        f'{_medalha_html(posicao, 84)}'
        f'<div style="font-size:1.9rem;font-weight:800;color:{CORES_POSICAO[posicao]};'
        f'line-height:1.1;margin-top:.2rem;">×{minha["total"][posicao]}</div>'
        f'<div style="font-size:.75rem;opacity:.7;font-weight:700;">{NOMES_MEDALHA[posicao]}</div>'
        '</div>'
        for posicao in (1, 2, 3)
    )

    st.markdown(
        '<div style="background:#f59e0b12;border:1px solid #f59e0b45;'
        'border-radius:1.2rem;padding:1.4rem 1.6rem;margin-top:.4rem;">'
        '<div style="font-size:.72rem;font-weight:800;letter-spacing:.5px;'
        'text-transform:uppercase;opacity:.65;text-align:center;">Suas medalhas</div>'
        '<div style="display:flex;justify-content:center;gap:2.2rem;flex-wrap:wrap;'
        f'margin-top:.8rem;">{blocos}</div>'
        '<div style="text-align:center;margin-top:.9rem;font-size:.95rem;font-weight:700;">'
        f'Total: {_plural(total_medalhas, "medalha", "medalhas")}</div>'
        '</div>',
        unsafe_allow_html=True
    )

    if total_medalhas == 0:

        st.info(
            "Você ainda não tem medalhas. Elas são concedidas no fechamento "
            "de cada mês, para quem fica entre os 3 primeiros."
        )

    else:

        st.markdown("##### Por categoria")

        linhas = []

        for categoria, (icone, rotulo) in CATEGORIAS_MEDALHA.items():

            contagem = minha["por_categoria"][categoria]

            chips = "".join(
                _chip_medalha(posicao, contagem[posicao])
                for posicao in (1, 2, 3)
                if contagem[posicao] > 0
            ) or '<span style="opacity:.5;font-size:.8rem;">—</span>'

            linhas.append(
                '<div style="display:flex;align-items:center;justify-content:space-between;'
                'gap:1rem;flex-wrap:wrap;padding:.55rem .2rem;'
                'border-bottom:1px solid rgba(148,163,184,.18);">'
                f'<div style="font-weight:700;">{icone} {rotulo}</div>'
                f'<div style="display:flex;gap:.4rem;flex-wrap:wrap;">{chips}</div>'
                '</div>'
            )

        st.markdown("".join(linhas), unsafe_allow_html=True)

        st.markdown("##### Últimas conquistas")

        recentes = sorted(
            minha["eventos"],
            key=lambda e: (e["mes_ref"], -e["posicao"]),
            reverse=True
        )[:10]

        st.markdown(
            "".join(
                '<div style="display:flex;align-items:center;gap:.7rem;padding:.3rem .2rem;">'
                f'{_medalha_html(e["posicao"], 30)}'
                f'<div style="font-size:.88rem;">'
                f'<b>{NOMES_MEDALHA[e["posicao"]]}</b> · '
                f'{CATEGORIAS_MEDALHA[e["categoria"]][0]} {CATEGORIAS_MEDALHA[e["categoria"]][1]}'
                f' · {_rotulo_mes(e["mes_ref"].year, e["mes_ref"].month)}</div>'
                '</div>'
                for e in recentes
            ),
            unsafe_allow_html=True
        )

    st.caption(
        "🔒 Por privacidade, você vê apenas as suas próprias medalhas. O "
        "quadro completo fica disponível só para a Gestão e o Fundador."
    )


def _render_quadro_completo(pessoas, usuario, armazem_id):

    if not pessoas:

        st.info(
            "Nenhuma medalha concedida ainda. Elas são concedidas no "
            "fechamento de cada mês."
        )
        return

    totais = {
        posicao: sum(p["total"][posicao] for p in pessoas.values())
        for posicao in (1, 2, 3)
    }

    _mostrar_kpis([
        _kpi("🏅", "Pessoas com medalhas", str(len(pessoas)), "#3b82f6"),
        _kpi("🥇", "Ouro concedidas", str(totais[1]), CORES_POSICAO[1]),
        _kpi("🥈", "Prata concedidas", str(totais[2]), CORES_POSICAO[2]),
        _kpi("🥉", "Bronze concedidas", str(totais[3]), CORES_POSICAO[3]),
    ])

    ordenadas = sorted(
        pessoas.values(),
        key=lambda p: (-p["total"][1], -p["total"][2], -p["total"][3], p["nome"].lower())
    )

    posicoes = _atribuir_posicoes(
        ordenadas,
        lambda p: (p["total"][1], p["total"][2], p["total"][3])
    )

    # fotos dos Perfis, quando houver
    fotos = {}

    for perfil in banco.ler_perfis(armazem_id):

        if perfil.get("foto"):
            fotos[_chave(banco.nome_completo_perfil(perfil))] = perfil["foto"]

    linhas = []

    for posicao, pessoa in zip(posicoes, ordenadas):

        por_categoria = " · ".join(
            f'{icone} {rotulo} {sum(pessoa["por_categoria"][categoria].values())}'
            for categoria, (icone, rotulo) in CATEGORIAS_MEDALHA.items()
        )

        linhas.append(_linha_ranking(
            posicao,
            pessoa["nome"],
            fotos.get(_chave(pessoa["nome"])),
            por_categoria,
            [
                _chip_medalha(p, pessoa["total"][p])
                for p in (1, 2, 3)
                if pessoa["total"][p] > 0
            ],
            banco.pessoa_pertence_ao_usuario(pessoa["nome"], usuario, armazem_id)
        ))

    st.markdown("".join(linhas), unsafe_allow_html=True)


def _render_medalhas(armazem_id, usuario, ve_tudo):

    st.caption(
        "No fechamento de cada mês, quem fica em 1º, 2º e 3º lugar no SAC, "
        "na Auditoria e no Top 3 do Dashboard (para a dupla da rua) ganha "
        "🥇, 🥈 e 🥉. O mês em andamento só vale quando fechar."
    )

    _verificar_fechamentos(armazem_id)

    pessoas = _agregar_por_pessoa(ler_medalhas(armazem_id))

    if ve_tudo:
        _render_quadro_completo(pessoas, usuario, armazem_id)
    else:
        _render_minhas_medalhas(pessoas, usuario, armazem_id)


# ==================================================
# TELA
# ==================================================

def render():

    armazem_id = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    usuario = st.session_state.get("usuario", "")
    tipo_usuario = st.session_state.get("tipo_usuario", "usuario")

    # Só Gestão e Fundador veem a lista completa dos rankings do SAC e
    # da Auditoria; os colaboradores veem apenas a própria posição e
    # quantas pessoas estão acima/abaixo (evita exposição e zoação).
    ve_tudo = (
        tipo_usuario in ("fundador", "gestao")
        or usuario.startswith(("Fundador.", "Gestao."))
    )

    st.subheader("🏆 Recordes")

    st.caption(
        "Os destaques da operação: quem mais se empenha aparece no topo."
    )

    aba_sac, aba_auditoria, aba_dashboard, aba_medalhas = st.tabs([
        "😊 SAC",
        "🎯 Auditoria",
        "📊 Dashboard",
        "🏅 Medalhas",
    ])

    with aba_sac:
        _render_sac(armazem_id, usuario, ve_tudo)

    with aba_auditoria:
        _render_auditoria(armazem_id, usuario, ve_tudo)

    with aba_dashboard:
        _render_dashboard(armazem_id)

    with aba_medalhas:
        _render_medalhas(armazem_id, usuario, ve_tudo)

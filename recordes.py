import html
from datetime import datetime
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
            f'<div style="font-size:1.9rem;line-height:1;text-align:center;">'
            f'{MEDALHAS[posicao]}</div>'
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
    Posição de competição: empatados dividem a mesma posição e a
    seguinte "pula" (1, 1, 1, 4...). `itens` já vem ordenado.
    """

    posicoes = []

    for indice, item in enumerate(itens):

        if indice > 0 and chave_empate(item) == chave_empate(itens[indice - 1]):
            posicoes.append(posicoes[-1])
        else:
            posicoes.append(indice + 1)

    return posicoes


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

    sem_chamados = sum(1 for _, p in ranking if p["chamados"] == 0)

    kpis = [
        _kpi("👥", "Colaboradores no ranking", str(len(ranking)), "#3b82f6"),
    ]

    # números de chamados (inclusive "quantos estão sem chamado") só
    # aparecem para quem gerencia
    if ve_tudo:
        kpis.append(
            _kpi("✅", "Sem nenhum chamado", str(sem_chamados), "#22c55e")
        )
        kpis.append(
            _kpi("📋", "Chamados no período", str(total_chamados), "#f59e0b")
        )

    _mostrar_kpis(kpis)

    itens = [
        (
            posicao,
            pessoa,
            banco.pessoa_pertence_ao_usuario(pessoa["nome"], usuario, armazem_id)
        )
        for posicao, pessoa in ranking
    ]

    # Colaboradores veem só o pódio (posições 1 a 3); Gestão e
    # Fundador veem a lista completa.
    visiveis = itens if ve_tudo else [i for i in itens if i[0] <= 3]

    st.markdown(
        "".join(
            _linha_sac(posicao, pessoa, e_voce, detalhado=(ve_tudo or e_voce))
            for posicao, pessoa, e_voce in visiveis
        ),
        unsafe_allow_html=True
    )

    if not ve_tudo:

        minha = next((i for i in itens if i[2] and i[0] > 3), None)

        if minha:

            st.markdown("##### 📍 Sua posição")

            st.markdown(
                _linha_sac(minha[0], minha[1], True, detalhado=True),
                unsafe_allow_html=True
            )

        st.caption(
            "🔒 Você vê o pódio e a sua própria posição. A lista completa "
            "fica disponível só para a Gestão e o Fundador."
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

    total_acertos = sum(p["acertos"] for _, p in ranking)
    total_erros = sum(p["erros"] for _, p in ranking)

    kpis = [
        _kpi("👥", "Colaboradores no ranking", str(len(ranking)), "#3b82f6"),
        _kpi("✅", "Acertos no período", str(total_acertos), "#22c55e"),
    ]

    # o total de erros só aparece para quem gerencia
    if ve_tudo:
        kpis.append(
            _kpi("❌", "Erros no período", str(total_erros), "#ef4444")
        )

    _mostrar_kpis(kpis)

    itens = [
        (
            posicao,
            pessoa,
            banco.pessoa_pertence_ao_usuario(pessoa["nome"], usuario, armazem_id)
        )
        for posicao, pessoa in ranking
    ]

    # Colaboradores veem só o pódio (posições 1 a 3); Gestão e
    # Fundador veem a lista completa.
    visiveis = itens if ve_tudo else [i for i in itens if i[0] <= 3]

    st.markdown(
        "".join(
            _linha_auditoria(posicao, pessoa, e_voce, detalhado=(ve_tudo or e_voce))
            for posicao, pessoa, e_voce in visiveis
        ),
        unsafe_allow_html=True
    )

    if not ve_tudo:

        minha = next((i for i in itens if i[2] and i[0] > 3), None)

        if minha:

            st.markdown("##### 📍 Sua posição")

            st.markdown(
                _linha_auditoria(minha[0], minha[1], True, detalhado=True),
                unsafe_allow_html=True
            )

        st.caption(
            "🔒 Você vê o pódio e a sua própria posição. A lista completa "
            "fica disponível só para a Gestão e o Fundador."
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


def _card_podio(posicao, item):

    cor = CORES_POSICAO[posicao]

    return (
        f'<div style="background:{cor}14;border:1px solid {cor}55;'
        'border-radius:1.1rem;padding:1.3rem 1rem;text-align:center;height:100%;">'
        f'<div style="font-size:2.5rem;line-height:1;">{MEDALHAS[posicao]}</div>'
        f'<div style="font-weight:800;font-size:1.1rem;margin-top:.5rem;">'
        f'{html.escape(item["rua"])}</div>'
        f'<div style="font-size:2.2rem;font-weight:800;color:{cor};'
        f'margin-top:.2rem;line-height:1.1;">{item["nota"]:.1f}</div>'
        f'<div style="font-size:.8rem;opacity:.7;margin-top:.4rem;">'
        f'👥 {html.escape(item["dupla"])}</div>'
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
                _card_podio(indice + 1, item),
                unsafe_allow_html=True
            )


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

    # Só Gestão e Fundador veem a lista completa dos rankings; os
    # colaboradores veem o pódio e a própria posição (evita que
    # alguém seja exposto/zoado pelos números dos colegas).
    ve_tudo = (
        tipo_usuario in ("fundador", "gestao")
        or usuario.startswith(("Fundador.", "Gestao."))
    )

    st.subheader("🏆 Recordes")

    st.caption(
        "Os destaques da operação: quem mais se empenha aparece no topo."
    )

    aba_sac, aba_auditoria, aba_dashboard = st.tabs([
        "😊 SAC",
        "🎯 Auditoria",
        "📊 Dashboard",
    ])

    with aba_sac:
        _render_sac(armazem_id, usuario, ve_tudo)

    with aba_auditoria:
        _render_auditoria(armazem_id, usuario, ve_tudo)

    with aba_dashboard:
        _render_dashboard(armazem_id)

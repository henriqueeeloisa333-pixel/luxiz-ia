import html

import pandas as pd
import streamlit as st

import banco
import estilos


# ==================================================
# AUTOAVALIAÇÃO DE RUAS (Dashboard)
# ==================================================
# Fluxo:
#   1. Separador/Conferente organiza a rua e envia a nota que acha
#      justa, escolhendo qual supervisor (Gestão/Fundador) vai conferir.
#   2. O supervisor vê a solicitação e:
#        ✅ aprova  -> a nota proposta vai para o Dashboard
#        ✏️ ajusta  -> escolhe outra nota e explica o motivo; a nota
#                      ajustada vai para o Dashboard e o colaborador
#                      vê a explicação.
#   3. Nada muda no Dashboard até o supervisor responder.

NOTA_MIN = 0.0
NOTA_MAX = 5.0

COR_PENDENTE = "#f59e0b"
COR_APROVADA = "#22c55e"
COR_AJUSTADA = "#a855f7"


# ==================================================
# PERMISSÕES
# ==================================================

def eh_supervisor(usuario, tipo):

    return (
        tipo in ("fundador", "gestao")
        or (usuario or "").startswith(("Fundador.", "Gestao."))
    )


def eh_fundador(usuario, tipo):

    return tipo == "fundador" or (usuario or "").startswith("Fundador.")


def eh_solicitante(usuario):

    return (usuario or "").startswith(("Separador.", "Conferente."))


# ==================================================
# TABELA (criada sozinha na primeira vez)
# ==================================================

@st.cache_resource(show_spinner=False)
def _garantir_tabela_avaliacoes():

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_avaliacoes (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            rua TEXT NOT NULL,
            dupla TEXT NOT NULL,
            nota_proposta NUMERIC(3,1) NOT NULL
                CHECK (nota_proposta >= 0 AND nota_proposta <= 5),
            solicitante TEXT NOT NULL,
            supervisor TEXT NOT NULL,
            observacao TEXT,
            status TEXT NOT NULL DEFAULT 'pendente'
                CHECK (status IN ('pendente', 'aprovada', 'ajustada')),
            nota_final NUMERIC(3,1)
                CHECK (nota_final IS NULL OR (nota_final >= 0 AND nota_final <= 5)),
            motivo TEXT,
            respondido_por TEXT,
            respondido_em TIMESTAMP,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_dash_aval_armazem
        ON dashboard_avaliacoes (armazem_id, status, criado_em DESC)
        """)

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    return True


# ==================================================
# BANCO
# ==================================================

def _hora_local(coluna):

    return f"({coluna} AT TIME ZONE 'UTC' AT TIME ZONE 'America/Campo_Grande')"


@st.cache_data(ttl=15, show_spinner=False)
def ler_avaliacoes(armazem_id, limite=300):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute(f"""
        SELECT
            id, rua, dupla, nota_proposta, solicitante, supervisor,
            observacao, status, nota_final, motivo, respondido_por,
            {_hora_local('respondido_em')},
            {_hora_local('criado_em')}
        FROM dashboard_avaliacoes
        WHERE armazem_id = %s
        ORDER BY criado_em DESC, id DESC
        LIMIT %s
        """, (armazem_id, limite))

        colunas = [
            "id", "rua", "dupla", "nota_proposta", "solicitante", "supervisor",
            "observacao", "status", "nota_final", "motivo", "respondido_por",
            "respondido_em", "criado_em"
        ]

        dados = []

        for row in cursor.fetchall():

            registro = dict(zip(colunas, row))

            registro["nota_proposta"] = float(registro["nota_proposta"])

            if registro["nota_final"] is not None:
                registro["nota_final"] = float(registro["nota_final"])

            dados.append(registro)

    finally:
        banco.liberar(conn)

    return dados


def ler_supervisores(armazem_id):
    """Usuários do armazém que podem conferir uma avaliação (Gestão/Fundador)."""

    supervisores = []

    for _, nome, tipo_usuario, _ in banco.listar_usuarios(armazem_id):

        if nome and eh_supervisor(nome, tipo_usuario):
            supervisores.append(nome)

    return sorted(supervisores)


def criar_avaliacao(
    rua, dupla, nota, solicitante, supervisor, observacao, armazem_id
):

    rua = (rua or "").strip()
    dupla = (dupla or "").strip()

    if not rua or rua not in banco.listar_ruas(armazem_id):
        return False, "Escolha uma rua válida."

    if not dupla:
        return False, "Informe quem organizou a rua (a dupla)."

    nota = round(float(nota), 1)

    if nota < NOTA_MIN or nota > NOTA_MAX:
        return False, "A nota precisa estar entre 0 e 5."

    if supervisor not in ler_supervisores(armazem_id):
        return False, "Escolha um supervisor válido para conferir a nota."

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT 1 FROM dashboard_avaliacoes
        WHERE armazem_id = %s AND rua = %s
          AND solicitante = %s AND status = 'pendente'
        LIMIT 1
        """, (armazem_id, rua, solicitante))

        if cursor.fetchone():
            conn.rollback()
            return False, (
                f"Você já tem uma avaliação da {rua} aguardando resposta. "
                "Espere o supervisor responder antes de enviar outra."
            )

        cursor.execute("""
        INSERT INTO dashboard_avaliacoes
            (armazem_id, rua, dupla, nota_proposta,
             solicitante, supervisor, observacao)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            armazem_id, rua, dupla, nota,
            solicitante, supervisor, (observacao or "").strip() or None
        ))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    ler_avaliacoes.clear()

    return True, "ok"


def _reabrir(id_avaliacao, armazem_id):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE dashboard_avaliacoes
        SET status = 'pendente', nota_final = NULL, motivo = NULL,
            respondido_por = NULL, respondido_em = NULL
        WHERE id = %s AND armazem_id = %s
        """, (id_avaliacao, armazem_id))

        conn.commit()

    except Exception:

        conn.rollback()

    finally:
        banco.liberar(conn)

    ler_avaliacoes.clear()


def _responder(
    id_avaliacao, status, nota_final, motivo,
    respondente, pode_qualquer, armazem_id
):
    """
    Marca a avaliação como respondida (com a linha travada, para duas
    pessoas não responderem a mesma ao mesmo tempo) e então grava a
    nota no Dashboard. Se gravar no Dashboard falhar, a avaliação
    volta a ficar pendente.
    """

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT rua, dupla, nota_proposta, supervisor, status
        FROM dashboard_avaliacoes
        WHERE id = %s AND armazem_id = %s
        FOR UPDATE
        """, (id_avaliacao, armazem_id))

        linha = cursor.fetchone()

        if not linha:
            conn.rollback()
            return False, "Avaliação não encontrada."

        rua, dupla, nota_proposta, supervisor, status_atual = linha
        nota_proposta = float(nota_proposta)

        if status_atual != "pendente":
            conn.rollback()
            return False, "Essa avaliação já foi respondida."

        if not pode_qualquer and supervisor != respondente:
            conn.rollback()
            return False, "Essa avaliação foi enviada para outro supervisor."

        if status == "aprovada":

            nota_aplicada = nota_proposta
            motivo = None

        else:

            nota_aplicada = round(float(nota_final), 1)
            motivo = (motivo or "").strip()

            if nota_aplicada < NOTA_MIN or nota_aplicada > NOTA_MAX:
                conn.rollback()
                return False, "A nota precisa estar entre 0 e 5."

            if abs(nota_aplicada - nota_proposta) < 0.05:
                conn.rollback()
                return False, (
                    "A nota escolhida é igual à proposta — use "
                    "✅ Aprovar em vez de ajustar."
                )

            if not motivo:
                conn.rollback()
                return False, "Explique o motivo de ter mudado a nota."

        cursor.execute("""
        UPDATE dashboard_avaliacoes
        SET status = %s, nota_final = %s, motivo = %s,
            respondido_por = %s, respondido_em = CURRENT_TIMESTAMP
        WHERE id = %s AND armazem_id = %s
        """, (
            status, nota_aplicada, motivo,
            respondente, id_avaliacao, armazem_id
        ))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    try:

        banco.salvar_dados(
            rua, nota_aplicada, dupla, armazem_id, usuario=respondente
        )

    except Exception:

        _reabrir(id_avaliacao, armazem_id)
        raise

    ler_avaliacoes.clear()

    return True, nota_aplicada


def aprovar_avaliacao(id_avaliacao, respondente, pode_qualquer, armazem_id):

    return _responder(
        id_avaliacao, "aprovada", None, None,
        respondente, pode_qualquer, armazem_id
    )


def ajustar_avaliacao(
    id_avaliacao, nota_final, motivo, respondente, pode_qualquer, armazem_id
):

    return _responder(
        id_avaliacao, "ajustada", nota_final, motivo,
        respondente, pode_qualquer, armazem_id
    )


# ==================================================
# APOIO VISUAL
# ==================================================

def _fmt_nota(valor):

    return f"{float(valor):.1f}".replace(".", ",")


def _nome(usuario):

    if not usuario:
        return "—"

    perfil = banco.ler_perfil(usuario)

    if perfil:
        return banco.nome_completo_perfil(perfil)

    if "." in usuario:
        return usuario.split(".", 1)[1].strip().title()

    return usuario


def _icone_supervisor(usuario):

    return "👑" if usuario.startswith("Fundador.") else "🛡️"


def _card(avaliacao, perspectiva):
    """HTML do card de uma avaliação. perspectiva: 'solicitante' ou 'supervisor'."""

    status = avaliacao["status"]

    if status == "pendente":
        cor, chip = COR_PENDENTE, "⏳ Aguardando"
    elif status == "aprovada":
        cor, chip = COR_APROVADA, "✅ Aprovada"
    else:
        cor, chip = COR_AJUSTADA, "🔄 Nota ajustada"

    quando = avaliacao["criado_em"].strftime("%d/%m %H:%M")

    if perspectiva == "solicitante":
        quem = (
            f"Enviada para <b>{html.escape(_nome(avaliacao['supervisor']))}</b>"
            f" · {quando}"
        )
    else:
        quem = (
            f"De <b>{html.escape(_nome(avaliacao['solicitante']))}</b>"
            f" · para {html.escape(_nome(avaliacao['supervisor']))}"
            f" · {quando}"
        )

    obs_html = ""

    if avaliacao["observacao"]:
        obs_html = (
            '<div style="margin-top:.5rem;font-size:.8rem;opacity:.85;">'
            f'💬 {html.escape(avaliacao["observacao"])}</div>'
        )

    resultado_html = ""

    if status == "aprovada":

        resultado_html = (
            f'<div style="margin-top:.6rem;font-size:.85rem;color:{cor};'
            'font-weight:700;">'
            f'Nota aprovada: {_fmt_nota(avaliacao["nota_final"])} '
            f'(por {html.escape(_nome(avaliacao["respondido_por"]))}'
            f' em {avaliacao["respondido_em"].strftime("%d/%m %H:%M")})</div>'
        )

    elif status == "ajustada":

        resultado_html = (
            f'<div style="margin-top:.6rem;font-size:.85rem;color:{cor};'
            'font-weight:700;">'
            f'Proposta {_fmt_nota(avaliacao["nota_proposta"])} → ficou '
            f'{_fmt_nota(avaliacao["nota_final"])} '
            f'(por {html.escape(_nome(avaliacao["respondido_por"]))}'
            f' em {avaliacao["respondido_em"].strftime("%d/%m %H:%M")})</div>'
            f'<div style="margin-top:.35rem;padding:.5rem .7rem;'
            f'border-left:4px solid {cor};background:{cor}14;'
            'border-radius:.4rem;font-size:.82rem;">'
            f'<b>Motivo:</b> {html.escape(avaliacao["motivo"] or "—")}</div>'
        )

    return (
        f'<div style="background:{cor}10;border:1px solid {cor}45;'
        'border-radius:.9rem;padding:.9rem 1rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:.5rem;">'
        f'<div><div style="font-weight:800;font-size:1.05rem;">'
        f'📍 {html.escape(avaliacao["rua"])}</div>'
        f'<div style="font-size:.8rem;opacity:.75;">'
        f'👥 {html.escape(avaliacao["dupla"])}</div></div>'
        f'<span style="background:{cor}22;color:{cor};border:1px solid {cor}55;'
        'padding:.15rem .6rem;border-radius:999px;font-size:.7rem;'
        f'font-weight:800;white-space:nowrap;">{chip}</span></div>'
        '<div style="margin-top:.5rem;">'
        f'<span style="font-size:1.8rem;font-weight:800;color:{cor};'
        f'line-height:1;">{_fmt_nota(avaliacao["nota_proposta"])}</span>'
        '<span style="font-size:.8rem;opacity:.7;margin-left:.4rem;">'
        'nota proposta</span></div>'
        f'<div style="margin-top:.4rem;font-size:.76rem;opacity:.7;">{quem}</div>'
        f'{obs_html}{resultado_html}'
        '</div>'
    )


# ==================================================
# TELA DO COLABORADOR (Separador / Conferente)
# ==================================================

def _tela_solicitante(avaliacoes, usuario, armazem_id):

    minhas = [a for a in avaliacoes if a["solicitante"] == usuario]

    tab_nova, tab_minhas = st.tabs([
        "📝 Pedir avaliação",
        f"📋 Minhas avaliações ({len(minhas)})",
    ])

    with tab_nova:

        st.caption(
            "Organizou uma rua? Dê a nota que você acha justa e escolha quem "
            "vai conferir. A nota só vai para o Dashboard depois que o "
            "supervisor responder — se ele mudar a nota, você vê o motivo."
        )

        ruas = banco.listar_ruas(armazem_id)
        supervisores = ler_supervisores(armazem_id)

        if not ruas:

            st.info("Nenhuma rua cadastrada ainda.")

        elif not supervisores:

            st.warning(
                "Não há nenhum supervisor (Gestão/Fundador) cadastrado "
                "para conferir a nota."
            )

        else:

            rua = st.selectbox(
                "Rua que você organizou",
                ruas,
                key="aval_rua"
            )

            nota_painel = banco.ler_notas(armazem_id).get(rua)

            st.caption(
                f"Nota atual da {rua} no painel: "
                f"{_fmt_nota(nota_painel) if nota_painel else 'ainda sem nota'}"
            )

            dupla_padrao = (
                banco.ler_duplas(armazem_id).get(rua)
                or _nome(usuario)
            )

            with st.form("form_avaliacao_rua", clear_on_submit=True):

                dupla = st.text_input(
                    "Dupla (quem organizou)",
                    value=dupla_padrao,
                    key=f"aval_dupla_{rua}"
                )

                nota = st.slider(
                    "Nota que você acha justa",
                    NOTA_MIN,
                    NOTA_MAX,
                    3.0,
                    0.1,
                    format="%.1f"
                )

                supervisor = st.selectbox(
                    "Quem vai conferir a nota",
                    supervisores,
                    format_func=lambda u: f"{_icone_supervisor(u)} {_nome(u)}"
                )

                observacao = st.text_input(
                    "Observação (opcional)",
                    placeholder="Ex.: rua limpa, paletes alinhados, etiquetas conferidas..."
                )

                enviou = st.form_submit_button(
                    "📤 Enviar para avaliação",
                    width='stretch'
                )

            if enviou:

                with estilos.mostrar_processando("enviando avaliação..."):

                    ok, erro = criar_avaliacao(
                        rua, dupla, nota, usuario,
                        supervisor, observacao, armazem_id
                    )

                if ok:

                    estilos.notificar_sucesso("avaliação enviada ao supervisor.")
                    st.rerun()

                else:

                    st.error(erro)

    with tab_minhas:

        if not minhas:

            st.info("Você ainda não enviou nenhuma avaliação.")

        else:

            for avaliacao in minhas[:30]:

                st.markdown(
                    _card(avaliacao, "solicitante"),
                    unsafe_allow_html=True
                )

                st.write("")


# ==================================================
# TELA DO SUPERVISOR (Gestão / Fundador)
# ==================================================

def _tela_supervisor(avaliacoes, recebidas, usuario, fundador, armazem_id):

    tab_recebidas, tab_historico = st.tabs([
        f"📥 Recebidas ({len(recebidas)})",
        "🕒 Histórico",
    ])

    with tab_recebidas:

        if not recebidas:

            st.info("Nenhuma avaliação aguardando a sua resposta.")

        notas_atuais = banco.ler_notas(armazem_id)

        for avaliacao in recebidas:

            id_av = avaliacao["id"]

            with st.container(border=True):

                st.markdown(
                    _card(avaliacao, "supervisor"),
                    unsafe_allow_html=True
                )

                nota_painel = notas_atuais.get(avaliacao["rua"])

                st.caption(
                    f"Nota atual da {avaliacao['rua']} no painel: "
                    f"{_fmt_nota(nota_painel) if nota_painel else 'ainda sem nota'}"
                )

                col_aprovar, col_ajustar = st.columns(2)

                with col_aprovar:

                    if st.button(
                        f"✅ Aprovar nota {_fmt_nota(avaliacao['nota_proposta'])}",
                        key=f"aval_ok_{id_av}",
                        width='stretch'
                    ):

                        with estilos.mostrar_processando("aprovando avaliação..."):

                            ok, resultado = aprovar_avaliacao(
                                id_av, usuario, fundador, armazem_id
                            )

                        if ok:

                            estilos.notificar_sucesso(
                                f"{avaliacao['rua']} atualizada com a nota "
                                f"{_fmt_nota(resultado)}."
                            )
                            st.rerun()

                        else:

                            st.error(resultado)

                with col_ajustar:

                    with st.popover("✏️ Alterar nota e explicar"):

                        st.caption(
                            "Escolha a nota correta e explique o motivo — o "
                            "colaborador vai ver a sua explicação."
                        )

                        nota_ajustada = st.slider(
                            "Nota correta",
                            NOTA_MIN,
                            NOTA_MAX,
                            float(avaliacao["nota_proposta"]),
                            0.1,
                            format="%.1f",
                            key=f"aval_nota_{id_av}"
                        )

                        motivo = st.text_area(
                            "Por que a nota foi alterada?",
                            key=f"aval_motivo_{id_av}",
                            placeholder="Ex.: paletes fora do alinhamento no fundo da rua..."
                        )

                        if st.button(
                            "📤 Enviar nota ajustada",
                            key=f"aval_alt_{id_av}",
                            width='stretch'
                        ):

                            with estilos.mostrar_processando("enviando nota ajustada..."):

                                ok, resultado = ajustar_avaliacao(
                                    id_av, nota_ajustada, motivo,
                                    usuario, fundador, armazem_id
                                )

                            if ok:

                                estilos.notificar_sucesso(
                                    f"{avaliacao['rua']} atualizada com a nota "
                                    f"{_fmt_nota(resultado)}."
                                )
                                st.rerun()

                            else:

                                st.error(resultado)

    with tab_historico:

        respondidas = [
            a for a in avaliacoes
            if a["status"] != "pendente"
            and (fundador or a["supervisor"] == usuario)
        ][:50]

        if not respondidas:

            st.info("Ainda não há avaliações respondidas.")

        else:

            linhas = []

            for a in respondidas:

                linhas.append({
                    "Respondida em": a["respondido_em"].strftime("%d/%m/%Y %H:%M"),
                    "Rua": a["rua"],
                    "Dupla": a["dupla"],
                    "Enviada por": _nome(a["solicitante"]),
                    "Proposta": _fmt_nota(a["nota_proposta"]),
                    "Nota final": _fmt_nota(a["nota_final"]),
                    "Resultado": "✅ Aprovada" if a["status"] == "aprovada" else "🔄 Ajustada",
                    "Motivo": a["motivo"] or "—",
                    "Respondida por": _nome(a["respondido_por"]),
                })

            st.dataframe(
                pd.DataFrame(linhas),
                width='stretch',
                hide_index=True
            )


# ==================================================
# ENTRADA (chamada pelo dashboard.py)
# ==================================================

def render(armazem_id):

    usuario = st.session_state.get("usuario", "")
    tipo_usuario = st.session_state.get("tipo_usuario", "usuario")

    supervisor = eh_supervisor(usuario, tipo_usuario)
    solicitante = eh_solicitante(usuario)

    # quem não envia nem confere avaliações não vê essa seção
    if not (supervisor or solicitante):
        return

    _garantir_tabela_avaliacoes()

    avaliacoes = ler_avaliacoes(armazem_id)

    if supervisor:

        fundador = eh_fundador(usuario, tipo_usuario)

        recebidas = [
            a for a in avaliacoes
            if a["status"] == "pendente"
            and (fundador or a["supervisor"] == usuario)
        ]

        rotulo = "📝 Avaliações de ruas"

        if recebidas:
            rotulo += f" • 🔴 {len(recebidas)} aguardando sua resposta"

        with st.expander(rotulo, expanded=bool(recebidas)):

            _tela_supervisor(avaliacoes, recebidas, usuario, fundador, armazem_id)

    else:

        aguardando = [
            a for a in avaliacoes
            if a["solicitante"] == usuario and a["status"] == "pendente"
        ]

        rotulo = "📝 Avaliar a minha rua"

        if aguardando:
            rotulo += f" • ⏳ {len(aguardando)} aguardando resposta"

        with st.expander(rotulo, expanded=False):

            _tela_solicitante(avaliacoes, usuario, armazem_id)

    st.write("")

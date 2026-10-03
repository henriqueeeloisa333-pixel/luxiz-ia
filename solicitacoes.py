import html
from datetime import date

import pandas as pd
import streamlit as st

import banco
import estilos


# ==================================================
# QUEM PODE O QUÊ
# ==================================================
# Solicitantes: usuários com esses prefixos. Para liberar outro
# perfil (ex.: "Empilhador."), basta incluir o prefixo na lista.

PREFIXOS_SOLICITANTES = ("Conferente.", "Recebimento.", "Separador.")

TIPOS_SOLICITACAO = [
    "Folga",
    "Sair mais cedo",
    "Chegar mais tarde",
    "Troca de horário",
    "Férias",
    "Outro",
]


def eh_solicitante(usuario):

    return (usuario or "").startswith(PREFIXOS_SOLICITANTES)


def eh_supervisor(usuario, tipo_usuario):

    return (
        tipo_usuario in ("fundador", "gestao")
        or (usuario or "").startswith(("Fundador.", "Gestao."))
    )


# ==================================================
# TABELA (criada sozinha na primeira vez)
# ==================================================

@st.cache_resource(show_spinner=False)
def _garantir_tabela_solicitacoes():

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            solicitante TEXT NOT NULL,
            solicitante_nome TEXT NOT NULL,
            destinatario TEXT NOT NULL,
            destinatario_nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            data_referencia DATE,
            horario TEXT,
            descricao TEXT,
            status TEXT NOT NULL DEFAULT 'pendente'
                CHECK (status IN ('pendente', 'aprovada', 'recusada', 'cancelada')),
            motivo_resposta TEXT,
            respondido_por TEXT,
            respondido_em TIMESTAMP,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_solicitacoes_destinatario ON solicitacoes (armazem_id, destinatario, status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_solicitacoes_solicitante ON solicitacoes (armazem_id, solicitante)")

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

_COLUNAS = [
    "id", "solicitante", "solicitante_nome", "destinatario",
    "destinatario_nome", "tipo", "data_referencia", "horario",
    "descricao", "status", "motivo_resposta", "respondido_por",
    "respondido_em", "criado_em"
]


def _consultar(armazem_id, filtro_sql="", params=()):

    _garantir_tabela_solicitacoes()

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute(f"""
        SELECT
            id, solicitante, solicitante_nome, destinatario,
            destinatario_nome, tipo, data_referencia, horario,
            descricao, status, motivo_resposta, respondido_por,
            (respondido_em AT TIME ZONE 'UTC' AT TIME ZONE 'America/Campo_Grande'),
            (criado_em AT TIME ZONE 'UTC' AT TIME ZONE 'America/Campo_Grande')
        FROM solicitacoes
        WHERE armazem_id = %s
        {filtro_sql}
        ORDER BY
            CASE status WHEN 'pendente' THEN 0 ELSE 1 END,
            COALESCE(respondido_em, criado_em) DESC,
            id DESC
        LIMIT 300
        """, (armazem_id,) + tuple(params))

        dados = [dict(zip(_COLUNAS, row)) for row in cursor.fetchall()]

    finally:
        banco.liberar(conn)

    return dados


@st.cache_data(ttl=15, show_spinner=False)
def ler_minhas(armazem_id, usuario):

    return _consultar(armazem_id, "AND solicitante = %s", (usuario,))


@st.cache_data(ttl=15, show_spinner=False)
def ler_recebidas(armazem_id, usuario):

    return _consultar(armazem_id, "AND destinatario = %s", (usuario,))


@st.cache_data(ttl=15, show_spinner=False)
def ler_todas(armazem_id):

    return _consultar(armazem_id)


@st.cache_data(ttl=15, show_spinner=False)
def contar_pendentes_supervisor(armazem_id, usuario):

    _garantir_tabela_solicitacoes()

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT COUNT(*)
        FROM solicitacoes
        WHERE armazem_id = %s
        AND destinatario = %s
        AND status = 'pendente'
        """, (armazem_id, usuario))

        total = cursor.fetchone()[0]

    finally:
        banco.liberar(conn)

    return total


def _limpar_caches():

    ler_minhas.clear()
    ler_recebidas.clear()
    ler_todas.clear()
    contar_pendentes_supervisor.clear()


def criar_solicitacao(
    solicitante, solicitante_nome, destinatario, destinatario_nome,
    tipo, data_referencia, horario, descricao, armazem_id
):

    _garantir_tabela_solicitacoes()

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO solicitacoes
            (armazem_id, solicitante, solicitante_nome, destinatario,
             destinatario_nome, tipo, data_referencia, horario, descricao)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            armazem_id, solicitante, solicitante_nome, destinatario,
            destinatario_nome, tipo, data_referencia,
            (horario or "").strip() or None, descricao.strip()
        ))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()


def responder_solicitacao(
    id_solicitacao, aprovar, motivo, nome_respondente,
    usuario, armazem_id
):
    """
    Só o supervisor escolhido como destinatário consegue responder,
    e só enquanto a solicitação está pendente. A recusa exige motivo.
    """

    motivo = (motivo or "").strip()

    if not aprovar and not motivo:
        return False, "Descreva o motivo da recusa para que o colaborador saiba."

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE solicitacoes
        SET status = %s,
            motivo_resposta = %s,
            respondido_por = %s,
            respondido_em = CURRENT_TIMESTAMP
        WHERE id = %s
        AND armazem_id = %s
        AND destinatario = %s
        AND status = 'pendente'
        """, (
            "aprovada" if aprovar else "recusada",
            motivo or None,
            nome_respondente,
            id_solicitacao,
            armazem_id,
            usuario
        ))

        atualizou = cursor.rowcount > 0

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()

    if not atualizou:
        return False, "Esta solicitação já foi respondida ou cancelada."

    return True, "ok"


def cancelar_solicitacao(id_solicitacao, usuario, armazem_id):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE solicitacoes
        SET status = 'cancelada'
        WHERE id = %s
        AND armazem_id = %s
        AND solicitante = %s
        AND status = 'pendente'
        """, (id_solicitacao, armazem_id, usuario))

        conn.commit()

    finally:
        banco.liberar(conn)

    _limpar_caches()


# ==================================================
# APOIO
# ==================================================

STATUS_VISUAL = {
    "pendente": ("#f59e0b", "⏳ Aguardando resposta"),
    "aprovada": ("#22c55e", "✅ Aprovada"),
    "recusada": ("#ef4444", "❌ Recusada"),
    "cancelada": ("#64748b", "🚫 Cancelada"),
}


def _nome_exibicao(usuario):

    perfil = banco.ler_perfil(usuario)

    if perfil:
        return banco.nome_completo_perfil(perfil)

    if "." in usuario:
        return usuario.split(".", 1)[1].strip().title()

    return usuario


def listar_supervisores(armazem_id):

    supervisores = []

    for _, usuario, tipo_usuario, _ in banco.listar_usuarios(armazem_id):

        if not usuario or not eh_supervisor(usuario, tipo_usuario):
            continue

        supervisores.append({
            "usuario": usuario,
            "nome": _nome_exibicao(usuario),
            "cargo": "Fundador" if (
                tipo_usuario == "fundador" or usuario.startswith("Fundador.")
            ) else "Gestão",
        })

    return supervisores


def _texto_html(texto):

    return html.escape(texto or "").replace("\n", "<br>")


def _fmt_data(data):

    return data.strftime("%d/%m/%Y") if data else "—"


def _fmt_data_hora(valor):

    return valor.strftime("%d/%m às %H:%M") if valor else ""


def _card(s, modo):
    """
    modo: "solicitante" (mostra para quem foi), "supervisor" (mostra
    quem pediu) ou "geral" (mostra os dois).
    """

    cor, rotulo_status = STATUS_VISUAL.get(s["status"], STATUS_VISUAL["cancelada"])

    partes = []

    if modo in ("supervisor", "geral"):
        partes.append(f'👤 De: <b>{html.escape(s["solicitante_nome"])}</b>')

    if modo in ("solicitante", "geral"):
        partes.append(f'🛡️ Para: <b>{html.escape(s["destinatario_nome"])}</b>')

    partes.append(f'📅 {_fmt_data(s["data_referencia"])}')

    if s["horario"]:
        partes.append(f'🕒 {html.escape(s["horario"])}')

    meta = " &nbsp;·&nbsp; ".join(partes)

    resposta_html = ""

    if s["status"] == "recusada":

        resposta_html = (
            '<div style="margin-top:.7rem;background:#ef444414;'
            'border-left:4px solid #ef4444;border-radius:.5rem;'
            'padding:.6rem .8rem;">'
            '<div style="font-size:.68rem;font-weight:800;letter-spacing:.4px;'
            'text-transform:uppercase;color:#ef4444;">Motivo da recusa</div>'
            f'<div style="margin-top:.2rem;font-size:.88rem;">{_texto_html(s["motivo_resposta"])}</div>'
            f'<div style="margin-top:.35rem;font-size:.72rem;opacity:.65;">'
            f'por {html.escape(s["respondido_por"] or "—")} · {_fmt_data_hora(s["respondido_em"])}</div>'
            '</div>'
        )

    elif s["status"] == "aprovada":

        observacao = (
            f'<div style="margin-top:.2rem;font-size:.88rem;">{_texto_html(s["motivo_resposta"])}</div>'
            if s["motivo_resposta"] else ""
        )

        resposta_html = (
            '<div style="margin-top:.7rem;background:#22c55e14;'
            'border-left:4px solid #22c55e;border-radius:.5rem;'
            'padding:.6rem .8rem;">'
            '<div style="font-size:.68rem;font-weight:800;letter-spacing:.4px;'
            'text-transform:uppercase;color:#22c55e;">Aprovada</div>'
            f'{observacao}'
            f'<div style="margin-top:.35rem;font-size:.72rem;opacity:.65;">'
            f'por {html.escape(s["respondido_por"] or "—")} · {_fmt_data_hora(s["respondido_em"])}</div>'
            '</div>'
        )

    return (
        f'<div style="background:{cor}10;border:1px solid {cor}45;'
        'border-radius:1rem;padding:1rem 1.2rem;margin-bottom:.5rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:.6rem;flex-wrap:wrap;">'
        f'<div style="font-weight:800;font-size:1.02rem;">{html.escape(s["tipo"])}</div>'
        f'<span style="background:{cor}22;color:{cor};border:1px solid {cor}55;'
        'padding:.15rem .7rem;border-radius:999px;font-size:.72rem;'
        f'font-weight:800;white-space:nowrap;">{rotulo_status}</span>'
        '</div>'
        f'<div style="margin-top:.35rem;font-size:.8rem;opacity:.8;">{meta}</div>'
        f'<div style="margin-top:.6rem;font-size:.9rem;">{_texto_html(s["descricao"])}</div>'
        f'<div style="margin-top:.5rem;font-size:.7rem;opacity:.55;">'
        f'Enviada em {_fmt_data_hora(s["criado_em"])}</div>'
        f'{resposta_html}'
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


# ==================================================
# TELA
# ==================================================

def render():

    _garantir_tabela_solicitacoes()

    armazem_id = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    usuario = st.session_state.get("usuario", "")
    tipo_usuario = st.session_state.get("tipo_usuario", "usuario")

    st.subheader("📨 Solicitações")

    if eh_supervisor(usuario, tipo_usuario):

        _render_supervisor(armazem_id, usuario, tipo_usuario)

    elif eh_solicitante(usuario):

        _render_solicitante(armazem_id, usuario)

    else:

        st.info("O seu perfil não envia nem recebe solicitações.")


# ---------- COLABORADOR ----------

def _render_solicitante(armazem_id, usuario):

    st.caption(
        "Peça folga, saída antecipada e outras solicitações direto ao "
        "seu supervisor. A resposta aparece aqui."
    )

    minhas = ler_minhas(armazem_id, usuario)

    pendentes = sum(1 for s in minhas if s["status"] == "pendente")
    aprovadas = sum(1 for s in minhas if s["status"] == "aprovada")
    recusadas = sum(1 for s in minhas if s["status"] == "recusada")

    _mostrar_kpis([
        _kpi("⏳", "Aguardando resposta", str(pendentes), "#f59e0b"),
        _kpi("✅", "Aprovadas", str(aprovadas), "#22c55e"),
        _kpi("❌", "Recusadas", str(recusadas), "#ef4444"),
    ])

    aba_nova, aba_minhas = st.tabs([
        "➕ Nova solicitação",
        "📋 Minhas solicitações",
    ])

    with aba_nova:

        supervisores = listar_supervisores(armazem_id)

        if not supervisores:

            st.warning(
                "Nenhum supervisor (Gestão ou Fundador) cadastrado para "
                "receber solicitações."
            )

        else:

            with st.form("form_nova_solicitacao", clear_on_submit=True):

                destinatario = st.selectbox(
                    "Enviar para",
                    [s["usuario"] for s in supervisores],
                    format_func=lambda u: next(
                        f"{s['nome']}  ({s['cargo']})"
                        for s in supervisores if s["usuario"] == u
                    )
                )

                col_tipo, col_data, col_hora = st.columns([2, 1.3, 1])

                with col_tipo:
                    tipo_solicitacao = st.selectbox("Tipo de solicitação", TIPOS_SOLICITACAO)

                with col_data:
                    data_referencia = st.date_input(
                        "Para o dia",
                        value=date.today(),
                        format="DD/MM/YYYY"
                    )

                with col_hora:
                    horario = st.text_input(
                        "Horário (opcional)",
                        placeholder="Ex.: 15:00"
                    )

                descricao = st.text_area(
                    "Explique o motivo do seu pedido",
                    height=110,
                    placeholder="Conte o que você precisa para o supervisor decidir..."
                )

                enviou = st.form_submit_button(
                    "📨 Enviar solicitação",
                    width='stretch'
                )

            if enviou:

                if len(descricao.strip()) < 3:

                    st.error("Explique o motivo do pedido antes de enviar.")

                else:

                    nome_destinatario = next(
                        s["nome"] for s in supervisores if s["usuario"] == destinatario
                    )

                    with estilos.mostrar_processando("enviando solicitação..."):

                        criar_solicitacao(
                            usuario,
                            _nome_exibicao(usuario),
                            destinatario,
                            nome_destinatario,
                            tipo_solicitacao,
                            data_referencia,
                            horario,
                            descricao,
                            armazem_id
                        )

                    estilos.notificar_sucesso("solicitação enviada.")
                    st.rerun()

    with aba_minhas:

        if not minhas:

            st.info("Você ainda não fez nenhuma solicitação.")

        else:

            filtro = st.radio(
                "Mostrar",
                ["Todas", "Aguardando", "Aprovadas", "Recusadas"],
                horizontal=True,
                key="sol_filtro_minhas"
            )

            mapa = {
                "Aguardando": "pendente",
                "Aprovadas": "aprovada",
                "Recusadas": "recusada",
            }

            for s in minhas:

                if filtro != "Todas" and s["status"] != mapa[filtro]:
                    continue

                st.markdown(_card(s, "solicitante"), unsafe_allow_html=True)

                if s["status"] == "pendente":

                    if st.button(
                        "🚫 Cancelar solicitação",
                        key=f"sol_cancelar_{s['id']}"
                    ):

                        with estilos.mostrar_processando("cancelando..."):
                            cancelar_solicitacao(s["id"], usuario, armazem_id)

                        estilos.notificar_sucesso("solicitação cancelada.")
                        st.rerun()

                    st.write("")


# ---------- SUPERVISOR (GESTÃO / FUNDADOR) ----------

def _render_supervisor(armazem_id, usuario, tipo_usuario):

    st.caption(
        "Solicitações que os colaboradores enviaram para você. Ao "
        "recusar, o motivo é obrigatório e fica visível para quem pediu."
    )

    recebidas = ler_recebidas(armazem_id, usuario)

    pendentes = [s for s in recebidas if s["status"] == "pendente"]
    respondidas = [s for s in recebidas if s["status"] in ("aprovada", "recusada")]

    _mostrar_kpis([
        _kpi("📥", "Aguardando sua resposta", str(len(pendentes)), "#f59e0b" if pendentes else "#22c55e"),
        _kpi("✅", "Aprovadas por você", str(sum(1 for s in respondidas if s["status"] == "aprovada")), "#22c55e"),
        _kpi("❌", "Recusadas por você", str(sum(1 for s in respondidas if s["status"] == "recusada")), "#ef4444"),
    ])

    nomes_abas = [f"📥 Recebidas ({len(pendentes)})", "✅ Respondidas"]

    eh_fundador = tipo_usuario == "fundador" or usuario.startswith("Fundador.")

    if eh_fundador:
        nomes_abas.append("🌐 Visão geral")

    abas = st.tabs(nomes_abas)

    nome_respondente = _nome_exibicao(usuario)

    with abas[0]:

        if not pendentes:

            st.success("Nenhuma solicitação aguardando a sua resposta. 🎉")

        for s in pendentes:

            st.markdown(_card(s, "supervisor"), unsafe_allow_html=True)

            texto_resposta = st.text_area(
                "Motivo (obrigatório para recusar)",
                key=f"sol_motivo_{s['id']}",
                height=80,
                placeholder="Se for recusar, explique o motivo. Para aceitar, pode deixar uma observação."
            )

            col_aceitar, col_recusar, _ = st.columns([1, 1, 3])

            with col_aceitar:

                aceitou = st.button(
                    "✅ Aceitar",
                    key=f"sol_aceitar_{s['id']}",
                    width='stretch'
                )

            with col_recusar:

                recusou = st.button(
                    "❌ Recusar",
                    key=f"sol_recusar_{s['id']}",
                    width='stretch'
                )

            if aceitou or recusou:

                if recusou and not texto_resposta.strip():

                    st.error("Descreva o motivo da recusa para que o colaborador saiba.")

                else:

                    with estilos.mostrar_processando("registrando resposta..."):

                        ok, mensagem = responder_solicitacao(
                            s["id"],
                            aceitou,
                            texto_resposta,
                            nome_respondente,
                            usuario,
                            armazem_id
                        )

                    if ok:

                        estilos.notificar_sucesso(
                            "solicitação aprovada." if aceitou else "solicitação recusada."
                        )
                        st.rerun()

                    else:

                        st.error(mensagem)

            st.divider()

    with abas[1]:

        if not respondidas:

            st.info("Você ainda não respondeu nenhuma solicitação.")

        for s in respondidas:

            st.markdown(_card(s, "supervisor"), unsafe_allow_html=True)

    if eh_fundador:

        with abas[2]:

            todas = ler_todas(armazem_id)

            if not todas:

                st.info("Nenhuma solicitação registrada neste armazém.")

            else:

                filtro_geral = st.radio(
                    "Situação",
                    ["Todas", "Aguardando", "Aprovadas", "Recusadas", "Canceladas"],
                    horizontal=True,
                    key="sol_filtro_geral"
                )

                mapa = {
                    "Aguardando": "pendente",
                    "Aprovadas": "aprovada",
                    "Recusadas": "recusada",
                    "Canceladas": "cancelada",
                }

                linhas = []

                for s in todas:

                    if filtro_geral != "Todas" and s["status"] != mapa[filtro_geral]:
                        continue

                    linhas.append({
                        "Enviada em": s["criado_em"].strftime("%d/%m/%Y %H:%M"),
                        "Colaborador": s["solicitante_nome"],
                        "Supervisor": s["destinatario_nome"],
                        "Tipo": s["tipo"],
                        "Para o dia": _fmt_data(s["data_referencia"]),
                        "Situação": STATUS_VISUAL[s["status"]][1],
                        "Respondida por": s["respondido_por"] or "—",
                        "Motivo / observação": s["motivo_resposta"] or "—",
                    })

                if linhas:

                    st.dataframe(
                        pd.DataFrame(linhas),
                        width='stretch',
                        hide_index=True
                    )

                else:

                    st.info("Nenhuma solicitação com esse filtro.")

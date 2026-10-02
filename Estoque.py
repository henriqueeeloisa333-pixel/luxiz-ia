import html

import pandas as pd
import streamlit as st

import banco
import estilos


# ==================================================
# TABELAS (criadas sozinhas na primeira vez que a aba abre)
# ==================================================
# O saldo NÃO é guardado em lugar nenhum: ele é sempre calculado
# (soma das entradas - soma das retiradas). Assim nunca fica
# "descalibrado" e todo movimento deixa rastro de quem fez.

@st.cache_resource(show_spinner=False)
def _garantir_tabelas_estoque():

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque_produtos (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            nome TEXT NOT NULL,
            unidade TEXT NOT NULL DEFAULT 'un',
            estoque_minimo NUMERIC(12,2) NOT NULL DEFAULT 0,
            criado_por TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (armazem_id, nome)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque_movimentos (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            produto_id BIGINT NOT NULL REFERENCES estoque_produtos(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'retirada')),
            quantidade NUMERIC(12,2) NOT NULL CHECK (quantidade > 0),
            responsavel TEXT NOT NULL,
            registrado_por TEXT,
            observacao TEXT,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_produtos_armazem ON estoque_produtos (armazem_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_mov_armazem ON estoque_movimentos (armazem_id, data_hora DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_mov_produto ON estoque_movimentos (produto_id)")

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

_SQL_HORA_LOCAL = "(data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Campo_Grande')"


@st.cache_data(ttl=30, show_spinner=False)
def ler_produtos(armazem_id):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT
            p.id, p.nome, p.unidade, p.estoque_minimo,
            COALESCE(SUM(
                CASE m.tipo
                    WHEN 'entrada' THEN m.quantidade
                    WHEN 'retirada' THEN -m.quantidade
                END
            ), 0) AS saldo
        FROM estoque_produtos p
        LEFT JOIN estoque_movimentos m ON m.produto_id = p.id
        WHERE p.armazem_id = %s
        GROUP BY p.id
        ORDER BY p.nome ASC
        """, (armazem_id,))

        produtos = [
            {
                "id": row[0],
                "nome": row[1],
                "unidade": row[2],
                "estoque_minimo": float(row[3]),
                "saldo": float(row[4]),
                "ultima_entrada": None,
                "ultima_retirada": None,
            }
            for row in cursor.fetchall()
        ]

        # Último movimento de cada tipo, por produto
        cursor.execute(f"""
        SELECT DISTINCT ON (produto_id, tipo)
            produto_id, tipo, responsavel, quantidade, {_SQL_HORA_LOCAL}
        FROM estoque_movimentos
        WHERE armazem_id = %s
        ORDER BY produto_id, tipo, data_hora DESC, id DESC
        """, (armazem_id,))

        ultimos = {}

        for produto_id, tipo, responsavel, quantidade, data_hora in cursor.fetchall():

            ultimos[(produto_id, tipo)] = {
                "responsavel": responsavel,
                "quantidade": float(quantidade),
                "data_hora": data_hora,
            }

    finally:
        banco.liberar(conn)

    for produto in produtos:
        produto["ultima_entrada"] = ultimos.get((produto["id"], "entrada"))
        produto["ultima_retirada"] = ultimos.get((produto["id"], "retirada"))

    return produtos


@st.cache_data(ttl=30, show_spinner=False)
def ler_movimentos(armazem_id, limite=500):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute(f"""
        SELECT
            m.id, p.nome, p.unidade, m.tipo, m.quantidade,
            m.responsavel, m.registrado_por, m.observacao,
            {_SQL_HORA_LOCAL.replace('data_hora', 'm.data_hora')}
        FROM estoque_movimentos m
        JOIN estoque_produtos p ON p.id = m.produto_id
        WHERE m.armazem_id = %s
        ORDER BY m.data_hora DESC, m.id DESC
        LIMIT %s
        """, (armazem_id, limite))

        colunas = [
            "id", "produto", "unidade", "tipo", "quantidade",
            "responsavel", "registrado_por", "observacao", "data_hora"
        ]

        dados = []

        for row in cursor.fetchall():
            registro = dict(zip(colunas, row))
            registro["quantidade"] = float(registro["quantidade"])
            dados.append(registro)

    finally:
        banco.liberar(conn)

    return dados


def _limpar_caches():

    ler_produtos.clear()
    ler_movimentos.clear()


def criar_produto(nome, unidade, estoque_minimo, armazem_id, usuario):

    nome = (nome or "").strip()

    if not nome:
        return False, "Informe o nome do produto."

    ja_existe = any(
        p["nome"].strip().lower() == nome.lower()
        for p in ler_produtos(armazem_id)
    )

    if ja_existe:
        return False, f"O produto \"{nome}\" já está cadastrado."

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO estoque_produtos
            (armazem_id, nome, unidade, estoque_minimo, criado_por)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """, (armazem_id, nome, unidade, estoque_minimo, usuario))

        novo_id = cursor.fetchone()[0]

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()

    return True, novo_id


def registrar_movimento(
    produto_id, tipo, quantidade, responsavel,
    observacao, usuario, armazem_id
):
    """
    Grava uma entrada ou retirada. Na retirada, confere o saldo
    dentro da própria transação (com o produto travado), então duas
    pessoas retirando ao mesmo tempo nunca deixam o estoque negativo.
    """

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT nome, unidade
        FROM estoque_produtos
        WHERE id = %s AND armazem_id = %s
        FOR UPDATE
        """, (produto_id, armazem_id))

        produto = cursor.fetchone()

        if not produto:
            conn.rollback()
            return False, "Produto não encontrado."

        if tipo == "retirada":

            cursor.execute("""
            SELECT COALESCE(SUM(
                CASE tipo WHEN 'entrada' THEN quantidade ELSE -quantidade END
            ), 0)
            FROM estoque_movimentos
            WHERE produto_id = %s
            """, (produto_id,))

            saldo = float(cursor.fetchone()[0])

            if quantidade > saldo:
                conn.rollback()
                return False, (
                    f"Estoque insuficiente: restam apenas "
                    f"{_fmt(saldo)} {produto[1]} de {produto[0]}."
                )

        cursor.execute("""
        INSERT INTO estoque_movimentos
            (armazem_id, produto_id, tipo, quantidade,
             responsavel, registrado_por, observacao)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            armazem_id, produto_id, tipo, quantidade,
            responsavel, usuario, (observacao or "").strip() or None
        ))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()

    return True, "ok"


def atualizar_minimo(produto_id, estoque_minimo, armazem_id):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE estoque_produtos
        SET estoque_minimo = %s
        WHERE id = %s AND armazem_id = %s
        """, (estoque_minimo, produto_id, armazem_id))

        conn.commit()

    finally:
        banco.liberar(conn)

    _limpar_caches()


def excluir_produto(produto_id, armazem_id):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        # os movimentos do produto vão junto (ON DELETE CASCADE)
        cursor.execute("""
        DELETE FROM estoque_produtos
        WHERE id = %s AND armazem_id = %s
        """, (produto_id, armazem_id))

        conn.commit()

    finally:
        banco.liberar(conn)

    _limpar_caches()


# ==================================================
# APOIO VISUAL
# ==================================================

UNIDADES = ["un", "cx", "pç", "pct", "par", "kg", "L", "m", "rolo"]


def _fmt(valor):

    valor = float(valor)

    if valor.is_integer():
        return f"{int(valor):,}".replace(",", ".")

    return f"{valor:.2f}".replace(".", ",")


def _status_produto(produto):

    saldo = produto["saldo"]
    minimo = produto["estoque_minimo"]

    if saldo <= 0:
        return "#ef4444", "Zerado"

    if minimo > 0 and saldo <= minimo:
        return "#f59e0b", "Estoque baixo"

    return "#22c55e", "Em estoque"


def _linha_ultimo_movimento(icone, rotulo, mov, unidade):

    if mov:
        texto = (
            f"<b>{html.escape(mov['responsavel'])}</b>"
            f" · {mov['data_hora'].strftime('%d/%m %H:%M')}"
            f" · {_fmt(mov['quantidade'])} {html.escape(unidade)}"
        )
    else:
        texto = "—"

    return (
        '<div style="display:flex;gap:.5rem;align-items:flex-start;'
        'font-size:.78rem;margin-top:.35rem;">'
        f'<span>{icone}</span>'
        '<div style="min-width:0;">'
        f'<div style="opacity:.6;font-size:.68rem;font-weight:700;'
        f'letter-spacing:.4px;text-transform:uppercase;">{rotulo}</div>'
        f'<div>{texto}</div>'
        '</div></div>'
    )


def _card_produto(produto):

    cor, status = _status_produto(produto)

    unidade = produto["unidade"]

    minimo_html = (
        f'<div style="font-size:.74rem;opacity:.65;margin-top:.1rem;">'
        f'Mínimo: {_fmt(produto["estoque_minimo"])} {html.escape(unidade)}</div>'
        if produto["estoque_minimo"] > 0 else ""
    )

    return (
        f'<div style="background:{cor}12;border:1px solid {cor}45;'
        'border-radius:1rem;padding:1rem 1.1rem;display:flex;'
        'flex-direction:column;gap:.1rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:.5rem;">'
        f'<div style="font-weight:800;font-size:1rem;line-height:1.25;">'
        f'{html.escape(produto["nome"])}</div>'
        f'<span style="background:{cor}22;color:{cor};border:1px solid {cor}55;'
        'padding:.15rem .6rem;border-radius:999px;font-size:.68rem;'
        f'font-weight:800;white-space:nowrap;">{status}</span>'
        '</div>'
        '<div style="margin-top:.5rem;">'
        f'<span style="font-size:2.1rem;font-weight:800;color:{cor};'
        f'line-height:1;">{_fmt(produto["saldo"])}</span>'
        f'<span style="font-size:.9rem;opacity:.7;margin-left:.35rem;">'
        f'{html.escape(unidade)} em estoque</span>'
        '</div>'
        f'{minimo_html}'
        f'<div style="height:1px;background:{cor}30;margin:.7rem 0 .3rem 0;"></div>'
        f'{_linha_ultimo_movimento("📥", "Última entrada por", produto["ultima_entrada"], unidade)}'
        f'{_linha_ultimo_movimento("📤", "Última retirada por", produto["ultima_retirada"], unidade)}'
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


def _nome_padrao_usuario(usuario, armazem_id):

    perfil = banco.ler_perfil(usuario)

    if perfil:
        return banco.nome_completo_perfil(perfil)

    if "." in usuario:
        return usuario.split(".", 1)[1].strip().title()

    return usuario


# ==================================================
# TELA
# ==================================================

def render():

    _garantir_tabelas_estoque()

    armazem_id = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    usuario = st.session_state.get("usuario", "")
    tipo_usuario = st.session_state.get("tipo_usuario", "usuario")

    pode_gerir = (
        tipo_usuario in ("fundador", "gestao")
        or usuario.startswith(("Fundador.", "Gestao."))
    )

    nome_padrao = _nome_padrao_usuario(usuario, armazem_id)

    produtos = ler_produtos(armazem_id)
    movimentos = ler_movimentos(armazem_id)

    st.subheader("📦 Controle de Estoque")

    st.caption(
        "Registre as entradas de mercadoria e as retiradas para uso — "
        "o saldo é calculado automaticamente."
    )

    # ---------- KPIs ----------

    hoje = estilos.agora_local().date()

    entradas_hoje = sum(
        1 for m in movimentos
        if m["tipo"] == "entrada" and m["data_hora"].date() == hoje
    )

    retiradas_hoje = sum(
        1 for m in movimentos
        if m["tipo"] == "retirada" and m["data_hora"].date() == hoje
    )

    em_alerta = sum(
        1 for p in produtos
        if _status_produto(p)[1] != "Em estoque"
    )

    kpis = [
        _kpi("📦", "Produtos cadastrados", str(len(produtos)), "#3b82f6"),
        _kpi("⚠️", "Zerados / estoque baixo", str(em_alerta), "#f59e0b" if em_alerta else "#22c55e"),
        _kpi("📥", "Entradas hoje", str(entradas_hoje), "#22c55e"),
        _kpi("📤", "Retiradas hoje", str(retiradas_hoje), "#a855f7"),
    ]

    for coluna, kpi_html in zip(st.columns(4), kpis):

        with coluna:
            st.markdown(kpi_html, unsafe_allow_html=True)

    st.write("")

    aba_estoque, aba_entrada, aba_retirada, aba_historico = st.tabs([
        "📦 Estoque atual",
        "📥 Entrada de mercadoria",
        "📤 Retirada para uso",
        "🕒 Histórico",
    ])

    # ---------- ESTOQUE ATUAL ----------

    with aba_estoque:

        col_busca, col_filtro = st.columns([2, 3])

        with col_busca:
            busca = st.text_input(
                "🔍 Buscar produto",
                key="estoque_busca",
                placeholder="Digite o nome..."
            )

        with col_filtro:
            filtro = st.radio(
                "Situação",
                ["Todos", "Em estoque", "Estoque baixo", "Zerado"],
                horizontal=True,
                key="estoque_filtro"
            )

        filtrados = [
            p for p in produtos
            if busca.strip().lower() in p["nome"].lower()
            and (filtro == "Todos" or _status_produto(p)[1] == filtro)
        ]

        if not produtos:

            st.info(
                "Nenhum produto cadastrado ainda. Use a aba "
                "**📥 Entrada de mercadoria** para cadastrar o primeiro."
            )

        elif not filtrados:

            st.info("Nenhum produto encontrado com esse filtro.")

        else:

            st.markdown(
                '<div style="display:grid;'
                'grid-template-columns:repeat(auto-fill,minmax(270px,1fr));'
                'gap:1rem;">'
                + "".join(_card_produto(p) for p in filtrados)
                + '</div>',
                unsafe_allow_html=True
            )

        if pode_gerir and produtos:

            st.write("")

            with st.expander("⚙️ Gerenciar produtos"):

                produto_id_gerir = st.selectbox(
                    "Produto",
                    [p["id"] for p in produtos],
                    format_func=lambda pid: next(
                        p["nome"] for p in produtos if p["id"] == pid
                    ),
                    key="estoque_gerir_produto"
                )

                produto_gerir = next(
                    p for p in produtos if p["id"] == produto_id_gerir
                )

                novo_minimo = st.number_input(
                    f"Estoque mínimo ({produto_gerir['unidade']})",
                    min_value=0.0,
                    value=float(produto_gerir["estoque_minimo"]),
                    step=1.0,
                    format="%g",
                    key=f"estoque_minimo_{produto_id_gerir}",
                    help="Abaixo (ou igual) a esse valor, o card fica amarelo como \"Estoque baixo\"."
                )

                if st.button("💾 Salvar mínimo", key="estoque_salvar_minimo"):

                    with estilos.mostrar_processando("salvando..."):
                        atualizar_minimo(produto_id_gerir, novo_minimo, armazem_id)

                    estilos.notificar_sucesso("estoque mínimo atualizado.")
                    st.rerun()

                st.divider()

                confirmar = st.checkbox(
                    "Confirmo que quero excluir este produto e todo o seu histórico",
                    key="estoque_confirmar_exclusao"
                )

                if st.button(
                    "🗑️ Excluir produto",
                    key="estoque_excluir_produto",
                    disabled=not confirmar
                ):

                    with estilos.mostrar_processando("excluindo produto..."):
                        excluir_produto(produto_id_gerir, armazem_id)

                    estilos.notificar_sucesso("produto excluído.")
                    st.rerun()

    # ---------- ENTRADA ----------

    with aba_entrada:

        st.markdown("##### 📥 Registrar entrada de mercadoria")

        produto_id_entrada = st.selectbox(
            "Produto",
            [None] + [p["id"] for p in produtos],
            format_func=lambda pid: (
                "➕ Cadastrar novo produto"
                if pid is None
                else next(
                    f"{p['nome']}  —  {_fmt(p['saldo'])} {p['unidade']} em estoque"
                    for p in produtos if p["id"] == pid
                )
            ),
            key="estoque_entrada_produto"
        )

        with st.form("form_estoque_entrada", clear_on_submit=True):

            if produto_id_entrada is None:

                col_nome, col_un, col_min = st.columns([3, 1, 1])

                with col_nome:
                    nome_novo = st.text_input("Nome do novo produto")

                with col_un:
                    unidade_nova = st.selectbox("Unidade", UNIDADES)

                with col_min:
                    minimo_novo = st.number_input(
                        "Estoque mínimo",
                        min_value=0.0,
                        value=0.0,
                        step=1.0,
                        format="%g"
                    )

            col_qtd, col_resp = st.columns([1, 2])

            with col_qtd:
                quantidade_entrada = st.number_input(
                    "Quantidade que entrou",
                    min_value=0.01,
                    value=1.0,
                    step=1.0,
                    format="%g"
                )

            with col_resp:
                responsavel_entrada = st.text_input(
                    "Quem deu a entrada",
                    value=nome_padrao
                )

            obs_entrada = st.text_input(
                "Observação (opcional)",
                placeholder="Ex.: NF 12345, fornecedor, lote..."
            )

            enviou_entrada = st.form_submit_button(
                "📥 Registrar entrada",
                width='stretch'
            )

        if enviou_entrada:

            if not responsavel_entrada.strip():

                st.error("Informe quem deu a entrada.")

            else:

                produto_id_final = produto_id_entrada
                erro = None

                with estilos.mostrar_processando("registrando entrada..."):

                    if produto_id_final is None:

                        ok_produto, resultado = criar_produto(
                            nome_novo, unidade_nova, minimo_novo,
                            armazem_id, usuario
                        )

                        if ok_produto:
                            produto_id_final = resultado
                        else:
                            erro = resultado

                    if erro is None:

                        ok, erro_mov = registrar_movimento(
                            produto_id_final,
                            "entrada",
                            quantidade_entrada,
                            banco.normalizar_nome_pessoa(responsavel_entrada, armazem_id),
                            obs_entrada,
                            usuario,
                            armazem_id
                        )

                        if not ok:
                            erro = erro_mov

                if erro:

                    st.error(erro)

                else:

                    estilos.notificar_sucesso("entrada registrada com sucesso.")
                    st.rerun()

    # ---------- RETIRADA ----------

    with aba_retirada:

        st.markdown("##### 📤 Registrar retirada para uso")

        com_saldo = [p for p in produtos if p["saldo"] > 0]

        if not produtos:

            st.info("Nenhum produto cadastrado ainda.")

        elif not com_saldo:

            st.warning("Todos os produtos estão com estoque zerado.")

        else:

            produto_id_retirada = st.selectbox(
                "Produto",
                [p["id"] for p in com_saldo],
                format_func=lambda pid: next(
                    f"{p['nome']}  —  {_fmt(p['saldo'])} {p['unidade']} disponíveis"
                    for p in com_saldo if p["id"] == pid
                ),
                key="estoque_retirada_produto"
            )

            produto_retirada = next(
                p for p in com_saldo if p["id"] == produto_id_retirada
            )

            with st.form("form_estoque_retirada", clear_on_submit=True):

                col_qtd, col_resp = st.columns([1, 2])

                with col_qtd:
                    quantidade_retirada = st.number_input(
                        f"Quantidade ({produto_retirada['unidade']})",
                        min_value=0.01,
                        max_value=float(produto_retirada["saldo"]),
                        value=min(1.0, float(produto_retirada["saldo"])),
                        step=1.0,
                        format="%g"
                    )

                with col_resp:
                    responsavel_retirada = st.text_input(
                        "Quem retirou",
                        value=nome_padrao
                    )

                obs_retirada = st.text_input(
                    "Para que será usado (opcional)",
                    placeholder="Ex.: manutenção da empilhadeira 02, setor de expedição..."
                )

                enviou_retirada = st.form_submit_button(
                    "📤 Registrar retirada",
                    width='stretch'
                )

            if enviou_retirada:

                if not responsavel_retirada.strip():

                    st.error("Informe quem retirou.")

                else:

                    with estilos.mostrar_processando("registrando retirada..."):

                        ok, erro_mov = registrar_movimento(
                            produto_id_retirada,
                            "retirada",
                            quantidade_retirada,
                            banco.normalizar_nome_pessoa(responsavel_retirada, armazem_id),
                            obs_retirada,
                            usuario,
                            armazem_id
                        )

                    if ok:

                        estilos.notificar_sucesso("retirada registrada com sucesso.")
                        st.rerun()

                    else:

                        st.error(erro_mov)

    # ---------- HISTÓRICO ----------

    with aba_historico:

        if not movimentos:

            st.info("Ainda não há movimentações registradas.")

        else:

            col_tipo, col_prod = st.columns([2, 3])

            with col_tipo:
                filtro_tipo = st.radio(
                    "Tipo",
                    ["Todos", "📥 Entradas", "📤 Retiradas"],
                    horizontal=True,
                    key="estoque_hist_tipo"
                )

            with col_prod:
                filtro_produto = st.selectbox(
                    "Produto",
                    ["Todos"] + sorted({m["produto"] for m in movimentos}),
                    key="estoque_hist_produto"
                )

            linhas = []

            for m in movimentos:

                if filtro_tipo == "📥 Entradas" and m["tipo"] != "entrada":
                    continue

                if filtro_tipo == "📤 Retiradas" and m["tipo"] != "retirada":
                    continue

                if filtro_produto != "Todos" and m["produto"] != filtro_produto:
                    continue

                sinal = "+" if m["tipo"] == "entrada" else "−"

                linhas.append({
                    "Data/Hora": m["data_hora"].strftime("%d/%m/%Y %H:%M"),
                    "Tipo": "📥 Entrada" if m["tipo"] == "entrada" else "📤 Retirada",
                    "Produto": m["produto"],
                    "Quantidade": f"{sinal}{_fmt(m['quantidade'])} {m['unidade']}",
                    "Quem deu entrada / retirou": m["responsavel"],
                    "Registrado por": m["registrado_por"] or "—",
                    "Observação": m["observacao"] or "—",
                })

            if linhas:

                st.dataframe(
                    pd.DataFrame(linhas),
                    width='stretch',
                    hide_index=True
                )

                st.caption(f"Mostrando as últimas {len(linhas)} movimentações.")

            else:

                st.info("Nenhuma movimentação com esse filtro.")

import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import banco
import estilos


# =====================================================
# LOJA VIRTUAL
# =====================================================
# Controle de vendas e revendas: cadastro de produtos (preço pago e
# preço de venda), entrada de estoque, vendas (para quem, quanto e
# quando vai pagar), pagamentos a receber e gráficos do andamento.
#
# As tabelas são criadas sozinhas na primeira vez que a aba é aberta
# (CREATE TABLE IF NOT EXISTS) — não precisa mexer no banco.py.

COR_LOJA = "#d946ef"

FORMAS_PAGAMENTO = [
    "Pix",
    "Dinheiro",
    "Cartão de crédito",
    "Cartão de débito",
    "Boleto",
    "Transferência",
    "Outro",
]

OPCOES_PERIODO = [
    "Este mês",
    "Últimos 30 dias",
    "Últimos 90 dias",
    "Este ano",
    "Tudo",
]


# =====================================================
# ACESSO
# =====================================================
# Dados de vendas e lucro são sensíveis: a aba só aparece para
# Fundador e Gestão. Para liberar para mais perfis, é só mudar
# esta função.

def tem_acesso(usuario, tipo):

    usuario = usuario or ""

    return (
        tipo in ("fundador", "gestao")
        or usuario.startswith("Fundador.")
        or usuario.startswith("Gestao.")
    )


# =====================================================
# FORMATAÇÃO
# =====================================================

def _brl(valor):

    try:
        valor = float(valor)
    except (TypeError, ValueError):
        valor = 0.0

    texto = f"{valor:,.2f}"

    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _data_br(valor):

    if valor is None or pd.isna(valor):
        return "—"

    return valor.strftime("%d/%m/%Y")


def _recarregar():

    # Dentro de um fragmento, recarrega só a aba (mais rápido). Se por
    # algum motivo não estiver num fragmento, cai no rerun normal.
    try:
        st.rerun(scope="fragment")
    except Exception:
        st.rerun()


# =====================================================
# BANCO DE DADOS
# =====================================================

@st.cache_resource(show_spinner=False)
def _garantir_schema():

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS loja_produtos (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            nome TEXT NOT NULL,
            categoria TEXT,
            custo NUMERIC(12,2) NOT NULL DEFAULT 0,
            preco_venda NUMERIC(12,2) NOT NULL DEFAULT 0,
            estoque_minimo INTEGER NOT NULL DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (armazem_id, nome)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS loja_entradas (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            produto_id BIGINT NOT NULL REFERENCES loja_produtos(id) ON DELETE CASCADE,
            quantidade INTEGER NOT NULL,
            custo_unitario NUMERIC(12,2) NOT NULL DEFAULT 0,
            data_entrada DATE NOT NULL,
            fornecedor TEXT,
            observacao TEXT,
            criado_por TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS loja_vendas (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            produto_id BIGINT REFERENCES loja_produtos(id) ON DELETE SET NULL,
            produto_nome TEXT NOT NULL,
            cliente TEXT,
            quantidade INTEGER NOT NULL,
            preco_unitario NUMERIC(12,2) NOT NULL,
            custo_unitario NUMERIC(12,2) NOT NULL DEFAULT 0,
            data_venda DATE NOT NULL,
            forma_pagamento TEXT,
            data_pagamento DATE,
            pago BOOLEAN NOT NULL DEFAULT FALSE,
            data_pago DATE,
            observacao TEXT,
            criado_por TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loja_produtos_armazem ON loja_produtos (armazem_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loja_entradas_armazem ON loja_entradas (armazem_id, data_entrada DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loja_entradas_produto ON loja_entradas (produto_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loja_vendas_armazem ON loja_vendas (armazem_id, data_venda DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loja_vendas_produto ON loja_vendas (produto_id)")

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    return True


def _consultar(sql, params=()):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)

        colunas = [c[0] for c in cursor.description]

        return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

    finally:
        banco.liberar(conn)


def _executar(sql, params=()):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)


def _limpar_cache():

    ler_produtos.clear()
    ler_vendas.clear()
    ler_entradas.clear()


@st.cache_data(ttl=20, show_spinner=False)
def ler_produtos(armazem_id):

    linhas = _consultar("""
    SELECT
        p.id,
        p.nome,
        COALESCE(p.categoria, '') AS categoria,
        p.custo::float AS custo,
        p.preco_venda::float AS preco_venda,
        p.estoque_minimo,
        COALESCE((
            SELECT SUM(e.quantidade) FROM loja_entradas e
            WHERE e.produto_id = p.id
        ), 0)::int AS entradas,
        COALESCE((
            SELECT SUM(v.quantidade) FROM loja_vendas v
            WHERE v.produto_id = p.id
        ), 0)::int AS vendidos
    FROM loja_produtos p
    WHERE p.armazem_id = %s
    ORDER BY LOWER(p.nome)
    """, (armazem_id,))

    for linha in linhas:
        linha["estoque"] = linha["entradas"] - linha["vendidos"]

    return linhas


@st.cache_data(ttl=20, show_spinner=False)
def ler_vendas(armazem_id):

    return _consultar("""
    SELECT
        id,
        produto_id,
        produto_nome,
        COALESCE(cliente, '') AS cliente,
        quantidade,
        preco_unitario::float AS preco_unitario,
        custo_unitario::float AS custo_unitario,
        data_venda,
        COALESCE(forma_pagamento, '') AS forma_pagamento,
        data_pagamento,
        pago,
        data_pago,
        COALESCE(observacao, '') AS observacao
    FROM loja_vendas
    WHERE armazem_id = %s
    ORDER BY data_venda DESC, id DESC
    """, (armazem_id,))


@st.cache_data(ttl=20, show_spinner=False)
def ler_entradas(armazem_id):

    return _consultar("""
    SELECT
        e.id,
        p.nome AS produto,
        e.quantidade,
        e.custo_unitario::float AS custo_unitario,
        e.data_entrada,
        COALESCE(e.fornecedor, '') AS fornecedor,
        COALESCE(e.observacao, '') AS observacao
    FROM loja_entradas e
    JOIN loja_produtos p ON p.id = e.produto_id
    WHERE e.armazem_id = %s
    ORDER BY e.data_entrada DESC, e.id DESC
    LIMIT 200
    """, (armazem_id,))


def criar_produto(
    armazem_id, nome, categoria, custo, preco_venda,
    estoque_minimo, estoque_inicial, usuario, hoje
):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO loja_produtos
            (armazem_id, nome, categoria, custo, preco_venda, estoque_minimo)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (armazem_id, nome) DO NOTHING
        RETURNING id
        """, (
            armazem_id, nome, categoria or None,
            custo, preco_venda, estoque_minimo
        ))

        linha = cursor.fetchone()

        if not linha:
            conn.rollback()
            return False

        if estoque_inicial > 0:

            cursor.execute("""
            INSERT INTO loja_entradas
                (armazem_id, produto_id, quantidade, custo_unitario,
                 data_entrada, observacao, criado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                armazem_id, linha[0], estoque_inicial, custo,
                hoje, "Estoque inicial", usuario
            ))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_cache()

    return True


def editar_produto(
    id_produto, armazem_id, nome, categoria,
    custo, preco_venda, estoque_minimo
):

    _executar("""
    UPDATE loja_produtos
    SET nome = %s,
        categoria = %s,
        custo = %s,
        preco_venda = %s,
        estoque_minimo = %s
    WHERE id = %s
    AND armazem_id = %s
    """, (
        nome, categoria or None, custo, preco_venda,
        estoque_minimo, id_produto, armazem_id
    ))

    _limpar_cache()


def excluir_produto(id_produto, armazem_id):

    # As vendas já feitas continuam no histórico (produto_id fica
    # vazio, mas o nome do produto foi guardado junto com a venda).
    _executar("""
    DELETE FROM loja_produtos
    WHERE id = %s
    AND armazem_id = %s
    """, (id_produto, armazem_id))

    _limpar_cache()


def registrar_entrada(
    armazem_id, produto_id, quantidade, custo_unitario,
    data_entrada, fornecedor, observacao, usuario
):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO loja_entradas
            (armazem_id, produto_id, quantidade, custo_unitario,
             data_entrada, fornecedor, observacao, criado_por)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            armazem_id, produto_id, quantidade, custo_unitario,
            data_entrada, fornecedor or None, observacao or None, usuario
        ))

        # Se informou o preço pago nessa compra, ele vira o "preço
        # pago" atual do produto (usado no lucro das próximas vendas).
        if custo_unitario > 0:

            cursor.execute("""
            UPDATE loja_produtos
            SET custo = %s
            WHERE id = %s
            AND armazem_id = %s
            """, (custo_unitario, produto_id, armazem_id))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_cache()


def excluir_entrada(id_entrada, armazem_id):

    _executar("""
    DELETE FROM loja_entradas
    WHERE id = %s
    AND armazem_id = %s
    """, (id_entrada, armazem_id))

    _limpar_cache()


def registrar_venda(
    armazem_id, produto_id, cliente, quantidade, preco_unitario,
    data_venda, forma_pagamento, data_pagamento, pago,
    observacao, usuario
):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        # Confere o estoque na hora (com o produto travado), para duas
        # vendas ao mesmo tempo não passarem do que existe.
        cursor.execute("""
        SELECT
            p.nome,
            p.custo::float,
            COALESCE((
                SELECT SUM(e.quantidade) FROM loja_entradas e
                WHERE e.produto_id = p.id
            ), 0)
            - COALESCE((
                SELECT SUM(v.quantidade) FROM loja_vendas v
                WHERE v.produto_id = p.id
            ), 0)
        FROM loja_produtos p
        WHERE p.id = %s
        AND p.armazem_id = %s
        FOR UPDATE OF p
        """, (produto_id, armazem_id))

        linha = cursor.fetchone()

        if not linha:
            conn.rollback()
            raise ValueError("Produto não encontrado.")

        nome_produto, custo_atual, estoque_atual = linha

        if quantidade > int(estoque_atual):
            conn.rollback()
            raise ValueError(
                f"Estoque insuficiente: restam {int(estoque_atual)} "
                f"unidade(s) de {nome_produto}."
            )

        cursor.execute("""
        INSERT INTO loja_vendas
            (armazem_id, produto_id, produto_nome, cliente, quantidade,
             preco_unitario, custo_unitario, data_venda, forma_pagamento,
             data_pagamento, pago, data_pago, observacao, criado_por)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            armazem_id, produto_id, nome_produto, cliente, quantidade,
            preco_unitario, custo_atual, data_venda, forma_pagamento,
            data_pagamento, pago, data_venda if pago else None,
            observacao or None, usuario
        ))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_cache()


def marcar_pago(id_venda, armazem_id, data_pago):

    _executar("""
    UPDATE loja_vendas
    SET pago = TRUE,
        data_pago = %s
    WHERE id = %s
    AND armazem_id = %s
    """, (data_pago, id_venda, armazem_id))

    _limpar_cache()


def desfazer_pagamento(id_venda, armazem_id):

    _executar("""
    UPDATE loja_vendas
    SET pago = FALSE,
        data_pago = NULL
    WHERE id = %s
    AND armazem_id = %s
    """, (id_venda, armazem_id))

    _limpar_cache()


def excluir_venda(id_venda, armazem_id):

    _executar("""
    DELETE FROM loja_vendas
    WHERE id = %s
    AND armazem_id = %s
    """, (id_venda, armazem_id))

    _limpar_cache()


# =====================================================
# APOIO (DataFrames, períodos, visual)
# =====================================================

def _df_vendas(vendas):

    df = pd.DataFrame(vendas)

    if df.empty:
        return df

    df["total"] = df["quantidade"] * df["preco_unitario"]
    df["custo_total"] = df["quantidade"] * df["custo_unitario"]
    df["lucro"] = df["total"] - df["custo_total"]
    df["data_venda"] = pd.to_datetime(df["data_venda"])
    df["data_pagamento"] = pd.to_datetime(df["data_pagamento"])
    df["pago"] = df["pago"].astype(bool)

    return df


def _intervalo(opcao, hoje):

    if opcao == "Este mês":
        return hoje.replace(day=1), hoje

    if opcao == "Últimos 30 dias":
        return hoje - timedelta(days=29), hoje

    if opcao == "Últimos 90 dias":
        return hoje - timedelta(days=89), hoje

    if opcao == "Este ano":
        return date(hoje.year, 1, 1), hoje

    return None, None


def _filtrar_periodo(df, opcao, hoje):

    if df.empty:
        return df

    inicio, fim = _intervalo(opcao, hoje)

    if inicio is None:
        return df

    return df[
        (df["data_venda"] >= pd.Timestamp(inicio))
        & (df["data_venda"] <= pd.Timestamp(fim))
    ]


def _soma(df, coluna):

    if df is None or df.empty:
        return 0.0

    return float(df[coluna].sum())


def _status_pagamento(pago, vencimento, hoje):

    if pago:
        return "✅ Pago"

    if vencimento is None or pd.isna(vencimento):
        return "⏳ A receber"

    dia = vencimento.date()

    if dia < hoje:
        return "🔴 Vencido"

    if dia == hoje:
        return "🟠 Vence hoje"

    return "⏳ A receber"


def _kpis(itens):

    colunas = st.columns(len(itens))

    for (icone, rotulo, valor, cor), coluna in zip(itens, colunas):

        with coluna:

            st.markdown(
                f'<div style="background:{cor}14;border:1px solid {cor}40;'
                f'border-radius:.9rem;padding:.7rem .9rem;text-align:center;'
                f'margin-bottom:.6rem;">'
                f'<div style="font-size:1.3rem;">{icone}</div>'
                f'<div style="font-size:1.1rem;font-weight:800;color:{cor};'
                f'margin-top:.1rem;">{valor}</div>'
                f'<div style="font-size:.72rem;opacity:.75;margin-top:.1rem;">'
                f'{rotulo}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


def _mapa_produtos(produtos):

    return {
        p["id"]: (
            f'{p["nome"]} — estoque: {p["estoque"]} — '
            f'{_brl(p["preco_venda"])}'
        )
        for p in produtos
    }


# =====================================================
# ABA: PAINEL
# =====================================================

def _aba_painel(produtos, vendas, hoje):

    df = _df_vendas(vendas)

    if not produtos and df.empty:

        st.info(
            "Ainda não há nada cadastrado. Comece pela aba "
            "**🏷️ Produtos** para cadastrar o primeiro produto."
        )

        return

    periodo = st.selectbox(
        "📅 Período",
        OPCOES_PERIODO,
        index=0,
        key="loja_painel_periodo"
    )

    df_periodo = _filtrar_periodo(df, periodo, hoje)

    receita = _soma(df_periodo, "total")
    lucro = _soma(df_periodo, "lucro")
    qtd_vendida = int(_soma(df_periodo, "quantidade"))
    num_vendas = 0 if df_periodo.empty else len(df_periodo)
    ticket = receita / num_vendas if num_vendas else 0.0
    margem = (lucro / receita * 100) if receita else 0.0

    _kpis([
        ("💵", f"Vendido ({periodo.lower()})", _brl(receita), "#3b82f6"),
        ("📈", f"Lucro ({margem:.0f}% de margem)", _brl(lucro), "#22c55e"),
        ("📦", "Unidades vendidas", str(qtd_vendida), "#a855f7"),
        ("🧾", "Ticket médio", _brl(ticket), "#0ea5e9"),
    ])

    if df.empty:
        pendentes = df
        vencidos = df
    else:
        pendentes = df[~df["pago"]]
        vencidos = pendentes[pendentes["data_pagamento"] < pd.Timestamp(hoje)]

    a_receber = _soma(pendentes, "total")
    total_vencido = _soma(vencidos, "total")

    valor_estoque_custo = sum(
        max(p["estoque"], 0) * p["custo"] for p in produtos
    )

    valor_estoque_venda = sum(
        max(p["estoque"], 0) * p["preco_venda"] for p in produtos
    )

    _kpis([
        ("⏳", "A receber (total)", _brl(a_receber), "#f59e0b"),
        ("🔴", "Vencido", _brl(total_vencido), "#ef4444"),
        ("🏷️", "Estoque (valor pago)", _brl(valor_estoque_custo), "#64748b"),
        ("🛍️", "Estoque (valor de venda)", _brl(valor_estoque_venda), COR_LOJA),
    ])

    # ---------------- alertas ----------------

    criticos = [
        p for p in produtos
        if p["estoque"] <= 0
        or (p["estoque_minimo"] > 0 and p["estoque"] <= p["estoque_minimo"])
    ]

    if criticos:

        texto_criticos = ", ".join(
            f'**{p["nome"]}** ({p["estoque"]} em estoque)'
            for p in criticos
        )

        st.warning(f"📦 Repor estoque: {texto_criticos}")

    if not vencidos.empty:

        st.error(
            f"🔴 {len(vencidos)} pagamento(s) vencido(s), somando "
            f"{_brl(total_vencido)}. Veja na aba **💰 A receber**."
        )

    # ---------------- gráficos ----------------

    st.divider()

    st.markdown("##### 📊 Vendas e lucro por mês")

    if df.empty:

        st.caption("Os gráficos aparecem assim que a primeira venda for registrada.")

    else:

        meses = pd.period_range(
            end=pd.Timestamp(hoje),
            periods=12,
            freq="M"
        )

        mensal = (
            df.groupby(df["data_venda"].dt.to_period("M"))[["total", "lucro"]]
            .sum()
            .reindex(meses, fill_value=0.0)
        )

        mensal.index = [p.strftime("%Y-%m") for p in mensal.index]
        mensal.columns = ["Vendido", "Lucro"]

        st.bar_chart(mensal, color=["#3b82f6", "#22c55e"])

        col_a, col_b = st.columns(2)

        with col_a:

            st.markdown(f"##### 🏆 Mais vendidos ({periodo.lower()})")

            if df_periodo.empty:
                st.caption("Sem vendas neste período.")
            else:
                por_produto = (
                    df_periodo.groupby("produto_nome")["total"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(10)
                )
                por_produto.name = "Vendido"
                st.bar_chart(por_produto, color="#a855f7", horizontal=True)

        with col_b:

            st.markdown(f"##### 💰 Lucro por produto ({periodo.lower()})")

            if df_periodo.empty:
                st.caption("Sem vendas neste período.")
            else:
                lucro_produto = (
                    df_periodo.groupby("produto_nome")["lucro"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(10)
                )
                lucro_produto.name = "Lucro"
                st.bar_chart(lucro_produto, color="#22c55e", horizontal=True)

        col_c, col_d = st.columns(2)

        with col_c:

            st.markdown(f"##### 👥 Melhores clientes ({periodo.lower()})")

            clientes_validos = (
                df_periodo[df_periodo["cliente"] != ""]
                if not df_periodo.empty else df_periodo
            )

            if clientes_validos.empty:
                st.caption("Sem vendas neste período.")
            else:
                por_cliente = (
                    clientes_validos.groupby("cliente")["total"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(10)
                )
                por_cliente.name = "Comprou"
                st.bar_chart(por_cliente, color="#0ea5e9", horizontal=True)

        with col_d:

            st.markdown("##### 🗓️ Previsão de recebimentos")

            if pendentes.empty:
                st.caption("Nada a receber no momento.")
            else:
                prev = pendentes.copy()

                prev["mes"] = prev["data_pagamento"].dt.strftime("%Y-%m")
                prev["mes"] = prev["mes"].fillna("Sem data")

                por_mes = prev.groupby("mes")["total"].sum()
                por_mes.name = "A receber"

                st.bar_chart(por_mes, color="#f59e0b")

    if produtos:

        st.markdown("##### 📦 Estoque atual x mínimo")

        estoque_df = pd.DataFrame({
            "Estoque": [max(p["estoque"], 0) for p in produtos],
            "Mínimo": [p["estoque_minimo"] for p in produtos],
        }, index=[p["nome"] for p in produtos])

        st.bar_chart(estoque_df, color=["#14b8a6", "#ef4444"])


# =====================================================
# ABA: PRODUTOS
# =====================================================

def _aba_produtos(armazem_id, usuario, produtos, hoje):

    with st.expander("➕ Cadastrar novo produto", expanded=not produtos):

        with st.form("loja_form_produto", clear_on_submit=True):

            col1, col2 = st.columns([2, 1])

            with col1:
                nome = st.text_input("Nome do produto")

            with col2:
                categoria = st.text_input("Categoria (opcional)")

            col3, col4 = st.columns(2)

            with col3:
                custo = st.number_input(
                    "Preço pago (custo por unidade) — R$",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f"
                )

            with col4:
                preco_venda = st.number_input(
                    "Preço de venda (por unidade) — R$",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f"
                )

            col5, col6 = st.columns(2)

            with col5:
                estoque_inicial = st.number_input(
                    "Quantidade que você tem agora",
                    min_value=0,
                    step=1,
                    value=0
                )

            with col6:
                estoque_minimo = st.number_input(
                    "Avisar quando chegar em (estoque mínimo)",
                    min_value=0,
                    step=1,
                    value=0
                )

            salvar = st.form_submit_button("💾 Salvar produto", width="stretch")

        if salvar:

            nome_limpo = (nome or "").strip()

            if not nome_limpo:

                st.error("Informe o nome do produto.")

            elif any(p["nome"].strip().lower() == nome_limpo.lower() for p in produtos):

                st.error("Já existe um produto com esse nome.")

            else:

                with estilos.mostrar_processando("salvando produto..."):
                    criado = criar_produto(
                        armazem_id, nome_limpo, (categoria or "").strip(),
                        custo, preco_venda, int(estoque_minimo),
                        int(estoque_inicial), usuario, hoje
                    )

                if criado:
                    estilos.notificar_sucesso("produto cadastrado com sucesso.")
                    _recarregar()
                else:
                    st.error("Não foi possível cadastrar (nome já existe?).")

    st.markdown("##### 🏷️ Produtos cadastrados")

    if not produtos:

        st.info("Nenhum produto cadastrado ainda.")

        return

    linhas = []

    for p in produtos:

        lucro_un = p["preco_venda"] - p["custo"]

        margem = (
            lucro_un / p["preco_venda"] * 100
            if p["preco_venda"] > 0 else 0
        )

        if p["estoque"] <= 0:
            situacao = "🔴 Sem estoque"
        elif p["estoque_minimo"] and p["estoque"] <= p["estoque_minimo"]:
            situacao = "🟠 Estoque baixo"
        else:
            situacao = "🟢 OK"

        linhas.append({
            "Produto": p["nome"],
            "Categoria": p["categoria"] or "—",
            "Preço pago": _brl(p["custo"]),
            "Preço de venda": _brl(p["preco_venda"]),
            "Lucro por un.": _brl(lucro_un),
            "Margem": f"{margem:.0f}%",
            "Estoque": p["estoque"],
            "Situação": situacao,
            "Valor em estoque (venda)": _brl(max(p["estoque"], 0) * p["preco_venda"]),
        })

    st.dataframe(
        pd.DataFrame(linhas),
        width="stretch",
        hide_index=True
    )

    with st.expander("✏️ Editar ou excluir produto"):

        mapa = {p["id"]: p["nome"] for p in produtos}

        pid = st.selectbox(
            "Produto",
            list(mapa.keys()),
            format_func=lambda i: mapa[i],
            key="loja_editar_produto"
        )

        produto = next(p for p in produtos if p["id"] == pid)

        with st.form(f"loja_form_editar_{pid}"):

            col1, col2 = st.columns([2, 1])

            with col1:
                nome_ed = st.text_input("Nome", value=produto["nome"])

            with col2:
                categoria_ed = st.text_input("Categoria", value=produto["categoria"])

            col3, col4, col5 = st.columns(3)

            with col3:
                custo_ed = st.number_input(
                    "Preço pago — R$",
                    min_value=0.0, step=1.0, format="%.2f",
                    value=float(produto["custo"])
                )

            with col4:
                preco_ed = st.number_input(
                    "Preço de venda — R$",
                    min_value=0.0, step=1.0, format="%.2f",
                    value=float(produto["preco_venda"])
                )

            with col5:
                minimo_ed = st.number_input(
                    "Estoque mínimo",
                    min_value=0, step=1,
                    value=int(produto["estoque_minimo"])
                )

            salvar_ed = st.form_submit_button("💾 Salvar alterações", width="stretch")

        st.caption(
            "Mudar o preço aqui vale só para as próximas vendas — as vendas "
            "já registradas continuam com o preço de quando foram feitas."
        )

        if salvar_ed:

            nome_ed_limpo = (nome_ed or "").strip()

            if not nome_ed_limpo:

                st.error("O nome não pode ficar vazio.")

            else:

                try:

                    with estilos.mostrar_processando("salvando alterações..."):
                        editar_produto(
                            pid, armazem_id, nome_ed_limpo,
                            (categoria_ed or "").strip(),
                            custo_ed, preco_ed, int(minimo_ed)
                        )

                    estilos.notificar_sucesso("produto atualizado com sucesso.")
                    _recarregar()

                except Exception:

                    st.error("Não foi possível salvar (já existe outro produto com esse nome?).")

        confirma = st.checkbox(
            "Confirmo que quero excluir este produto "
            "(as vendas já feitas continuam no histórico)",
            key=f"loja_conf_excluir_produto_{pid}"
        )

        if st.button(
            "🗑️ Excluir produto",
            disabled=not confirma,
            key=f"loja_btn_excluir_produto_{pid}"
        ):

            with estilos.mostrar_processando("excluindo produto..."):
                excluir_produto(pid, armazem_id)

            estilos.notificar_sucesso("produto excluído.")
            _recarregar()


# =====================================================
# ABA: ENTRADA DE ESTOQUE
# =====================================================

def _aba_entrada(armazem_id, usuario, produtos, hoje):

    if not produtos:

        st.info("Cadastre um produto primeiro, na aba **🏷️ Produtos**.")

        return

    st.caption(
        "Use quando comprar mais mercadoria para revender. A quantidade "
        "soma no estoque; se informar o preço pago, ele passa a valer "
        "como o novo preço pago do produto."
    )

    mapa = _mapa_produtos(produtos)

    with st.form("loja_form_entrada", clear_on_submit=True):

        pid = st.selectbox(
            "Produto",
            list(mapa.keys()),
            format_func=lambda i: mapa[i]
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            quantidade = st.number_input("Quantidade comprada", min_value=1, step=1, value=1)

        with col2:
            custo = st.number_input(
                "Preço pago por unidade — R$",
                min_value=0.0, step=1.0, format="%.2f",
                help="Deixe 0 para manter o preço pago atual do produto."
            )

        with col3:
            data_entrada = st.date_input("Data da compra", value=hoje, format="DD/MM/YYYY")

        col4, col5 = st.columns(2)

        with col4:
            fornecedor = st.text_input("Fornecedor (opcional)")

        with col5:
            observacao = st.text_input("Observação (opcional)")

        salvar = st.form_submit_button("📥 Registrar entrada", width="stretch")

    if salvar:

        with estilos.mostrar_processando("registrando entrada..."):
            registrar_entrada(
                armazem_id, pid, int(quantidade), custo, data_entrada,
                (fornecedor or "").strip(), (observacao or "").strip(), usuario
            )

        estilos.notificar_sucesso("entrada de estoque registrada.")
        _recarregar()

    entradas = ler_entradas(armazem_id)

    st.markdown("##### 📜 Últimas entradas")

    if not entradas:

        st.caption("Nenhuma entrada registrada ainda.")

        return

    tabela = pd.DataFrame([
        {
            "Data": _data_br(pd.Timestamp(e["data_entrada"])),
            "Produto": e["produto"],
            "Qtd": e["quantidade"],
            "Preço pago un.": _brl(e["custo_unitario"]),
            "Total pago": _brl(e["quantidade"] * e["custo_unitario"]),
            "Fornecedor": e["fornecedor"] or "—",
            "Obs.": e["observacao"] or "—",
        }
        for e in entradas
    ])

    st.dataframe(tabela, width="stretch", hide_index=True)

    with st.expander("🗑️ Excluir uma entrada (lançada errado)"):

        mapa_entradas = {
            e["id"]: (
                f'{_data_br(pd.Timestamp(e["data_entrada"]))} · {e["produto"]} · '
                f'{e["quantidade"]} un.'
            )
            for e in entradas
        }

        eid = st.selectbox(
            "Entrada",
            list(mapa_entradas.keys()),
            format_func=lambda i: mapa_entradas[i],
            key="loja_excluir_entrada"
        )

        st.caption("Ao excluir, a quantidade sai do estoque do produto.")

        confirma = st.checkbox("Confirmo a exclusão", key="loja_conf_excluir_entrada")

        if st.button("🗑️ Excluir entrada", disabled=not confirma, key="loja_btn_excluir_entrada"):

            with estilos.mostrar_processando("excluindo entrada..."):
                excluir_entrada(eid, armazem_id)

            estilos.notificar_sucesso("entrada excluída.")
            _recarregar()


# =====================================================
# ABA: NOVA VENDA
# =====================================================

def _aba_nova_venda(armazem_id, usuario, produtos, vendas, hoje):

    if not produtos:

        st.info("Cadastre um produto primeiro, na aba **🏷️ Produtos**.")

        return

    # Contador usado nas chaves dos campos: ao registrar uma venda ele
    # aumenta e todos os campos voltam em branco.
    n = st.session_state.get("loja_venda_n", 0)

    mapa = _mapa_produtos(produtos)

    pid = st.selectbox(
        "Produto",
        list(mapa.keys()),
        format_func=lambda i: mapa[i],
        key=f"loja_v_produto_{n}"
    )

    produto = next(p for p in produtos if p["id"] == pid)

    estoque = produto["estoque"]

    if estoque <= 0:
        st.error("Este produto está sem estoque. Registre uma entrada na aba **📥 Entrada de estoque**.")

    clientes = sorted(
        {v["cliente"] for v in vendas if v["cliente"]},
        key=str.lower
    )

    OPCAO_NOVO = "➕ Novo cliente"

    col1, col2 = st.columns(2)

    with col1:

        escolha_cliente = st.selectbox(
            "Cliente (para quem vendeu)",
            [OPCAO_NOVO] + clientes,
            key=f"loja_v_cliente_{n}"
        )

        if escolha_cliente == OPCAO_NOVO:
            cliente = st.text_input("Nome do cliente", key=f"loja_v_cliente_novo_{n}").strip()
        else:
            cliente = escolha_cliente

    with col2:

        data_venda = st.date_input(
            "Data da venda",
            value=hoje,
            format="DD/MM/YYYY",
            key=f"loja_v_data_{n}"
        )

    col3, col4, col5 = st.columns(3)

    with col3:

        quantidade = st.number_input(
            "Quantidade",
            min_value=1,
            max_value=max(estoque, 1),
            value=1,
            step=1,
            key=f"loja_v_qtd_{n}_{pid}"
        )

    with col4:

        preco = st.number_input(
            "Preço de venda (por unidade) — R$",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            value=float(produto["preco_venda"]),
            key=f"loja_v_preco_{n}_{pid}"
        )

    with col5:

        forma = st.selectbox(
            "Forma de pagamento",
            FORMAS_PAGAMENTO,
            key=f"loja_v_forma_{n}"
        )

    situacao = st.radio(
        "Situação do pagamento",
        ["✅ Já foi pago", "⏳ Vai pagar depois"],
        horizontal=True,
        key=f"loja_v_situacao_{n}"
    )

    pago = situacao.startswith("✅")

    if pago:

        data_pagamento = data_venda

    else:

        data_pagamento = st.date_input(
            "Quando vai pagar?",
            value=hoje + timedelta(days=7),
            format="DD/MM/YYYY",
            key=f"loja_v_vencimento_{n}"
        )

    observacao = st.text_input("Observação (opcional)", key=f"loja_v_obs_{n}")

    total = quantidade * preco
    lucro = quantidade * (preco - produto["custo"])

    st.info(
        f"Total da venda: **{_brl(total)}**  ·  "
        f"Lucro estimado: **{_brl(lucro)}**  ·  "
        f"Estoque depois da venda: **{estoque - quantidade}**"
    )

    if st.button(
        "🛒 Registrar venda",
        type="primary",
        disabled=estoque <= 0,
        key=f"loja_v_registrar_{n}"
    ):

        if not cliente:

            st.error("Informe para quem foi a venda.")

        else:

            try:

                with estilos.mostrar_processando("registrando venda..."):
                    registrar_venda(
                        armazem_id, pid, cliente, int(quantidade), preco,
                        data_venda, forma, data_pagamento, pago,
                        (observacao or "").strip(), usuario
                    )

                st.session_state["loja_venda_n"] = n + 1

                estilos.notificar_sucesso("venda registrada com sucesso.")
                _recarregar()

            except ValueError as erro:

                st.error(str(erro))


# =====================================================
# ABA: A RECEBER
# =====================================================

def _aba_a_receber(armazem_id, vendas, hoje):

    df = _df_vendas(vendas)

    pendentes = df if df.empty else df[~df["pago"]]

    if pendentes.empty:

        st.success("🎉 Nenhum pagamento pendente. Tudo recebido!")

        return

    pendentes = pendentes.sort_values(
        "data_pagamento",
        na_position="last"
    )

    ts_hoje = pd.Timestamp(hoje)

    vencidos = pendentes[pendentes["data_pagamento"] < ts_hoje]

    proximos = pendentes[
        (pendentes["data_pagamento"] >= ts_hoje)
        & (pendentes["data_pagamento"] <= ts_hoje + pd.Timedelta(days=7))
    ]

    _kpis([
        ("⏳", "Total a receber", _brl(_soma(pendentes, "total")), "#f59e0b"),
        ("🔴", f"Vencido ({len(vencidos)})", _brl(_soma(vencidos, "total")), "#ef4444"),
        ("🗓️", f"Vence em 7 dias ({len(proximos)})", _brl(_soma(proximos, "total")), "#0ea5e9"),
    ])

    st.markdown("##### 👥 Quanto cada cliente deve")

    por_cliente = (
        pendentes.assign(cliente=pendentes["cliente"].replace("", "(sem nome)"))
        .groupby("cliente")["total"]
        .sum()
        .sort_values(ascending=False)
    )

    st.dataframe(
        pd.DataFrame({
            "Cliente": por_cliente.index,
            "Deve": [_brl(v) for v in por_cliente.values],
        }),
        width="stretch",
        hide_index=True
    )

    st.markdown("##### 💰 Pagamentos pendentes")

    for _, linha in pendentes.iterrows():

        status = _status_pagamento(False, linha["data_pagamento"], hoje)

        col_a, col_b, col_c, col_d, col_e = st.columns([2.2, 2.6, 1.5, 1.8, 1.5])

        with col_a:
            st.markdown(f"**{linha['cliente'] or '(sem nome)'}**")
            st.caption(f"Venda de {_data_br(linha['data_venda'])}")

        with col_b:
            st.markdown(f"{linha['produto_nome']}")
            st.caption(f"{int(linha['quantidade'])} un. × {_brl(linha['preco_unitario'])}")

        with col_c:
            st.markdown(f"**{_brl(linha['total'])}**")

        with col_d:
            st.markdown(status)
            st.caption(f"Vencimento: {_data_br(linha['data_pagamento'])}")

        with col_e:

            if st.button("✅ Recebi", key=f"loja_pago_{int(linha['id'])}"):

                with estilos.mostrar_processando("registrando pagamento..."):
                    marcar_pago(int(linha["id"]), armazem_id, hoje)

                estilos.notificar_sucesso("pagamento registrado.")
                _recarregar()

        st.divider()


# =====================================================
# ABA: VENDAS (histórico)
# =====================================================

def _aba_vendas(armazem_id, vendas, hoje):

    df = _df_vendas(vendas)

    if df.empty:

        st.info("Nenhuma venda registrada ainda.")

        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        periodo = st.selectbox(
            "Período",
            OPCOES_PERIODO,
            index=len(OPCOES_PERIODO) - 1,
            key="loja_vendas_periodo"
        )

    clientes = sorted({c for c in df["cliente"] if c}, key=str.lower)
    produtos_vendidos = sorted(set(df["produto_nome"]), key=str.lower)

    with col2:
        filtro_cliente = st.selectbox("Cliente", ["Todos"] + clientes, key="loja_vendas_cliente")

    with col3:
        filtro_produto = st.selectbox("Produto", ["Todos"] + produtos_vendidos, key="loja_vendas_produto")

    with col4:
        filtro_situacao = st.selectbox(
            "Situação",
            ["Todas", "Pagas", "A receber", "Vencidas"],
            key="loja_vendas_situacao"
        )

    filtrado = _filtrar_periodo(df, periodo, hoje)

    if filtro_cliente != "Todos":
        filtrado = filtrado[filtrado["cliente"] == filtro_cliente]

    if filtro_produto != "Todos":
        filtrado = filtrado[filtrado["produto_nome"] == filtro_produto]

    if filtro_situacao == "Pagas":
        filtrado = filtrado[filtrado["pago"]]
    elif filtro_situacao == "A receber":
        filtrado = filtrado[~filtrado["pago"]]
    elif filtro_situacao == "Vencidas":
        filtrado = filtrado[
            (~filtrado["pago"])
            & (filtrado["data_pagamento"] < pd.Timestamp(hoje))
        ]

    if filtrado.empty:

        st.info("Nenhuma venda encontrada com esses filtros.")

        return

    st.caption(
        f"{len(filtrado)} venda(s)  ·  Total: {_brl(_soma(filtrado, 'total'))}  ·  "
        f"Lucro: {_brl(_soma(filtrado, 'lucro'))}"
    )

    tabela = pd.DataFrame({
        "Data": filtrado["data_venda"].dt.strftime("%d/%m/%Y"),
        "Cliente": filtrado["cliente"].replace("", "—"),
        "Produto": filtrado["produto_nome"],
        "Qtd": filtrado["quantidade"],
        "Preço un.": filtrado["preco_unitario"].map(_brl),
        "Total": filtrado["total"].map(_brl),
        "Lucro": filtrado["lucro"].map(_brl),
        "Pagamento": filtrado["forma_pagamento"].replace("", "—"),
        "Situação": filtrado.apply(
            lambda r: _status_pagamento(r["pago"], r["data_pagamento"], hoje),
            axis=1
        ),
        "Vencimento": filtrado["data_pagamento"].dt.strftime("%d/%m/%Y").fillna("—"),
        "Obs.": filtrado["observacao"].replace("", "—"),
    })

    st.dataframe(tabela, width="stretch", hide_index=True)

    st.download_button(
        "📥 Baixar esta lista (planilha CSV)",
        data=tabela.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"vendas_{hoje.strftime('%Y-%m-%d')}.csv",
        mime="text/csv",
        key="loja_baixar_vendas"
    )

    with st.expander("🛠️ Corrigir uma venda (desfazer pagamento ou excluir)"):

        mapa = {
            int(r["id"]): (
                f'{_data_br(r["data_venda"])} · {r["cliente"] or "(sem nome)"} · '
                f'{r["produto_nome"]} · {_brl(r["total"])}'
            )
            for _, r in filtrado.iterrows()
        }

        vid = st.selectbox(
            "Venda",
            list(mapa.keys()),
            format_func=lambda i: mapa[i],
            key="loja_corrigir_venda"
        )

        venda = filtrado[filtrado["id"] == vid].iloc[0]

        if venda["pago"]:

            if st.button("↩️ Desfazer pagamento (voltar para 'a receber')", key=f"loja_desfazer_{vid}"):

                with estilos.mostrar_processando("atualizando venda..."):
                    desfazer_pagamento(vid, armazem_id)

                estilos.notificar_sucesso("pagamento desfeito.")
                _recarregar()

        st.caption("Ao excluir uma venda, as unidades voltam para o estoque.")

        confirma = st.checkbox("Confirmo a exclusão desta venda", key=f"loja_conf_excluir_venda_{vid}")

        if st.button("🗑️ Excluir venda", disabled=not confirma, key=f"loja_btn_excluir_venda_{vid}"):

            with estilos.mostrar_processando("excluindo venda..."):
                excluir_venda(vid, armazem_id)

            estilos.notificar_sucesso("venda excluída.")
            _recarregar()


# =====================================================
# TELA PRINCIPAL
# =====================================================

def render():

    estilos.exibir_notificacao_pendente()

    usuario = st.session_state.get("usuario", "")
    tipo = st.session_state.get("tipo_usuario", "usuario")

    if not tem_acesso(usuario, tipo):

        st.error("Você não tem acesso a esta área.")

        return

    _garantir_schema()

    armazem_id = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    estilos.cabecalho_pagina(
        "🛍️",
        "Loja Virtual",
        "Produtos, estoque, vendas e pagamentos a receber — tudo em um só lugar.",
        COR_LOJA
    )

    st.write("")

    hoje = estilos.agora_local().date()

    produtos = ler_produtos(armazem_id)
    vendas = ler_vendas(armazem_id)

    aba_painel, aba_produtos, aba_entrada, aba_venda, aba_receber, aba_historico = st.tabs([
        "📊 Painel",
        "🏷️ Produtos",
        "📥 Entrada de estoque",
        "🛒 Nova venda",
        "💰 A receber",
        "📜 Vendas",
    ])

    with aba_painel:
        _aba_painel(produtos, vendas, hoje)

    with aba_produtos:
        _aba_produtos(armazem_id, usuario, produtos, hoje)

    with aba_entrada:
        _aba_entrada(armazem_id, usuario, produtos, hoje)

    with aba_venda:
        _aba_nova_venda(armazem_id, usuario, produtos, vendas, hoje)

    with aba_receber:
        _aba_a_receber(armazem_id, vendas, hoje)

    with aba_historico:
        _aba_vendas(armazem_id, vendas, hoje)

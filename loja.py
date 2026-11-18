import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import html as _html

import banco
import estilos

try:
    import altair as alt
except Exception:  # altair vem junto com o Streamlit
    alt = None


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

# Lingerie (peças de fornecedor): comissão sobre o total vendido.
# Até o limite (inclusive) vale o percentual baixo; acima dele, o
# percentual alto — aplicado sobre o total inteiro.
LINGERIE_LIMITE = 500.0
LINGERIE_PCT_BAIXO = 30
LINGERIE_PCT_ALTO = 40


# =====================================================
# ACESSO
# =====================================================
# Dados de vendas e lucro são sensíveis: a aba só aparece para logins
# no formato "Fundador.Nome" e para os logins listados abaixo em
# USUARIOS_LIBERADOS. O tipo da conta (fundador/gestão) é ignorado de
# propósito — nem a Gestão nem os demais perfis enxergam esta área.
# Para liberar mais alguém, é só acrescentar o login na lista.

USUARIOS_LIBERADOS = [
    "adm.vanessa",
]

def tem_acesso(usuario, tipo):

    usuario = (usuario or "").strip()

    return (
        usuario.startswith("Fundador.")
        or usuario.lower() in USUARIOS_LIBERADOS
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
    ler_lingerie_abertas.clear()
    ler_lingerie_acertos.clear()
    ler_lingerie_pecas_fechadas.clear()


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
# ABA: LINGERIE (peças de fornecedor, com comissão)
# =====================================================
# As peças vendidas vão sendo lançadas numa lista aberta (já salvas
# no banco, então não se perdem se a página recarregar). O total
# soma sozinho e a comissão depende dele:
#
#   total até R$ 500,00  → comissão de 30% sobre o total
#   total acima de R$ 500,00 → comissão de 40% sobre o total
#
# Quando terminar a rodada com o fornecedor, "Fechar acerto" guarda
# a lista no histórico (com total, comissão e quanto repassar ao
# fornecedor) e começa uma lista nova.

@st.cache_resource(show_spinner=False)
def _garantir_schema_lingerie():

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lingerie_acertos (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            fornecedor TEXT,
            data_acerto DATE NOT NULL,
            total NUMERIC(12,2) NOT NULL,
            percentual INTEGER NOT NULL,
            comissao NUMERIC(12,2) NOT NULL,
            repasse NUMERIC(12,2) NOT NULL,
            criado_por TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lingerie_pecas (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            acerto_id BIGINT REFERENCES lingerie_acertos(id) ON DELETE SET NULL,
            descricao TEXT NOT NULL,
            preco NUMERIC(12,2) NOT NULL,
            criado_por TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lingerie_acertos_armazem ON lingerie_acertos (armazem_id, data_acerto DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lingerie_pecas_armazem ON lingerie_pecas (armazem_id, acerto_id)")

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    return True


def _calcular_comissao(total):

    total = round(float(total or 0), 2)

    percentual = (
        LINGERIE_PCT_ALTO if total > LINGERIE_LIMITE
        else LINGERIE_PCT_BAIXO
    )

    comissao = round(total * percentual / 100, 2)
    repasse = round(total - comissao, 2)

    return percentual, comissao, repasse


@st.cache_data(ttl=20, show_spinner=False)
def ler_lingerie_abertas(armazem_id):

    return _consultar("""
    SELECT
        id,
        descricao,
        preco::float AS preco
    FROM lingerie_pecas
    WHERE armazem_id = %s
    AND acerto_id IS NULL
    ORDER BY id
    """, (armazem_id,))


@st.cache_data(ttl=20, show_spinner=False)
def ler_lingerie_acertos(armazem_id):

    return _consultar("""
    SELECT
        a.id,
        COALESCE(a.fornecedor, '') AS fornecedor,
        a.data_acerto,
        a.total::float AS total,
        a.percentual,
        a.comissao::float AS comissao,
        a.repasse::float AS repasse,
        (
            SELECT COUNT(*) FROM lingerie_pecas p
            WHERE p.acerto_id = a.id
        )::int AS qtd
    FROM lingerie_acertos a
    WHERE a.armazem_id = %s
    ORDER BY a.data_acerto DESC, a.id DESC
    LIMIT 100
    """, (armazem_id,))


@st.cache_data(ttl=20, show_spinner=False)
def ler_lingerie_pecas_fechadas(armazem_id):

    return _consultar("""
    SELECT
        acerto_id,
        descricao,
        preco::float AS preco
    FROM lingerie_pecas
    WHERE armazem_id = %s
    AND acerto_id IS NOT NULL
    ORDER BY id
    """, (armazem_id,))


def adicionar_peca_lingerie(armazem_id, descricao, preco, usuario):

    _executar("""
    INSERT INTO lingerie_pecas
        (armazem_id, descricao, preco, criado_por)
    VALUES (%s, %s, %s, %s)
    """, (armazem_id, descricao, preco, usuario))

    _limpar_cache()


def excluir_peca_lingerie(id_peca, armazem_id):

    # Só remove peças da lista aberta; peças de acertos já fechados
    # só mudam se o acerto for desfeito.
    _executar("""
    DELETE FROM lingerie_pecas
    WHERE id = %s
    AND armazem_id = %s
    AND acerto_id IS NULL
    """, (id_peca, armazem_id))

    _limpar_cache()


def fechar_acerto_lingerie(armazem_id, fornecedor, data_acerto, usuario):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, preco
        FROM lingerie_pecas
        WHERE armazem_id = %s
        AND acerto_id IS NULL
        FOR UPDATE
        """, (armazem_id,))

        linhas = cursor.fetchall()

        if not linhas:
            conn.rollback()
            raise ValueError("Não há peças na lista para fechar.")

        total = round(sum(float(l[1]) for l in linhas), 2)

        percentual, comissao, repasse = _calcular_comissao(total)

        cursor.execute("""
        INSERT INTO lingerie_acertos
            (armazem_id, fornecedor, data_acerto, total,
             percentual, comissao, repasse, criado_por)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (
            armazem_id, fornecedor or None, data_acerto, total,
            percentual, comissao, repasse, usuario
        ))

        acerto_id = cursor.fetchone()[0]

        cursor.execute("""
        UPDATE lingerie_pecas
        SET acerto_id = %s
        WHERE armazem_id = %s
        AND acerto_id IS NULL
        """, (acerto_id, armazem_id))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_cache()


def desfazer_acerto_lingerie(id_acerto, armazem_id):

    # As peças voltam para a lista aberta (ON DELETE SET NULL).
    _executar("""
    DELETE FROM lingerie_acertos
    WHERE id = %s
    AND armazem_id = %s
    """, (id_acerto, armazem_id))

    _limpar_cache()


# =====================================================
# VISUAL (tema, CSS, cards, gráficos)
# =====================================================
# Tudo o que é aparência da Loja Virtual fica aqui. O CSS é
# "escopado" no container `loja-raiz` (veja render()), então não
# interfere no resto do Luxiz IA. As cores seguem o tema claro/escuro
# escolhido no topo do app.

COR_LOJA_2 = "#8b5cf6"
COR_OK = "#22c55e"
COR_AZUL = "#3b82f6"
COR_ROXO = "#a855f7"
COR_CIANO = "#0ea5e9"
COR_AMBAR = "#f59e0b"
COR_VERM = "#ef4444"
COR_TEAL = "#14b8a6"

MESES_ABREV = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]

DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def _paleta():

    escuro = st.session_state.get("tema", "escuro") != "claro"

    if escuro:
        return {
            "texto": "#e2e8f0",
            "suave": "#94a3b8",
            "card": "rgba(255,255,255,.035)",
            "card2": "rgba(255,255,255,.06)",
            "borda": "rgba(255,255,255,.09)",
            "grade": "rgba(148,163,184,.16)",
            "campo": "rgba(255,255,255,.05)",
        }

    return {
        "texto": "#0f172a",
        "suave": "#64748b",
        "card": "#ffffff",
        "card2": "#f1f5f9",
        "borda": "rgba(15,23,42,.10)",
        "grade": "rgba(15,23,42,.09)",
        "campo": "#ffffff",
    }


_CSS_LOJA = """
.st-key-loja-raiz [data-baseweb="tab-list"]{
    gap:.35rem;
    padding:.28rem;
    flex-wrap:wrap;
    background:var(--lj-card);
    border:1px solid var(--lj-borda);
    border-radius:999px;
}
.st-key-loja-raiz button[data-baseweb="tab"]{
    border-radius:999px !important;
    padding:.45rem 1rem !important;
    height:auto !important;
    background:transparent;
    transition:background .18s ease, box-shadow .18s ease;
}
.st-key-loja-raiz button[data-baseweb="tab"]:hover{
    background:rgba(217,70,239,.10) !important;
}
.st-key-loja-raiz button[data-baseweb="tab"][aria-selected="true"]{
    background:linear-gradient(135deg,var(--lj-acento),var(--lj-acento2)) !important;
    box-shadow:0 6px 16px rgba(139,92,246,.35);
}
.st-key-loja-raiz button[data-baseweb="tab"][aria-selected="true"] p{
    color:#ffffff !important;
    font-weight:800 !important;
}
.st-key-loja-raiz [data-baseweb="tab-highlight"],
.st-key-loja-raiz [data-baseweb="tab-border"]{
    display:none !important;
}

.st-key-loja-raiz [data-testid="stWidgetLabel"] p{
    font-weight:700;
    font-size:.8rem;
    letter-spacing:.2px;
    color:var(--lj-suave);
}
.st-key-loja-raiz [data-baseweb="input"],
.st-key-loja-raiz [data-baseweb="select"] > div,
.st-key-loja-raiz [data-baseweb="textarea"]{
    border-radius:12px !important;
    border:1px solid var(--lj-borda) !important;
    background:var(--lj-campo) !important;
    transition:border-color .15s ease, box-shadow .15s ease;
}
.st-key-loja-raiz [data-baseweb="base-input"]{
    border-radius:12px !important;
}
.st-key-loja-raiz [data-baseweb="input"]:focus-within,
.st-key-loja-raiz [data-baseweb="select"] > div:focus-within,
.st-key-loja-raiz [data-baseweb="textarea"]:focus-within{
    border-color:var(--lj-acento) !important;
    box-shadow:0 0 0 3px rgba(217,70,239,.22) !important;
}

.st-key-loja-raiz [data-testid="stForm"]{
    border-radius:1.1rem;
    border:1px solid var(--lj-borda);
    background:linear-gradient(145deg,rgba(217,70,239,.07),rgba(139,92,246,.03) 60%);
    padding:1.1rem 1.2rem;
}
.st-key-loja-raiz [data-testid="stExpander"]{
    border-radius:1rem;
    border:1px solid var(--lj-borda);
    background:var(--lj-card);
}
.st-key-loja-raiz [data-testid="stDataFrame"]{
    border-radius:12px;
    overflow:hidden;
    border:1px solid var(--lj-borda);
}
.st-key-loja-raiz div[class*="st-key-loja-card"]{
    border:1px solid var(--lj-borda) !important;
    background:var(--lj-card) !important;
    border-radius:1.1rem !important;
    padding:.5rem .4rem;
}

.st-key-loja-raiz button[kind="primary"],
.st-key-loja-raiz button[kind="primaryFormSubmit"]{
    background:linear-gradient(135deg,var(--lj-acento),var(--lj-acento2)) !important;
    border:none !important;
    color:#ffffff !important;
    font-weight:800 !important;
    border-radius:12px !important;
    box-shadow:0 8px 20px rgba(139,92,246,.30);
    transition:transform .15s ease, filter .15s ease;
}
.st-key-loja-raiz button[kind="primary"]:hover,
.st-key-loja-raiz button[kind="primaryFormSubmit"]:hover{
    transform:translateY(-1px);
    filter:brightness(1.08);
}
.st-key-loja-raiz button[kind="secondary"],
.st-key-loja-raiz button[kind="secondaryFormSubmit"]{
    border-radius:12px !important;
    font-weight:700 !important;
}

.lj-hero{
    position:relative;
    overflow:hidden;
    border-radius:1.2rem;
    padding:1.3rem 1.5rem;
    margin:.4rem 0 1rem 0;
    background:linear-gradient(120deg,#86198f,#7c3aed 55%,#2563eb);
    color:#ffffff;
    box-shadow:0 16px 34px rgba(124,58,237,.30);
}
.lj-hero::before{
    content:"";
    position:absolute;
    width:230px;height:230px;
    border-radius:50%;
    background:rgba(255,255,255,.12);
    top:-100px;right:-50px;
}
.lj-hero::after{
    content:"";
    position:absolute;
    width:150px;height:150px;
    border-radius:50%;
    background:rgba(255,255,255,.08);
    bottom:-80px;right:22%;
}
.lj-hero-t{
    position:relative;z-index:1;
    margin:0;
    font-size:.76rem;
    font-weight:800;
    letter-spacing:.6px;
    text-transform:uppercase;
    opacity:.85;
}
.lj-hero-v{
    position:relative;z-index:1;
    margin:.1rem 0 .6rem 0;
    font-size:2.1rem;
    font-weight:800;
    line-height:1.15;
}
.lj-hero-chips{position:relative;z-index:1;}
.lj-chip{
    display:inline-flex;
    align-items:center;
    gap:.35rem;
    margin:0 .4rem .3rem 0;
    padding:.22rem .7rem;
    border-radius:999px;
    font-size:.76rem;
    font-weight:700;
    color:#ffffff;
    background:rgba(255,255,255,.16);
    border:1px solid rgba(255,255,255,.24);
}

.lj-kpi{
    position:relative;
    overflow:hidden;
    border-radius:1rem;
    padding:.95rem 1.05rem;
    margin-bottom:.7rem;
    transition:transform .18s ease, box-shadow .18s ease;
}
.lj-kpi:hover{
    transform:translateY(-3px);
    box-shadow:0 12px 26px rgba(0,0,0,.18);
}
.lj-kpi::before{
    content:"";
    position:absolute;
    left:0;top:0;right:0;
    height:3px;
    background:linear-gradient(90deg,var(--c),transparent);
}
.lj-kpi-top{display:flex;align-items:center;gap:.55rem;}
.lj-kpi-ico{
    width:34px;height:34px;
    border-radius:10px;
    display:flex;align-items:center;justify-content:center;
    font-size:1.05rem;
    background:var(--cb);
}
.lj-kpi-rotulo{
    font-size:.7rem;
    font-weight:800;
    letter-spacing:.4px;
    text-transform:uppercase;
    color:var(--lj-suave);
}
.lj-kpi-valor{
    margin:.45rem 0 .1rem 0;
    font-size:1.55rem;
    font-weight:800;
    line-height:1.15;
    color:var(--c);
}
.lj-kpi-sub{
    min-height:1.1em;
    font-size:.74rem;
    color:var(--lj-suave);
}
.lj-up{color:#22c55e;font-weight:800;}
.lj-down{color:#ef4444;font-weight:800;}

.lj-sec{display:flex;align-items:center;gap:.7rem;margin:1rem 0 .6rem 0;}
.lj-sec-ico{
    width:36px;height:36px;
    border-radius:11px;
    display:flex;align-items:center;justify-content:center;
    font-size:1.1rem;
    background:linear-gradient(135deg,rgba(217,70,239,.25),rgba(139,92,246,.20));
}
.lj-sec-t{
    font-weight:800;
    font-size:1.05rem;
    line-height:1.2;
    color:var(--lj-texto);
}
.lj-sec-s{font-size:.76rem;color:var(--lj-suave);}

.lj-alerta{
    display:flex;
    align-items:flex-start;
    gap:.7rem;
    margin:.4rem 0;
    padding:.7rem .95rem;
    border-radius:.9rem;
    font-size:.88rem;
    color:var(--lj-texto);
    border:1px solid var(--c);
    border-left-width:4px;
    background:var(--cb);
}

.lj-vazio{
    text-align:center;
    padding:2.4rem 1rem;
    margin:.6rem 0;
    border:2px dashed var(--lj-borda);
    border-radius:1.2rem;
    background:var(--lj-card);
}
.lj-vazio-ico{font-size:2.4rem;}
.lj-vazio-t{font-weight:800;font-size:1.05rem;color:var(--lj-texto);margin-top:.3rem;}
.lj-vazio-s{font-size:.85rem;color:var(--lj-suave);margin-top:.2rem;}

.lj-badge{
    display:inline-block;
    padding:.14rem .6rem;
    border-radius:999px;
    font-size:.68rem;
    font-weight:800;
    white-space:nowrap;
    color:var(--c);
    background:var(--cb);
    border:1px solid var(--c);
}

.lj-prod{
    border-radius:1rem;
    padding:1rem 1.1rem;
    margin-bottom:.8rem;
    background:var(--lj-card);
    border:1px solid var(--lj-borda);
    border-top:3px solid var(--c);
    transition:transform .18s ease, box-shadow .18s ease;
}
.lj-prod:hover{
    transform:translateY(-3px);
    box-shadow:0 12px 26px rgba(0,0,0,.16);
}
.lj-prod-top{display:flex;justify-content:space-between;align-items:flex-start;gap:.5rem;}
.lj-prod-nome{font-weight:800;font-size:1rem;line-height:1.25;color:var(--lj-texto);}
.lj-prod-cat{font-size:.74rem;color:var(--lj-suave);margin:.15rem 0 .7rem 0;}
.lj-prod-precos{display:grid;grid-template-columns:repeat(3,1fr);gap:.4rem;margin-bottom:.75rem;}
.lj-prod-precos div{
    background:var(--lj-card2);
    border-radius:.6rem;
    padding:.4rem .4rem;
    text-align:center;
}
.lj-prod-precos span{
    display:block;
    font-size:.62rem;
    font-weight:700;
    letter-spacing:.3px;
    text-transform:uppercase;
    color:var(--lj-suave);
}
.lj-prod-precos b{font-size:.84rem;color:var(--lj-texto);}
.lj-trilho{
    height:8px;
    border-radius:999px;
    overflow:hidden;
    background:rgba(148,163,184,.25);
}
.lj-trilho-fill{
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg,var(--c),var(--c2,var(--c)));
}
.lj-prod-estoque{
    display:flex;
    justify-content:space-between;
    margin-top:.35rem;
    font-size:.74rem;
    color:var(--lj-suave);
}

.lj-linha{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
    padding:.75rem 1rem;
    border-radius:.9rem;
    background:var(--lj-card);
    border:1px solid var(--lj-borda);
    border-left:4px solid var(--c);
}
.lj-linha-esq{display:flex;align-items:center;gap:.8rem;min-width:0;}
.lj-linha-t{font-weight:800;color:var(--lj-texto);}
.lj-linha-s{font-size:.76rem;color:var(--lj-suave);}
.lj-linha-dir{text-align:right;white-space:nowrap;}
.lj-linha-v{font-weight:800;font-size:1.05rem;color:var(--lj-texto);}
.lj-num{
    flex-shrink:0;
    width:30px;height:30px;
    border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-size:.8rem;
    font-weight:800;
    color:#ffffff;
    background:linear-gradient(135deg,var(--lj-acento),var(--lj-acento2));
}

.lj-resumo{
    border-radius:1.1rem;
    padding:1.1rem 1.2rem;
    margin-bottom:.8rem;
    background:linear-gradient(145deg,rgba(217,70,239,.10),rgba(139,92,246,.05) 65%);
    border:1px solid rgba(217,70,239,.30);
}
.lj-resumo-topo{
    font-size:.72rem;
    font-weight:800;
    letter-spacing:.5px;
    text-transform:uppercase;
    color:var(--lj-suave);
}
.lj-resumo-prod{font-weight:800;font-size:1rem;margin-top:.3rem;color:var(--lj-texto);}
.lj-resumo-total{
    font-size:2rem;
    font-weight:800;
    line-height:1.2;
    margin:.1rem 0 .5rem 0;
    color:var(--lj-acento);
}
.lj-resumo-linha{
    display:flex;
    justify-content:space-between;
    padding:.38rem 0;
    font-size:.86rem;
    color:var(--lj-suave);
    border-bottom:1px dashed var(--lj-borda);
}
.lj-resumo-linha b{color:var(--lj-texto);}

.lj-prog{
    border-radius:1.1rem;
    padding:1.1rem 1.3rem;
    margin-bottom:.8rem;
    background:var(--lj-card);
    border:1px solid var(--lj-borda);
}
.lj-prog-topo{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;flex-wrap:wrap;}
.lj-prog-titulo{
    font-size:.72rem;
    font-weight:800;
    letter-spacing:.5px;
    text-transform:uppercase;
    color:var(--lj-suave);
}
.lj-prog-valor{font-size:1.8rem;font-weight:800;color:var(--c);line-height:1.2;}
.lj-prog-pista{
    position:relative;
    height:16px;
    margin:1.4rem 0 2rem 0;
    border-radius:999px;
    background:rgba(148,163,184,.25);
}
.lj-prog-fill{
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg,var(--c),var(--c2));
    transition:width .4s ease;
}
.lj-prog-marca{
    position:absolute;
    top:-6px;
    width:2px;height:28px;
    background:var(--lj-texto);
    opacity:.55;
}
.lj-prog-marca span{
    position:absolute;
    top:32px;left:50%;
    transform:translateX(-50%);
    font-size:.7rem;
    font-weight:800;
    white-space:nowrap;
    color:var(--lj-suave);
}
.lj-prog-msg{font-size:.84rem;color:var(--lj-texto);margin-bottom:.8rem;}
.lj-faixas{display:flex;gap:.6rem;flex-wrap:wrap;}
.lj-faixa{
    flex:1;
    min-width:150px;
    padding:.55rem .8rem;
    border-radius:.8rem;
    font-size:.8rem;
    color:var(--lj-texto);
    border:1px solid var(--lj-borda);
    opacity:.5;
}
.lj-faixa.ativa{
    opacity:1;
    border-color:var(--c);
    background:var(--cb);
}
.lj-faixa b{font-size:1.1rem;color:var(--c);}
"""


def _injetar_css():

    p = _paleta()

    variaveis = (
        ".st-key-loja-raiz{"
        f"--lj-texto:{p['texto']};"
        f"--lj-suave:{p['suave']};"
        f"--lj-card:{p['card']};"
        f"--lj-card2:{p['card2']};"
        f"--lj-borda:{p['borda']};"
        f"--lj-campo:{p['campo']};"
        f"--lj-acento:{COR_LOJA};"
        f"--lj-acento2:{COR_LOJA_2};"
        "}"
    )

    st.markdown(
        "<style>" + variaveis + _CSS_LOJA + "</style>",
        unsafe_allow_html=True
    )


# ---------------- pequenos componentes HTML ----------------

def _e(texto):

    return _html.escape("" if texto is None else str(texto))


def _titulo(icone, titulo, sub=""):

    st.markdown(
        f'<div class="lj-sec"><div class="lj-sec-ico">{icone}</div>'
        f'<div><div class="lj-sec-t">{titulo}</div>'
        + (f'<div class="lj-sec-s">{sub}</div>' if sub else "")
        + '</div></div>',
        unsafe_allow_html=True
    )


def _alerta(cor, icone, texto_html):

    st.markdown(
        f'<div class="lj-alerta" style="--c:{cor};--cb:{cor}1a;">'
        f'<div>{icone}</div><div>{texto_html}</div></div>',
        unsafe_allow_html=True
    )


def _vazio(icone, titulo, texto):

    st.markdown(
        f'<div class="lj-vazio"><div class="lj-vazio-ico">{icone}</div>'
        f'<div class="lj-vazio-t">{titulo}</div>'
        f'<div class="lj-vazio-s">{texto}</div></div>',
        unsafe_allow_html=True
    )


def _kpis(itens):

    # Cada item: (ícone, rótulo, valor, cor) ou (ícone, rótulo, valor, cor, subtexto)
    colunas = st.columns(len(itens))

    for item, coluna in zip(itens, colunas):

        icone, rotulo, valor, cor = item[:4]
        sub = item[4] if len(item) > 4 else ""

        with coluna:

            st.markdown(
                f'<div class="lj-kpi" style="--c:{cor};--cb:{cor}26;'
                f'background:linear-gradient(145deg,{cor}1f,{cor}08 70%);'
                f'border:1px solid {cor}40;">'
                f'<div class="lj-kpi-top"><div class="lj-kpi-ico">{icone}</div>'
                f'<div class="lj-kpi-rotulo">{rotulo}</div></div>'
                f'<div class="lj-kpi-valor">{valor}</div>'
                f'<div class="lj-kpi-sub">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


def _delta_pct(atual, anterior):

    if anterior is None:
        return None

    if anterior <= 0:
        return None if atual <= 0 else float("inf")

    return (atual - anterior) / anterior * 100


def _delta_html(pct):

    if pct is None:
        return ""

    if pct == float("inf"):
        return '<span class="lj-up">▲ novo</span> vs. período anterior'

    seta, classe = ("▲", "lj-up") if pct >= 0 else ("▼", "lj-down")

    return (
        f'<span class="{classe}">{seta} {abs(pct):.0f}%</span> '
        f'vs. período anterior'
    )


# =====================================================
# GRÁFICOS (Altair — já vem instalado junto com o Streamlit)
# =====================================================

def _configurar(chart, altura=None):

    p = _paleta()

    if altura:
        chart = chart.properties(height=altura)

    return (
        chart
        .configure(background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor=p["suave"],
            titleColor=p["suave"],
            gridColor=p["grade"],
            domainColor=p["grade"],
            tickColor=p["grade"],
            labelFontSize=11,
        )
        .configure_legend(
            labelColor=p["texto"],
            titleColor=p["suave"],
            orient="bottom",
            labelFontSize=11,
        )
    )


def _exibir(chart):

    try:
        st.altair_chart(chart, width="stretch", theme=None)
    except TypeError:
        st.altair_chart(chart, use_container_width=True, theme=None)


def _plot(construtor):

    # Se um gráfico falhar por qualquer motivo, só ele some — a aba
    # continua funcionando.
    if alt is None:
        st.caption("Gráficos indisponíveis neste servidor.")
        return

    try:
        _exibir(construtor())
    except Exception:
        st.caption("⚠️ Não foi possível desenhar este gráfico agora.")


def _chart_linhas_mensal(longo, ordem):

    cores = alt.Scale(
        domain=["Vendido", "Lucro"],
        range=[COR_AZUL, COR_OK]
    )

    base = alt.Chart(longo).encode(
        x=alt.X("mes:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("valor:Q", title=None, stack=None, axis=alt.Axis(format=",.0f")),
        color=alt.Color("serie:N", scale=cores, legend=alt.Legend(title=None)),
        tooltip=[
            alt.Tooltip("mes:N", title="Mês"),
            alt.Tooltip("serie:N", title="Item"),
            alt.Tooltip("valor:Q", title="R$", format=",.2f"),
        ],
    )

    area = base.mark_area(opacity=0.16, interpolate="monotone")
    linha = base.mark_line(strokeWidth=3, interpolate="monotone")
    pontos = base.mark_point(filled=True, size=70)

    return _configurar(alt.layer(area, linha, pontos), 280)


def _chart_donut(df, cat, val, cores):

    escala = alt.Scale(domain=list(cores.keys()), range=list(cores.values()))

    chart = alt.Chart(df).mark_arc(
        innerRadius=62,
        padAngle=0.02,
        cornerRadius=4,
    ).encode(
        theta=alt.Theta(f"{val}:Q"),
        color=alt.Color(f"{cat}:N", scale=escala, legend=alt.Legend(title=None)),
        tooltip=[
            alt.Tooltip(f"{cat}:N", title="Item"),
            alt.Tooltip(f"{val}:Q", title="R$", format=",.2f"),
        ],
    )

    return _configurar(chart, 250)


def _chart_barras_h(df, cat, val, cor=None, cores=None, rotulo_fn=None):

    p = _paleta()

    rotulo_fn = rotulo_fn or _brl

    df = df.copy()
    df["rot"] = df[val].map(rotulo_fn)

    ordem = list(df[cat])

    vmax = float(df[val].max()) if len(df) else 1.0
    vmax = vmax if vmax > 0 else 1.0

    base = alt.Chart(df).encode(
        y=alt.Y(
            f"{cat}:N", sort=ordem, title=None,
            axis=alt.Axis(labelLimit=190)
        ),
        x=alt.X(
            f"{val}:Q", title=None,
            scale=alt.Scale(domain=[0, vmax * 1.32]),
            axis=None
        ),
    )

    if cores:

        barras = base.mark_bar(cornerRadiusEnd=6, size=20).encode(
            color=alt.Color(
                f"{cat}:N",
                scale=alt.Scale(
                    domain=list(cores.keys()),
                    range=list(cores.values())
                ),
                legend=None
            ),
            tooltip=[
                alt.Tooltip(f"{cat}:N", title="Item"),
                alt.Tooltip("rot:N", title="Valor"),
            ],
        )

    else:

        barras = base.mark_bar(
            cornerRadiusEnd=6, size=20, color=cor or COR_LOJA
        ).encode(
            tooltip=[
                alt.Tooltip(f"{cat}:N", title="Item"),
                alt.Tooltip("rot:N", title="Valor"),
            ],
        )

    rotulos = base.mark_text(
        align="left", dx=6, fontSize=11, fontWeight=700, color=p["texto"]
    ).encode(text=alt.Text("rot:N"))

    altura = max(70, 34 * len(df) + 20)

    return _configurar(alt.layer(barras, rotulos), altura)


def _chart_colunas(df, cat, val, cor, ordem=None, rotulo_fn=None):

    p = _paleta()

    rotulo_fn = rotulo_fn or _brl

    df = df.copy()
    df["rot"] = df[val].map(rotulo_fn)

    ordem = ordem or list(df[cat])

    base = alt.Chart(df).encode(
        x=alt.X(f"{cat}:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{val}:Q", title=None, axis=alt.Axis(format=",.0f")),
    )

    barras = base.mark_bar(cornerRadiusEnd=6, color=cor).encode(
        tooltip=[
            alt.Tooltip(f"{cat}:N", title="Item"),
            alt.Tooltip("rot:N", title="Valor"),
        ],
    )

    return _configurar(barras, 240)


def _chart_estoque(df):

    p = _paleta()

    df = df.sort_values("estoque", ascending=False).copy()

    ordem = list(df["produto"])

    cores = alt.Scale(
        domain=["OK", "Baixo", "Sem estoque"],
        range=[COR_OK, COR_AMBAR, COR_VERM]
    )

    base = alt.Chart(df).encode(
        y=alt.Y("produto:N", sort=ordem, title=None, axis=alt.Axis(labelLimit=190)),
    )

    barras = base.mark_bar(cornerRadiusEnd=6, size=20).encode(
        x=alt.X("estoque:Q", title=None),
        color=alt.Color(
            "situacao:N", scale=cores,
            legend=alt.Legend(title=None)
        ),
        tooltip=[
            alt.Tooltip("produto:N", title="Produto"),
            alt.Tooltip("estoque:Q", title="Em estoque"),
            alt.Tooltip("minimo:Q", title="Mínimo"),
        ],
    )

    com_minimo = df[df["minimo"] > 0]

    camadas = [barras]

    if not com_minimo.empty:

        marcas = alt.Chart(com_minimo).mark_tick(
            color=p["texto"], thickness=3, size=24
        ).encode(
            y=alt.Y("produto:N", sort=ordem),
            x=alt.X("minimo:Q"),
        )

        camadas.append(marcas)

    return _configurar(alt.layer(*camadas), max(90, 36 * len(df) + 40))


def _chart_acertos(df):

    base = alt.Chart(df).encode(
        x=alt.X("rot:N", sort=list(df["rot"]), title=None, axis=alt.Axis(labelAngle=0)),
    )

    barras = base.mark_bar(cornerRadiusEnd=6, color=COR_LOJA, opacity=0.85).encode(
        y=alt.Y("total:Q", title=None, axis=alt.Axis(format=",.0f")),
        tooltip=[
            alt.Tooltip("rot:N", title="Acerto"),
            alt.Tooltip("total:Q", title="Total vendido", format=",.2f"),
            alt.Tooltip("percentual:Q", title="Comissão %"),
        ],
    )

    linha = base.mark_line(color=COR_OK, strokeWidth=3, point=alt.OverlayMarkDef(
        color=COR_OK, size=70, filled=True
    )).encode(
        y=alt.Y("comissao:Q", title=None),
        tooltip=[
            alt.Tooltip("rot:N", title="Acerto"),
            alt.Tooltip("comissao:Q", title="Sua comissão", format=",.2f"),
        ],
    )

    return _configurar(alt.layer(barras, linha), 250)


# =====================================================
# APOIO (DataFrames, períodos)
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


def _periodo_anterior(opcao, hoje):

    inicio, fim = _intervalo(opcao, hoje)

    if inicio is None:
        return None, None

    dias = (fim - inicio).days + 1

    ant_fim = inicio - timedelta(days=1)
    ant_inicio = ant_fim - timedelta(days=dias - 1)

    return ant_inicio, ant_fim


def _filtrar_intervalo(df, inicio, fim):

    if df.empty or inicio is None:
        return df

    return df[
        (df["data_venda"] >= pd.Timestamp(inicio))
        & (df["data_venda"] <= pd.Timestamp(fim))
    ]


def _filtrar_periodo(df, opcao, hoje):

    inicio, fim = _intervalo(opcao, hoje)

    return _filtrar_intervalo(df, inicio, fim)


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


def _cor_status(texto_status):

    if texto_status.startswith("🔴"):
        return COR_VERM

    if texto_status.startswith("🟠"):
        return COR_AMBAR

    if texto_status.startswith("✅"):
        return COR_OK

    return COR_AZUL


def _mapa_produtos(produtos):

    return {
        p["id"]: (
            f'{p["nome"]} — estoque: {p["estoque"]} — '
            f'{_brl(p["preco_venda"])}'
        )
        for p in produtos
    }


def _situacao_produto(p):

    if p["estoque"] <= 0:
        return "Sem estoque", COR_VERM

    if p["estoque_minimo"] and p["estoque"] <= p["estoque_minimo"]:
        return "Estoque baixo", COR_AMBAR

    return "Em estoque", COR_OK


# =====================================================
# ABA: PAINEL
# =====================================================

def _aba_painel(produtos, vendas, hoje):

    df = _df_vendas(vendas)

    if not produtos and df.empty:

        _vazio(
            "🛍️",
            "Sua loja ainda está vazia",
            "Cadastre o primeiro produto na aba <b>🏷️ Produtos</b> "
            "para o painel ganhar vida."
        )

        return

    col_t, col_p = st.columns([3, 1.3])

    with col_t:
        _titulo(
            "📊", "Visão geral da loja",
            "Vendas, lucro, estoque e recebimentos num só lugar"
        )

    with col_p:
        periodo = st.selectbox(
            "📅 Período",
            OPCOES_PERIODO,
            index=0,
            key="loja_painel_periodo"
        )

    df_periodo = _filtrar_periodo(df, periodo, hoje)

    ini_ant, fim_ant = _periodo_anterior(periodo, hoje)

    df_ant = (
        _filtrar_intervalo(df, ini_ant, fim_ant)
        if ini_ant is not None else None
    )

    receita = _soma(df_periodo, "total")
    lucro = _soma(df_periodo, "lucro")
    qtd_vendida = int(_soma(df_periodo, "quantidade"))
    num_vendas = 0 if df_periodo.empty else len(df_periodo)
    ticket = receita / num_vendas if num_vendas else 0.0
    margem = (lucro / receita * 100) if receita else 0.0

    clientes_periodo = (
        0 if df_periodo.empty
        else df_periodo.loc[df_periodo["cliente"] != "", "cliente"].nunique()
    )

    if df_ant is not None:

        receita_ant = _soma(df_ant, "total")
        lucro_ant = _soma(df_ant, "lucro")
        qtd_ant = int(_soma(df_ant, "quantidade"))
        n_ant = 0 if df_ant.empty else len(df_ant)
        ticket_ant = receita_ant / n_ant if n_ant else 0.0

        d_receita = _delta_pct(receita, receita_ant)
        d_lucro = _delta_pct(lucro, lucro_ant)
        d_qtd = _delta_pct(qtd_vendida, qtd_ant)
        d_ticket = _delta_pct(ticket, ticket_ant)

    else:

        d_receita = d_lucro = d_qtd = d_ticket = None

    st.markdown(
        '<div class="lj-hero">'
        f'<p class="lj-hero-t">Faturamento · {periodo.lower()}</p>'
        f'<p class="lj-hero-v">{_brl(receita)}</p>'
        '<div class="lj-hero-chips">'
        f'<span class="lj-chip">🧾 {num_vendas} venda(s)</span>'
        f'<span class="lj-chip">👥 {clientes_periodo} cliente(s)</span>'
        f'<span class="lj-chip">📦 {qtd_vendida} unidade(s)</span>'
        f'<span class="lj-chip">🏷️ {len(produtos)} produto(s) cadastrado(s)</span>'
        '</div></div>',
        unsafe_allow_html=True
    )

    _kpis([
        ("📈", "Lucro", _brl(lucro), COR_OK, _delta_html(d_lucro)),
        ("🎯", "Margem de lucro", f"{margem:.1f}%", COR_ROXO, "lucro ÷ vendido"),
        ("📦", "Unidades vendidas", str(qtd_vendida), COR_AZUL, _delta_html(d_qtd)),
        ("🧾", "Ticket médio", _brl(ticket), COR_CIANO, _delta_html(d_ticket)),
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

    n_pendentes = 0 if pendentes.empty else len(pendentes)
    n_vencidos = 0 if vencidos.empty else len(vencidos)

    _kpis([
        ("⏳", "A receber", _brl(a_receber), COR_AMBAR, f"{n_pendentes} venda(s) pendente(s)"),
        ("🔴", "Vencido", _brl(total_vencido), COR_VERM, f"{n_vencidos} venda(s) em atraso"),
        ("🏷️", "Estoque (valor pago)", _brl(valor_estoque_custo), "#64748b", "o que você investiu"),
        (
            "🛍️", "Estoque (valor de venda)", _brl(valor_estoque_venda), COR_LOJA,
            f"lucro potencial {_brl(valor_estoque_venda - valor_estoque_custo)}"
        ),
    ])

    # ---------------- alertas ----------------

    criticos = [
        p for p in produtos
        if p["estoque"] <= 0
        or (p["estoque_minimo"] > 0 and p["estoque"] <= p["estoque_minimo"])
    ]

    if criticos:

        texto_criticos = ", ".join(
            f'<b>{_e(p["nome"])}</b> ({p["estoque"]})'
            for p in criticos
        )

        _alerta(COR_AMBAR, "📦", f"<b>Repor estoque:</b> {texto_criticos}")

    if n_vencidos:

        _alerta(
            COR_VERM, "🔴",
            f"<b>{n_vencidos} pagamento(s) vencido(s)</b>, somando "
            f"{_brl(total_vencido)}. Veja na aba <b>💰 A receber</b>."
        )

    # ---------------- gráficos ----------------

    if df.empty:

        st.write("")

        _vazio(
            "📊", "Os gráficos aparecem com a primeira venda",
            "Registre uma venda na aba <b>🛒 Nova venda</b>."
        )

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

        rotulos_meses = [
            f"{MESES_ABREV[m.month - 1]}/{str(m.year)[2:]}" for m in mensal.index
        ]

        longo = pd.DataFrame(
            [
                {"mes": r, "serie": "Vendido", "valor": float(v)}
                for r, v in zip(rotulos_meses, mensal["total"])
            ]
            + [
                {"mes": r, "serie": "Lucro", "valor": float(v)}
                for r, v in zip(rotulos_meses, mensal["lucro"])
            ]
        )

        recebido = _soma(df[df["pago"]], "total")

        no_prazo = max(a_receber - total_vencido, 0.0)

        col_a, col_b = st.columns([2, 1])

        with col_a:

            with st.container(border=True, key="loja-card-mensal"):

                _titulo("📈", "Vendas e lucro por mês", "Últimos 12 meses")

                _plot(lambda: _chart_linhas_mensal(longo, rotulos_meses))

        with col_b:

            with st.container(border=True, key="loja-card-receb"):

                _titulo("💳", "Recebimentos", "Quanto já entrou e quanto falta")

                dados_receb = pd.DataFrame({
                    "situacao": ["Recebido", "A receber", "Vencido"],
                    "valor": [recebido, no_prazo, total_vencido],
                })

                dados_receb = dados_receb[dados_receb["valor"] > 0]

                if dados_receb.empty:
                    st.caption("Sem valores para mostrar.")
                else:
                    _plot(lambda: _chart_donut(
                        dados_receb, "situacao", "valor",
                        {
                            "Recebido": COR_OK,
                            "A receber": COR_AMBAR,
                            "Vencido": COR_VERM,
                        }
                    ))

        col_c, col_d = st.columns(2)

        with col_c:

            with st.container(border=True, key="loja-card-top"):

                _titulo("🏆", "Mais vendidos", periodo)

                if df_periodo.empty:
                    st.caption("Sem vendas neste período.")
                else:
                    por_produto = (
                        df_periodo.groupby("produto_nome")["total"]
                        .sum()
                        .sort_values(ascending=False)
                        .head(8)
                        .reset_index()
                    )
                    _plot(lambda: _chart_barras_h(
                        por_produto, "produto_nome", "total", cor=COR_ROXO
                    ))

        with col_d:

            with st.container(border=True, key="loja-card-lucroprod"):

                _titulo("💰", "Lucro por produto", periodo)

                if df_periodo.empty:
                    st.caption("Sem vendas neste período.")
                else:
                    lucro_produto = (
                        df_periodo.groupby("produto_nome")["lucro"]
                        .sum()
                        .sort_values(ascending=False)
                        .head(8)
                        .reset_index()
                    )
                    _plot(lambda: _chart_barras_h(
                        lucro_produto, "produto_nome", "lucro", cor=COR_OK
                    ))

        col_e, col_f = st.columns(2)

        with col_e:

            with st.container(border=True, key="loja-card-clientes"):

                _titulo("👥", "Melhores clientes", periodo)

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
                        .head(8)
                        .reset_index()
                    )
                    _plot(lambda: _chart_barras_h(
                        por_cliente, "cliente", "total", cor=COR_CIANO
                    ))

        with col_f:

            with st.container(border=True, key="loja-card-formas"):

                _titulo("💠", "Formas de pagamento", periodo)

                formas = (
                    df_periodo[df_periodo["forma_pagamento"] != ""]
                    if not df_periodo.empty else df_periodo
                )

                if formas.empty:
                    st.caption("Sem vendas neste período.")
                else:
                    por_forma = (
                        formas.groupby("forma_pagamento")["total"]
                        .sum()
                        .reset_index()
                    )

                    paleta_formas = [
                        COR_LOJA, COR_AZUL, COR_OK, COR_AMBAR,
                        COR_CIANO, COR_ROXO, "#64748b",
                    ]

                    cores_formas = {
                        nome: paleta_formas[i % len(paleta_formas)]
                        for i, nome in enumerate(por_forma["forma_pagamento"])
                    }

                    _plot(lambda: _chart_donut(
                        por_forma, "forma_pagamento", "total", cores_formas
                    ))

        col_g, col_h = st.columns(2)

        with col_g:

            with st.container(border=True, key="loja-card-semana"):

                _titulo("🗓️", "Vendas por dia da semana", periodo)

                if df_periodo.empty:
                    st.caption("Sem vendas neste período.")
                else:
                    por_dia = (
                        df_periodo.groupby(df_periodo["data_venda"].dt.dayofweek)["total"]
                        .sum()
                        .reindex(range(7), fill_value=0.0)
                    )

                    dados_dia = pd.DataFrame({
                        "dia": DIAS_SEMANA,
                        "total": [float(v) for v in por_dia.values],
                    })

                    _plot(lambda: _chart_colunas(
                        dados_dia, "dia", "total", COR_AZUL, ordem=DIAS_SEMANA
                    ))

        with col_h:

            with st.container(border=True, key="loja-card-prev"):

                _titulo("⏳", "Previsão de recebimentos", "Por mês de vencimento")

                if pendentes.empty:
                    st.caption("Nada a receber no momento.")
                else:
                    prev = pendentes.copy()

                    prev["mes"] = prev["data_pagamento"].dt.strftime("%Y-%m")
                    prev["mes"] = prev["mes"].fillna("Sem data")

                    por_mes = (
                        prev.groupby("mes")["total"]
                        .sum()
                        .sort_index()
                        .reset_index()
                    )

                    _plot(lambda: _chart_colunas(
                        por_mes, "mes", "total", COR_AMBAR
                    ))

    if produtos:

        col_i, col_j = st.columns(2)

        with col_i:

            with st.container(border=True, key="loja-card-estoque"):

                _titulo(
                    "📦", "Estoque atual × mínimo",
                    "O traço marca o estoque mínimo"
                )

                dados_estoque = pd.DataFrame({
                    "produto": [p["nome"] for p in produtos],
                    "estoque": [max(p["estoque"], 0) for p in produtos],
                    "minimo": [p["estoque_minimo"] for p in produtos],
                    "situacao": [
                        {"Em estoque": "OK", "Estoque baixo": "Baixo",
                         "Sem estoque": "Sem estoque"}[_situacao_produto(p)[0]]
                        for p in produtos
                    ],
                })

                _plot(lambda: _chart_estoque(dados_estoque))

        with col_j:

            with st.container(border=True, key="loja-card-margem"):

                _titulo("🎯", "Margem por produto", "Quanto sobra em cada venda")

                com_preco = [p for p in produtos if p["preco_venda"] > 0]

                if not com_preco:
                    st.caption("Cadastre o preço de venda dos produtos.")
                else:
                    dados_margem = pd.DataFrame({
                        "produto": [p["nome"] for p in com_preco],
                        "margem": [
                            (p["preco_venda"] - p["custo"]) / p["preco_venda"] * 100
                            for p in com_preco
                        ],
                    }).sort_values("margem", ascending=False).head(10)

                    _plot(lambda: _chart_barras_h(
                        dados_margem, "produto", "margem", cor=COR_TEAL,
                        rotulo_fn=lambda v: f"{v:.0f}%"
                    ))


# =====================================================
# ABA: PRODUTOS
# =====================================================

def _card_produto(p):

    situacao, cor = _situacao_produto(p)

    lucro_un = p["preco_venda"] - p["custo"]

    referencia = max(p["estoque_minimo"] * 2, p["estoque"], 1)
    pct = max(0, min(100, p["estoque"] / referencia * 100))

    categoria = p["categoria"] or "Sem categoria"

    return (
        f'<div class="lj-prod" style="--c:{cor};--cb:{cor}1f;">'
        f'<div class="lj-prod-top">'
        f'<div class="lj-prod-nome">{_e(p["nome"])}</div>'
        f'<span class="lj-badge">{situacao}</span></div>'
        f'<div class="lj-prod-cat">🏷️ {_e(categoria)}</div>'
        f'<div class="lj-prod-precos">'
        f'<div><span>Pago</span><b>{_brl(p["custo"])}</b></div>'
        f'<div><span>Venda</span><b>{_brl(p["preco_venda"])}</b></div>'
        f'<div><span>Lucro/un.</span><b>{_brl(lucro_un)}</b></div>'
        f'</div>'
        f'<div class="lj-trilho"><div class="lj-trilho-fill" style="width:{pct:.0f}%"></div></div>'
        f'<div class="lj-prod-estoque"><span>{p["estoque"]} em estoque</span>'
        f'<span>mín. {p["estoque_minimo"]}</span></div>'
        f'</div>'
    )


def _aba_produtos(armazem_id, usuario, produtos, hoje):

    with st.expander("➕ Cadastrar novo produto", expanded=not produtos):

        with st.form("loja_form_produto", clear_on_submit=True):

            col1, col2 = st.columns([2, 1])

            with col1:
                nome = st.text_input(
                    "🏷️ Nome do produto",
                    placeholder="Ex.: Camiseta básica branca"
                )

            with col2:
                categoria = st.text_input(
                    "📂 Categoria (opcional)",
                    placeholder="Ex.: Roupas"
                )

            col3, col4 = st.columns(2)

            with col3:
                custo = st.number_input(
                    "💸 Preço pago (custo por unidade) — R$",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f"
                )

            with col4:
                preco_venda = st.number_input(
                    "💰 Preço de venda (por unidade) — R$",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f"
                )

            col5, col6 = st.columns(2)

            with col5:
                estoque_inicial = st.number_input(
                    "📦 Quantidade que você tem agora",
                    min_value=0,
                    step=1,
                    value=0
                )

            with col6:
                estoque_minimo = st.number_input(
                    "🔔 Avisar quando chegar em (estoque mínimo)",
                    min_value=0,
                    step=1,
                    value=0
                )

            salvar = st.form_submit_button(
                "💾 Salvar produto", type="primary", width="stretch"
            )

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

    if not produtos:

        _vazio(
            "🏷️", "Nenhum produto cadastrado",
            "Abra <b>➕ Cadastrar novo produto</b> acima para começar."
        )

        return

    unidades = sum(max(p["estoque"], 0) for p in produtos)

    valor_venda = sum(max(p["estoque"], 0) * p["preco_venda"] for p in produtos)

    n_baixo = sum(
        1 for p in produtos if _situacao_produto(p)[0] != "Em estoque"
    )

    _kpis([
        ("🏷️", "Produtos", str(len(produtos)), COR_LOJA),
        ("📦", "Unidades em estoque", str(unidades), COR_AZUL),
        ("🛍️", "Valor em estoque (venda)", _brl(valor_venda), COR_OK),
        (
            "🔔", "Precisam de reposição", str(n_baixo),
            COR_VERM if n_baixo else COR_TEAL
        ),
    ])

    _titulo("🛒", "Catálogo", "Seus produtos, preços e situação do estoque")

    busca = st.text_input(
        "🔎 Buscar produto",
        placeholder="Digite o nome ou a categoria...",
        key="loja_busca_produto"
    )

    termo = (busca or "").strip().lower()

    visiveis = [
        p for p in produtos
        if not termo
        or termo in p["nome"].lower()
        or termo in (p["categoria"] or "").lower()
    ]

    if not visiveis:

        st.info("Nenhum produto encontrado com essa busca.")

    for inicio in range(0, len(visiveis), 3):

        colunas = st.columns(3)

        for offset in range(3):

            indice = inicio + offset

            if indice >= len(visiveis):
                continue

            with colunas[offset]:

                st.markdown(
                    _card_produto(visiveis[indice]),
                    unsafe_allow_html=True
                )

    with st.expander("📋 Ver em formato de tabela"):

        linhas = []

        for p in produtos:

            lucro_un = p["preco_venda"] - p["custo"]

            margem = (
                lucro_un / p["preco_venda"] * 100
                if p["preco_venda"] > 0 else 0
            )

            linhas.append({
                "Produto": p["nome"],
                "Categoria": p["categoria"] or "—",
                "Preço pago": _brl(p["custo"]),
                "Preço de venda": _brl(p["preco_venda"]),
                "Lucro por un.": _brl(lucro_un),
                "Margem": f"{margem:.0f}%",
                "Estoque": p["estoque"],
                "Situação": _situacao_produto(p)[0],
                "Valor em estoque (venda)": _brl(
                    max(p["estoque"], 0) * p["preco_venda"]
                ),
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
                nome_ed = st.text_input("🏷️ Nome", value=produto["nome"])

            with col2:
                categoria_ed = st.text_input("📂 Categoria", value=produto["categoria"])

            col3, col4, col5 = st.columns(3)

            with col3:
                custo_ed = st.number_input(
                    "💸 Preço pago — R$",
                    min_value=0.0, step=1.0, format="%.2f",
                    value=float(produto["custo"])
                )

            with col4:
                preco_ed = st.number_input(
                    "💰 Preço de venda — R$",
                    min_value=0.0, step=1.0, format="%.2f",
                    value=float(produto["preco_venda"])
                )

            with col5:
                minimo_ed = st.number_input(
                    "🔔 Estoque mínimo",
                    min_value=0, step=1,
                    value=int(produto["estoque_minimo"])
                )

            salvar_ed = st.form_submit_button(
                "💾 Salvar alterações", type="primary", width="stretch"
            )

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

        _vazio(
            "📥", "Cadastre um produto primeiro",
            "Use a aba <b>🏷️ Produtos</b> para cadastrar o que você revende."
        )

        return

    _titulo(
        "📥", "Entrada de estoque",
        "Use quando comprar mais mercadoria. Se informar o preço pago, "
        "ele vira o novo preço pago do produto."
    )

    mapa = _mapa_produtos(produtos)

    with st.form("loja_form_entrada", clear_on_submit=True):

        pid = st.selectbox(
            "🏷️ Produto",
            list(mapa.keys()),
            format_func=lambda i: mapa[i]
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            quantidade = st.number_input(
                "📦 Quantidade comprada", min_value=1, step=1, value=1
            )

        with col2:
            custo = st.number_input(
                "💸 Preço pago por unidade — R$",
                min_value=0.0, step=1.0, format="%.2f",
                help="Deixe 0 para manter o preço pago atual do produto."
            )

        with col3:
            data_entrada = st.date_input(
                "📅 Data da compra", value=hoje, format="DD/MM/YYYY"
            )

        col4, col5 = st.columns(2)

        with col4:
            fornecedor = st.text_input(
                "🏭 Fornecedor (opcional)",
                placeholder="Ex.: Distribuidora Central"
            )

        with col5:
            observacao = st.text_input(
                "📝 Observação (opcional)",
                placeholder="Ex.: nota fiscal 1234"
            )

        salvar = st.form_submit_button(
            "📥 Registrar entrada", type="primary", width="stretch"
        )

    if salvar:

        with estilos.mostrar_processando("registrando entrada..."):
            registrar_entrada(
                armazem_id, pid, int(quantidade), custo, data_entrada,
                (fornecedor or "").strip(), (observacao or "").strip(), usuario
            )

        estilos.notificar_sucesso("entrada de estoque registrada.")
        _recarregar()

    entradas = ler_entradas(armazem_id)

    if not entradas:

        st.caption("Nenhuma entrada registrada ainda.")

        return

    investido = sum(e["quantidade"] * e["custo_unitario"] for e in entradas)

    unidades = sum(e["quantidade"] for e in entradas)

    _kpis([
        ("📥", "Entradas registradas", str(len(entradas)), COR_AZUL, "últimos lançamentos"),
        ("📦", "Unidades compradas", str(unidades), COR_ROXO),
        ("💸", "Total investido", _brl(investido), COR_AMBAR),
    ])

    _titulo("📜", "Últimas entradas")

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

        _vazio(
            "🛒", "Cadastre um produto primeiro",
            "Use a aba <b>🏷️ Produtos</b> para cadastrar o que você vende."
        )

        return

    # Contador usado nas chaves dos campos: ao registrar uma venda ele
    # aumenta e todos os campos voltam em branco.
    n = st.session_state.get("loja_venda_n", 0)

    _titulo(
        "🛒", "Nova venda",
        "Preencha os dados — o resumo ao lado atualiza na hora"
    )

    col_form, col_resumo = st.columns([3, 2])

    mapa = _mapa_produtos(produtos)

    with col_form:

        pid = st.selectbox(
            "🏷️ Produto",
            list(mapa.keys()),
            format_func=lambda i: mapa[i],
            key=f"loja_v_produto_{n}"
        )

        produto = next(p for p in produtos if p["id"] == pid)

        estoque = produto["estoque"]

        if estoque <= 0:
            st.error(
                "Este produto está sem estoque. Registre uma entrada na "
                "aba **📥 Entrada de estoque**."
            )

        clientes = sorted(
            {v["cliente"] for v in vendas if v["cliente"]},
            key=str.lower
        )

        OPCAO_NOVO = "➕ Novo cliente"

        col1, col2 = st.columns(2)

        with col1:

            escolha_cliente = st.selectbox(
                "👤 Cliente (para quem vendeu)",
                [OPCAO_NOVO] + clientes,
                key=f"loja_v_cliente_{n}"
            )

            if escolha_cliente == OPCAO_NOVO:
                cliente = st.text_input(
                    "✍️ Nome do cliente",
                    placeholder="Ex.: Maria Silva",
                    key=f"loja_v_cliente_novo_{n}"
                ).strip()
            else:
                cliente = escolha_cliente

        with col2:

            data_venda = st.date_input(
                "📅 Data da venda",
                value=hoje,
                format="DD/MM/YYYY",
                key=f"loja_v_data_{n}"
            )

        col3, col4, col5 = st.columns(3)

        with col3:

            quantidade = st.number_input(
                "📦 Quantidade",
                min_value=1,
                max_value=max(estoque, 1),
                value=1,
                step=1,
                key=f"loja_v_qtd_{n}_{pid}"
            )

        with col4:

            preco = st.number_input(
                "💰 Preço por unidade — R$",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                value=float(produto["preco_venda"]),
                key=f"loja_v_preco_{n}_{pid}"
            )

        with col5:

            forma = st.selectbox(
                "💳 Pagamento",
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
                "🗓️ Quando vai pagar?",
                value=hoje + timedelta(days=7),
                format="DD/MM/YYYY",
                key=f"loja_v_vencimento_{n}"
            )

        observacao = st.text_input(
            "📝 Observação (opcional)",
            placeholder="Ex.: entrega no sábado",
            key=f"loja_v_obs_{n}"
        )

    total = quantidade * preco
    lucro = quantidade * (preco - produto["custo"])
    margem = (lucro / total * 100) if total else 0.0
    estoque_depois = estoque - quantidade

    cor_lucro = COR_OK if lucro >= 0 else COR_VERM

    cor_estoque = (
        COR_VERM if estoque_depois <= 0
        else COR_AMBAR if produto["estoque_minimo"] and estoque_depois <= produto["estoque_minimo"]
        else COR_OK
    )

    texto_pagamento = (
        "✅ Pago" if pago
        else f"⏳ Vence em {_data_br(pd.Timestamp(data_pagamento))}"
    )

    with col_resumo:

        st.markdown(
            '<div class="lj-resumo">'
            '<div class="lj-resumo-topo">🧾 Resumo da venda</div>'
            f'<div class="lj-resumo-prod">{_e(produto["nome"])}</div>'
            f'<div class="lj-resumo-total">{_brl(total)}</div>'
            f'<div class="lj-resumo-linha"><span>Quantidade × preço</span>'
            f'<b>{int(quantidade)} × {_brl(preco)}</b></div>'
            f'<div class="lj-resumo-linha"><span>Lucro estimado</span>'
            f'<b style="color:{cor_lucro};">{_brl(lucro)} ({margem:.0f}%)</b></div>'
            f'<div class="lj-resumo-linha"><span>Estoque depois da venda</span>'
            f'<b style="color:{cor_estoque};">{estoque_depois}</b></div>'
            f'<div class="lj-resumo-linha"><span>Cliente</span>'
            f'<b>{_e(cliente) if cliente else "—"}</b></div>'
            f'<div class="lj-resumo-linha"><span>Pagamento</span>'
            f'<b>{_e(forma)} · {texto_pagamento}</b></div>'
            '</div>',
            unsafe_allow_html=True
        )

        if st.button(
            "🛒 Registrar venda",
            type="primary",
            width="stretch",
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

def _faixa_vencimento(vencimento, ts_hoje):

    if vencimento is None or pd.isna(vencimento):
        return "Sem data"

    dias = (ts_hoje - vencimento).days

    if dias > 30:
        return "Vencido há +30 dias"

    if dias >= 8:
        return "Vencido 8–30 dias"

    if dias >= 1:
        return "Vencido 1–7 dias"

    if dias == 0:
        return "Vence hoje"

    if dias >= -7:
        return "Vence em até 7 dias"

    return "Vence depois"


FAIXAS_VENCIMENTO = {
    "Vencido há +30 dias": "#b91c1c",
    "Vencido 8–30 dias": COR_VERM,
    "Vencido 1–7 dias": "#fb923c",
    "Vence hoje": COR_AMBAR,
    "Vence em até 7 dias": COR_CIANO,
    "Vence depois": COR_OK,
    "Sem data": "#64748b",
}


def _aba_a_receber(armazem_id, vendas, hoje):

    df = _df_vendas(vendas)

    pendentes = df if df.empty else df[~df["pago"]]

    if pendentes.empty:

        _vazio(
            "🎉", "Nenhum pagamento pendente",
            "Tudo recebido! Quando alguém ficar de pagar depois, aparece aqui."
        )

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
        ("⏳", "Total a receber", _brl(_soma(pendentes, "total")), COR_AMBAR, f"{len(pendentes)} venda(s)"),
        ("🔴", "Vencido", _brl(_soma(vencidos, "total")), COR_VERM, f"{len(vencidos)} em atraso"),
        ("🗓️", "Vence em 7 dias", _brl(_soma(proximos, "total")), COR_CIANO, f"{len(proximos)} venda(s)"),
    ])

    por_faixa = {}

    for _, linha in pendentes.iterrows():

        faixa = _faixa_vencimento(linha["data_pagamento"], ts_hoje)

        por_faixa[faixa] = por_faixa.get(faixa, 0.0) + float(linha["total"])

    dados_faixas = pd.DataFrame([
        {"faixa": nome, "valor": por_faixa[nome]}
        for nome in FAIXAS_VENCIMENTO
        if por_faixa.get(nome, 0) > 0
    ])

    por_cliente = (
        pendentes.assign(cliente=pendentes["cliente"].replace("", "(sem nome)"))
        .groupby("cliente")["total"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )

    col_a, col_b = st.columns(2)

    with col_a:

        with st.container(border=True, key="loja-card-faixas"):

            _titulo("📅", "Situação dos vencimentos", "Quanto vence em cada prazo")

            _plot(lambda: _chart_barras_h(
                dados_faixas, "faixa", "valor", cores=FAIXAS_VENCIMENTO
            ))

    with col_b:

        with st.container(border=True, key="loja-card-deve"):

            _titulo("👥", "Quanto cada cliente deve", "Maiores valores em aberto")

            _plot(lambda: _chart_barras_h(
                por_cliente, "cliente", "total", cor=COR_AMBAR
            ))

    _titulo("💰", "Pagamentos pendentes", "Do vencimento mais antigo para o mais novo")

    for _, linha in pendentes.iterrows():

        status = _status_pagamento(False, linha["data_pagamento"], hoje)

        cor = _cor_status(status)

        col_card, col_btn = st.columns([6, 1.3], vertical_alignment="center")

        with col_card:

            st.markdown(
                f'<div class="lj-linha" style="--c:{cor};--cb:{cor}1f;">'
                f'<div class="lj-linha-esq"><div>'
                f'<div class="lj-linha-t">{_e(linha["cliente"] or "(sem nome)")}</div>'
                f'<div class="lj-linha-s">{_e(linha["produto_nome"])} · '
                f'{int(linha["quantidade"])} un. × {_brl(linha["preco_unitario"])} · '
                f'venda de {_data_br(linha["data_venda"])}</div>'
                f'</div></div>'
                f'<div class="lj-linha-dir">'
                f'<div class="lj-linha-v">{_brl(linha["total"])}</div>'
                f'<div class="lj-linha-s"><span class="lj-badge" style="--c:{cor};--cb:{cor}1f;">{status}</span>'
                f' vence {_data_br(linha["data_pagamento"])}</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

        with col_btn:

            if st.button(
                "✅ Recebi",
                key=f"loja_pago_{int(linha['id'])}",
                width="stretch"
            ):

                with estilos.mostrar_processando("registrando pagamento..."):
                    marcar_pago(int(linha["id"]), armazem_id, hoje)

                estilos.notificar_sucesso("pagamento registrado.")
                _recarregar()


# =====================================================
# ABA: VENDAS (histórico)
# =====================================================

def _aba_vendas(armazem_id, vendas, hoje):

    df = _df_vendas(vendas)

    if df.empty:

        _vazio(
            "📜", "Nenhuma venda registrada ainda",
            "As vendas feitas na aba <b>🛒 Nova venda</b> aparecem aqui."
        )

        return

    with st.container(border=True, key="loja-card-filtros"):

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            periodo = st.selectbox(
                "📅 Período",
                OPCOES_PERIODO,
                index=len(OPCOES_PERIODO) - 1,
                key="loja_vendas_periodo"
            )

        clientes = sorted({c for c in df["cliente"] if c}, key=str.lower)
        produtos_vendidos = sorted(set(df["produto_nome"]), key=str.lower)

        with col2:
            filtro_cliente = st.selectbox(
                "👤 Cliente", ["Todos"] + clientes, key="loja_vendas_cliente"
            )

        with col3:
            filtro_produto = st.selectbox(
                "🏷️ Produto", ["Todos"] + produtos_vendidos, key="loja_vendas_produto"
            )

        with col4:
            filtro_situacao = st.selectbox(
                "💳 Situação",
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

    total_filtrado = _soma(filtrado, "total")

    _kpis([
        ("🧾", "Vendas", str(len(filtrado)), COR_AZUL),
        ("💵", "Total vendido", _brl(total_filtrado), COR_LOJA),
        ("📈", "Lucro", _brl(_soma(filtrado, "lucro")), COR_OK),
        ("🎯", "Ticket médio", _brl(total_filtrado / len(filtrado)), COR_CIANO),
    ])

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
# ABA: LINGERIE (tela)
# =====================================================

def _html_progresso(total, percentual, comissao):

    escala = max(LINGERIE_LIMITE * 1.25, total * 1.1)

    pct_fill = min(total / escala * 100, 100) if escala else 0
    pct_marca = LINGERIE_LIMITE / escala * 100 if escala else 0

    acima = total > LINGERIE_LIMITE

    cor = COR_OK if acima else COR_AMBAR
    cor2 = "#16a34a" if acima else COR_LOJA

    if acima:
        mensagem = (
            f"🎉 Você passou de <b>{_brl(LINGERIE_LIMITE)}</b>! "
            f"Comissão de <b>{LINGERIE_PCT_ALTO}%</b> sobre o total."
        )
    else:
        mensagem = (
            f"Faltam <b>{_brl(LINGERIE_LIMITE - total)}</b> para chegar a "
            f"{_brl(LINGERIE_LIMITE)} — acima disso a comissão sobe para "
            f"<b>{LINGERIE_PCT_ALTO}%</b> sobre o total."
        )

    ativa_baixa = " ativa" if not acima else ""
    ativa_alta = " ativa" if acima else ""

    return (
        f'<div class="lj-prog" style="--c:{cor};--c2:{cor2};--cb:{cor}1f;">'
        f'<div class="lj-prog-topo">'
        f'<div><div class="lj-prog-titulo">Total da rodada</div>'
        f'<div class="lj-prog-valor">{_brl(total)}</div></div>'
        f'<div style="text-align:right;"><div class="lj-prog-titulo">Sua comissão ({percentual}%)</div>'
        f'<div class="lj-prog-valor">{_brl(comissao)}</div></div>'
        f'</div>'
        f'<div class="lj-prog-pista">'
        f'<div class="lj-prog-fill" style="width:{pct_fill:.1f}%"></div>'
        f'<div class="lj-prog-marca" style="left:{pct_marca:.1f}%"><span>{_brl(LINGERIE_LIMITE)}</span></div>'
        f'</div>'
        f'<div class="lj-prog-msg">{mensagem}</div>'
        f'<div class="lj-faixas">'
        f'<div class="lj-faixa{ativa_baixa}" style="--c:{COR_AMBAR};--cb:{COR_AMBAR}1f;">'
        f'<b>{LINGERIE_PCT_BAIXO}%</b><br>até {_brl(LINGERIE_LIMITE)}</div>'
        f'<div class="lj-faixa{ativa_alta}" style="--c:{COR_OK};--cb:{COR_OK}1f;">'
        f'<b>{LINGERIE_PCT_ALTO}%</b><br>acima de {_brl(LINGERIE_LIMITE)}</div>'
        f'</div></div>'
    )


def _aba_lingerie(armazem_id, usuario, hoje):

    pecas = ler_lingerie_abertas(armazem_id)

    total = round(sum(p["preco"] for p in pecas), 2)

    percentual, comissao, repasse = _calcular_comissao(total)

    _titulo(
        "👙", "Venda de lingerie",
        "Lance cada peça vendida — o total e a comissão atualizam sozinhos"
    )

    col_form, col_prog = st.columns([3, 2])

    with col_form:

        with st.form("loja_form_lingerie", clear_on_submit=True):

            descricao = st.text_input(
                "👙 Peça vendida",
                placeholder="Ex.: Conjunto de renda preto, tam. M"
            )

            preco = st.number_input(
                "💰 Preço vendido — R$",
                min_value=0.0,
                step=1.0,
                format="%.2f"
            )

            adicionar = st.form_submit_button(
                "➕ Adicionar peça", type="primary", width="stretch"
            )

        if adicionar:

            descricao_limpa = (descricao or "").strip()

            if not descricao_limpa:

                st.error("Informe qual peça foi vendida.")

            elif preco <= 0:

                st.error("Informe o preço da venda (maior que zero).")

            else:

                with estilos.mostrar_processando("adicionando peça..."):
                    adicionar_peca_lingerie(
                        armazem_id, descricao_limpa, preco, usuario
                    )

                _recarregar()

    with col_prog:

        st.markdown(
            _html_progresso(total, percentual, comissao),
            unsafe_allow_html=True
        )

    _kpis([
        ("🧾", "Peças na lista", str(len(pecas)), COR_AZUL),
        ("💵", "Total vendido", _brl(total), COR_LOJA),
        ("💖", f"Sua comissão ({percentual}%)", _brl(comissao), COR_OK),
        ("🏭", "Repassar ao fornecedor", _brl(repasse), COR_AMBAR),
    ])

    if pecas:

        _titulo("🛍️", "Peças desta rodada", "Remova com a lixeira se lançar algo errado")

        for numero, peca in enumerate(pecas, start=1):

            col_card, col_x = st.columns([8, 1], vertical_alignment="center")

            with col_card:

                st.markdown(
                    f'<div class="lj-linha" style="--c:{COR_LOJA};">'
                    f'<div class="lj-linha-esq"><div class="lj-num">{numero}</div>'
                    f'<div class="lj-linha-t">{_e(peca["descricao"])}</div></div>'
                    f'<div class="lj-linha-dir"><div class="lj-linha-v">{_brl(peca["preco"])}</div></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            with col_x:

                if st.button(
                    "🗑️", key=f"loja_ling_del_{peca['id']}",
                    help="Remover esta peça", width="stretch"
                ):

                    with estilos.mostrar_processando("removendo peça..."):
                        excluir_peca_lingerie(peca["id"], armazem_id)

                    _recarregar()

        with st.container(border=True, key="loja-card-fechar"):

            _titulo(
                "✅", "Fechar acerto",
                "Guarda o total, a comissão e o valor do fornecedor no "
                "histórico e começa uma lista nova"
            )

            col_f, col_d2 = st.columns([2, 1])

            with col_f:
                fornecedor = st.text_input(
                    "🏭 Fornecedor (opcional)",
                    placeholder="Nome do fornecedor",
                    key="loja_ling_fornecedor"
                )

            with col_d2:
                data_acerto = st.date_input(
                    "📅 Data do acerto",
                    value=hoje,
                    format="DD/MM/YYYY",
                    key="loja_ling_data"
                )

            if st.button(
                "✅ Fechar acerto",
                type="primary",
                width="stretch",
                key="loja_ling_fechar"
            ):

                try:

                    with estilos.mostrar_processando("fechando acerto..."):
                        fechar_acerto_lingerie(
                            armazem_id, (fornecedor or "").strip(),
                            data_acerto, usuario
                        )

                    estilos.notificar_sucesso("acerto fechado e guardado no histórico.")
                    _recarregar()

                except ValueError as erro:

                    st.error(str(erro))

    else:

        _vazio(
            "👙", "Nenhuma peça lançada ainda",
            "Preencha a peça e o preço acima e clique em <b>Adicionar peça</b>."
        )

    # ---------------- histórico ----------------

    acertos = ler_lingerie_acertos(armazem_id)

    if not acertos:
        return

    comissao_total = sum(a["comissao"] for a in acertos)
    vendido_total = sum(a["total"] for a in acertos)
    repasse_total = sum(a["repasse"] for a in acertos)

    _titulo("📜", "Acertos anteriores", "Histórico das rodadas já fechadas")

    _kpis([
        ("📚", "Acertos fechados", str(len(acertos)), COR_AZUL),
        ("💵", "Total vendido", _brl(vendido_total), COR_LOJA),
        ("💖", "Comissão acumulada", _brl(comissao_total), COR_OK),
        ("🏭", "Repassado ao fornecedor", _brl(repasse_total), COR_AMBAR),
    ])

    recentes = list(reversed(acertos[:12]))

    dados_acertos = pd.DataFrame({
        "rot": [a["data_acerto"].strftime("%d/%m") for a in recentes],
        "total": [a["total"] for a in recentes],
        "comissao": [a["comissao"] for a in recentes],
        "percentual": [a["percentual"] for a in recentes],
    })

    # Se dois acertos caírem no mesmo dia, o rótulo ganha um número
    # para não juntar as colunas no gráfico.
    vistos = {}

    rotulos_unicos = []

    for rot in dados_acertos["rot"]:

        vistos[rot] = vistos.get(rot, 0) + 1

        rotulos_unicos.append(rot if vistos[rot] == 1 else f"{rot} ({vistos[rot]})")

    dados_acertos["rot"] = rotulos_unicos

    with st.container(border=True, key="loja-card-acertos"):

        _titulo(
            "📊", "Evolução dos acertos",
            "Barras: total vendido · Linha verde: sua comissão"
        )

        _plot(lambda: _chart_acertos(dados_acertos))

    st.dataframe(
        pd.DataFrame([
            {
                "Data": _data_br(pd.Timestamp(a["data_acerto"])),
                "Fornecedor": a["fornecedor"] or "—",
                "Peças": a["qtd"],
                "Total vendido": _brl(a["total"]),
                "Comissão": f'{a["percentual"]}%',
                "Valor da comissão": _brl(a["comissao"]),
                "Repassar ao fornecedor": _brl(a["repasse"]),
            }
            for a in acertos
        ]),
        width="stretch",
        hide_index=True
    )

    with st.expander("🔍 Ver peças de um acerto ou desfazê-lo"):

        mapa = {
            a["id"]: (
                f'{_data_br(pd.Timestamp(a["data_acerto"]))} · '
                f'{a["fornecedor"] or "sem fornecedor"} · {_brl(a["total"])}'
            )
            for a in acertos
        }

        aid = st.selectbox(
            "Acerto",
            list(mapa.keys()),
            format_func=lambda i: mapa[i],
            key="loja_ling_ver_acerto"
        )

        pecas_fechadas = [
            p for p in ler_lingerie_pecas_fechadas(armazem_id)
            if p["acerto_id"] == aid
        ]

        if pecas_fechadas:

            st.dataframe(
                pd.DataFrame([
                    {"Peça": p["descricao"], "Preço": _brl(p["preco"])}
                    for p in pecas_fechadas
                ]),
                width="stretch",
                hide_index=True
            )

        st.caption(
            "Ao desfazer, as peças voltam para a lista da rodada atual."
        )

        confirma = st.checkbox(
            "Confirmo que quero desfazer este acerto",
            key=f"loja_ling_conf_desfazer_{aid}"
        )

        if st.button(
            "↩️ Desfazer acerto",
            disabled=not confirma,
            key=f"loja_ling_btn_desfazer_{aid}"
        ):

            with estilos.mostrar_processando("desfazendo acerto..."):
                desfazer_acerto_lingerie(aid, armazem_id)

            estilos.notificar_sucesso("acerto desfeito.")
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
    _garantir_schema_lingerie()

    armazem_id = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    # Tudo da Loja fica dentro deste container: o CSS acima só vale aqui.
    with st.container(key="loja-raiz"):

        _injetar_css()

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

        (
            aba_painel, aba_produtos, aba_entrada, aba_venda,
            aba_receber, aba_historico, aba_lingerie
        ) = st.tabs([
            "📊 Painel",
            "🏷️ Produtos",
            "📥 Entrada de estoque",
            "🛒 Nova venda",
            "💰 A receber",
            "📜 Vendas",
            "👙 Lingerie",
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

        with aba_lingerie:
            _aba_lingerie(armazem_id, usuario, hoje)

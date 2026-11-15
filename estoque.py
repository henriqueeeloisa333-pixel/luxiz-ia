import html

import pandas as pd
import streamlit as st

import banco
import estilos


# ==================================================
# COMO ESTE MÓDULO FUNCIONA
# ==================================================
# O estoque tem LOCAIS: um 🫁 Pulmão (depósito principal) e vários
# 🗄️ Armários (Logística, Administrativo, Fracionado, Limpeza...).
#
#   📥 Entrada        -> mercadoria nova chega (normalmente no Pulmão)
#   🔁 Transferência  -> sai de um local e vai para outro (Pulmão -> Armário)
#   📤 Retirada       -> sai do local para uso/consumo (baixa definitiva)
#
# O saldo NÃO é guardado em lugar nenhum: é sempre calculado a partir
# dos movimentos. Assim nunca fica "descalibrado" e todo movimento
# deixa rastro de quem fez.

LOCAL_PULMAO = "pulmao"
LOCAL_ARMARIO = "armario"

ARMARIOS_PADRAO = ["Logística", "Administrativo", "Fracionado", "Limpeza"]

UNIDADES = ["un", "cx", "pç", "pct", "par", "kg", "L", "m", "rolo"]

COR_OK = "#22c55e"
COR_BAIXO = "#f59e0b"
COR_FALTA = "#ef4444"
COR_NEUTRA = "#64748b"


# ==================================================
# TABELAS (criadas/migradas sozinhas na primeira vez)
# ==================================================

def _semear_locais(cursor, armazem_id):
    """Cria o Pulmão e os armários padrão se o armazém ainda não tem nenhum local."""

    cursor.execute(
        "SELECT COUNT(*) FROM estoque_locais WHERE armazem_id = %s",
        (armazem_id,)
    )

    if cursor.fetchone()[0] > 0:
        return

    cursor.execute("""
    INSERT INTO estoque_locais (armazem_id, nome, tipo)
    VALUES (%s, 'Pulmão', 'pulmao')
    ON CONFLICT DO NOTHING
    """, (armazem_id,))

    for nome in ARMARIOS_PADRAO:

        cursor.execute("""
        INSERT INTO estoque_locais (armazem_id, nome, tipo)
        VALUES (%s, %s, 'armario')
        ON CONFLICT DO NOTHING
        """, (armazem_id, nome))


@st.cache_resource(show_spinner=False)
def _garantir_tabelas_estoque():

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque_locais (
            id BIGSERIAL PRIMARY KEY,
            armazem_id BIGINT NOT NULL REFERENCES armazens(id),
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'armario'
                CHECK (tipo IN ('pulmao', 'armario')),
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (armazem_id, nome)
        )
        """)

        # só pode existir UM pulmão por armazém
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_estoque_locais_pulmao
        ON estoque_locais (armazem_id) WHERE tipo = 'pulmao'
        """)

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
            tipo TEXT NOT NULL,
            quantidade NUMERIC(12,2) NOT NULL CHECK (quantidade > 0),
            responsavel TEXT NOT NULL,
            registrado_por TEXT,
            observacao TEXT,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # ---- migração do modelo antigo (sem locais) ----

        cursor.execute("ALTER TABLE estoque_movimentos ADD COLUMN IF NOT EXISTS local_id BIGINT REFERENCES estoque_locais(id)")
        cursor.execute("ALTER TABLE estoque_movimentos ADD COLUMN IF NOT EXISTS local_destino_id BIGINT REFERENCES estoque_locais(id)")

        # o tipo agora aceita também 'transferencia'
        cursor.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'estoque_movimentos_tipo_check') THEN
                ALTER TABLE estoque_movimentos DROP CONSTRAINT estoque_movimentos_tipo_check;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'estoque_mov_tipo_ck') THEN
                ALTER TABLE estoque_movimentos
                ADD CONSTRAINT estoque_mov_tipo_ck
                CHECK (tipo IN ('entrada', 'retirada', 'transferencia'));
            END IF;
        END $$;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque_minimos (
            produto_id BIGINT NOT NULL REFERENCES estoque_produtos(id) ON DELETE CASCADE,
            local_id BIGINT NOT NULL REFERENCES estoque_locais(id),
            minimo NUMERIC(12,2) NOT NULL DEFAULT 0,
            PRIMARY KEY (produto_id, local_id)
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_produtos_armazem ON estoque_produtos (armazem_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_mov_armazem ON estoque_movimentos (armazem_id, data_hora DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_mov_produto ON estoque_movimentos (produto_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estoque_mov_local ON estoque_movimentos (local_id)")

        # Pulmão + armários padrão em todo armazém que ainda não tem locais
        cursor.execute("SELECT id FROM armazens")

        for (id_armazem,) in cursor.fetchall():
            _semear_locais(cursor, id_armazem)

        # Tudo o que já estava registrado no modelo antigo passa a
        # valer para o Pulmão (depois você transfere/une para os armários)
        cursor.execute("""
        UPDATE estoque_movimentos m
        SET local_id = l.id
        FROM estoque_locais l
        WHERE m.local_id IS NULL
          AND l.armazem_id = m.armazem_id
          AND l.tipo = 'pulmao'
        """)

        # O "estoque mínimo" antigo (um por produto) vira o mínimo do Pulmão
        cursor.execute("""
        INSERT INTO estoque_minimos (produto_id, local_id, minimo)
        SELECT p.id, l.id, p.estoque_minimo
        FROM estoque_produtos p
        JOIN estoque_locais l
          ON l.armazem_id = p.armazem_id AND l.tipo = 'pulmao'
        WHERE p.estoque_minimo > 0
        ON CONFLICT (produto_id, local_id) DO NOTHING
        """)

        cursor.execute("UPDATE estoque_produtos SET estoque_minimo = 0 WHERE estoque_minimo > 0")

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    return True


# ==================================================
# BANCO — LEITURA
# ==================================================

def _hora_local(coluna="data_hora"):

    return f"({coluna} AT TIME ZONE 'UTC' AT TIME ZONE 'America/Campo_Grande')"


@st.cache_data(ttl=30, show_spinner=False)
def ler_locais(armazem_id):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        _semear_locais(cursor, armazem_id)
        conn.commit()

        cursor.execute("""
        SELECT id, nome, tipo
        FROM estoque_locais
        WHERE armazem_id = %s AND ativo
        ORDER BY (tipo = 'pulmao') DESC, nome ASC
        """, (armazem_id,))

        locais = [
            {"id": row[0], "nome": row[1], "tipo": row[2]}
            for row in cursor.fetchall()
        ]

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    return locais


@st.cache_data(ttl=30, show_spinner=False)
def ler_produtos(armazem_id):
    """
    Cada produto traz o saldo, o mínimo e os últimos movimentos
    SEPARADOS POR LOCAL (dicionários indexados pelo id do local).
    """

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, nome, unidade
        FROM estoque_produtos
        WHERE armazem_id = %s
        ORDER BY nome ASC
        """, (armazem_id,))

        produtos = {
            row[0]: {
                "id": row[0],
                "nome": row[1],
                "unidade": row[2],
                "saldos": {},
                "minimos": {},
                "ult_reposicao": {},
                "ult_retirada": {},
            }
            for row in cursor.fetchall()
        }

        # saldo por produto e local: entradas + transferências recebidas
        # - transferências enviadas - retiradas
        cursor.execute("""
        SELECT produto_id, loc, SUM(qtd)
        FROM (
            SELECT produto_id, local_id AS loc,
                CASE tipo WHEN 'entrada' THEN quantidade ELSE -quantidade END AS qtd
            FROM estoque_movimentos
            WHERE armazem_id = %s
            UNION ALL
            SELECT produto_id, local_destino_id AS loc, quantidade AS qtd
            FROM estoque_movimentos
            WHERE armazem_id = %s AND tipo = 'transferencia'
        ) t
        WHERE loc IS NOT NULL
        GROUP BY produto_id, loc
        """, (armazem_id, armazem_id))

        for produto_id, loc, saldo in cursor.fetchall():

            if produto_id in produtos:
                produtos[produto_id]["saldos"][loc] = float(saldo)

        cursor.execute("""
        SELECT mi.produto_id, mi.local_id, mi.minimo
        FROM estoque_minimos mi
        JOIN estoque_produtos p ON p.id = mi.produto_id
        WHERE p.armazem_id = %s
        """, (armazem_id,))

        for produto_id, loc, minimo in cursor.fetchall():

            if produto_id in produtos:
                produtos[produto_id]["minimos"][loc] = float(minimo)

        # última reposição (entrada ou transferência recebida) por local
        cursor.execute(f"""
        SELECT DISTINCT ON (produto_id, loc)
            produto_id, loc, responsavel, quantidade, hora
        FROM (
            SELECT produto_id, local_id AS loc, responsavel, quantidade,
                id, data_hora, {_hora_local()} AS hora
            FROM estoque_movimentos
            WHERE armazem_id = %s AND tipo = 'entrada'
            UNION ALL
            SELECT produto_id, local_destino_id AS loc, responsavel, quantidade,
                id, data_hora, {_hora_local()} AS hora
            FROM estoque_movimentos
            WHERE armazem_id = %s AND tipo = 'transferencia'
        ) t
        WHERE loc IS NOT NULL
        ORDER BY produto_id, loc, data_hora DESC, id DESC
        """, (armazem_id, armazem_id))

        for produto_id, loc, responsavel, quantidade, hora in cursor.fetchall():

            if produto_id in produtos:
                produtos[produto_id]["ult_reposicao"][loc] = {
                    "responsavel": responsavel,
                    "quantidade": float(quantidade),
                    "data_hora": hora,
                }

        # última retirada (uso/consumo) por local
        cursor.execute(f"""
        SELECT DISTINCT ON (produto_id, local_id)
            produto_id, local_id, responsavel, quantidade, {_hora_local()}
        FROM estoque_movimentos
        WHERE armazem_id = %s AND tipo = 'retirada' AND local_id IS NOT NULL
        ORDER BY produto_id, local_id, data_hora DESC, id DESC
        """, (armazem_id,))

        for produto_id, loc, responsavel, quantidade, hora in cursor.fetchall():

            if produto_id in produtos:
                produtos[produto_id]["ult_retirada"][loc] = {
                    "responsavel": responsavel,
                    "quantidade": float(quantidade),
                    "data_hora": hora,
                }

    finally:
        banco.liberar(conn)

    return list(produtos.values())


@st.cache_data(ttl=30, show_spinner=False)
def ler_movimentos(armazem_id, limite=500):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute(f"""
        SELECT
            m.id, p.nome, p.unidade, m.tipo, m.quantidade,
            m.responsavel, m.registrado_por, m.observacao,
            {_hora_local('m.data_hora')},
            lo.nome, ld.nome
        FROM estoque_movimentos m
        JOIN estoque_produtos p ON p.id = m.produto_id
        LEFT JOIN estoque_locais lo ON lo.id = m.local_id
        LEFT JOIN estoque_locais ld ON ld.id = m.local_destino_id
        WHERE m.armazem_id = %s
        ORDER BY m.data_hora DESC, m.id DESC
        LIMIT %s
        """, (armazem_id, limite))

        colunas = [
            "id", "produto", "unidade", "tipo", "quantidade",
            "responsavel", "registrado_por", "observacao", "data_hora",
            "local", "local_destino"
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

    ler_locais.clear()
    ler_produtos.clear()
    ler_movimentos.clear()


# ==================================================
# BANCO — ESCRITA
# ==================================================

def criar_produto(nome, unidade, armazem_id, usuario):

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
        INSERT INTO estoque_produtos (armazem_id, nome, unidade, criado_por)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """, (armazem_id, nome, unidade, usuario))

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
    observacao, usuario, armazem_id,
    local_id, local_destino_id=None
):
    """
    Grava uma entrada, transferência ou retirada.

    - entrada:        soma no local_id
    - retirada:       tira do local_id (uso/consumo)
    - transferencia:  tira do local_id e soma no local_destino_id

    Retirada e transferência conferem o saldo do local de origem
    dentro da própria transação (com o produto travado), então duas
    pessoas movimentando ao mesmo tempo nunca deixam o saldo negativo.
    """

    if tipo not in ("entrada", "retirada", "transferencia"):
        return False, "Tipo de movimento inválido."

    if tipo == "transferencia" and (
        not local_destino_id or local_destino_id == local_id
    ):
        return False, "Escolha um destino diferente da origem."

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

        ids_locais = [local_id]

        if tipo == "transferencia":
            ids_locais.append(local_destino_id)

        cursor.execute("""
        SELECT id, nome
        FROM estoque_locais
        WHERE armazem_id = %s AND ativo AND id = ANY(%s)
        """, (armazem_id, ids_locais))

        nomes_locais = dict(cursor.fetchall())

        if len(nomes_locais) != len(set(ids_locais)):
            conn.rollback()
            return False, "Local não encontrado."

        if tipo in ("retirada", "transferencia"):

            cursor.execute("""
            SELECT COALESCE(SUM(
                CASE
                    WHEN local_id = %s AND tipo = 'entrada' THEN quantidade
                    WHEN local_id = %s AND tipo IN ('retirada', 'transferencia') THEN -quantidade
                    WHEN local_destino_id = %s AND tipo = 'transferencia' THEN quantidade
                    ELSE 0
                END
            ), 0)
            FROM estoque_movimentos
            WHERE produto_id = %s
            """, (local_id, local_id, local_id, produto_id))

            saldo = float(cursor.fetchone()[0])

            if quantidade > saldo + 1e-9:
                conn.rollback()
                return False, (
                    f"Estoque insuficiente em {nomes_locais[local_id]}: "
                    f"restam apenas {_fmt(saldo)} {produto[1]} de {produto[0]}."
                )

        cursor.execute("""
        INSERT INTO estoque_movimentos
            (armazem_id, produto_id, tipo, quantidade,
             responsavel, registrado_por, observacao,
             local_id, local_destino_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            armazem_id, produto_id, tipo, quantidade,
            responsavel, usuario, (observacao or "").strip() or None,
            local_id, local_destino_id if tipo == "transferencia" else None
        ))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()

    return True, "ok"


def atualizar_minimo(produto_id, local_id, minimo, armazem_id):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO estoque_minimos (produto_id, local_id, minimo)
        SELECT p.id, %s, %s
        FROM estoque_produtos p
        WHERE p.id = %s AND p.armazem_id = %s
        ON CONFLICT (produto_id, local_id)
        DO UPDATE SET minimo = EXCLUDED.minimo
        """, (local_id, minimo, produto_id, armazem_id))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()


def editar_produto(produto_id, nome, unidade, armazem_id):

    nome = (nome or "").strip()

    if not nome:
        return False, "Informe o nome do produto."

    duplicado = any(
        p["id"] != produto_id and p["nome"].strip().lower() == nome.lower()
        for p in ler_produtos(armazem_id)
    )

    if duplicado:
        return False, f"Já existe outro produto chamado \"{nome}\"."

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE estoque_produtos
        SET nome = %s, unidade = %s
        WHERE id = %s AND armazem_id = %s
        """, (nome, unidade, produto_id, armazem_id))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()

    return True, "ok"


def excluir_produto(produto_id, armazem_id):

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        # movimentos e mínimos do produto vão junto (ON DELETE CASCADE)
        cursor.execute("""
        DELETE FROM estoque_produtos
        WHERE id = %s AND armazem_id = %s
        """, (produto_id, armazem_id))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()


def unir_produtos(origem_id, destino_id, local_id, armazem_id):
    """
    Junta dois cadastros do mesmo produto (ex.: "Capa de Chuva (ARMÁRIO)"
    dentro de "Capa de Chuva"). Todo o histórico do produto de origem
    passa para o de destino e o cadastro de origem é apagado.

    Se local_id for informado, todo o histórico do produto de origem
    passa a valer para ESSE local (útil para os cadastros antigos que
    eram "do armário" mas estavam registrados no Pulmão).
    """

    if origem_id == destino_id:
        return False, "Escolha dois produtos diferentes."

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id FROM estoque_produtos
        WHERE id = ANY(%s) AND armazem_id = %s
        ORDER BY id
        FOR UPDATE
        """, ([origem_id, destino_id], armazem_id))

        if len(cursor.fetchall()) != 2:
            conn.rollback()
            return False, "Produto não encontrado."

        if local_id:

            cursor.execute("""
            SELECT 1 FROM estoque_locais
            WHERE id = %s AND armazem_id = %s AND ativo
            """, (local_id, armazem_id))

            if not cursor.fetchone():
                conn.rollback()
                return False, "Local não encontrado."

            cursor.execute("""
            SELECT 1 FROM estoque_movimentos
            WHERE produto_id = %s AND tipo = 'transferencia'
            LIMIT 1
            """, (origem_id,))

            if cursor.fetchone():
                conn.rollback()
                return False, (
                    "Esse produto já tem transferências — una sem "
                    "escolher um local, para preservar o histórico."
                )

            cursor.execute("""
            UPDATE estoque_movimentos
            SET produto_id = %s, local_id = %s
            WHERE produto_id = %s
            """, (destino_id, local_id, origem_id))

        else:

            cursor.execute("""
            UPDATE estoque_movimentos
            SET produto_id = %s
            WHERE produto_id = %s
            """, (destino_id, origem_id))

        cursor.execute(
            "DELETE FROM estoque_produtos WHERE id = %s AND armazem_id = %s",
            (origem_id, armazem_id)
        )

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()

    return True, "ok"


def criar_local(nome, armazem_id):

    nome = (nome or "").strip()

    if not nome:
        return False, "Informe o nome do armário."

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, ativo FROM estoque_locais
        WHERE armazem_id = %s AND LOWER(nome) = LOWER(%s)
        """, (armazem_id, nome))

        existente = cursor.fetchone()

        if existente:

            if existente[1]:
                conn.rollback()
                return False, f"Já existe um local chamado \"{nome}\"."

            # estava arquivado: reativa
            cursor.execute(
                "UPDATE estoque_locais SET ativo = TRUE WHERE id = %s",
                (existente[0],)
            )

        else:

            cursor.execute("""
            INSERT INTO estoque_locais (armazem_id, nome, tipo)
            VALUES (%s, %s, 'armario')
            """, (armazem_id, nome))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()

    return True, "ok"


def renomear_local(local_id, novo_nome, armazem_id):

    novo_nome = (novo_nome or "").strip()

    if not novo_nome:
        return False, "Informe o novo nome."

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT 1 FROM estoque_locais
        WHERE armazem_id = %s AND LOWER(nome) = LOWER(%s) AND id <> %s
        """, (armazem_id, novo_nome, local_id))

        if cursor.fetchone():
            conn.rollback()
            return False, f"Já existe um local chamado \"{novo_nome}\"."

        cursor.execute("""
        UPDATE estoque_locais
        SET nome = %s
        WHERE id = %s AND armazem_id = %s AND tipo = 'armario'
        """, (novo_nome, local_id, armazem_id))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()

    return True, "ok"


def arquivar_local(local_id, armazem_id):
    """Tira o armário da tela (o histórico é mantido). Só se estiver vazio."""

    for produto in ler_produtos(armazem_id):

        if abs(produto["saldos"].get(local_id, 0.0)) > 0.0001:
            return False, (
                f"Esse armário ainda tem {_fmt(produto['saldos'][local_id])} "
                f"{produto['unidade']} de {produto['nome']}. Transfira ou "
                "retire tudo antes de arquivar."
            )

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE estoque_locais
        SET ativo = FALSE
        WHERE id = %s AND armazem_id = %s AND tipo = 'armario'
        """, (local_id, armazem_id))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _limpar_caches()

    return True, "ok"


# ==================================================
# APOIO
# ==================================================

def _fmt(valor):

    valor = float(valor)

    if valor.is_integer():
        return f"{int(valor):,}".replace(",", ".")

    return f"{valor:.2f}".replace(".", ",")


def _status(saldo, minimo):
    """Devolve (nível, cor, rótulo). Nível: 0 ok, 1 baixo, 2 em falta."""

    if minimo > 0 and saldo <= 0:
        return 2, COR_FALTA, "Em falta"

    if minimo > 0 and saldo <= minimo:
        return 1, COR_BAIXO, "Estoque baixo"

    if saldo > 0:
        return 0, COR_OK, "Em estoque"

    return 0, COR_NEUTRA, "Zerado"


def _rotulo_local(local):

    if local["tipo"] == LOCAL_PULMAO:
        return "🫁 Pulmão"

    return f"🗄️ {local['nome']}"


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


def _cabecalho_card(nome, cor, status):

    return (
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:.5rem;">'
        f'<div style="font-weight:800;font-size:1rem;line-height:1.25;">'
        f'{html.escape(nome)}</div>'
        f'<span style="background:{cor}22;color:{cor};border:1px solid {cor}55;'
        'padding:.15rem .6rem;border-radius:999px;font-size:.68rem;'
        f'font-weight:800;white-space:nowrap;">{status}</span>'
        '</div>'
    )


def _card_local(produto, local, saldo_pulmao):
    """Card de um produto dentro de UM local (Pulmão ou armário)."""

    lid = local["id"]
    unidade = produto["unidade"]

    saldo = produto["saldos"].get(lid, 0.0)
    minimo = produto["minimos"].get(lid, 0.0)

    nivel, cor, status = _status(saldo, minimo)

    minimo_html = (
        f'<div style="font-size:.74rem;opacity:.65;margin-top:.1rem;">'
        f'Mínimo: {_fmt(minimo)} {html.escape(unidade)}</div>'
        if minimo > 0 else ""
    )

    aviso_html = ""

    if nivel >= 1:

        if local["tipo"] == LOCAL_ARMARIO:

            if saldo_pulmao > 0:
                texto = (
                    f"🫁 O Pulmão tem {_fmt(saldo_pulmao)} {html.escape(unidade)} "
                    "— faça a transferência para ressuprir"
                )
            else:
                texto = "🫁 O Pulmão também está zerado — hora de comprar"

        else:

            texto = "🛒 Pulmão baixo — hora de comprar"

        aviso_html = (
            f'<div style="margin-top:.55rem;font-size:.76rem;font-weight:700;'
            f'color:{cor};">{texto}</div>'
        )

    return (
        f'<div style="background:{cor}12;border:1px solid {cor}45;'
        'border-radius:1rem;padding:1rem 1.1rem;display:flex;'
        'flex-direction:column;gap:.1rem;">'
        f'{_cabecalho_card(produto["nome"], cor, status)}'
        '<div style="margin-top:.5rem;">'
        f'<span style="font-size:2.1rem;font-weight:800;color:{cor};'
        f'line-height:1;">{_fmt(saldo)}</span>'
        f'<span style="font-size:.9rem;opacity:.7;margin-left:.35rem;">'
        f'{html.escape(unidade)} em estoque</span>'
        '</div>'
        f'{minimo_html}'
        f'{aviso_html}'
        f'<div style="height:1px;background:{cor}30;margin:.7rem 0 .3rem 0;"></div>'
        f'{_linha_ultimo_movimento("📥", "Última reposição por", produto["ult_reposicao"].get(lid), unidade)}'
        f'{_linha_ultimo_movimento("📤", "Última retirada por", produto["ult_retirada"].get(lid), unidade)}'
        '</div>'
    )


def _card_geral(produto, locais):
    """Card de um produto na Visão geral: total + quanto tem em cada local."""

    unidade = produto["unidade"]

    total = sum(produto["saldos"].get(l["id"], 0.0) for l in locais)

    pior = 0

    chips = []

    for local in locais:

        saldo = produto["saldos"].get(local["id"], 0.0)
        minimo = produto["minimos"].get(local["id"], 0.0)

        nivel, cor_local, _ = _status(saldo, minimo)

        pior = max(pior, nivel)

        if saldo <= 0 and nivel == 0:
            continue

        chips.append(
            f'<span style="background:{cor_local}1f;color:{cor_local};'
            f'border:1px solid {cor_local}55;padding:.2rem .6rem;'
            'border-radius:999px;font-size:.74rem;font-weight:700;'
            f'white-space:nowrap;">{html.escape(_rotulo_local(local))}: '
            f'<b>{_fmt(saldo)}</b> {html.escape(unidade)}</span>'
        )

    if pior == 2:
        cor, status = COR_FALTA, "Em falta"
    elif pior == 1:
        cor, status = COR_BAIXO, "Estoque baixo"
    else:
        cor, status = COR_OK, "Em estoque"

    return (
        f'<div style="background:{cor}12;border:1px solid {cor}45;'
        'border-radius:1rem;padding:1rem 1.1rem;display:flex;'
        'flex-direction:column;gap:.1rem;">'
        f'{_cabecalho_card(produto["nome"], cor, status)}'
        '<div style="margin-top:.5rem;">'
        f'<span style="font-size:2.1rem;font-weight:800;color:{cor};'
        f'line-height:1;">{_fmt(total)}</span>'
        f'<span style="font-size:.9rem;opacity:.7;margin-left:.35rem;">'
        f'{html.escape(unidade)} no total</span>'
        '</div>'
        f'<div style="height:1px;background:{cor}30;margin:.7rem 0 .5rem 0;"></div>'
        '<div style="display:flex;flex-wrap:wrap;gap:.4rem;">'
        + "".join(chips) +
        '</div></div>'
    )


def _grade_cards(cards_html):

    st.markdown(
        '<div style="display:grid;'
        'grid-template-columns:repeat(auto-fill,minmax(270px,1fr));'
        'gap:1rem;">'
        + "".join(cards_html)
        + '</div>',
        unsafe_allow_html=True
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

    locais = ler_locais(armazem_id)
    produtos = ler_produtos(armazem_id)
    movimentos = ler_movimentos(armazem_id)

    pulmao = next((l for l in locais if l["tipo"] == LOCAL_PULMAO), None)
    armarios = [l for l in locais if l["tipo"] == LOCAL_ARMARIO]

    if pulmao is None:
        st.error("Não foi possível carregar o Pulmão deste armazém.")
        return

    mapa_locais = {l["id"]: l for l in locais}
    mapa_produtos = {p["id"]: p for p in produtos}
    ids_locais = list(mapa_locais.keys())

    def saldo(produto, local_id):
        return produto["saldos"].get(local_id, 0.0)

    def total(produto):
        return sum(saldo(produto, lid) for lid in ids_locais)

    def nivel_pior(produto):
        return max(
            (
                _status(
                    saldo(produto, lid),
                    produto["minimos"].get(lid, 0.0)
                )[0]
                for lid in ids_locais
            ),
            default=0
        )

    # alertas: (nível, produto, local) onde o mínimo foi atingido
    alertas = []

    for p in produtos:

        for l in locais:

            nivel, _, _ = _status(saldo(p, l["id"]), p["minimos"].get(l["id"], 0.0))

            if nivel >= 1:
                alertas.append((nivel, p, l))

    alertas.sort(key=lambda a: (-a[0], a[1]["nome"].lower()))

    st.subheader("📦 Controle de Estoque")

    st.caption(
        "A mercadoria entra no 🫁 Pulmão, é transferida para os 🗄️ armários "
        "e sai dos armários para uso e consumo — o saldo de cada local é "
        "calculado automaticamente."
    )

    # ---------- KPIs ----------

    hoje = estilos.agora_local().date()

    def contar_hoje(tipo_mov):
        return sum(
            1 for m in movimentos
            if m["tipo"] == tipo_mov and m["data_hora"].date() == hoje
        )

    kpis = [
        _kpi("📦", "Produtos em estoque", str(sum(1 for p in produtos if total(p) > 0)), "#3b82f6"),
        _kpi("⚠️", "Alertas de reposição", str(len(alertas)), COR_BAIXO if alertas else COR_OK),
        _kpi("📥", "Entradas hoje", str(contar_hoje("entrada")), COR_OK),
        _kpi("🔁", "Transferências hoje", str(contar_hoje("transferencia")), "#0ea5e9"),
        _kpi("📤", "Retiradas hoje", str(contar_hoje("retirada")), "#a855f7"),
    ]

    for coluna, kpi_html in zip(st.columns(5), kpis):

        with coluna:
            st.markdown(kpi_html, unsafe_allow_html=True)

    st.write("")

    aba_estoque, aba_entrada, aba_transferir, aba_retirada, aba_historico = st.tabs([
        "📦 Estoque",
        "📥 Entrada",
        "🔁 Transferir / Ressuprir",
        "📤 Retirar para uso",
        "🕒 Histórico",
    ])

    # ==================================================
    # ESTOQUE (visão geral e por local)
    # ==================================================

    with aba_estoque:

        col_visao, col_busca = st.columns([3, 2])

        with col_visao:
            visao = st.radio(
                "Ver",
                ["geral"] + ids_locais,
                format_func=lambda v: (
                    "📊 Visão geral" if v == "geral" else _rotulo_local(mapa_locais[v])
                ),
                horizontal=True,
                key="estoque_visao_local"
            )

        with col_busca:
            busca = st.text_input(
                "🔍 Buscar produto",
                key="estoque_busca",
                placeholder="Digite o nome..."
            ).strip().lower()

        produtos_busca = [p for p in produtos if busca in p["nome"].lower()]

        if not produtos:

            st.info(
                "Nenhum produto cadastrado ainda. Use a aba "
                "**📥 Entrada** para cadastrar o primeiro."
            )

        elif visao == "geral" or visao not in mapa_locais:

            if alertas:

                with st.expander(f"⚠️ Precisam de reposição ({len(alertas)})", expanded=True):

                    for nivel, p, l in alertas[:15]:

                        icone = "🔴" if nivel == 2 else "🟡"

                        linha = (
                            f"{icone} **{p['nome']}** — {_rotulo_local(l)}: "
                            f"{_fmt(saldo(p, l['id']))} {p['unidade']} "
                            f"(mín. {_fmt(p['minimos'].get(l['id'], 0))})"
                        )

                        if l["tipo"] == LOCAL_ARMARIO:

                            no_pulmao = saldo(p, pulmao["id"])

                            linha += (
                                f" · 🫁 Pulmão tem {_fmt(no_pulmao)}"
                                if no_pulmao > 0
                                else " · 🛒 Pulmão zerado, comprar"
                            )

                        st.markdown(linha)

            com_estoque = [
                p for p in produtos_busca
                if total(p) > 0 or nivel_pior(p) >= 1
            ]

            com_estoque.sort(key=lambda p: (-nivel_pior(p), p["nome"].lower()))

            if com_estoque:
                _grade_cards(_card_geral(p, locais) for p in com_estoque)
            else:
                st.info("Nenhum produto com estoque encontrado.")

            sem_estoque = [
                p for p in produtos_busca
                if total(p) <= 0 and nivel_pior(p) == 0
            ]

            if sem_estoque:

                with st.expander(f"💤 Sem estoque em lugar nenhum ({len(sem_estoque)})"):

                    for p in sem_estoque:
                        st.markdown(f"• {p['nome']}")

                    st.caption(
                        "Esses produtos ficam escondidos para não poluir a tela. "
                        "Quando uma nova entrada for registrada, voltam sozinhos."
                    )

        else:

            local_ativo = mapa_locais[visao]

            itens = []

            for p in produtos_busca:

                s = saldo(p, local_ativo["id"])
                nivel, _, _ = _status(s, p["minimos"].get(local_ativo["id"], 0.0))

                if s > 0 or nivel >= 1:
                    itens.append((nivel, p))

            itens.sort(key=lambda i: (-i[0], i[1]["nome"].lower()))

            if itens:

                _grade_cards(
                    _card_local(p, local_ativo, saldo(p, pulmao["id"]))
                    for _, p in itens
                )

            else:

                st.info(
                    f"Nenhum item em estoque em {_rotulo_local(local_ativo)}. "
                    "Use a aba **🔁 Transferir / Ressuprir** para abastecer."
                    if local_ativo["tipo"] == LOCAL_ARMARIO
                    else "Nenhum item em estoque no Pulmão. Use a aba "
                         "**📥 Entrada** para registrar mercadoria."
                )

            acabaram = [
                p for p in produtos_busca
                if saldo(p, local_ativo["id"]) <= 0
                and _status(saldo(p, local_ativo["id"]), p["minimos"].get(local_ativo["id"], 0.0))[0] == 0
                and (
                    local_ativo["id"] in p["ult_reposicao"]
                    or local_ativo["id"] in p["ult_retirada"]
                )
            ]

            if acabaram:

                with st.expander(f"💤 Acabaram aqui ({len(acabaram)})"):

                    for p in acabaram:

                        ult = p["ult_retirada"].get(local_ativo["id"])

                        detalhe = (
                            f" — última retirada por {ult['responsavel']} "
                            f"em {ult['data_hora'].strftime('%d/%m')}"
                            if ult else ""
                        )

                        st.markdown(f"• {p['nome']}{detalhe}")

        # ---------- GERENCIAR ----------

        if pode_gerir and produtos:

            st.write("")

            with st.expander("⚙️ Gerenciar estoque"):

                tab_min, tab_prod, tab_loc = st.tabs([
                    "🎯 Estoque mínimo", "📝 Produtos", "🗄️ Locais"
                ])

                # ---- mínimo por local ----

                with tab_min:

                    st.caption(
                        "Defina o mínimo por local. Quando o saldo chega nele, "
                        "o card fica amarelo (baixo) ou vermelho (em falta) e "
                        "aparece em \"Precisam de reposição\". Mínimo 0 = sem alerta."
                    )

                    col_a, col_b = st.columns(2)

                    with col_a:
                        pid_min = st.selectbox(
                            "Produto",
                            [p["id"] for p in produtos],
                            format_func=lambda pid: mapa_produtos[pid]["nome"],
                            key="estoque_min_produto"
                        )

                    with col_b:
                        lid_min = st.selectbox(
                            "Local",
                            ids_locais,
                            format_func=lambda lid: _rotulo_local(mapa_locais[lid]),
                            key="estoque_min_local"
                        )

                    produto_min = mapa_produtos[pid_min]

                    novo_minimo = st.number_input(
                        f"Estoque mínimo ({produto_min['unidade']})",
                        min_value=0.0,
                        value=float(produto_min["minimos"].get(lid_min, 0.0)),
                        step=1.0,
                        format="%g",
                        key=f"estoque_min_valor_{pid_min}_{lid_min}"
                    )

                    if st.button("💾 Salvar mínimo", key="estoque_salvar_minimo"):

                        with estilos.mostrar_processando("salvando..."):
                            atualizar_minimo(pid_min, lid_min, novo_minimo, armazem_id)

                        estilos.notificar_sucesso("estoque mínimo atualizado.")
                        st.rerun()

                # ---- produtos ----

                with tab_prod:

                    st.markdown("**Editar nome / unidade**")

                    pid_ed = st.selectbox(
                        "Produto",
                        [p["id"] for p in produtos],
                        format_func=lambda pid: mapa_produtos[pid]["nome"],
                        key="estoque_ed_produto"
                    )

                    produto_ed = mapa_produtos[pid_ed]

                    with st.form(f"form_estoque_editar_{pid_ed}"):

                        nome_ed = st.text_input("Nome", value=produto_ed["nome"])

                        unidade_ed = st.selectbox(
                            "Unidade",
                            UNIDADES if produto_ed["unidade"] in UNIDADES
                            else UNIDADES + [produto_ed["unidade"]],
                            index=(
                                UNIDADES.index(produto_ed["unidade"])
                                if produto_ed["unidade"] in UNIDADES
                                else len(UNIDADES)
                            )
                        )

                        enviou_ed = st.form_submit_button("💾 Salvar alterações")

                    if enviou_ed:

                        ok, msg = editar_produto(pid_ed, nome_ed, unidade_ed, armazem_id)

                        if ok:
                            estilos.notificar_sucesso("produto atualizado.")
                            st.rerun()
                        else:
                            st.error(msg)

                    st.divider()

                    st.markdown("**Unir cadastros duplicados**")

                    st.caption(
                        "Ex.: unir \"Capa de Chuva (ARMÁRIO)\" em \"Capa de Chuva\". "
                        "Todo o histórico do cadastro de origem passa para o de "
                        "destino e a origem é apagada. Se quiser, escolha o local "
                        "onde esse saldo está de verdade (ex.: um armário)."
                    )

                    col_o, col_d = st.columns(2)

                    with col_o:
                        pid_origem = st.selectbox(
                            "Unir este (será apagado)",
                            [p["id"] for p in produtos],
                            format_func=lambda pid: mapa_produtos[pid]["nome"],
                            key="estoque_unir_origem"
                        )

                    with col_d:
                        pid_destino = st.selectbox(
                            "Neste (continua existindo)",
                            [p["id"] for p in produtos],
                            format_func=lambda pid: mapa_produtos[pid]["nome"],
                            key="estoque_unir_destino"
                        )

                    local_unir = st.selectbox(
                        "Esse saldo está em…",
                        [None] + ids_locais,
                        format_func=lambda lid: (
                            "Manter o local como está registrado"
                            if lid is None else _rotulo_local(mapa_locais[lid])
                        ),
                        key="estoque_unir_local"
                    )

                    if (
                        pid_origem != pid_destino
                        and mapa_produtos[pid_origem]["unidade"] != mapa_produtos[pid_destino]["unidade"]
                    ):
                        st.warning("As unidades dos dois produtos são diferentes — confira antes de unir.")

                    confirmar_unir = st.checkbox(
                        "Confirmo que quero unir os dois cadastros",
                        key="estoque_unir_confirmar"
                    )

                    if st.button("🔗 Unir produtos", key="estoque_unir_botao", disabled=not confirmar_unir):

                        with estilos.mostrar_processando("unindo produtos..."):
                            ok, msg = unir_produtos(pid_origem, pid_destino, local_unir, armazem_id)

                        if ok:
                            estilos.notificar_sucesso("produtos unidos.")
                            st.rerun()
                        else:
                            st.error(msg)

                    st.divider()

                    st.markdown("**Excluir produto**")

                    pid_exc = st.selectbox(
                        "Produto",
                        [p["id"] for p in produtos],
                        format_func=lambda pid: mapa_produtos[pid]["nome"],
                        key="estoque_exc_produto"
                    )

                    confirmar_exc = st.checkbox(
                        "Confirmo que quero excluir este produto e todo o seu histórico",
                        key="estoque_confirmar_exclusao"
                    )

                    if st.button(
                        "🗑️ Excluir produto",
                        key="estoque_excluir_produto",
                        disabled=not confirmar_exc
                    ):

                        with estilos.mostrar_processando("excluindo produto..."):
                            excluir_produto(pid_exc, armazem_id)

                        estilos.notificar_sucesso("produto excluído.")
                        st.rerun()

                # ---- locais ----

                with tab_loc:

                    st.caption(
                        "O 🫁 Pulmão é fixo. Os armários podem ser criados, "
                        "renomeados e arquivados (só quando estiverem vazios)."
                    )

                    with st.form("form_estoque_novo_local", clear_on_submit=True):

                        nome_novo_local = st.text_input(
                            "Novo armário",
                            placeholder="Ex.: Armário da Expedição"
                        )

                        enviou_local = st.form_submit_button("➕ Criar armário")

                    if enviou_local:

                        ok, msg = criar_local(nome_novo_local, armazem_id)

                        if ok:
                            estilos.notificar_sucesso("armário criado.")
                            st.rerun()
                        else:
                            st.error(msg)

                    if armarios:

                        st.divider()

                        lid_gerir = st.selectbox(
                            "Armário",
                            [l["id"] for l in armarios],
                            format_func=lambda lid: mapa_locais[lid]["nome"],
                            key="estoque_local_gerir"
                        )

                        with st.form(f"form_estoque_renomear_local_{lid_gerir}"):

                            nome_renomear = st.text_input(
                                "Novo nome",
                                value=mapa_locais[lid_gerir]["nome"]
                            )

                            enviou_renomear = st.form_submit_button("💾 Renomear")

                        if enviou_renomear:

                            ok, msg = renomear_local(lid_gerir, nome_renomear, armazem_id)

                            if ok:
                                estilos.notificar_sucesso("armário renomeado.")
                                st.rerun()
                            else:
                                st.error(msg)

                        if st.button("📁 Arquivar este armário", key="estoque_arquivar_local"):

                            ok, msg = arquivar_local(lid_gerir, armazem_id)

                            if ok:
                                estilos.notificar_sucesso("armário arquivado.")
                                st.rerun()
                            else:
                                st.error(msg)

    # ==================================================
    # ENTRADA
    # ==================================================

    with aba_entrada:

        st.markdown("##### 📥 Registrar entrada de mercadoria")

        st.caption(
            "Mercadoria nova que chegou. Normalmente entra no 🫁 Pulmão; "
            "para levar aos armários, use **🔁 Transferir / Ressuprir**."
        )

        local_entrada_id = st.selectbox(
            "Entrou em",
            ids_locais,
            format_func=lambda lid: _rotulo_local(mapa_locais[lid]),
            key="estoque_entrada_local"
        )

        produto_id_entrada = st.selectbox(
            "Produto",
            [None] + [p["id"] for p in produtos],
            format_func=lambda pid: (
                "➕ Cadastrar novo produto"
                if pid is None
                else (
                    f"{mapa_produtos[pid]['nome']}  —  "
                    f"{_fmt(saldo(mapa_produtos[pid], local_entrada_id))} "
                    f"{mapa_produtos[pid]['unidade']} neste local"
                )
            ),
            key="estoque_entrada_produto"
        )

        nome_novo = ""
        unidade_nova = "un"
        minimo_novo = 0.0

        with st.form("form_estoque_entrada", clear_on_submit=True):

            if produto_id_entrada is None:

                col_nome, col_un, col_min = st.columns([3, 1, 1])

                with col_nome:
                    nome_novo = st.text_input("Nome do novo produto")

                with col_un:
                    unidade_nova = st.selectbox("Unidade", UNIDADES)

                with col_min:
                    minimo_novo = st.number_input(
                        "Mínimo neste local",
                        min_value=0.0,
                        value=0.0,
                        step=1.0,
                        format="%g",
                        help="Opcional. Quando o saldo chegar nesse valor, aparece o alerta de reposição."
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
                            nome_novo, unidade_nova, armazem_id, usuario
                        )

                        if ok_produto:

                            produto_id_final = resultado

                            if minimo_novo > 0:
                                atualizar_minimo(
                                    produto_id_final, local_entrada_id,
                                    minimo_novo, armazem_id
                                )

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
                            armazem_id,
                            local_entrada_id
                        )

                        if not ok:
                            erro = erro_mov

                if erro:

                    st.error(erro)

                else:

                    estilos.notificar_sucesso("entrada registrada com sucesso.")
                    st.rerun()

    # ==================================================
    # TRANSFERIR / RESSUPRIR
    # ==================================================

    with aba_transferir:

        st.markdown("##### 🔁 Transferir / ressuprir")

        st.caption(
            "Move mercadoria de um local para outro — por exemplo, do 🫁 Pulmão "
            "para o armário que zerou. O total não muda, só o lugar."
        )

        sugestoes = [
            (p, l) for nivel, p, l in alertas
            if l["tipo"] == LOCAL_ARMARIO and saldo(p, pulmao["id"]) > 0
        ]

        if sugestoes:

            with st.expander(f"💡 Reposições sugeridas ({len(sugestoes)})", expanded=True):

                for p, l in sugestoes[:15]:

                    st.markdown(
                        f"• **{p['nome']}** → {_rotulo_local(l)}: tem "
                        f"{_fmt(saldo(p, l['id']))} {p['unidade']} "
                        f"(mín. {_fmt(p['minimos'].get(l['id'], 0))}) · "
                        f"🫁 Pulmão tem {_fmt(saldo(p, pulmao['id']))}"
                    )

        if len(locais) < 2:

            st.info("É preciso ter pelo menos dois locais para transferir.")

        else:

            col_origem, col_destino = st.columns(2)

            with col_origem:
                origem_id = st.selectbox(
                    "Sai de",
                    ids_locais,
                    format_func=lambda lid: _rotulo_local(mapa_locais[lid]),
                    key="estoque_transf_origem"
                )

            with col_destino:
                destinos_ids = [lid for lid in ids_locais if lid != origem_id]

                destino_id = st.selectbox(
                    "Vai para",
                    destinos_ids,
                    format_func=lambda lid: _rotulo_local(mapa_locais[lid]),
                    key=f"estoque_transf_destino_{origem_id}"
                )

            disponiveis = [p for p in produtos if saldo(p, origem_id) > 0]

            if not disponiveis:

                st.warning(
                    f"Não há nenhum produto em {_rotulo_local(mapa_locais[origem_id])} "
                    "para transferir."
                )

            else:

                produto_id_transf = st.selectbox(
                    "Produto",
                    [p["id"] for p in disponiveis],
                    format_func=lambda pid: (
                        f"{mapa_produtos[pid]['nome']}  —  "
                        f"origem: {_fmt(saldo(mapa_produtos[pid], origem_id))} · "
                        f"destino: {_fmt(saldo(mapa_produtos[pid], destino_id))} "
                        f"{mapa_produtos[pid]['unidade']}"
                    ),
                    key=f"estoque_transf_produto_{origem_id}_{destino_id}"
                )

                produto_transf = mapa_produtos[produto_id_transf]
                saldo_origem = saldo(produto_transf, origem_id)

                with st.form("form_estoque_transferencia", clear_on_submit=True):

                    col_qtd, col_resp = st.columns([1, 2])

                    with col_qtd:
                        quantidade_transf = st.number_input(
                            f"Quantidade ({produto_transf['unidade']})",
                            min_value=0.01,
                            max_value=float(saldo_origem),
                            value=min(1.0, float(saldo_origem)),
                            step=1.0,
                            format="%g"
                        )

                    with col_resp:
                        responsavel_transf = st.text_input(
                            "Quem transferiu",
                            value=nome_padrao
                        )

                    obs_transf = st.text_input(
                        "Observação (opcional)",
                        placeholder="Ex.: reposição semanal..."
                    )

                    enviou_transf = st.form_submit_button(
                        "🔁 Registrar transferência",
                        width='stretch'
                    )

                if enviou_transf:

                    if not responsavel_transf.strip():

                        st.error("Informe quem transferiu.")

                    else:

                        with estilos.mostrar_processando("registrando transferência..."):

                            ok, erro_mov = registrar_movimento(
                                produto_id_transf,
                                "transferencia",
                                quantidade_transf,
                                banco.normalizar_nome_pessoa(responsavel_transf, armazem_id),
                                obs_transf,
                                usuario,
                                armazem_id,
                                origem_id,
                                destino_id
                            )

                        if ok:

                            estilos.notificar_sucesso("transferência registrada com sucesso.")
                            st.rerun()

                        else:

                            st.error(erro_mov)

    # ==================================================
    # RETIRADA (USO E CONSUMO)
    # ==================================================

    with aba_retirada:

        st.markdown("##### 📤 Registrar retirada para uso / consumo")

        st.caption(
            "Baixa definitiva: o item saiu do armário para ser usado. "
            "Se o armário estiver sem o produto, ressupra antes pela aba "
            "**🔁 Transferir / Ressuprir**."
        )

        locais_retirada = armarios + [pulmao]

        local_retirada_id = st.selectbox(
            "Retirado de",
            [l["id"] for l in locais_retirada],
            format_func=lambda lid: _rotulo_local(mapa_locais[lid]),
            key="estoque_retirada_local"
        )

        com_saldo = [p for p in produtos if saldo(p, local_retirada_id) > 0]

        if not produtos:

            st.info("Nenhum produto cadastrado ainda.")

        elif not com_saldo:

            st.warning(
                f"{_rotulo_local(mapa_locais[local_retirada_id])} está sem estoque. "
                "Faça uma transferência para ressuprir."
            )

        else:

            produto_id_retirada = st.selectbox(
                "Produto",
                [p["id"] for p in com_saldo],
                format_func=lambda pid: (
                    f"{mapa_produtos[pid]['nome']}  —  "
                    f"{_fmt(saldo(mapa_produtos[pid], local_retirada_id))} "
                    f"{mapa_produtos[pid]['unidade']} disponíveis"
                ),
                key=f"estoque_retirada_produto_{local_retirada_id}"
            )

            produto_retirada = mapa_produtos[produto_id_retirada]
            saldo_retirada = saldo(produto_retirada, local_retirada_id)

            with st.form("form_estoque_retirada", clear_on_submit=True):

                col_qtd, col_resp = st.columns([1, 2])

                with col_qtd:
                    quantidade_retirada = st.number_input(
                        f"Quantidade ({produto_retirada['unidade']})",
                        min_value=0.01,
                        max_value=float(saldo_retirada),
                        value=min(1.0, float(saldo_retirada)),
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
                            armazem_id,
                            local_retirada_id
                        )

                    if ok:

                        estilos.notificar_sucesso("retirada registrada com sucesso.")
                        st.rerun()

                    else:

                        st.error(erro_mov)

    # ==================================================
    # HISTÓRICO
    # ==================================================

    with aba_historico:

        if not movimentos:

            st.info("Ainda não há movimentações registradas.")

        else:

            col_tipo, col_local, col_prod = st.columns([3, 2, 3])

            with col_tipo:
                filtro_tipo = st.radio(
                    "Tipo",
                    ["Todos", "📥 Entradas", "🔁 Transferências", "📤 Retiradas"],
                    horizontal=True,
                    key="estoque_hist_tipo"
                )

            with col_local:
                filtro_local = st.selectbox(
                    "Local",
                    ["Todos"] + [l["nome"] for l in locais],
                    key="estoque_hist_local"
                )

            with col_prod:
                filtro_produto = st.selectbox(
                    "Produto",
                    ["Todos"] + sorted({m["produto"] for m in movimentos}),
                    key="estoque_hist_produto"
                )

            tipo_por_filtro = {
                "📥 Entradas": "entrada",
                "🔁 Transferências": "transferencia",
                "📤 Retiradas": "retirada",
            }

            rotulos_tipo = {
                "entrada": "📥 Entrada",
                "transferencia": "🔁 Transferência",
                "retirada": "📤 Retirada",
            }

            linhas = []

            for m in movimentos:

                if filtro_tipo != "Todos" and m["tipo"] != tipo_por_filtro[filtro_tipo]:
                    continue

                if filtro_local != "Todos" and filtro_local not in (m["local"], m["local_destino"]):
                    continue

                if filtro_produto != "Todos" and m["produto"] != filtro_produto:
                    continue

                if m["tipo"] == "entrada":
                    sinal = "+"
                    onde = f"→ {m['local'] or '—'}"
                elif m["tipo"] == "retirada":
                    sinal = "−"
                    onde = f"de {m['local'] or '—'}"
                else:
                    sinal = "↔ "
                    onde = f"{m['local'] or '—'} → {m['local_destino'] or '—'}"

                linhas.append({
                    "Data/Hora": m["data_hora"].strftime("%d/%m/%Y %H:%M"),
                    "Tipo": rotulos_tipo.get(m["tipo"], m["tipo"]),
                    "Produto": m["produto"],
                    "Quantidade": f"{sinal}{_fmt(m['quantidade'])} {m['unidade']}",
                    "Local": onde,
                    "Responsável": m["responsavel"],
                    "Registrado por": m["registrado_por"] or "—",
                    "Observação": m["observacao"] or "—",
                })

            if linhas:

                st.dataframe(
                    pd.DataFrame(linhas),
                    width='stretch',
                    hide_index=True
                )

                st.caption(f"Mostrando {len(linhas)} movimentações (até as últimas 500 registradas).")

            else:

                st.info("Nenhuma movimentação com esse filtro.")

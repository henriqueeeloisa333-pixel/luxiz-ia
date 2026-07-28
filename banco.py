import os
import streamlit as st
import psycopg2
from psycopg2 import pool
from psycopg2.extras import Json
from datetime import datetime


# ==================================================
# CONFIGURAÇÃO SUPABASE
# ==================================================

HOST = os.getenv("SUPABASE_HOST")
PORT = os.getenv("SUPABASE_PORT")
DATABASE = os.getenv("SUPABASE_DATABASE")

USER = os.getenv("SUPABASE_USER")
PASSWORD = os.getenv("SUPABASE_PASSWORD")

# ==================================================
# FUNDADOR (SECRETS)
# ==================================================

USUARIO_FUNDADOR = os.getenv(
    "FUNDADOR_USUARIO"
)

SENHA_FUNDADOR = os.getenv(
    "FUNDADOR_SENHA"
)

# ==================================================
# CONEXÃO (POOL REAPROVEITADO)
# ==================================================
# Antes, cada ação abria uma conexão nova com o Supabase
# do zero (handshake TLS completo a cada clique), o que
# deixava tudo mais lento. Agora um pool mantém conexões
# já abertas prontas para uso — conectar() pega uma
# emprestada, liberar() devolve pro pool (sem fechar de
# verdade), evitando repetir esse custo a cada ação.

@st.cache_resource
def _obter_pool():

    return psycopg2.pool.SimpleConnectionPool(
        1,
        10,
        host=HOST,
        port=PORT,
        database=DATABASE,
        user=USER,
        password=PASSWORD,
        connect_timeout=10
    )


def conectar():

    pool_obj = _obter_pool()
    conn = pool_obj.getconn()

    # O Supabase (assim como bancos gerenciados em geral) derruba
    # conexões que ficam muito tempo ociosas no pool, mas o psycopg2
    # só percebe isso na hora de usar a conexão — daí o erro
    # "server closed the connection unexpectedly". Testando com um
    # SELECT 1 aqui, a gente descarta conexões mortas e pega outra
    # do pool antes de repassar pro resto do código.

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")

    except Exception:

        try:
            pool_obj.putconn(conn, close=True)
        except Exception:
            pass

        conn = pool_obj.getconn()

    return conn


def liberar(conn):

    try:
        _obter_pool().putconn(conn)
    except Exception:
        pass


@st.cache_resource
def _garantir_schema():

    print("🔎 Iniciando conexão com o banco...", flush=True)
    print(f"HOST={HOST!r} PORT={PORT!r} DATABASE={DATABASE!r} USER={USER!r}", flush=True)

    try:
        conn = conectar()
        print("✅ Conectado com sucesso.", flush=True)
    except Exception as e:
        print(f"❌ ERRO AO CONECTAR: {e}", flush=True)
        raise
    cursor = conn.cursor()

    # ==============================
    # NOTAS
    # ==============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notas (
        rua TEXT PRIMARY KEY,
        nota REAL,
        dupla TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_notas (
        id BIGSERIAL PRIMARY KEY,
        rua TEXT NOT NULL,
        nota REAL,
        dupla TEXT,
        data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # REMANEJAMENTO
    # ==============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS remanejamento (
        id BIGSERIAL PRIMARY KEY,
        item TEXT NOT NULL,
        prioridade TEXT DEFAULT 'Normal'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_remanejamento (
        id BIGSERIAL PRIMARY KEY,
        item TEXT NOT NULL,
        prioridade TEXT,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # SAC
    # ==============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sac_historico (
        mes_ano TEXT PRIMARY KEY,
        reclamacoes INTEGER,
        meta INTEGER
    )
    """)

    # ==============================
    # ANÁLISE TÉCNICA (SAC)
    # ==============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analise_tecnica (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT,
        tipo_erro TEXT NOT NULL,
        data_erro DATE NOT NULL,
        descricao TEXT,
        chamado TEXT,
        cliente TEXT,
        nota_fiscal TEXT,
        cod_produto TEXT,
        produto TEXT,
        tratativa TEXT,
        hora TIME,
        separador TEXT,
        volume TEXT,
        carga TEXT,
        regiao TEXT,
        motorista TEXT,
        balanca TEXT,
        conferente TEXT,
        vinculos_notificados JSONB DEFAULT '[]'::jsonb,
        registrado_por TEXT,
        data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # AUDITORIA DE ATIVIDADES
    # ==============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria_atividades (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        funcao TEXT NOT NULL,
        qtd_acertos INTEGER DEFAULT 0,
        qtd_erros INTEGER DEFAULT 0,
        data_atividade DATE NOT NULL,
        descricao TEXT,
        registrado_por TEXT,
        data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # RODÍZIO - FIM DE EXPEDIENTE
    # ==============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rotativo_pessoas (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT UNIQUE NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rotativo_atividades (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT UNIQUE NOT NULL,
        tipo TEXT DEFAULT 'rotativo',
        pessoa_fixa TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # CHECKLISTS
    # ==============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checklist_hidraulicos (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        numero TEXT NOT NULL,
        data_checklist DATE NOT NULL,
        status TEXT NOT NULL,
        descricao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checklist_carrinhos (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        numero TEXT NOT NULL,
        data_checklist DATE NOT NULL,
        status TEXT NOT NULL,
        descricao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checklist_empilhadeiras (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        numero TEXT NOT NULL,
        data_checklist DATE NOT NULL,
        status TEXT NOT NULL,
        descricao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checklist_pigmentacao (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        data_checklist DATE NOT NULL,
        status TEXT NOT NULL,
        descricao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # EQUIPAMENTOS: RESPONSÁVEIS E CARRINHOS FIXOS
    # ==============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS responsaveis_hidraulicos (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        numero TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS responsaveis_carrinhos (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        numero TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS carrinhos_fixos (
        id BIGSERIAL PRIMARY KEY,
        local TEXT NOT NULL,
        numero TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Carrinhos fixos por local já vêm pré-cadastrados na primeira
    # vez que o app roda — depois disso, tudo é editável normalmente
    # pela aba de Equipamentos no Administrativo.

    cursor.execute("SELECT COUNT(*) FROM carrinhos_fixos")

    if cursor.fetchone()[0] == 0:

        carrinhos_padrao = (
            [("Remanejamento", numero) for numero in ["06", "08", "09", "13"]] +
            [("Fracionado", numero) for numero in ["10", "11", "12"]]
        )

        for local, numero in carrinhos_padrao:

            cursor.execute("""
            INSERT INTO carrinhos_fixos (local, numero)
            VALUES (%s, %s)
            """, (local, numero))

    # ==============================
    # USUÁRIOS
    # ==============================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id BIGSERIAL PRIMARY KEY,
        usuario TEXT UNIQUE,
        senha TEXT,
        tipo TEXT DEFAULT 'usuario',
        trocar_senha INTEGER DEFAULT 1
    )
    """)

    # ==============================
    # CRIA FUNDADOR
    # ==============================

    cursor.execute("""
    SELECT usuario
    FROM usuarios
    WHERE usuario = %s
    """, (
        USUARIO_FUNDADOR,
    ))

    fundador = cursor.fetchone()

    if not fundador:

        cursor.execute("""
        INSERT INTO usuarios
            (
            usuario,
            senha,
            tipo,
            trocar_senha
        )
        VALUES (%s, %s, %s, %s)
        """, (
            USUARIO_FUNDADOR,
            SENHA_FUNDADOR,
            "fundador",
            0
        ))

    conn.commit()
    liberar(conn)    

    # ==============================
    # MIGRAÇÃO: colunas de auditoria
    # (seguro rodar mesmo com o banco já existente)
    # ==============================

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE notas ADD COLUMN IF NOT EXISTS atualizado_por TEXT")
    cursor.execute("ALTER TABLE historico_notas ADD COLUMN IF NOT EXISTS usuario TEXT")
    cursor.execute("ALTER TABLE remanejamento ADD COLUMN IF NOT EXISTS criado_por TEXT")
    cursor.execute("ALTER TABLE historico_remanejamento ADD COLUMN IF NOT EXISTS usuario TEXT")
    cursor.execute("ALTER TABLE sac_historico ADD COLUMN IF NOT EXISTS atualizado_por TEXT")
    cursor.execute("ALTER TABLE sac_historico ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    cursor.execute("ALTER TABLE analise_tecnica ALTER COLUMN nome DROP NOT NULL")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS descricao TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS chamado TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS cliente TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS nota_fiscal TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS cod_produto TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS produto TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS tratativa TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS hora TIME")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS separador TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS volume TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS carga TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS regiao TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS motorista TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS balanca TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS conferente TEXT")
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS vinculos_notificados JSONB DEFAULT '[]'::jsonb")
    cursor.execute("ALTER TABLE rotativo_atividades ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'rotativo'")
    cursor.execute("ALTER TABLE rotativo_atividades ADD COLUMN IF NOT EXISTS pessoa_fixa TEXT")

    conn.commit()
    liberar(conn)

    return True


def inicializar_banco():

    _garantir_schema()

# ==================================================
# DASHBOARD
# ==================================================

@st.cache_data(ttl=30)
def ler_notas():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        rua,
        nota
    FROM notas
    """)

    dados = {
        row[0]: float(row[1]) if row[1] is not None else 0
        for row in cursor.fetchall()
    }

    liberar(conn)

    return dados


@st.cache_data(ttl=30)
def ler_duplas():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        rua,
        dupla
    FROM notas
    """)

    dados = {
        row[0]: row[1]
        for row in cursor.fetchall()
    }

    liberar(conn)

    return dados


@st.cache_data(ttl=30)
def ler_tudo():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        rua,
        nota,
        dupla
    FROM notas
    """)

    dados = {}

    for row in cursor.fetchall():

        dados[row[0]] = {
            "nota": float(row[1]) if row[1] is not None else 0,
            "dupla": row[2]
        }

    liberar(conn)

    return dados


def salvar_dados(
    rua,
    nota,
    dupla,
    usuario=None
):

    conn = conectar()
    cursor = conn.cursor()

    # Atualiza o painel atual
    cursor.execute("""
    INSERT INTO notas
    (
        rua,
        nota,
        dupla,
        atualizado_por
    )
    VALUES (%s, %s, %s, %s)

    ON CONFLICT (rua)
    DO UPDATE SET
        nota = EXCLUDED.nota,
        dupla = EXCLUDED.dupla,
        atualizado_por = EXCLUDED.atualizado_por
    """, (
        rua,
        nota,
        dupla,
        usuario
    ))

    # Salva histórico
    cursor.execute("""
    INSERT INTO historico_notas
    (
        rua,
        nota,
        dupla,
        usuario
    )
    VALUES (%s, %s, %s, %s)
    """, (
        rua,
        nota,
        dupla,
        usuario
    ))

    conn.commit()
    liberar(conn)

    # limpa o cache para refletir o dado novo imediatamente
    ler_notas.clear()
    ler_duplas.clear()
    ler_tudo.clear()
    ler_historico_rua.clear()


@st.cache_data(ttl=30)
def ler_historico_rua(
    rua,
    limite=10
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        nota,
        dupla,
        data_atualizacao,
        usuario
    FROM historico_notas
    WHERE rua = %s
    ORDER BY data_atualizacao DESC
    LIMIT %s
    """, (
        rua,
        limite
    ))

    dados = cursor.fetchall()

    liberar(conn)

    return dados

# ==================================================
# REMANEJAMENTO
# ==================================================

@st.cache_data(ttl=30)
def ler_remanejamentos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        item,
        prioridade,
        criado_por
    FROM remanejamento
    ORDER BY
        CASE prioridade
            WHEN 'Alta' THEN 1
            WHEN 'Média' THEN 2
            ELSE 3
        END,
        id DESC
    """)

    dados = []

    for row in cursor.fetchall():

        dados.append({
            "id": row[0],
            "nome": row[1],
            "prioridade": row[2],
            "criado_por": row[3]
        })

    liberar(conn)

    return dados


def adicionar_remanejamento(
    item,
    prioridade="Normal",
    usuario=None
):

    if not item or not item.strip():
        raise ValueError("O campo 'item' não pode ser vazio.")

    item = item.strip()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO remanejamento
    (
        item,
        prioridade,
        criado_por
    )
    VALUES (%s, %s, %s)
    """, (
        item,
        prioridade,
        usuario
    ))

    cursor.execute("""
    INSERT INTO historico_remanejamento
    (
        item,
        prioridade,
        usuario
    )
    VALUES (%s, %s, %s)
    """, (
        item,
        prioridade,
        usuario
    ))

    conn.commit()
    liberar(conn)

    ler_remanejamentos.clear()
    ler_historico_remanejamento.clear()


def excluir_remanejamento(
    id_item
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM remanejamento
    WHERE id = %s
    """, (
        id_item,
    ))

    conn.commit()
    liberar(conn)

    ler_remanejamentos.clear()


def excluir_remanejamento_lote(
    ids_itens
):

    if not ids_itens:
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM remanejamento
    WHERE id = ANY(%s)
    """, (
        ids_itens,
    ))

    conn.commit()
    liberar(conn)

    ler_remanejamentos.clear()


def total_remanejamentos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM remanejamento
    """)

    total = cursor.fetchone()[0]

    liberar(conn)

    return total

@st.cache_data(ttl=30)
def ler_historico_remanejamento(
    limite=20
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        item,
        prioridade,
        data_hora,
        usuario
    FROM historico_remanejamento
    ORDER BY data_hora DESC
    LIMIT %s
    """, (limite,))

    dados = cursor.fetchall()

    liberar(conn)

    return dados

# ==================================================
# SAC
# ==================================================

def atualizar_sac_mensal(
    reclamacoes,
    meta,
    usuario=None
):

    mes_ano = datetime.now().strftime(
        "%Y-%m"
    )

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO sac_historico
    (
        mes_ano,
        reclamacoes,
        meta,
        atualizado_por,
        atualizado_em
    )
    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)

    ON CONFLICT (mes_ano)
    DO UPDATE SET
        reclamacoes = EXCLUDED.reclamacoes,
        meta = EXCLUDED.meta,
        atualizado_por = EXCLUDED.atualizado_por,
        atualizado_em = CURRENT_TIMESTAMP
    """, (
        mes_ano,
        reclamacoes,
        meta,
        usuario
    ))

    conn.commit()
    liberar(conn)

    ler_historico_sac.clear()


@st.cache_data(ttl=30)
def ler_historico_sac():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        mes_ano,
        reclamacoes,
        meta,
        atualizado_por,
        atualizado_em
    FROM sac_historico
    ORDER BY mes_ano ASC
    """)

    dados = cursor.fetchall()

    liberar(conn)

    return dados


def total_reclamacoes():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        COALESCE(
            SUM(reclamacoes),
            0
        )
    FROM sac_historico
    """)

    total = cursor.fetchone()[0]

    liberar(conn)

    return total

# ==================================================
# ANÁLISE TÉCNICA (SAC)
# ==================================================

def adicionar_analise_tecnica(
    dados,
    vinculos,
    usuario=None
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO analise_tecnica
    (
        nome, tipo_erro, data_erro, descricao,
        chamado, cliente, nota_fiscal, cod_produto, produto,
        tratativa, hora, separador, volume, carga, regiao,
        motorista, balanca, conferente, vinculos_notificados,
        registrado_por
    )
    VALUES (
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s
    )
    """, (
        None, dados["tipo_erro"], dados["data_erro"], dados["descricao"],
        dados["chamado"], dados["cliente"], dados["nota_fiscal"], dados["cod_produto"], dados["produto"],
        dados["tratativa"], dados["hora"], dados["separador"], dados["volume"], dados["carga"], dados["regiao"],
        dados["motorista"], dados["balanca"], dados["conferente"], Json(vinculos),
        usuario
    ))

    conn.commit()
    liberar(conn)

    ler_analise_tecnica.clear()


@st.cache_data(ttl=30)
def ler_analise_tecnica():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id, nome, tipo_erro, data_erro, descricao,
        chamado, cliente, nota_fiscal, cod_produto, produto,
        tratativa, hora, separador, volume, carga, regiao,
        motorista, balanca, conferente, vinculos_notificados,
        registrado_por
    FROM analise_tecnica
    ORDER BY data_erro DESC
    """)

    colunas = [
        "id", "nome", "tipo_erro", "data_erro", "descricao",
        "chamado", "cliente", "nota_fiscal", "cod_produto", "produto",
        "tratativa", "hora", "separador", "volume", "carga", "regiao",
        "motorista", "balanca", "conferente", "vinculos_notificados",
        "registrado_por"
    ]

    dados = []

    for row in cursor.fetchall():

        dados.append(
            dict(zip(colunas, row))
        )

    liberar(conn)

    return dados


def excluir_analise_tecnica(
    id_registro
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM analise_tecnica
    WHERE id = %s
    """, (
        id_registro,
    ))

    conn.commit()
    liberar(conn)

    ler_analise_tecnica.clear()


def excluir_analise_tecnica_lote(
    ids_registros
):

    if not ids_registros:
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM analise_tecnica
    WHERE id = ANY(%s)
    """, (
        ids_registros,
    ))

    conn.commit()
    liberar(conn)

    ler_analise_tecnica.clear()

# ==================================================
# AUDITORIA DE ATIVIDADES
# ==================================================


def adicionar_auditoria(
    nome,
    funcao,
    qtd_acertos,
    qtd_erros,
    data_atividade,
    descricao,
    usuario=None
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO auditoria_atividades
    (
        nome, funcao, qtd_acertos, qtd_erros,
        data_atividade, descricao, registrado_por
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        nome, funcao, qtd_acertos, qtd_erros,
        data_atividade, descricao, usuario
    ))

    conn.commit()
    liberar(conn)

    ler_auditoria.clear()


@st.cache_data(ttl=30)
def ler_auditoria():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id, nome, funcao, qtd_acertos, qtd_erros,
        data_atividade, descricao, registrado_por
    FROM auditoria_atividades
    ORDER BY data_atividade DESC
    """)

    colunas = [
        "id", "nome", "funcao", "qtd_acertos", "qtd_erros",
        "data_atividade", "descricao", "registrado_por"
    ]

    dados = []

    for row in cursor.fetchall():

        dados.append(
            dict(zip(colunas, row))
        )

    liberar(conn)

    return dados


def excluir_auditoria(
    id_registro
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM auditoria_atividades
    WHERE id = %s
    """, (
        id_registro,
    ))

    conn.commit()
    liberar(conn)

    ler_auditoria.clear()


def excluir_auditoria_lote(
    ids_registros
):

    if not ids_registros:
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM auditoria_atividades
    WHERE id = ANY(%s)
    """, (
        ids_registros,
    ))

    conn.commit()
    liberar(conn)

    ler_auditoria.clear()

# ==================================================
# RODÍZIO - FIM DE EXPEDIENTE
# ==================================================


def adicionar_pessoa_rotativo(nome):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO rotativo_pessoas (nome)
    VALUES (%s)
    ON CONFLICT (nome) DO NOTHING
    """, (
        nome,
    ))

    conn.commit()
    liberar(conn)

    listar_pessoas_rotativo.clear()


@st.cache_data(ttl=30)
def listar_pessoas_rotativo():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nome
    FROM rotativo_pessoas
    ORDER BY id
    """)

    dados = cursor.fetchall()

    liberar(conn)

    return dados


def excluir_pessoa_rotativo(id_pessoa):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM rotativo_pessoas
    WHERE id = %s
    """, (
        id_pessoa,
    ))

    conn.commit()
    liberar(conn)

    listar_pessoas_rotativo.clear()


def adicionar_atividade_rotativo(
    nome,
    tipo="rotativo",
    pessoa_fixa=None
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO rotativo_atividades (nome, tipo, pessoa_fixa)
    VALUES (%s, %s, %s)
    ON CONFLICT (nome) DO NOTHING
    """, (
        nome, tipo, pessoa_fixa
    ))

    conn.commit()
    liberar(conn)

    listar_atividades_rotativo.clear()


@st.cache_data(ttl=30)
def listar_atividades_rotativo():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nome, tipo, pessoa_fixa
    FROM rotativo_atividades
    ORDER BY id
    """)

    dados = cursor.fetchall()

    liberar(conn)

    return dados


def excluir_atividade_rotativo(id_atividade):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM rotativo_atividades
    WHERE id = %s
    """, (
        id_atividade,
    ))

    conn.commit()
    liberar(conn)

    listar_atividades_rotativo.clear()

# ==================================================
# CHECKLISTS
# ==================================================


def _adicionar_checklist(tabela, nome, numero, data_checklist, status, descricao):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    INSERT INTO {tabela}
    (nome, numero, data_checklist, status, descricao)
    VALUES (%s, %s, %s, %s, %s)
    """, (
        nome, numero, data_checklist, status, descricao
    ))

    conn.commit()
    liberar(conn)


def _ler_checklist(tabela):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    SELECT id, nome, numero, data_checklist, status, descricao
    FROM {tabela}
    ORDER BY data_checklist DESC, id DESC
    """)

    colunas = ["id", "nome", "numero", "data_checklist", "status", "descricao"]

    dados = [
        dict(zip(colunas, row))
        for row in cursor.fetchall()
    ]

    liberar(conn)

    return dados


def _editar_checklist(tabela, id_registro, nome, numero, data_checklist, status, descricao):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    UPDATE {tabela}
    SET nome = %s,
        numero = %s,
        data_checklist = %s,
        status = %s,
        descricao = %s
    WHERE id = %s
    """, (
        nome, numero, data_checklist, status, descricao, id_registro
    ))

    conn.commit()
    liberar(conn)


def adicionar_checklist_hidraulico(nome, numero, data_checklist, status, descricao):

    _adicionar_checklist(
        "checklist_hidraulicos",
        nome, numero, data_checklist, status, descricao
    )

    ler_checklist_hidraulicos.clear()


@st.cache_data(ttl=30)
def ler_checklist_hidraulicos():

    return _ler_checklist("checklist_hidraulicos")


def editar_checklist_hidraulico(id_registro, nome, numero, data_checklist, status, descricao):

    _editar_checklist(
        "checklist_hidraulicos",
        id_registro, nome, numero, data_checklist, status, descricao
    )

    ler_checklist_hidraulicos.clear()


def adicionar_checklist_carrinho(nome, numero, data_checklist, status, descricao):

    _adicionar_checklist(
        "checklist_carrinhos",
        nome, numero, data_checklist, status, descricao
    )

    ler_checklist_carrinhos.clear()


@st.cache_data(ttl=30)
def ler_checklist_carrinhos():

    return _ler_checklist("checklist_carrinhos")


def editar_checklist_carrinho(id_registro, nome, numero, data_checklist, status, descricao):

    _editar_checklist(
        "checklist_carrinhos",
        id_registro, nome, numero, data_checklist, status, descricao
    )

    ler_checklist_carrinhos.clear()


def adicionar_checklist_empilhadeira(nome, numero, data_checklist, status, descricao):

    _adicionar_checklist(
        "checklist_empilhadeiras",
        nome, numero, data_checklist, status, descricao
    )

    ler_checklist_empilhadeiras.clear()


@st.cache_data(ttl=30)
def ler_checklist_empilhadeiras():

    return _ler_checklist("checklist_empilhadeiras")


def editar_checklist_empilhadeira(id_registro, nome, numero, data_checklist, status, descricao):

    _editar_checklist(
        "checklist_empilhadeiras",
        id_registro, nome, numero, data_checklist, status, descricao
    )

    ler_checklist_empilhadeiras.clear()


def adicionar_checklist_pigmentacao(nome, data_checklist, status, descricao):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO checklist_pigmentacao
    (nome, data_checklist, status, descricao)
    VALUES (%s, %s, %s, %s)
    """, (
        nome, data_checklist, status, descricao
    ))

    conn.commit()
    liberar(conn)

    ler_checklist_pigmentacao.clear()


@st.cache_data(ttl=30)
def ler_checklist_pigmentacao():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nome, data_checklist, status, descricao
    FROM checklist_pigmentacao
    ORDER BY data_checklist DESC, id DESC
    """)

    colunas = ["id", "nome", "data_checklist", "status", "descricao"]

    dados = [
        dict(zip(colunas, row))
        for row in cursor.fetchall()
    ]

    liberar(conn)

    return dados


def editar_checklist_pigmentacao(id_registro, nome, data_checklist, status, descricao):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE checklist_pigmentacao
    SET nome = %s,
        data_checklist = %s,
        status = %s,
        descricao = %s
    WHERE id = %s
    """, (
        nome, data_checklist, status, descricao, id_registro
    ))

    conn.commit()
    liberar(conn)

    ler_checklist_pigmentacao.clear()

# ==================================================
# EQUIPAMENTOS: RESPONSÁVEIS E CARRINHOS FIXOS
# ==================================================

def _ler_responsaveis(tabela):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    SELECT id, nome, numero
    FROM {tabela}
    ORDER BY nome ASC
    """)

    colunas = ["id", "nome", "numero"]

    dados = [
        dict(zip(colunas, row))
        for row in cursor.fetchall()
    ]

    liberar(conn)

    return dados


def _adicionar_responsavel(tabela, nome, numero):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    INSERT INTO {tabela} (nome, numero)
    VALUES (%s, %s)
    """, (nome, numero))

    conn.commit()
    liberar(conn)


def _editar_responsavel(tabela, id_registro, nome, numero):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    UPDATE {tabela}
    SET nome = %s,
        numero = %s
    WHERE id = %s
    """, (nome, numero, id_registro))

    conn.commit()
    liberar(conn)


def _excluir_responsavel(tabela, id_registro):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    DELETE FROM {tabela}
    WHERE id = %s
    """, (id_registro,))

    conn.commit()
    liberar(conn)


@st.cache_data(ttl=30)
def ler_responsaveis_hidraulicos():

    return _ler_responsaveis("responsaveis_hidraulicos")


def adicionar_responsavel_hidraulico(nome, numero):

    _adicionar_responsavel("responsaveis_hidraulicos", nome, numero)
    ler_responsaveis_hidraulicos.clear()


def editar_responsavel_hidraulico(id_registro, nome, numero):

    _editar_responsavel("responsaveis_hidraulicos", id_registro, nome, numero)
    ler_responsaveis_hidraulicos.clear()


def excluir_responsavel_hidraulico(id_registro):

    _excluir_responsavel("responsaveis_hidraulicos", id_registro)
    ler_responsaveis_hidraulicos.clear()


@st.cache_data(ttl=30)
def ler_responsaveis_carrinhos():

    return _ler_responsaveis("responsaveis_carrinhos")


def adicionar_responsavel_carrinho(nome, numero):

    _adicionar_responsavel("responsaveis_carrinhos", nome, numero)
    ler_responsaveis_carrinhos.clear()


def editar_responsavel_carrinho(id_registro, nome, numero):

    _editar_responsavel("responsaveis_carrinhos", id_registro, nome, numero)
    ler_responsaveis_carrinhos.clear()


def excluir_responsavel_carrinho(id_registro):

    _excluir_responsavel("responsaveis_carrinhos", id_registro)
    ler_responsaveis_carrinhos.clear()


@st.cache_data(ttl=30)
def ler_carrinhos_fixos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, local, numero
    FROM carrinhos_fixos
    ORDER BY local ASC, numero ASC
    """)

    colunas = ["id", "local", "numero"]

    dados = [
        dict(zip(colunas, row))
        for row in cursor.fetchall()
    ]

    liberar(conn)

    return dados


def adicionar_carrinho_fixo(local, numero):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO carrinhos_fixos (local, numero)
    VALUES (%s, %s)
    """, (local, numero))

    conn.commit()
    liberar(conn)

    ler_carrinhos_fixos.clear()


def editar_carrinho_fixo(id_registro, local, numero):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE carrinhos_fixos
    SET local = %s,
        numero = %s
    WHERE id = %s
    """, (local, numero, id_registro))

    conn.commit()
    liberar(conn)

    ler_carrinhos_fixos.clear()


def excluir_carrinho_fixo(id_registro):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM carrinhos_fixos
    WHERE id = %s
    """, (id_registro,))

    conn.commit()
    liberar(conn)

    ler_carrinhos_fixos.clear()

# ==================================================
# USUÁRIOS
# ==================================================

def autenticar(
    usuario,
    senha
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        tipo,
        trocar_senha
    FROM usuarios
    WHERE usuario = %s
    AND senha = %s
    """, (
        usuario,
        senha
    ))

    resultado = cursor.fetchone()

    liberar(conn)

    return resultado


def criar_usuario(
    usuario,
    senha,
    tipo="usuario"
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO usuarios
    (
        usuario,
        senha,
        tipo,
        trocar_senha
    )
    VALUES (%s, %s, %s, %s)
    """, (
        usuario,
        senha,
        tipo,
        1
    ))

    conn.commit()
    liberar(conn)

    listar_usuarios.clear()


@st.cache_data(ttl=30)
def listar_usuarios():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        usuario,
        tipo
    FROM usuarios
    ORDER BY usuario
    """)

    usuarios = cursor.fetchall()

    liberar(conn)

    return usuarios


def excluir_usuario(usuario):

    # Nunca permitir apagar o fundador
    if usuario == USUARIO_FUNDADOR:
        return False

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM usuarios
    WHERE usuario = %s
    """, (
        usuario,
    ))

    conn.commit()
    liberar(conn)

    listar_usuarios.clear()

    return True


def alterar_senha(
    usuario,
    nova_senha
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE usuarios
    SET
        senha = %s,
        trocar_senha = 0
    WHERE usuario = %s
    """, (
        nova_senha,
        usuario
    ))

    conn.commit()
    liberar(conn)


def resetar_senha(
    usuario,
    senha_temporaria
):

    # proteção adicional
    if usuario == USUARIO_FUNDADOR:
        return False

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE usuarios
    SET
        senha = %s,
        trocar_senha = 1
    WHERE usuario = %s
    """, (
        senha_temporaria,
        usuario
    ))

    conn.commit()
    liberar(conn)

    return True

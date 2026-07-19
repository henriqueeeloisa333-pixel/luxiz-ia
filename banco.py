import os
import streamlit as st
import psycopg2
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
# CONEXÃO
# ==================================================

def conectar():

    return psycopg2.connect(
        host=HOST,
        port=PORT,
        database=DATABASE,
        user=USER,
        password=PASSWORD,
        connect_timeout=10
    )   

def inicializar_banco():

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
    conn.close()    

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

    conn.commit()
    conn.close()

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

    conn.close()

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

    conn.close()

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

    conn.close()

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
    conn.close()

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

    conn.close()

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

    conn.close()

    return dados


def adicionar_remanejamento(
    item,
    prioridade="Normal",
    usuario=None
):

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
    conn.close()

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
    conn.close()

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
    conn.close()

    ler_remanejamentos.clear()


def total_remanejamentos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM remanejamento
    """)

    total = cursor.fetchone()[0]

    conn.close()

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

    conn.close()

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
    conn.close()

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

    conn.close()

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

    conn.close()

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
    conn.close()

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

    conn.close()

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
    conn.close()

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
    conn.close()

    ler_analise_tecnica.clear()

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

    conn.close()

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
    conn.close()


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

    conn.close()

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
    conn.close()

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
    conn.close()


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
    conn.close()

    return True

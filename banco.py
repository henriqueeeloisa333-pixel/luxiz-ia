import os
import secrets
import streamlit as st
import psycopg2
from psycopg2 import pool
from psycopg2.extras import Json
from datetime import datetime, timedelta


# ==================================================
# CONFIGURAÇÃO SUPABASE
# ==================================================

HOST = os.getenv("SUPABASE_HOST")
PORT = os.getenv("SUPABASE_PORT")
DATABASE = os.getenv("SUPABASE_DATABASE")

USER = os.getenv("SUPABASE_USER")
PASSWORD = os.getenv("SUPABASE_PASSWORD")

# ==================================================
# RUAS PADRÃO (usadas só para semear um armazém novo)
# ==================================================

RUAS_PADRAO = [
    "Rua 01",
    "Rua 02",
    "Rua 03",
    "Rua 04",
    "Rua 05",
    "Rua 06",
    "Rua 07",
    "Rua 35&32",
    "Rua 33&34"
]

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

    # ThreadedConnectionPool (não SimpleConnectionPool): o pool é
    # compartilhado por TODAS as sessões/usuários do app ao mesmo
    # tempo (é um recurso cacheado a nível de processo). O
    # SimpleConnectionPool não é seguro para uso concorrente por
    # várias threads — com vários usuários mexendo no app ao mesmo
    # tempo, isso podia causar lentidão e travamentos aleatórios.

    return psycopg2.pool.ThreadedConnectionPool(
        1,
        20,
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
        data_fechamento DATE,
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
    # SESSÕES ATIVAS (login persistente)
    # ==============================
    # Guarda um token por login, associado a um link (URL) que o
    # navegador mantém mesmo depois de um F5 ou de uma queda de
    # rede rápida — assim, ao reconectar, o app reconhece o token
    # e restaura a sessão sem pedir login de novo.

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessoes_ativas (
        token TEXT PRIMARY KEY,
        usuario TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expira_em TIMESTAMP
    )
    """)

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
    cursor.execute("ALTER TABLE analise_tecnica ADD COLUMN IF NOT EXISTS data_fechamento DATE")
    cursor.execute("ALTER TABLE rotativo_atividades ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'rotativo'")
    cursor.execute("ALTER TABLE rotativo_atividades ADD COLUMN IF NOT EXISTS pessoa_fixa TEXT")

    # Rastreio de "quem está logado agora": guarda o momento do último
    # acesso/atividade de cada usuário, atualizado no login e a cada
    # renovação automática do rodapé (ver render_status_footer no app.py).
    cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultimo_acesso TIMESTAMP")

    # Manutenção de equipamentos (checklist de hidráulicos, carrinhos e
    # empilhadeiras): permite marcar um item "Não Conforme" como enviado
    # para manutenção, e depois registrar o retorno.
    for tabela_checklist in ("checklist_hidraulicos", "checklist_carrinhos", "checklist_empilhadeiras"):

        cursor.execute(f"ALTER TABLE {tabela_checklist} ADD COLUMN IF NOT EXISTS em_manutencao BOOLEAN DEFAULT FALSE")
        cursor.execute(f"ALTER TABLE {tabela_checklist} ADD COLUMN IF NOT EXISTS manutencao_motivo TEXT")
        cursor.execute(f"ALTER TABLE {tabela_checklist} ADD COLUMN IF NOT EXISTS manutencao_enviado_por TEXT")
        cursor.execute(f"ALTER TABLE {tabela_checklist} ADD COLUMN IF NOT EXISTS manutencao_enviado_em TIMESTAMP")
        cursor.execute(f"ALTER TABLE {tabela_checklist} ADD COLUMN IF NOT EXISTS manutencao_retornado_por TEXT")
        cursor.execute(f"ALTER TABLE {tabela_checklist} ADD COLUMN IF NOT EXISTS manutencao_retornado_em TIMESTAMP")

    conn.commit()
    liberar(conn)

    # ==============================
    # MIGRAÇÃO: MULTI-ARMAZÉM
    # ==============================
    # Cada cliente/armazém que usar o Luxiz IA passa a ter os
    # próprios dados isolados dentro do MESMO banco, através da
    # coluna armazem_id. Os dados que já existiam (de antes dessa
    # migração) são automaticamente colocados no "Armazém Principal"
    # — nada se perde.

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS armazens (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT UNIQUE NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("SELECT id FROM armazens ORDER BY id ASC LIMIT 1")
    linha_armazem_padrao = cursor.fetchone()

    if not linha_armazem_padrao:

        cursor.execute("""
        INSERT INTO armazens (nome)
        VALUES (%s)
        RETURNING id
        """, ("Armazém Principal",))

        linha_armazem_padrao = cursor.fetchone()

    ID_ARMAZEM_PADRAO = linha_armazem_padrao[0]

    # ==============================
    # RUAS (cadastro dinâmico por armazém)
    # ==============================
    # Antes a lista de ruas era fixa (9 ruas "hardcoded" no código).
    # Agora cada armazém tem seu próprio cadastro de ruas, editável
    # no Administrativo > Dashboard ("Criar rua" / "Excluir rua").

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ruas (
        id BIGSERIAL PRIMARY KEY,
        armazem_id BIGINT REFERENCES armazens(id),
        nome TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (armazem_id, nome)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ruas_armazem ON ruas (armazem_id)")

    # Semeia as 9 ruas padrão em qualquer armazém que ainda não
    # tenha nenhuma rua cadastrada — preserva o comportamento atual
    # sem perder nada para quem já usa o app.
    cursor.execute("SELECT id FROM armazens")
    ids_todos_armazens = [linha[0] for linha in cursor.fetchall()]

    for id_armazem in ids_todos_armazens:

        cursor.execute(
            "SELECT COUNT(*) FROM ruas WHERE armazem_id = %s",
            (id_armazem,)
        )

        if cursor.fetchone()[0] == 0:

            for nome_rua in RUAS_PADRAO:

                cursor.execute(
                    """
                    INSERT INTO ruas (armazem_id, nome)
                    VALUES (%s, %s)
                    ON CONFLICT (armazem_id, nome) DO NOTHING
                    """,
                    (id_armazem, nome_rua)
                )

    conn.commit()

    TABELAS_COM_ARMAZEM = [
        "notas", "historico_notas",
        "remanejamento", "historico_remanejamento",
        "sac_historico",
        "analise_tecnica",
        "auditoria_atividades",
        "rotativo_pessoas", "rotativo_atividades",
        "checklist_hidraulicos", "checklist_carrinhos",
        "checklist_empilhadeiras", "checklist_pigmentacao",
        "responsaveis_hidraulicos", "responsaveis_carrinhos",
        "carrinhos_fixos",
        "usuarios",
    ]

    for tabela in TABELAS_COM_ARMAZEM:

        cursor.execute(
            f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS "
            f"armazem_id BIGINT REFERENCES armazens(id)"
        )

        cursor.execute(
            f"UPDATE {tabela} SET armazem_id = %s WHERE armazem_id IS NULL",
            (ID_ARMAZEM_PADRAO,)
        )

        cursor.execute(
            f"ALTER TABLE {tabela} ALTER COLUMN armazem_id SET NOT NULL"
        )

    # notas: cada armazém tem sua própria "Rua 01", "Rua 02"... então
    # a chave única passa a ser (armazem_id, rua), não só "rua".
    cursor.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'notas_pkey') THEN
            ALTER TABLE notas DROP CONSTRAINT notas_pkey;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'notas_armazem_rua_key') THEN
            ALTER TABLE notas ADD CONSTRAINT notas_armazem_rua_key UNIQUE (armazem_id, rua);
        END IF;
    END $$;
    """)

    # sac_historico: (armazem_id, mes_ano) em vez de só "mes_ano".
    cursor.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'sac_historico_pkey') THEN
            ALTER TABLE sac_historico DROP CONSTRAINT sac_historico_pkey;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'sac_historico_armazem_mes_key') THEN
            ALTER TABLE sac_historico ADD CONSTRAINT sac_historico_armazem_mes_key UNIQUE (armazem_id, mes_ano);
        END IF;
    END $$;
    """)

    # rotativo_pessoas / rotativo_atividades: nome único por armazém,
    # não mais globalmente (dois armazéns podem ter uma pessoa "João").
    cursor.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'rotativo_pessoas_nome_key') THEN
            ALTER TABLE rotativo_pessoas DROP CONSTRAINT rotativo_pessoas_nome_key;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'rotativo_pessoas_armazem_nome_key') THEN
            ALTER TABLE rotativo_pessoas ADD CONSTRAINT rotativo_pessoas_armazem_nome_key UNIQUE (armazem_id, nome);
        END IF;
    END $$;
    """)

    cursor.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'rotativo_atividades_nome_key') THEN
            ALTER TABLE rotativo_atividades DROP CONSTRAINT rotativo_atividades_nome_key;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'rotativo_atividades_armazem_nome_key') THEN
            ALTER TABLE rotativo_atividades ADD CONSTRAINT rotativo_atividades_armazem_nome_key UNIQUE (armazem_id, nome);
        END IF;
    END $$;
    """)

    # ==============================
    # CRIA FUNDADOR
    # ==============================
    # Roda aqui (depois da migração multi-armazém) para já poder
    # gravar o armazem_id junto — se rodasse antes, em um banco que
    # já tivesse passado por essa migração, o INSERT quebraria por
    # não informar armazem_id (coluna NOT NULL).

    if USUARIO_FUNDADOR and SENHA_FUNDADOR:

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
                trocar_senha,
                armazem_id
            )
            VALUES (%s, %s, %s, %s, %s)
            """, (
                USUARIO_FUNDADOR,
                SENHA_FUNDADOR,
                "fundador",
                0,
                ID_ARMAZEM_PADRAO
            ))

    else:

        print(
            "⚠️ FUNDADOR_USUARIO / FUNDADOR_SENHA não configurados "
            "(secrets/variáveis de ambiente) — fundador não foi criado.",
            flush=True
        )

    # ==============================
    # MIGRAÇÃO: ÍNDICES DE PERFORMANCE
    # ==============================
    # armazem_id é FK, e o Postgres NÃO cria índice automático em
    # coluna de FK — só na chave primária. Como quase toda leitura
    # filtra por armazem_id (e várias ainda ordenam por data), sem
    # esses índices o banco varre a tabela inteira a cada consulta.
    # Isso não dói com poucos registros, mas piora conforme a base
    # cresce. IF NOT EXISTS torna seguro rodar em todo startup.

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_notas_rua_armazem ON historico_notas (armazem_id, rua, data_atualizacao DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historico_reman_armazem ON historico_remanejamento (armazem_id, data_hora DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analise_tecnica_armazem ON analise_tecnica (armazem_id, data_erro DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_armazem ON auditoria_atividades (armazem_id, data_atividade DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sac_historico_armazem ON sac_historico (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_remanejamento_armazem ON remanejamento (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rotativo_pessoas_armazem ON rotativo_pessoas (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rotativo_atividades_armazem ON rotativo_atividades (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_hidraulicos_armazem ON checklist_hidraulicos (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_carrinhos_armazem ON checklist_carrinhos (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_empilhadeiras_armazem ON checklist_empilhadeiras (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_checklist_pigmentacao_armazem ON checklist_pigmentacao (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_responsaveis_hidraulicos_armazem ON responsaveis_hidraulicos (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_responsaveis_carrinhos_armazem ON responsaveis_carrinhos (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_carrinhos_fixos_armazem ON carrinhos_fixos (armazem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_armazem ON usuarios (armazem_id)")

    conn.commit()
    liberar(conn)

    return True


def inicializar_banco():

    _garantir_schema()

# ==================================================
# DASHBOARD
# ==================================================

@st.cache_data(ttl=30)
def listar_ruas(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT nome
    FROM ruas
    WHERE armazem_id = %s
    ORDER BY criado_em ASC, id ASC
    """, (armazem_id,))

    dados = [row[0] for row in cursor.fetchall()]

    liberar(conn)

    return dados


def criar_rua(nome, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO ruas (armazem_id, nome)
    VALUES (%s, %s)
    ON CONFLICT (armazem_id, nome) DO NOTHING
    """, (armazem_id, nome))

    conn.commit()
    liberar(conn)

    listar_ruas.clear()


def excluir_rua(nome, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    # Remove o cadastro da rua e também os dados que já existiam
    # dela no Dashboard (nota atual + histórico), já que a rua
    # deixa de existir para esse armazém.
    cursor.execute(
        "DELETE FROM ruas WHERE armazem_id = %s AND nome = %s",
        (armazem_id, nome)
    )

    cursor.execute(
        "DELETE FROM notas WHERE armazem_id = %s AND rua = %s",
        (armazem_id, nome)
    )

    cursor.execute(
        "DELETE FROM historico_notas WHERE armazem_id = %s AND rua = %s",
        (armazem_id, nome)
    )

    conn.commit()
    liberar(conn)

    listar_ruas.clear()
    ler_notas.clear()
    ler_duplas.clear()
    ler_tudo.clear()
    ler_historico_rua.clear()


@st.cache_data(ttl=30)
def ler_notas(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        rua,
        nota
    FROM notas
    WHERE armazem_id = %s
    """, (armazem_id,))

    dados = {
        row[0]: float(row[1]) if row[1] is not None else 0
        for row in cursor.fetchall()
    }

    liberar(conn)

    return dados


@st.cache_data(ttl=30)
def ler_duplas(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        rua,
        dupla
    FROM notas
    WHERE armazem_id = %s
    """, (armazem_id,))

    dados = {
        row[0]: row[1]
        for row in cursor.fetchall()
    }

    liberar(conn)

    return dados


@st.cache_data(ttl=30)
def ler_tudo(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        rua,
        nota,
        dupla
    FROM notas
    WHERE armazem_id = %s
    """, (armazem_id,))

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
    armazem_id,
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
        atualizado_por,
        armazem_id
    )
    VALUES (%s, %s, %s, %s, %s)

    ON CONFLICT (armazem_id, rua)
    DO UPDATE SET
        nota = EXCLUDED.nota,
        dupla = EXCLUDED.dupla,
        atualizado_por = EXCLUDED.atualizado_por
    """, (
        rua,
        nota,
        dupla,
        usuario,
        armazem_id
    ))

    # Salva histórico
    cursor.execute("""
    INSERT INTO historico_notas
    (
        rua,
        nota,
        dupla,
        usuario,
        armazem_id
    )
    VALUES (%s, %s, %s, %s, %s)
    """, (
        rua,
        nota,
        dupla,
        usuario,
        armazem_id
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
    armazem_id,
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
    AND armazem_id = %s
    ORDER BY data_atualizacao DESC
    LIMIT %s
    """, (
        rua,
        armazem_id,
        limite
    ))

    dados = cursor.fetchall()

    liberar(conn)

    return dados

# ==================================================
# REMANEJAMENTO
# ==================================================

@st.cache_data(ttl=30)
def ler_remanejamentos(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        item,
        prioridade,
        criado_por
    FROM remanejamento
    WHERE armazem_id = %s
    ORDER BY
        CASE prioridade
            WHEN 'Alta' THEN 1
            WHEN 'Média' THEN 2
            ELSE 3
        END,
        id DESC
    """, (armazem_id,))

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
    armazem_id,
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
        criado_por,
        armazem_id
    )
    VALUES (%s, %s, %s, %s)
    """, (
        item,
        prioridade,
        usuario,
        armazem_id
    ))

    cursor.execute("""
    INSERT INTO historico_remanejamento
    (
        item,
        prioridade,
        usuario,
        armazem_id
    )
    VALUES (%s, %s, %s, %s)
    """, (
        item,
        prioridade,
        usuario,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_remanejamentos.clear()
    ler_historico_remanejamento.clear()
    total_remanejamentos.clear()


def excluir_remanejamento(
    id_item,
    armazem_id
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM remanejamento
    WHERE id = %s
    AND armazem_id = %s
    """, (
        id_item,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_remanejamentos.clear()
    total_remanejamentos.clear()


def excluir_remanejamento_lote(
    ids_itens,
    armazem_id
):

    if not ids_itens:
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM remanejamento
    WHERE id = ANY(%s)
    AND armazem_id = %s
    """, (
        ids_itens,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_remanejamentos.clear()
    total_remanejamentos.clear()


@st.cache_data(ttl=30)
def total_remanejamentos(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM remanejamento
    WHERE armazem_id = %s
    """, (armazem_id,))

    total = cursor.fetchone()[0]

    liberar(conn)

    return total

@st.cache_data(ttl=30)
def ler_historico_remanejamento(
    armazem_id,
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
    WHERE armazem_id = %s
    ORDER BY data_hora DESC
    LIMIT %s
    """, (armazem_id, limite))

    dados = cursor.fetchall()

    liberar(conn)

    return dados

# ==================================================
# SAC
# ==================================================

def atualizar_sac_mensal(
    reclamacoes,
    meta,
    armazem_id,
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
        atualizado_em,
        armazem_id
    )
    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)

    ON CONFLICT (armazem_id, mes_ano)
    DO UPDATE SET
        reclamacoes = EXCLUDED.reclamacoes,
        meta = EXCLUDED.meta,
        atualizado_por = EXCLUDED.atualizado_por,
        atualizado_em = CURRENT_TIMESTAMP
    """, (
        mes_ano,
        reclamacoes,
        meta,
        usuario,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_historico_sac.clear()
    total_reclamacoes.clear()


@st.cache_data(ttl=30)
def ler_historico_sac(armazem_id):

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
    WHERE armazem_id = %s
    ORDER BY mes_ano ASC
    """, (armazem_id,))

    dados = cursor.fetchall()

    liberar(conn)

    return dados


@st.cache_data(ttl=30)
def total_reclamacoes(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        COALESCE(
            SUM(reclamacoes),
            0
        )
    FROM sac_historico
    WHERE armazem_id = %s
    """, (armazem_id,))

    total = cursor.fetchone()[0]

    liberar(conn)

    return total

# ==================================================
# ANÁLISE TÉCNICA (SAC)
# ==================================================

def adicionar_analise_tecnica(
    dados,
    vinculos,
    armazem_id,
    usuario=None
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO analise_tecnica
    (
        nome, tipo_erro, data_erro, data_fechamento, descricao,
        chamado, cliente, nota_fiscal, cod_produto, produto,
        tratativa, hora, separador, volume, carga, regiao,
        motorista, balanca, conferente, vinculos_notificados,
        registrado_por, armazem_id
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s
    )
    """, (
        None, dados["tipo_erro"], dados["data_erro"], dados.get("data_fechamento"), dados["descricao"],
        dados["chamado"], dados["cliente"], dados["nota_fiscal"], dados["cod_produto"], dados["produto"],
        dados["tratativa"], dados["hora"], dados["separador"], dados["volume"], dados["carga"], dados["regiao"],
        dados["motorista"], dados["balanca"], dados["conferente"], Json(vinculos),
        usuario, armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_analise_tecnica.clear()


@st.cache_data(ttl=30)
def ler_analise_tecnica(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id, nome, tipo_erro, data_erro, data_fechamento, descricao,
        chamado, cliente, nota_fiscal, cod_produto, produto,
        tratativa, hora, separador, volume, carga, regiao,
        motorista, balanca, conferente, vinculos_notificados,
        registrado_por
    FROM analise_tecnica
    WHERE armazem_id = %s
    ORDER BY data_erro DESC
    """, (armazem_id,))

    colunas = [
        "id", "nome", "tipo_erro", "data_erro", "data_fechamento", "descricao",
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


def finalizar_analise_tecnica(
    id_registro,
    data_fechamento,
    armazem_id
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE analise_tecnica
    SET data_fechamento = %s
    WHERE id = %s
    AND armazem_id = %s
    """, (
        data_fechamento,
        id_registro,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_analise_tecnica.clear()


def excluir_analise_tecnica(
    id_registro,
    armazem_id
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM analise_tecnica
    WHERE id = %s
    AND armazem_id = %s
    """, (
        id_registro,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_analise_tecnica.clear()


def excluir_analise_tecnica_lote(
    ids_registros,
    armazem_id
):

    if not ids_registros:
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM analise_tecnica
    WHERE id = ANY(%s)
    AND armazem_id = %s
    """, (
        ids_registros,
        armazem_id
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
    armazem_id,
    usuario=None
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO auditoria_atividades
    (
        nome, funcao, qtd_acertos, qtd_erros,
        data_atividade, descricao, registrado_por, armazem_id
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        nome, funcao, qtd_acertos, qtd_erros,
        data_atividade, descricao, usuario, armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_auditoria.clear()


@st.cache_data(ttl=30)
def ler_auditoria(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id, nome, funcao, qtd_acertos, qtd_erros,
        data_atividade, descricao, registrado_por
    FROM auditoria_atividades
    WHERE armazem_id = %s
    ORDER BY data_atividade DESC
    """, (armazem_id,))

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
    id_registro,
    armazem_id
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM auditoria_atividades
    WHERE id = %s
    AND armazem_id = %s
    """, (
        id_registro,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_auditoria.clear()


def excluir_auditoria_lote(
    ids_registros,
    armazem_id
):

    if not ids_registros:
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM auditoria_atividades
    WHERE id = ANY(%s)
    AND armazem_id = %s
    """, (
        ids_registros,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_auditoria.clear()

# ==================================================
# RODÍZIO - FIM DE EXPEDIENTE
# ==================================================


def adicionar_pessoa_rotativo(nome, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO rotativo_pessoas (nome, armazem_id)
    VALUES (%s, %s)
    ON CONFLICT (armazem_id, nome) DO NOTHING
    """, (
        nome,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    listar_pessoas_rotativo.clear()


@st.cache_data(ttl=30)
def listar_pessoas_rotativo(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nome
    FROM rotativo_pessoas
    WHERE armazem_id = %s
    ORDER BY id
    """, (armazem_id,))

    dados = cursor.fetchall()

    liberar(conn)

    return dados


def excluir_pessoa_rotativo(id_pessoa, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM rotativo_pessoas
    WHERE id = %s
    AND armazem_id = %s
    """, (
        id_pessoa,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    listar_pessoas_rotativo.clear()


def adicionar_atividade_rotativo(
    nome,
    armazem_id,
    tipo="rotativo",
    pessoa_fixa=None
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO rotativo_atividades (nome, tipo, pessoa_fixa, armazem_id)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (armazem_id, nome) DO NOTHING
    """, (
        nome, tipo, pessoa_fixa, armazem_id
    ))

    conn.commit()
    liberar(conn)

    listar_atividades_rotativo.clear()


@st.cache_data(ttl=30)
def listar_atividades_rotativo(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nome, tipo, pessoa_fixa
    FROM rotativo_atividades
    WHERE armazem_id = %s
    ORDER BY id
    """, (armazem_id,))

    dados = cursor.fetchall()

    liberar(conn)

    return dados


def excluir_atividade_rotativo(id_atividade, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM rotativo_atividades
    WHERE id = %s
    AND armazem_id = %s
    """, (
        id_atividade,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    listar_atividades_rotativo.clear()

# ==================================================
# CHECKLISTS
# ==================================================


def _adicionar_checklist(tabela, nome, numero, data_checklist, status, descricao, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    INSERT INTO {tabela}
    (nome, numero, data_checklist, status, descricao, armazem_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        nome, numero, data_checklist, status, descricao, armazem_id
    ))

    conn.commit()
    liberar(conn)


def _ler_checklist(tabela, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    SELECT id, nome, numero, data_checklist, status, descricao,
        em_manutencao, manutencao_motivo, manutencao_enviado_por,
        manutencao_enviado_em, manutencao_retornado_por, manutencao_retornado_em
    FROM {tabela}
    WHERE armazem_id = %s
    ORDER BY data_checklist DESC, id DESC
    """, (armazem_id,))

    colunas = [
        "id", "nome", "numero", "data_checklist", "status", "descricao",
        "em_manutencao", "manutencao_motivo", "manutencao_enviado_por",
        "manutencao_enviado_em", "manutencao_retornado_por", "manutencao_retornado_em"
    ]

    dados = [
        dict(zip(colunas, row))
        for row in cursor.fetchall()
    ]

    liberar(conn)

    return dados


def _editar_checklist(tabela, id_registro, nome, numero, data_checklist, status, descricao, armazem_id):

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
    AND armazem_id = %s
    """, (
        nome, numero, data_checklist, status, descricao, id_registro, armazem_id
    ))

    conn.commit()
    liberar(conn)


def _enviar_manutencao_checklist(tabela, id_registro, motivo, usuario, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    UPDATE {tabela}
    SET em_manutencao = TRUE,
        manutencao_motivo = %s,
        manutencao_enviado_por = %s,
        manutencao_enviado_em = CURRENT_TIMESTAMP,
        manutencao_retornado_por = NULL,
        manutencao_retornado_em = NULL
    WHERE id = %s
    AND armazem_id = %s
    """, (
        motivo, usuario, id_registro, armazem_id
    ))

    conn.commit()
    liberar(conn)


def _retornar_manutencao_checklist(tabela, id_registro, usuario, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    UPDATE {tabela}
    SET em_manutencao = FALSE,
        manutencao_retornado_por = %s,
        manutencao_retornado_em = CURRENT_TIMESTAMP
    WHERE id = %s
    AND armazem_id = %s
    """, (
        usuario, id_registro, armazem_id
    ))

    conn.commit()
    liberar(conn)


def adicionar_checklist_hidraulico(nome, numero, data_checklist, status, descricao, armazem_id):

    _adicionar_checklist(
        "checklist_hidraulicos",
        nome, numero, data_checklist, status, descricao, armazem_id
    )

    ler_checklist_hidraulicos.clear()


@st.cache_data(ttl=30)
def ler_checklist_hidraulicos(armazem_id):

    return _ler_checklist("checklist_hidraulicos", armazem_id)


def editar_checklist_hidraulico(id_registro, nome, numero, data_checklist, status, descricao, armazem_id):

    _editar_checklist(
        "checklist_hidraulicos",
        id_registro, nome, numero, data_checklist, status, descricao, armazem_id
    )

    ler_checklist_hidraulicos.clear()


def enviar_manutencao_hidraulico(id_registro, motivo, usuario, armazem_id):

    _enviar_manutencao_checklist(
        "checklist_hidraulicos", id_registro, motivo, usuario, armazem_id
    )

    ler_checklist_hidraulicos.clear()


def retornar_manutencao_hidraulico(id_registro, usuario, armazem_id):

    _retornar_manutencao_checklist(
        "checklist_hidraulicos", id_registro, usuario, armazem_id
    )

    ler_checklist_hidraulicos.clear()


def adicionar_checklist_carrinho(nome, numero, data_checklist, status, descricao, armazem_id):

    _adicionar_checklist(
        "checklist_carrinhos",
        nome, numero, data_checklist, status, descricao, armazem_id
    )

    ler_checklist_carrinhos.clear()


@st.cache_data(ttl=30)
def ler_checklist_carrinhos(armazem_id):

    return _ler_checklist("checklist_carrinhos", armazem_id)


def editar_checklist_carrinho(id_registro, nome, numero, data_checklist, status, descricao, armazem_id):

    _editar_checklist(
        "checklist_carrinhos",
        id_registro, nome, numero, data_checklist, status, descricao, armazem_id
    )

    ler_checklist_carrinhos.clear()


def enviar_manutencao_carrinho(id_registro, motivo, usuario, armazem_id):

    _enviar_manutencao_checklist(
        "checklist_carrinhos", id_registro, motivo, usuario, armazem_id
    )

    ler_checklist_carrinhos.clear()


def retornar_manutencao_carrinho(id_registro, usuario, armazem_id):

    _retornar_manutencao_checklist(
        "checklist_carrinhos", id_registro, usuario, armazem_id
    )

    ler_checklist_carrinhos.clear()


def adicionar_checklist_empilhadeira(nome, numero, data_checklist, status, descricao, armazem_id):

    _adicionar_checklist(
        "checklist_empilhadeiras",
        nome, numero, data_checklist, status, descricao, armazem_id
    )

    ler_checklist_empilhadeiras.clear()


@st.cache_data(ttl=30)
def ler_checklist_empilhadeiras(armazem_id):

    return _ler_checklist("checklist_empilhadeiras", armazem_id)


def editar_checklist_empilhadeira(id_registro, nome, numero, data_checklist, status, descricao, armazem_id):

    _editar_checklist(
        "checklist_empilhadeiras",
        id_registro, nome, numero, data_checklist, status, descricao, armazem_id
    )

    ler_checklist_empilhadeiras.clear()


def enviar_manutencao_empilhadeira(id_registro, motivo, usuario, armazem_id):

    _enviar_manutencao_checklist(
        "checklist_empilhadeiras", id_registro, motivo, usuario, armazem_id
    )

    ler_checklist_empilhadeiras.clear()


def retornar_manutencao_empilhadeira(id_registro, usuario, armazem_id):

    _retornar_manutencao_checklist(
        "checklist_empilhadeiras", id_registro, usuario, armazem_id
    )

    ler_checklist_empilhadeiras.clear()


def adicionar_checklist_pigmentacao(nome, data_checklist, status, descricao, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO checklist_pigmentacao
    (nome, data_checklist, status, descricao, armazem_id)
    VALUES (%s, %s, %s, %s, %s)
    """, (
        nome, data_checklist, status, descricao, armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_checklist_pigmentacao.clear()


@st.cache_data(ttl=30)
def ler_checklist_pigmentacao(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nome, data_checklist, status, descricao
    FROM checklist_pigmentacao
    WHERE armazem_id = %s
    ORDER BY data_checklist DESC, id DESC
    """, (armazem_id,))

    colunas = ["id", "nome", "data_checklist", "status", "descricao"]

    dados = [
        dict(zip(colunas, row))
        for row in cursor.fetchall()
    ]

    liberar(conn)

    return dados


def editar_checklist_pigmentacao(id_registro, nome, data_checklist, status, descricao, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE checklist_pigmentacao
    SET nome = %s,
        data_checklist = %s,
        status = %s,
        descricao = %s
    WHERE id = %s
    AND armazem_id = %s
    """, (
        nome, data_checklist, status, descricao, id_registro, armazem_id
    ))

    conn.commit()
    liberar(conn)

    ler_checklist_pigmentacao.clear()

# ==================================================
# EQUIPAMENTOS: RESPONSÁVEIS E CARRINHOS FIXOS
# ==================================================

def _ler_responsaveis(tabela, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    SELECT id, nome, numero
    FROM {tabela}
    WHERE armazem_id = %s
    ORDER BY nome ASC
    """, (armazem_id,))

    colunas = ["id", "nome", "numero"]

    dados = [
        dict(zip(colunas, row))
        for row in cursor.fetchall()
    ]

    liberar(conn)

    return dados


def _adicionar_responsavel(tabela, nome, numero, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    INSERT INTO {tabela} (nome, numero, armazem_id)
    VALUES (%s, %s, %s)
    """, (nome, numero, armazem_id))

    conn.commit()
    liberar(conn)


def _editar_responsavel(tabela, id_registro, nome, numero, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    UPDATE {tabela}
    SET nome = %s,
        numero = %s
    WHERE id = %s
    AND armazem_id = %s
    """, (nome, numero, id_registro, armazem_id))

    conn.commit()
    liberar(conn)


def _excluir_responsavel(tabela, id_registro, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(f"""
    DELETE FROM {tabela}
    WHERE id = %s
    AND armazem_id = %s
    """, (id_registro, armazem_id))

    conn.commit()
    liberar(conn)


@st.cache_data(ttl=30)
def ler_responsaveis_hidraulicos(armazem_id):

    return _ler_responsaveis("responsaveis_hidraulicos", armazem_id)


def adicionar_responsavel_hidraulico(nome, numero, armazem_id):

    _adicionar_responsavel("responsaveis_hidraulicos", nome, numero, armazem_id)
    ler_responsaveis_hidraulicos.clear()


def editar_responsavel_hidraulico(id_registro, nome, numero, armazem_id):

    _editar_responsavel("responsaveis_hidraulicos", id_registro, nome, numero, armazem_id)
    ler_responsaveis_hidraulicos.clear()


def excluir_responsavel_hidraulico(id_registro, armazem_id):

    _excluir_responsavel("responsaveis_hidraulicos", id_registro, armazem_id)
    ler_responsaveis_hidraulicos.clear()


@st.cache_data(ttl=30)
def ler_responsaveis_carrinhos(armazem_id):

    return _ler_responsaveis("responsaveis_carrinhos", armazem_id)


def adicionar_responsavel_carrinho(nome, numero, armazem_id):

    _adicionar_responsavel("responsaveis_carrinhos", nome, numero, armazem_id)
    ler_responsaveis_carrinhos.clear()


def editar_responsavel_carrinho(id_registro, nome, numero, armazem_id):

    _editar_responsavel("responsaveis_carrinhos", id_registro, nome, numero, armazem_id)
    ler_responsaveis_carrinhos.clear()


def excluir_responsavel_carrinho(id_registro, armazem_id):

    _excluir_responsavel("responsaveis_carrinhos", id_registro, armazem_id)
    ler_responsaveis_carrinhos.clear()


@st.cache_data(ttl=30)
def ler_carrinhos_fixos(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, local, numero
    FROM carrinhos_fixos
    WHERE armazem_id = %s
    ORDER BY local ASC, numero ASC
    """, (armazem_id,))

    colunas = ["id", "local", "numero"]

    dados = [
        dict(zip(colunas, row))
        for row in cursor.fetchall()
    ]

    liberar(conn)

    return dados


def adicionar_carrinho_fixo(local, numero, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO carrinhos_fixos (local, numero, armazem_id)
    VALUES (%s, %s, %s)
    """, (local, numero, armazem_id))

    conn.commit()
    liberar(conn)

    ler_carrinhos_fixos.clear()


def editar_carrinho_fixo(id_registro, local, numero, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE carrinhos_fixos
    SET local = %s,
        numero = %s
    WHERE id = %s
    AND armazem_id = %s
    """, (local, numero, id_registro, armazem_id))

    conn.commit()
    liberar(conn)

    ler_carrinhos_fixos.clear()


def excluir_carrinho_fixo(id_registro, armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM carrinhos_fixos
    WHERE id = %s
    AND armazem_id = %s
    """, (id_registro, armazem_id))

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
        u.id,
        u.tipo,
        u.trocar_senha,
        u.armazem_id,
        a.nome
    FROM usuarios u
    JOIN armazens a ON a.id = u.armazem_id
    WHERE u.usuario = %s
    AND u.senha = %s
    """, (
        usuario,
        senha
    ))

    resultado = cursor.fetchone()

    liberar(conn)

    return resultado


# ==================================================
# SESSÕES ATIVAS (login persistente)
# ==================================================
# Um token é gerado a cada login e colocado na URL da página.
# Como a URL fica salva no navegador, se a página recarregar
# sozinha (F5, queda de rede, reconexão) o app consegue validar
# esse token aqui e devolver o usuário para onde estava, sem
# precisar fazer login de novo.

def criar_sessao(usuario, dias_validade=30):

    token = secrets.token_urlsafe(32)

    expira_em = datetime.utcnow() + timedelta(days=dias_validade)

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO sessoes_ativas (token, usuario, expira_em)
    VALUES (%s, %s, %s)
    """, (
        token,
        usuario,
        expira_em
    ))

    conn.commit()
    liberar(conn)

    return token


def validar_sessao(token):

    if not token:
        return None

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        u.usuario,
        u.tipo,
        u.trocar_senha,
        u.armazem_id,
        a.nome
    FROM sessoes_ativas s
    JOIN usuarios u ON u.usuario = s.usuario
    JOIN armazens a ON a.id = u.armazem_id
    WHERE s.token = %s
    AND (s.expira_em IS NULL OR s.expira_em > CURRENT_TIMESTAMP)
    """, (token,))

    resultado = cursor.fetchone()

    liberar(conn)

    return resultado


def renovar_sessao(token, dias_validade=30):

    if not token:
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE sessoes_ativas
    SET expira_em = %s
    WHERE token = %s
    """, (
        datetime.utcnow() + timedelta(days=dias_validade),
        token
    ))

    conn.commit()
    liberar(conn)


def encerrar_sessao(token):

    if not token:
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM sessoes_ativas
    WHERE token = %s
    """, (token,))

    conn.commit()
    liberar(conn)


def criar_usuario(
    usuario,
    senha,
    armazem_id,
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
        trocar_senha,
        armazem_id
    )
    VALUES (%s, %s, %s, %s, %s)
    """, (
        usuario,
        senha,
        tipo,
        1,
        armazem_id
    ))

    conn.commit()
    liberar(conn)

    listar_usuarios.clear()


@st.cache_data(ttl=30)
def listar_usuarios(armazem_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        usuario,
        tipo,
        ultimo_acesso
    FROM usuarios
    WHERE armazem_id = %s
    ORDER BY usuario
    """, (armazem_id,))

    usuarios = cursor.fetchall()

    liberar(conn)

    return usuarios


def atualizar_ultimo_acesso(usuario):

    # Esse "heartbeat" roda sozinho em segundo plano, a cada 120s,
    # para TODA sessão logada (ver render_status_footer no app.py).
    # Por isso precisa ser à prova de falha: se o UPDATE der erro
    # por qualquer instabilidade momentânea do banco, a conexão tem
    # que voltar pro pool mesmo assim (senão, rodando sem parar,
    # acaba vazando as conexões até esgotar o pool) — e o erro não
    # pode nunca derrubar a tela do usuário.

    conn = None

    try:

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE usuarios
        SET ultimo_acesso = CURRENT_TIMESTAMP
        WHERE usuario = %s
        """, (
            usuario,
        ))

        conn.commit()

        listar_usuarios.clear()

    except Exception:

        pass

    finally:

        if conn is not None:
            liberar(conn)


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


def excluir_usuario_por_id(uid):

    conn = conectar()
    cursor = conn.cursor()

    # Nunca permitir apagar o fundador, mesmo por id
    cursor.execute("""
    DELETE FROM usuarios
    WHERE id = %s
    AND usuario IS DISTINCT FROM %s
    """, (
        uid,
        USUARIO_FUNDADOR,
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


# ==================================================
# ARMAZÉNS (MULTI-TENANT)
# ==================================================

@st.cache_data(ttl=30)
def listar_armazens():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, nome
    FROM armazens
    ORDER BY nome ASC
    """)

    dados = cursor.fetchall()

    liberar(conn)

    return dados


def criar_armazem(nome):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO armazens (nome)
    VALUES (%s)
    RETURNING id
    """, (nome,))

    novo_id = cursor.fetchone()[0]

    for nome_rua in RUAS_PADRAO:

        cursor.execute(
            """
            INSERT INTO ruas (armazem_id, nome)
            VALUES (%s, %s)
            ON CONFLICT (armazem_id, nome) DO NOTHING
            """,
            (novo_id, nome_rua)
        )

    conn.commit()
    liberar(conn)

    listar_armazens.clear()
    listar_ruas.clear()

    return novo_id


def renomear_armazem(armazem_id, novo_nome):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE armazens
    SET nome = %s
    WHERE id = %s
    """, (novo_nome, armazem_id))

    conn.commit()
    liberar(conn)

    listar_armazens.clear()
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

import banco
import estilos


# =====================================================
# SAC AUTOMÁTICO
# =====================================================
# ANTES: a pessoa digitava no Administrativo a quantidade de
# reclamações do mês e a meta (tabela sac_historico).
#
# AGORA:
#   - RECLAMAÇÕES = número de cards (chamados) da Análise Técnica
#     abertos no mês (data de abertura). Entrou um card novo, o número
#     do mês sobe sozinho — sem digitar nada.
#   - META continua MANUAL, definida no Administrativo > SAC. Meses sem
#     meta própria herdam a última meta definida, então o mês novo já
#     começa com a meta anterior.
#
# Para não precisar mexer em todas as telas que já leem o SAC (Central
# SAC, cabeçalho do Administrativo etc.), este módulo SUBSTITUI, em
# tempo de execução, as três funções do banco.py que cuidam disso
# (ver ativar() no fim do arquivo). O resto do app continua chamando
# banco.ler_historico_sac(...) como sempre, e agora recebe os números
# automáticos.
#
# Histórico antigo: nos meses ANTERIORES ao atual que têm um número
# digitado à mão no passado, vale o MAIOR entre o digitado e a contagem
# dos cards — assim nada do que já foi lançado se perde, mesmo que a
# Análise Técnica daquele mês esteja incompleta. O mês atual é sempre
# 100% automático.

FUSO = ZoneInfo("America/Campo_Grande")

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]


def _mes_atual_texto():

    return datetime.now(FUSO).strftime("%Y-%m")


def _rotulo_mes(mes_ano):

    ano, mes = mes_ano.split("-")

    return f"{MESES_PT[int(mes) - 1]}/{ano}"


# -----------------------------------------------------
# LEITURA
# -----------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def _ler_linhas_manuais(armazem_id):
    """Linhas gravadas em sac_historico (meta e, no passado, reclamações)."""

    conn = banco.conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT mes_ano, reclamacoes, meta, atualizado_por, atualizado_em
        FROM sac_historico
        WHERE armazem_id = %s
        ORDER BY mes_ano ASC
        """, (armazem_id,))

        linhas = cursor.fetchall()

    finally:
        banco.liberar(conn)

    return linhas


def _contar_chamados_por_mes(armazem_id):

    contagem = Counter()

    for registro in banco.ler_analise_tecnica(armazem_id):

        data = registro.get("data_erro")

        if data:
            contagem[data.strftime("%Y-%m")] += 1

    return contagem


def ler_historico_sac(armazem_id):
    """
    Mesmo formato de banco.ler_historico_sac, em ordem cronológica:
    (mes_ano, reclamacoes, meta, atualizado_por, atualizado_em).
    """

    linhas = {
        linha[0]: linha for linha in _ler_linhas_manuais(armazem_id)
    }

    contagem = _contar_chamados_por_mes(armazem_id)

    atual = _mes_atual_texto()

    meses = sorted(set(linhas) | set(contagem) | {atual})

    resultado = []

    meta_corrente = 0

    for mes in meses:

        linha = linhas.get(mes)

        atualizado_por = None
        atualizado_em = None
        reclamacoes_manual = 0

        if linha:

            _, reclamacoes_manual, meta_linha, atualizado_por, atualizado_em = linha

            reclamacoes_manual = reclamacoes_manual or 0

            if meta_linha is not None:
                meta_corrente = meta_linha

        automatico = contagem.get(mes, 0)

        if mes < atual and linha and reclamacoes_manual > automatico:

            # Mês antigo, de antes da automação, com número digitado à mão
            # MAIOR que o dos cards: mantém o digitado (os cards daquele
            # mês podem não ter sido todos lançados na Análise Técnica).
            # Se os cards já passam do digitado, vale o automático.
            reclamacoes = reclamacoes_manual
            origem = atualizado_por

        else:

            reclamacoes = automatico
            origem = "Automático"

            if atualizado_por:
                origem = f"Automático · meta: {atualizado_por}"

        resultado.append((
            mes,
            reclamacoes,
            meta_corrente,
            origem,
            atualizado_em
        ))

    return resultado


def total_reclamacoes(armazem_id):

    return sum(linha[1] for linha in ler_historico_sac(armazem_id))


def resumo_mes_atual(armazem_id):
    """(mes_ano, reclamacoes automáticas, meta vigente) do mês atual."""

    mes, reclamacoes, meta, _, _ = ler_historico_sac(armazem_id)[-1]

    return mes, reclamacoes, meta


# -----------------------------------------------------
# GRAVAÇÃO (só a meta)
# -----------------------------------------------------

def atualizar_sac_mensal(
    reclamacoes,
    meta,
    armazem_id,
    usuario=None
):
    """
    Mantém a assinatura antiga (para qualquer tela que ainda a chame),
    mas grava SÓ a meta do mês atual: o número de reclamações vem dos
    cards da Análise Técnica e o valor recebido em `reclamacoes` é
    ignorado de propósito.
    """

    conn = banco.conectar()

    try:
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
        VALUES (%s, 0, %s, %s, CURRENT_TIMESTAMP, %s)

        ON CONFLICT (armazem_id, mes_ano)
        DO UPDATE SET
            meta = EXCLUDED.meta,
            atualizado_por = EXCLUDED.atualizado_por,
            atualizado_em = CURRENT_TIMESTAMP
        """, (
            _mes_atual_texto(),
            meta,
            usuario,
            armazem_id
        ))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:
        banco.liberar(conn)

    _ler_linhas_manuais.clear()


# O banco.py original expõe .clear() nessas funções (eram st.cache_data);
# outras partes do app podem chamá-lo, então mantemos o método.
ler_historico_sac.clear = lambda: _ler_linhas_manuais.clear()
total_reclamacoes.clear = lambda: _ler_linhas_manuais.clear()


# -----------------------------------------------------
# TELA: Administrativo > SAC (só a meta é digitada)
# -----------------------------------------------------

def render_formulario_meta(armazem_id, usuario):
    """
    Substitui o antigo formulário "Atualização Mensal do SAC". Deve ser
    chamado de dentro de um st.fragment (como o Administrativo já faz).
    """

    mes, reclamacoes, meta = resumo_mes_atual(armazem_id)

    st.subheader(
        "Meta Mensal do SAC"
    )

    st.caption(
        "As reclamações são contadas **automaticamente**: cada card novo na "
        "Análise Técnica soma 1 no mês da data de abertura do chamado. "
        "Só a meta é digitada aqui."
    )

    col_reclamacoes, col_meta = st.columns(2)

    with col_reclamacoes:

        st.metric(
            f"📢 Reclamações em {_rotulo_mes(mes)}",
            reclamacoes,
            help="Automático — vem dos cards da Análise Técnica."
        )

    with col_meta:

        st.metric(
            "🎯 Meta vigente",
            meta
        )

    with st.form(
        "form_sac_meta"
    ):

        nova_meta = st.number_input(
            f"Meta de {_rotulo_mes(mes)}",
            min_value=0,
            step=1,
            value=int(meta)
        )

        salvar = st.form_submit_button(
            "💾 Salvar meta"
        )

        if salvar:

            with estilos.mostrar_processando("meta do SAC..."):
                atualizar_sac_mensal(
                    0,
                    nova_meta,
                    armazem_id,
                    usuario=usuario
                )

            estilos.notificar_sucesso("Meta do SAC atualizada.")
            st.rerun(scope="fragment")


# -----------------------------------------------------
# ATIVAÇÃO
# -----------------------------------------------------

def ativar():
    """
    Faz o resto do app passar a usar o SAC automático. Seguro chamar a
    cada execução do app: só substitui uma vez.
    """

    if getattr(banco, "_sac_automatico_ativo", False):
        return

    banco.ler_historico_sac = ler_historico_sac
    banco.total_reclamacoes = total_reclamacoes
    banco.atualizar_sac_mensal = atualizar_sac_mensal
    banco._sac_automatico_ativo = True

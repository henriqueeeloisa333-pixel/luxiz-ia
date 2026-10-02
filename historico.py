import re
from datetime import timedelta

import pandas as pd
import streamlit as st

import banco
import estilos


# =====================================================
# CORES / COMPONENTES VISUAIS
# =====================================================

def _cor(pct):
    if pct is None:
        return "#64748b"
    if pct >= 80:
        return "#22c55e"
    if pct >= 50:
        return "#f59e0b"
    return "#ef4444"


def _anel(pct, titulo, icone, detalhe, tamanho=130):
    """Gráfico de anel (donut) feito em CSS — sem dependências."""

    cor = _cor(pct)
    valor = 0 if pct is None else max(0, min(100, pct))
    texto = "—" if pct is None else f"{round(pct)}%"

    st.markdown(
        f"""
        <div style="
            background:{cor}12;border:1px solid {cor}40;
            border-radius:1rem;padding:1rem .6rem;text-align:center;
        ">
            <div style="font-size:.85rem;font-weight:800;margin-bottom:.6rem;">
                {icone} {titulo}
            </div>
            <div style="position:relative;width:{tamanho}px;height:{tamanho}px;margin:0 auto;">
                <div style="
                    width:100%;height:100%;border-radius:50%;
                    background:conic-gradient({cor} {valor}%, {cor}22 0);
                    -webkit-mask:radial-gradient(farthest-side, transparent 62%, #000 63%);
                    mask:radial-gradient(farthest-side, transparent 62%, #000 63%);
                "></div>
                <div style="
                    position:absolute;inset:0;display:flex;
                    align-items:center;justify-content:center;
                    font-size:1.5rem;font-weight:800;color:{cor};
                ">{texto}</div>
            </div>
            <div style="font-size:.74rem;opacity:.75;margin-top:.6rem;min-height:2.2em;">
                {detalhe}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# COLETA DOS DADOS DA PESSOA
# =====================================================

def _eh_a_pessoa(nome, usuario_alvo, armazem_id):

    if not nome:
        return False

    return banco.pessoa_pertence_ao_usuario(nome, usuario_alvo, armazem_id)


def _dentro_do_periodo(data, limite):

    if limite is None or data is None:
        return True

    return data >= limite


def _coletar(usuario_alvo, armazem_id):

    # ---------------- SAC (cards no nome da pessoa) ----------------
    sac = [
        r for r in banco.ler_analise_tecnica(armazem_id)
        if any(
            _eh_a_pessoa(v.get("nome"), usuario_alvo, armazem_id)
            for v in (r.get("vinculos_notificados") or [])
        )
    ]

    # ---------------- AUDITORIA ----------------
    auditoria = [
        r for r in banco.ler_auditoria(armazem_id)
        if _eh_a_pessoa(r["nome"], usuario_alvo, armazem_id)
    ]

    # ---------------- EPI ----------------
    epis = [
        e for e in banco.ler_epis(armazem_id)
        if banco.epi_pertence_ao_usuario(e["nome"], usuario_alvo)
    ]

    # ---------------- DASHBOARD (ruas em que está na dupla) ----------------
    ruas_pessoa = []

    for rua, info in banco.ler_tudo(armazem_id).items():

        dupla = info.get("dupla") or ""
        nota = info.get("nota") or 0

        if nota <= 0 or not dupla:
            continue

        pedacos = re.split(r"\s+e\s+|[,/&+]", dupla)

        if any(_eh_a_pessoa(p.strip(), usuario_alvo, armazem_id) for p in pedacos):
            ruas_pessoa.append((rua, float(nota)))

    # ---------------- CHECKLIST (últimas 4 sextas) ----------------
    ultima_sexta = banco._sexta_feira_mais_recente()
    sextas = [ultima_sexta - timedelta(days=7 * i) for i in range(4)]

    def _feito(item, registros, sexta):
        return any(
            r["data_checklist"] == sexta
            and str(r["numero"]).strip() == str(item["numero"]).strip()
            for r in registros
        )

    reg_hid = banco.ler_checklist_hidraulicos(armazem_id)
    reg_car = banco.ler_checklist_carrinhos(armazem_id)

    meus_hid = [
        i for i in banco.ler_responsaveis_hidraulicos(armazem_id)
        if _eh_a_pessoa(i["nome"], usuario_alvo, armazem_id)
    ]
    meus_car = [
        i for i in banco.ler_responsaveis_carrinhos(armazem_id)
        if _eh_a_pessoa(i["nome"], usuario_alvo, armazem_id)
    ]

    checklist_total = (len(meus_hid) + len(meus_car)) * len(sextas)
    checklist_feitos = 0

    for sexta in sextas:
        checklist_feitos += sum(1 for i in meus_hid if _feito(i, reg_hid, sexta))
        checklist_feitos += sum(1 for i in meus_car if _feito(i, reg_car, sexta))

    return {
        "sac": sac,
        "auditoria": auditoria,
        "epis": epis,
        "ruas": ruas_pessoa,
        "checklist_total": checklist_total,
        "checklist_feitos": checklist_feitos,
    }


# =====================================================
# PONTUAÇÃO POR MÓDULO
# =====================================================

def _pontuar(dados, limite):

    sac = [r for r in dados["sac"] if _dentro_do_periodo(r["data_erro"], limite)]
    aud = [r for r in dados["auditoria"] if _dentro_do_periodo(r["data_atividade"], limite)]
    epis = [e for e in dados["epis"] if _dentro_do_periodo(e["data"], limite)]

    resultado = {}

    # SAC: sem cards = 100%; cada card tira 25 pontos
    resultado["sac"] = {
        "pct": max(0, 100 - 25 * len(sac)),
        "detalhe": (
            "Nenhuma ocorrência 🎉" if not sac
            else f"{len(sac)} ocorrência(s) no período"
        ),
    }

    # Dashboard
    if dados["ruas"]:
        media = sum(n for _, n in dados["ruas"]) / len(dados["ruas"])
        resultado["dashboard"] = {
            "pct": media / 5 * 100,
            "detalhe": f"Média {media:.1f}/5 em {len(dados['ruas'])} rua(s)",
        }
    else:
        resultado["dashboard"] = {"pct": None, "detalhe": "Sem rua vinculada ao seu nome"}

    # Checklist
    if dados["checklist_total"]:
        pct = dados["checklist_feitos"] / dados["checklist_total"] * 100
        resultado["checklist"] = {
            "pct": pct,
            "detalhe": f"{dados['checklist_feitos']} de {dados['checklist_total']} preenchidos (4 últimas sextas)",
        }
    else:
        resultado["checklist"] = {"pct": None, "detalhe": "Sem equipamento sob sua responsabilidade"}

    # Auditoria
    acertos = sum(r["qtd_acertos"] or 0 for r in aud)
    erros = sum(r["qtd_erros"] or 0 for r in aud)

    if acertos + erros > 0:
        resultado["auditoria"] = {
            "pct": acertos / (acertos + erros) * 100,
            "detalhe": f"{len(aud)} auditoria(s) no período",
        }
    else:
        resultado["auditoria"] = {"pct": None, "detalhe": "Sem auditorias no período"}

    # EPI
    if epis:
        assinados = sum(1 for e in epis if e["assinatura"])
        resultado["epi"] = {
            "pct": assinados / len(epis) * 100,
            "detalhe": f"{assinados} de {len(epis)} assinado(s)",
        }
    else:
        resultado["epi"] = {"pct": None, "detalhe": "Nenhum EPI registrado"}

    return resultado, sac, aud, epis


def _evolucao_mensal(dados, hoje):
    """Pontos de atenção por mês (últimos 6) para o gráfico de barras."""

    meses = []
    ano, mes = hoje.year, hoje.month

    for _ in range(6):
        meses.append(f"{ano}-{mes:02d}")
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1

    meses.reverse()

    tabela = pd.DataFrame(
        0, index=meses, columns=["SAC", "Auditoria", "EPI pendente"]
    )

    for r in dados["sac"]:
        chave = r["data_erro"].strftime("%Y-%m")
        if chave in tabela.index:
            tabela.loc[chave, "SAC"] += 1

    for r in dados["auditoria"]:
        chave = r["data_atividade"].strftime("%Y-%m")
        if chave in tabela.index:
            tabela.loc[chave, "Auditoria"] += int(r["qtd_erros"] or 0)

    for e in dados["epis"]:
        if e["assinatura"]:
            continue
        chave = e["data"].strftime("%Y-%m")
        if chave in tabela.index:
            tabela.loc[chave, "EPI pendente"] += 1

    return tabela


# =====================================================
# TELA
# =====================================================

def render():

    estilos.exibir_notificacao_pendente()

    usuario_logado = st.session_state.get("usuario", "")

    armazem_id = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    admin_master = (
        usuario_logado.startswith("Fundador.")
        or usuario_logado.startswith("Gestao.")
    )

    estilos.cabecalho_pagina(
        "📈",
        "Histórico Produtivo",
        "Veja como está o seu empenho dentro do Luxiz IA",
        cor="#14b8a6"
    )

    usuario_alvo = usuario_logado

    col_filtro1, col_filtro2 = st.columns([2, 1])

    with col_filtro1:

        if admin_master:

            usuarios = [
                u[1] for u in banco.listar_usuarios(armazem_id) if u[1]
            ]

            if usuario_logado not in usuarios:
                usuarios.insert(0, usuario_logado)

            usuario_alvo = st.selectbox(
                "👤 Ver o histórico de:",
                usuarios,
                index=usuarios.index(usuario_logado),
                key="historico_pessoa"
            )

    with col_filtro2:

        periodo = st.radio(
            "Período",
            ["30 dias", "90 dias", "Tudo"],
            index=1,
            horizontal=True,
            key="historico_periodo"
        )

    hoje = estilos.agora_local().date()

    limite = {
        "30 dias": hoje - timedelta(days=30),
        "90 dias": hoje - timedelta(days=90),
        "Tudo": None,
    }[periodo]

    dados = _coletar(usuario_alvo, armazem_id)

    pontuacao, sac, aud, epis = _pontuar(dados, limite)

    st.divider()

    # ------------- NOTA GERAL + ANÉIS POR MÓDULO -------------

    pcts = [m["pct"] for m in pontuacao.values() if m["pct"] is not None]
    geral = sum(pcts) / len(pcts) if pcts else None

    col_geral, col_modulos = st.columns([1, 4])

    with col_geral:
        _anel(geral, "Nota geral", "🏆", "Média dos módulos com dados", tamanho=160)

    with col_modulos:

        cols = st.columns(5)

        itens = [
            ("sac", "SAC", "😊"),
            ("dashboard", "Dashboard", "📊"),
            ("checklist", "Checklist", "✅"),
            ("auditoria", "Auditoria", "🎯"),
            ("epi", "EPI", "🦺"),
        ]

        for col, (chave, nome, icone) in zip(cols, itens):
            with col:
                _anel(
                    pontuacao[chave]["pct"], nome, icone,
                    pontuacao[chave]["detalhe"]
                )

    st.divider()

    # ------------- O QUE MELHORAR -------------

    st.subheader("🎯 O que você precisa melhorar")

    pontos = []

    if len(sac):
        pontos.append(f"😊 **SAC** — {len(sac)} ocorrência(s) com o seu nome no período.")

    p = pontuacao["dashboard"]["pct"]
    if p is not None and p < 80:
        pontos.append(f"📊 **Dashboard** — {pontuacao['dashboard']['detalhe']}.")

    p = pontuacao["checklist"]["pct"]
    if p is not None and p < 100:
        faltam = dados["checklist_total"] - dados["checklist_feitos"]
        pontos.append(f"✅ **Checklist** — {faltam} preenchimento(s) pendente(s) nas últimas 4 sextas.")

    p = pontuacao["auditoria"]["pct"]
    if p is not None and p < 80:
        pontos.append(f"🎯 **Auditoria** — aproveitamento de {round(p)}%.")

    pendentes_epi = [e for e in epis if not e["assinatura"]]
    if pendentes_epi:
        pontos.append(f"🦺 **EPI** — {len(pendentes_epi)} item(ns) aguardando a sua assinatura.")

    if not pontos:
        st.success("Tudo em dia! Nenhum ponto de atenção no período. 👏")
    else:
        for ponto in pontos:
            st.warning(ponto)

    st.divider()

    # ------------- EVOLUÇÃO MENSAL -------------

    st.subheader("📅 Pontos de atenção por mês")

    st.caption("Quanto menor, melhor. Barras vazias significam um mês saudável.")

    evolucao = _evolucao_mensal(dados, hoje)

    if evolucao.values.sum() == 0:
        st.success("Nenhum ponto de atenção nos últimos 6 meses. 🌟")
    else:
        st.bar_chart(evolucao)

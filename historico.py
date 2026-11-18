import html
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

    # SAC: sem cards = 100%; cada card reduz 25% do que sobrou
    # (1 card = 75%, 3 = 42%, 7 = 13%) — nunca zera de vez
    resultado["sac"] = {
        "pct": 100 * (0.75 ** len(sac)),
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


def _nota_geral(pontuacao):

    pcts = [m["pct"] for m in pontuacao.values() if m["pct"] is not None]

    return sum(pcts) / len(pcts) if pcts else None


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
# RANKING DA EQUIPE (Fundador / Gestão)
# =====================================================

# Perfis administrativos/painel não entram no ranking operacional.
PREFIXOS_FORA_DO_RANKING = ("Fundador.", "Gestao.", "Painel.")

ROTULOS_FUNCAO = {
    "Separador.": "📦 Separador",
    "Conferente.": "🔎 Conferente",
    "Recebimento.": "📥 Recebimento",
    "Empilhador.": "🏗️ Empilhador",
    "Assistente.": "🧑‍💼 Assistente Logístico",
}

# Módulos que aparecem em cada cartão: (coluna, rótulo, ícone)
MODULOS_RANKING = [
    ("SAC", "SAC", "😊"),
    ("Dashboard", "Dashboard", "📊"),
    ("Checklist", "Checklist", "✅"),
    ("Auditoria", "Auditoria", "🎯"),
    ("EPI", "EPI", "🦺"),
]

MEDALHAS_RANKING = {1: "🥇", 2: "🥈", 3: "🥉"}
CORES_PODIO = {1: "#f59e0b", 2: "#94a3b8", 3: "#f97316"}

COLUNAS_RANKING = [
    "Pessoa", "Função", "Geral", "SAC", "Dashboard",
    "Checklist", "Auditoria", "EPI", "Usuario"
]


def _rotulo_funcao(usuario):

    for prefixo, rotulo in ROTULOS_FUNCAO.items():
        if usuario.startswith(prefixo):
            return rotulo

    return "👤 Usuário"


def _nome_para_exibir(usuario):

    perfil = banco.ler_perfil(usuario)

    if perfil:
        return banco.nome_completo_perfil(perfil)

    if "." in usuario:
        return usuario.split(".", 1)[1].strip().title()

    return usuario


@st.cache_data(ttl=60, show_spinner=False)
def _montar_ranking(armazem_id, dias):

    hoje = estilos.agora_local().date()
    limite = (hoje - timedelta(days=dias)) if dias else None

    linhas = []

    for usuario in [u[1] for u in banco.listar_usuarios(armazem_id) if u[1]]:

        if usuario.startswith(PREFIXOS_FORA_DO_RANKING):
            continue

        dados = _coletar(usuario, armazem_id)
        pontuacao, _, _, _ = _pontuar(dados, limite)

        linhas.append({
            "Pessoa": _nome_para_exibir(usuario),
            "Função": _rotulo_funcao(usuario),
            "Geral": _nota_geral(pontuacao),
            "SAC": pontuacao["sac"]["pct"],
            "Dashboard": pontuacao["dashboard"]["pct"],
            "Checklist": pontuacao["checklist"]["pct"],
            "Auditoria": pontuacao["auditoria"]["pct"],
            "EPI": pontuacao["epi"]["pct"],
            "Usuario": usuario,
        })

    return pd.DataFrame(linhas, columns=COLUNAS_RANKING)


_CSS_RANKING = """
<style>

/* ---------- nota explicativa ---------- */
.hp-nota{
    display:flex;
    gap:.75rem;
    align-items:flex-start;
    margin:.4rem 0 1rem 0;
    padding:.75rem 1rem;
    border-radius:.9rem;
    background:rgba(20,184,166,.08);
    border:1px solid rgba(20,184,166,.25);
    border-left:4px solid #14b8a6;
    font-size:.86rem;
    line-height:1.5;
}
.hp-nota-ico{ flex-shrink:0; font-size:1.1rem; line-height:1.4; }

/* ---------- título de seção ---------- */
.hp-secao{
    display:flex;
    align-items:center;
    gap:.8rem;
    margin:1.6rem 0 .8rem 0;
}
.hp-secao span{
    font-size:.74rem;
    font-weight:800;
    letter-spacing:1.6px;
    text-transform:uppercase;
    opacity:.7;
    white-space:nowrap;
}
.hp-secao i{
    flex:1;
    height:1px;
    background:rgba(148,163,184,.28);
}

/* ---------- cartão de cada pessoa ---------- */
.hp-card{
    border-radius:1.1rem;
    padding:.95rem 1.15rem 1rem 1.15rem;
    margin-bottom:.65rem;
    transition:transform .15s ease, box-shadow .15s ease;
}
.hp-card:hover{
    transform:translateY(-1px);
    box-shadow:0 8px 22px rgba(0,0,0,.18);
}
.hp-topo{
    display:grid;
    grid-template-columns:46px 46px minmax(0,1fr) auto;
    align-items:center;
    gap:.85rem;
}
.hp-pos{
    text-align:center;
    font-weight:800;
    font-size:1.05rem;
    opacity:.8;
}
.hp-pos.hp-medalha{
    font-size:1.7rem;
    opacity:1;
}
.hp-nome{
    font-weight:800;
    font-size:1rem;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
}
.hp-funcao{
    font-size:.76rem;
    opacity:.65;
    margin-top:.1rem;
}
.hp-nota-geral{
    text-align:right;
    line-height:1.1;
}
.hp-nota-geral b{
    display:block;
    font-size:1.6rem;
    font-weight:800;
}
.hp-nota-geral small{
    font-size:.66rem;
    font-weight:700;
    letter-spacing:1px;
    text-transform:uppercase;
    opacity:.6;
}
.hp-barra{
    height:8px;
    border-radius:999px;
    margin:.8rem 0 .85rem 0;
    overflow:hidden;
}
.hp-barra div{
    height:100%;
    border-radius:999px;
}
.hp-modulos{
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(118px, 1fr));
    gap:.7rem;
}
.hp-mod-topo{
    display:flex;
    justify-content:space-between;
    align-items:center;
    font-size:.72rem;
    font-weight:700;
    margin-bottom:.3rem;
}
.hp-mod-topo span:first-child{ opacity:.75; }
.hp-mini{
    height:5px;
    border-radius:999px;
    overflow:hidden;
}
.hp-mini div{
    height:100%;
    border-radius:999px;
}

/* ---------- pódio ---------- */
.hp-podio{
    text-align:center;
    border-radius:1.2rem;
    padding:1.3rem .9rem 1.2rem .9rem;
}
.hp-podio-medalha{ font-size:2.6rem; line-height:1; }
.hp-podio-nome{
    font-weight:800;
    font-size:1.02rem;
    margin-top:.55rem;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
}
.hp-podio-funcao{ font-size:.75rem; opacity:.65; margin-top:.1rem; }
.hp-podio-nota{
    font-size:2.2rem;
    font-weight:800;
    line-height:1.1;
    margin-top:.5rem;
}

/* ---------- pessoas que precisam de apoio ---------- */
.hp-apoio{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
    flex-wrap:wrap;
    padding:.8rem 1.1rem;
    margin-bottom:.55rem;
    border-radius:1rem;
    background:rgba(239,68,68,.08);
    border:1px solid rgba(239,68,68,.3);
    border-left:4px solid #ef4444;
}
.hp-apoio-nome{ font-weight:800; font-size:.95rem; }
.hp-apoio-sub{ font-size:.76rem; opacity:.7; margin-top:.1rem; }
.hp-chip{
    display:inline-block;
    padding:.18rem .65rem;
    margin:.1rem .25rem .1rem 0;
    border-radius:999px;
    font-size:.74rem;
    font-weight:800;
    background:rgba(239,68,68,.14);
    color:#ef4444;
    border:1px solid rgba(239,68,68,.4);
    white-space:nowrap;
}

@media (max-width: 760px){
    .hp-topo{ grid-template-columns:34px 40px minmax(0,1fr) auto; gap:.55rem; }
}

</style>
"""


def _vazio(valor):

    return valor is None or pd.isna(valor)


def _pct_ou_none(valor):

    return None if _vazio(valor) else float(valor)


def _avatar_ranking(nome, foto, tamanho=44):

    if foto:

        return (
            f'<img src="{foto}" style="width:{tamanho}px;height:{tamanho}px;'
            'border-radius:50%;object-fit:cover;flex-shrink:0;">'
        )

    iniciais = "".join(p[0].upper() for p in nome.split()[:2]) or "?"

    return (
        f'<div style="width:{tamanho}px;height:{tamanho}px;border-radius:50%;'
        'flex-shrink:0;background:linear-gradient(135deg,#14b8a6,#6366f1);'
        'display:flex;align-items:center;justify-content:center;color:white;'
        f'font-weight:800;font-size:{max(tamanho * 0.32, 11):.0f}px;">'
        f'{html.escape(iniciais)}</div>'
    )


def _kpi_ranking(icone, rotulo, valor, cor):

    return (
        f'<div style="display:flex;align-items:center;gap:.9rem;'
        f'background:{cor}12;border:1px solid {cor}33;border-left:4px solid {cor};'
        'border-radius:1rem;padding:.85rem 1.05rem;min-height:84px;">'
        f'<div style="flex-shrink:0;width:46px;height:46px;border-radius:13px;'
        f'background:{cor}22;display:flex;align-items:center;justify-content:center;'
        f'font-size:1.4rem;">{icone}</div>'
        '<div style="min-width:0;">'
        f'<div style="font-size:1.55rem;font-weight:800;color:{cor};line-height:1.1;">{valor}</div>'
        f'<div style="font-size:.76rem;opacity:.72;margin-top:.2rem;">{rotulo}</div>'
        '</div>'
        '</div>'
    )


def _titulo_secao_ranking(texto):

    st.markdown(
        f'<div class="hp-secao"><span>{texto}</span><i></i></div>',
        unsafe_allow_html=True
    )


def _card_podio(posicao, linha, foto):

    cor = CORES_PODIO[posicao]
    nome = linha["Pessoa"]

    return (
        f'<div class="hp-podio" style="background:linear-gradient(180deg,{cor}1f,{cor}0a);'
        f'border:1px solid {cor}55;'
        f'{"box-shadow:0 14px 34px " + cor + "33;" if posicao == 1 else ""}">'
        f'<div class="hp-podio-medalha">{MEDALHAS_RANKING[posicao]}</div>'
        f'<div style="display:flex;justify-content:center;margin-top:.7rem;">'
        f'<div style="border:3px solid {cor};border-radius:50%;line-height:0;">'
        f'{_avatar_ranking(nome, foto, 64)}</div></div>'
        f'<div class="hp-podio-nome">{html.escape(nome)}</div>'
        f'<div class="hp-podio-funcao">{html.escape(linha["Função"])}</div>'
        f'<div class="hp-podio-nota" style="color:{cor};">{round(linha["Geral"])}%</div>'
        '</div>'
    )


def _card_pessoa(posicao, linha, foto):

    geral = _pct_ou_none(linha["Geral"])
    cor = _cor(geral)

    nome = linha["Pessoa"]

    if geral is not None and posicao in MEDALHAS_RANKING:
        selo = f'<div class="hp-pos hp-medalha">{MEDALHAS_RANKING[posicao]}</div>'
    else:
        selo = f'<div class="hp-pos">{posicao}º</div>'

    if geral is None:
        nota_html = (
            '<div class="hp-nota-geral"><b style="color:#64748b;">—</b>'
            '<small>Sem nota</small></div>'
        )
        barra = ""
    else:
        nota_html = (
            f'<div class="hp-nota-geral"><b style="color:{cor};">{round(geral)}%</b>'
            '<small>Nota geral</small></div>'
        )
        barra = (
            f'<div class="hp-barra" style="background:{cor}22;">'
            f'<div style="width:{max(0, min(100, geral)):.0f}%;background:{cor};"></div>'
            '</div>'
        )

    modulos = []

    for chave, rotulo, icone in MODULOS_RANKING:

        valor = _pct_ou_none(linha[chave])
        cor_mod = _cor(valor)
        texto = "—" if valor is None else f"{round(valor)}%"
        largura = 0 if valor is None else max(0, min(100, valor))

        modulos.append(
            '<div>'
            '<div class="hp-mod-topo">'
            f'<span>{icone} {rotulo}</span>'
            f'<span style="color:{cor_mod};">{texto}</span>'
            '</div>'
            f'<div class="hp-mini" style="background:{cor_mod}22;">'
            f'<div style="width:{largura:.0f}%;background:{cor_mod};"></div>'
            '</div>'
            '</div>'
        )

    return (
        f'<div class="hp-card" style="background:{cor}0c;border:1px solid {cor}33;'
        f'border-left:4px solid {cor};">'
        '<div class="hp-topo">'
        f'{selo}'
        f'{_avatar_ranking(nome, foto, 44)}'
        '<div style="min-width:0;">'
        f'<div class="hp-nome">{html.escape(nome)}</div>'
        f'<div class="hp-funcao">{html.escape(linha["Função"])}</div>'
        '</div>'
        f'{nota_html}'
        '</div>'
        f'{barra}'
        f'<div class="hp-modulos">{"".join(modulos)}</div>'
        '</div>'
    )


def _render_ranking(armazem_id, dias):

    st.markdown(_CSS_RANKING, unsafe_allow_html=True)

    st.markdown(
        '<div class="hp-nota">'
        '<div class="hp-nota-ico">🏅</div>'
        '<div>Ranking ordenado da <b>nota geral</b> mais alta para a mais baixa. '
        'A nota geral é a média dos módulos que a pessoa tem dados. Quem não '
        'tem dados em nenhum módulo aparece no final, sem nota.</div>'
        '</div>',
        unsafe_allow_html=True
    )

    with estilos.mostrar_processando("calculando ranking..."):
        tabela = _montar_ranking(armazem_id, dias)

    if tabela.empty:
        st.info("Nenhum usuário operacional cadastrado ainda.")
        return

    com_nota = tabela[tabela["Geral"].notna()].sort_values(
        ["Geral", "Pessoa"], ascending=[False, True]
    )
    sem_nota = tabela[tabela["Geral"].isna()].sort_values("Pessoa")

    ordenada = pd.concat([com_nota, sem_nota], ignore_index=True)
    ordenada.insert(0, "Posição", range(1, len(ordenada) + 1))

    fotos = {
        perfil["usuario"]: perfil.get("foto")
        for perfil in banco.ler_perfis(armazem_id)
    }

    # ------------- resumo -------------

    total = len(tabela)
    saudaveis = int((com_nota["Geral"] >= 80).sum())
    atencao = int(((com_nota["Geral"] >= 50) & (com_nota["Geral"] < 80)).sum())
    criticos = int((com_nota["Geral"] < 50).sum())

    kpis = [
        _kpi_ranking("👥", "Pessoas no ranking", str(total), "#3b82f6"),
        _kpi_ranking("🟢", "Saudáveis (80%+)", str(saudaveis), "#22c55e"),
        _kpi_ranking("🟡", "Em atenção (50–79%)", str(atencao), "#f59e0b"),
        _kpi_ranking("🔴", "Precisam de apoio", str(criticos), "#ef4444"),
    ]

    for coluna, kpi in zip(st.columns(4), kpis):

        with coluna:
            st.markdown(kpi, unsafe_allow_html=True)

    # ------------- pódio -------------

    if len(com_nota) >= 3:

        _titulo_secao_ranking("🏆 Destaques da equipe")

        podio = [ordenada.iloc[i] for i in range(3)]

        # 2º · 1º · 3º, com o 1º lugar no centro
        colunas_podio = st.columns(3)

        for coluna, posicao in zip(colunas_podio, (2, 1, 3)):

            linha = podio[posicao - 1]

            with coluna:

                st.markdown(
                    f'<div style="margin-top:{"0" if posicao == 1 else "1.8rem"};">'
                    f'{_card_podio(posicao, linha, fotos.get(linha["Usuario"]))}'
                    '</div>',
                    unsafe_allow_html=True
                )

    # ------------- filtros -------------

    _titulo_secao_ranking("📋 Classificação completa")

    col_busca, col_funcao = st.columns([2, 1])

    with col_busca:
        busca = st.text_input(
            "Buscar pessoa",
            placeholder="Digite um nome...",
            key="hist_rank_busca"
        )

    with col_funcao:
        funcoes = sorted(ordenada["Função"].unique())
        funcao_escolhida = st.selectbox(
            "Função",
            ["Todas"] + funcoes,
            key="hist_rank_funcao"
        )

    visiveis = ordenada

    if busca.strip():
        visiveis = visiveis[
            visiveis["Pessoa"].str.contains(busca.strip(), case=False, na=False)
        ]

    if funcao_escolhida != "Todas":
        visiveis = visiveis[visiveis["Função"] == funcao_escolhida]

    if visiveis.empty:

        st.info("Nenhuma pessoa encontrada com esse filtro.")

    else:

        st.markdown(
            "".join(
                _card_pessoa(
                    int(linha["Posição"]),
                    linha,
                    fotos.get(linha["Usuario"])
                )
                for _, linha in visiveis.iterrows()
            ),
            unsafe_allow_html=True
        )

    # ------------- quem precisa de atenção -------------

    precisam = com_nota[com_nota["Geral"] < 50]

    if not precisam.empty:

        _titulo_secao_ranking("🔴 Pessoas que precisam de apoio")

        blocos = []

        for _, linha in precisam.sort_values("Geral").iterrows():

            fracos = [
                rotulo for chave, rotulo, _ in MODULOS_RANKING
                if pd.notna(linha[chave]) and linha[chave] < 80
            ]

            chips = "".join(
                f'<span class="hp-chip">{html.escape(f)}</span>' for f in fracos
            ) or "—"

            blocos.append(
                '<div class="hp-apoio">'
                '<div>'
                f'<div class="hp-apoio-nome">{html.escape(linha["Pessoa"])}</div>'
                f'<div class="hp-apoio-sub">{html.escape(linha["Função"])} · '
                f'nota geral {round(linha["Geral"])}%</div>'
                '</div>'
                f'<div><span style="font-size:.72rem;opacity:.7;margin-right:.4rem;">'
                f'Pontos de atenção:</span>{chips}</div>'
                '</div>'
            )

        st.markdown("".join(blocos), unsafe_allow_html=True)

    # ------------- tabela detalhada (para consulta e exportação) -------------

    st.write("")

    with st.expander("📑 Tabela detalhada por módulo"):

        config_barra = st.column_config.ProgressColumn(
            min_value=0, max_value=100, format="%d%%"
        )

        tabela_exibida = ordenada.drop(columns=["Usuario"])

        st.dataframe(
            tabela_exibida,
            hide_index=True,
            width="stretch",
            column_config={
                "Geral": config_barra,
                "SAC": config_barra,
                "Dashboard": config_barra,
                "Checklist": config_barra,
                "Auditoria": config_barra,
                "EPI": config_barra,
            }
        )

        st.download_button(
            "📥 Baixar ranking (CSV)",
            data=tabela_exibida.to_csv(index=False).encode("utf-8-sig"),
            file_name="ranking_equipe.csv",
            mime="text/csv",
            key="hist_rank_download"
        )


# =====================================================
# VISÃO INDIVIDUAL
# =====================================================

def _render_pessoa(usuario_alvo, armazem_id, limite, hoje):

    dados = _coletar(usuario_alvo, armazem_id)

    pontuacao, sac, aud, epis = _pontuar(dados, limite)

    st.divider()

    # ------------- NOTA GERAL + ANÉIS POR MÓDULO -------------

    geral = _nota_geral(pontuacao)

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

    st.subheader("🎯 O que precisa melhorar")

    pontos = []

    if len(sac):
        pontos.append(f"😊 **SAC** — {len(sac)} ocorrência(s) com o nome no período.")

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
        pontos.append(f"🦺 **EPI** — {len(pendentes_epi)} item(ns) aguardando assinatura.")

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


# =====================================================
# TELA
# =====================================================

# Perfis que enxergam SOMENTE o próprio histórico. Todos os demais
# (Fundador, Gestao, Painel, nome.nome etc.) veem o histórico de
# qualquer pessoa e o ranking da equipe. Para restringir mais algum
# perfil (ex.: "Empilhador."), basta incluir o prefixo aqui.
PREFIXOS_APENAS_PROPRIO = ("Separador.", "Conferente.", "Recebimento.")


def render():

    estilos.exibir_notificacao_pendente()

    usuario_logado = st.session_state.get("usuario", "")

    armazem_id = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    ve_tudo = not usuario_logado.startswith(PREFIXOS_APENAS_PROPRIO)

    estilos.cabecalho_pagina(
        "📈",
        "Histórico Produtivo",
        "Veja como está o empenho dentro do Luxiz IA",
        cor="#14b8a6"
    )

    periodo = st.radio(
        "Período",
        ["30 dias", "90 dias", "Tudo"],
        index=1,
        horizontal=True,
        key="historico_periodo"
    )

    dias = {"30 dias": 30, "90 dias": 90, "Tudo": None}[periodo]

    hoje = estilos.agora_local().date()

    limite = (hoje - timedelta(days=dias)) if dias else None

    if not ve_tudo:

        _render_pessoa(usuario_logado, armazem_id, limite, hoje)
        return

    aba_pessoa, aba_ranking = st.tabs(
        ["👤 Meu histórico", "🏅 Ranking da equipe"]
    )

    with aba_pessoa:

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

        _render_pessoa(usuario_alvo, armazem_id, limite, hoje)

    with aba_ranking:

        _render_ranking(armazem_id, dias)

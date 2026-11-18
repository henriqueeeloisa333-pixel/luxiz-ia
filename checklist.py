import html
import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import banco
import estilos


MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

# Dia da semana em que o checklist de Hidráulicos e Carrinhos deve ser
# feito (0=Segunda ... 4=Sexta). Mesma regra do alerta da sexta-feira
# que já existe em banco.listar_pendentes_checklist_sexta.
DIA_PREVISTO_CHECKLIST = 4

# O controle de "não preenchido" só vale a partir de outubro/2026.
# Sextas-feiras anteriores a esta data nunca contam como negativo.
DATA_INICIO_CONTROLE = date(2026, 10, 1)

COR_TOTAL = "#6366f1"
COR_CONFORME = "#22c55e"
COR_NAO_CONFORME = "#f59e0b"
COR_PENDENTE = "#ef4444"


# =====================================================
# VISUAL (CSS da aba, claro e escuro)
# =====================================================

def _css_checklist(tema):

    if tema == "claro":
        v = {
            "__INPUT_BG__": "#ffffff",
            "__INPUT_BORDER__": "rgba(15,23,42,.16)",
            "__FORM_BG__": "rgba(99,102,241,.05)",
            "__FORM_BORDER__": "rgba(99,102,241,.25)",
            "__TAB_BG__": "rgba(15,23,42,.05)",
            "__TAB_TXT__": "#334155",
            "__MUTED__": "#64748b",
        }
    else:
        v = {
            "__INPUT_BG__": "#0f1a30",
            "__INPUT_BORDER__": "rgba(148,163,184,.25)",
            "__FORM_BG__": "rgba(99,102,241,.07)",
            "__FORM_BORDER__": "rgba(129,140,248,.28)",
            "__TAB_BG__": "rgba(255,255,255,.05)",
            "__TAB_TXT__": "#cbd5e1",
            "__MUTED__": "#94a3b8",
        }

    css = """
    <style>

    /* iframes de altura zero (scripts de rede/tema) não ocupam espaço */
    iframe[height="0"]{ display:none !important; }
    .stElementContainer:has(> iframe[height="0"]){ display:none !important; }

    /* ---------- abas em formato de pílula ---------- */
    div.stTabs [data-baseweb="tab-list"]{
        gap:.5rem;
        border-bottom:none !important;
        padding-bottom:.3rem;
    }
    div.stTabs [data-baseweb="tab-highlight"],
    div.stTabs [data-baseweb="tab-border"]{
        display:none !important;
    }
    div.stTabs button[data-baseweb="tab"]{
        height:auto;
        padding:.5rem 1.15rem;
        border-radius:999px;
        background:__TAB_BG__;
        border:1px solid transparent;
        transition:background .2s ease, transform .15s ease;
    }
    div.stTabs button[data-baseweb="tab"] p{
        font-size:.9rem;
        font-weight:700;
        color:__TAB_TXT__;
    }
    div.stTabs button[data-baseweb="tab"]:hover{
        transform:translateY(-1px);
    }
    div.stTabs button[data-baseweb="tab"][aria-selected="true"]{
        background:linear-gradient(135deg,#a855f7,#6366f1) !important;
        box-shadow:0 6px 16px rgba(99,102,241,.35);
    }
    div.stTabs button[data-baseweb="tab"][aria-selected="true"] p{
        color:#ffffff !important;
    }

    /* ---------- formulário em cartão ---------- */
    div[data-testid="stForm"]{
        border-radius:1.1rem !important;
        border:1px solid __FORM_BORDER__ !important;
        background:__FORM_BG__;
        padding:1.1rem 1.2rem .9rem 1.2rem !important;
    }
    div[data-testid="stForm"] label p{
        font-size:.78rem !important;
        font-weight:700 !important;
        letter-spacing:.3px;
        color:__MUTED__ !important;
    }
    div[data-testid="stForm"] div[data-baseweb="input"],
    div[data-testid="stForm"] div[data-baseweb="textarea"],
    div[data-testid="stForm"] div[data-baseweb="select"] > div{
        background:__INPUT_BG__ !important;
        border:1px solid __INPUT_BORDER__ !important;
        border-radius:11px !important;
    }
    div[data-testid="stForm"] div[data-baseweb="input"] > div,
    div[data-testid="stForm"] div[data-baseweb="textarea"] > div,
    div[data-testid="stForm"] textarea{
        background:transparent !important;
        border-color:transparent !important;
    }
    div[data-testid="stForm"] div[data-baseweb="input"]:focus-within,
    div[data-testid="stForm"] div[data-baseweb="textarea"]:focus-within{
        border-color:#818cf8 !important;
        box-shadow:0 0 0 3px rgba(129,140,248,.18) !important;
    }
    div[data-testid="stForm"] button[kind="secondaryFormSubmit"],
    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button{
        height:44px;
        border:none !important;
        border-radius:12px !important;
        color:#ffffff !important;
        font-weight:700 !important;
        background:linear-gradient(135deg,#a855f7,#6366f1) !important;
        box-shadow:0 8px 20px rgba(99,102,241,.32);
    }

    /* ---------- títulos de seção ---------- */
    .lxc-secao{
        display:flex;
        align-items:center;
        gap:.6rem;
        margin:1.3rem 0 .6rem 0;
    }
    .lxc-secao-barra{
        width:5px;
        height:22px;
        border-radius:999px;
        background:linear-gradient(180deg,#a855f7,#6366f1);
    }
    .lxc-secao-titulo{
        font-size:1.05rem;
        font-weight:800;
        letter-spacing:.2px;
    }
    .lxc-secao-sub{
        font-size:.78rem;
        color:__MUTED__;
        margin-left:.2rem;
    }

    /* ---------- cartões de indicadores ---------- */
    .lxc-kpis{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        gap:.8rem;
        margin:.3rem 0 .9rem 0;
    }
    .lxc-kpi{
        position:relative;
        overflow:hidden;
        border-radius:1rem;
        padding:.85rem 1rem;
    }
    .lxc-kpi-topo{
        display:flex;
        align-items:center;
        justify-content:space-between;
    }
    .lxc-kpi-rotulo{
        font-size:.7rem;
        font-weight:800;
        letter-spacing:.5px;
        text-transform:uppercase;
        opacity:.75;
    }
    .lxc-kpi-icone{ font-size:1.05rem; }
    .lxc-kpi-valor{
        font-size:1.9rem;
        font-weight:800;
        line-height:1.15;
        margin-top:.15rem;
    }
    .lxc-kpi-sub{
        font-size:.72rem;
        opacity:.65;
        margin-top:.1rem;
    }

    /* ---------- barra de conformidade ---------- */
    .lxc-barra-wrap{ margin:.2rem 0 1rem 0; }
    .lxc-barra-linha{
        display:flex;
        justify-content:space-between;
        font-size:.76rem;
        font-weight:700;
        margin-bottom:.3rem;
    }
    .lxc-barra-fundo{
        height:9px;
        border-radius:999px;
        background:rgba(127,127,127,.2);
        overflow:hidden;
    }
    .lxc-barra-preenchida{
        height:100%;
        border-radius:999px;
        background:linear-gradient(90deg,#22c55e,#16a34a);
    }

    /* ---------- não preenchidos ---------- */
    .lxc-aviso{
        border-radius:.9rem;
        padding:.75rem 1rem;
        margin-bottom:.7rem;
        background:rgba(239,68,68,.09);
        border:1px solid rgba(239,68,68,.3);
        font-size:.82rem;
    }
    .lxc-aviso strong{ color:#ef4444; }
    .lxc-grupo{
        border-radius:.9rem;
        padding:.65rem .9rem .5rem .9rem;
        margin-bottom:.55rem;
        background:rgba(127,127,127,.07);
        border:1px solid rgba(127,127,127,.2);
    }
    .lxc-grupo-titulo{
        font-size:.82rem;
        font-weight:800;
        margin-bottom:.3rem;
    }
    .lxc-grupo-titulo span{
        font-weight:600;
        color:__MUTED__;
    }
    .lxc-chip{
        display:inline-flex;
        align-items:center;
        gap:.4rem;
        background:rgba(239,68,68,.12);
        border:1px solid rgba(239,68,68,.35);
        border-radius:999px;
        padding:.22rem .7rem;
        font-size:.78rem;
        font-weight:600;
        margin:.18rem .3rem .18rem 0;
    }
    .lxc-chip b{
        color:#ef4444;
        font-weight:800;
    }

    /* ---------- tabelas e expanders ---------- */
    div[data-testid="stExpander"]{
        border-radius:1rem !important;
        border:1px solid rgba(127,127,127,.25) !important;
        overflow:hidden;
    }
    div[data-testid="stExpander"] summary{
        font-weight:700;
    }

    </style>
    """

    for chave, valor in v.items():
        css = css.replace(chave, valor)

    return css


def _titulo_secao(titulo, subtitulo=""):

    sub_html = (
        f'<span class="lxc-secao-sub">{html.escape(subtitulo)}</span>'
        if subtitulo else ""
    )

    st.markdown(
        f"""
        <div class="lxc-secao">
            <div class="lxc-secao-barra"></div>
            <div class="lxc-secao-titulo">{html.escape(titulo)}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def _mostrar_kpis(cartoes):
    """
    cartoes: lista de (icone, rotulo, valor, cor, subtitulo)
    """

    html_cartoes = "".join(
        f"""
        <div class="lxc-kpi" style="
            background:{cor}14;
            border:1px solid {cor}45;
            box-shadow:0 6px 18px {cor}12;
        ">
            <div class="lxc-kpi-topo">
                <span class="lxc-kpi-rotulo">{html.escape(rotulo)}</span>
                <span class="lxc-kpi-icone">{icone}</span>
            </div>
            <div class="lxc-kpi-valor" style="color:{cor};">{valor}</div>
            <div class="lxc-kpi-sub">{html.escape(subtitulo)}</div>
        </div>
        """
        for icone, rotulo, valor, cor, subtitulo in cartoes
    )

    st.markdown(
        f'<div class="lxc-kpis">{html_cartoes}</div>',
        unsafe_allow_html=True
    )


def _mostrar_barra_conformidade(conformes, total):

    if not total:
        return

    percentual = round(conformes / total * 100)

    st.markdown(
        f"""
        <div class="lxc-barra-wrap">
            <div class="lxc-barra-linha">
                <span>Taxa de conformidade</span>
                <span style="color:{COR_CONFORME};">{percentual}%</span>
            </div>
            <div class="lxc-barra-fundo">
                <div class="lxc-barra-preenchida" style="width:{percentual}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# APOIO: MESES E "NÃO PREENCHIDOS"
# =====================================================

def _chave_mes(data):

    return data.strftime("%Y-%m")


def _rotulo_mes(chave_mes):

    ano, mes = chave_mes.split("-")

    return f"{MESES_PT[int(mes) - 1]}/{ano}"


def _nomes_compativeis(nome_a, nome_b):
    """
    "João" (responsável cadastrado) deve casar com "João Silva"
    (nome completo salvo no checklist), sem diferenciar acentos ou
    maiúsculas. O número do equipamento também é conferido, então
    o risco de casar a pessoa errada é baixo.
    """

    a = banco._normalizar_texto(nome_a)
    b = banco._normalizar_texto(nome_b)

    if not a or not b:
        return False

    return a == b or a.startswith(b + " ") or b.startswith(a + " ")


def calcular_nao_preenchidos(responsaveis, registros):
    """
    Para cada sexta-feira já encerrada (anterior a hoje), cada
    responsável cadastrado em Equipamentos que NÃO tem checklist
    daquele equipamento na data prevista vira um "Não preenchido"
    (ficará negativo em seu PDL).

    - A sexta-feira de hoje ainda não conta: a pessoa tem o dia todo.
    - Só valem sextas-feiras a partir de DATA_INICIO_CONTROLE
      (outubro/2026); nada anterior a isso conta.
    - Se o responsável tiver "criado_em" (data de cadastro), sextas
      anteriores a esse cadastro não contam contra ele.
    """

    if not responsaveis:
        return []

    hoje = estilos.agora_local().date()

    dia = DATA_INICIO_CONTROLE + timedelta(
        days=(DIA_PREVISTO_CHECKLIST - DATA_INICIO_CONTROLE.weekday()) % 7
    )

    sextas = []

    while dia < hoje:
        sextas.append(dia)
        dia += timedelta(days=7)

    if not sextas:
        return []

    registros_por_data = {}

    for registro in registros:
        registros_por_data.setdefault(
            registro["data_checklist"], []
        ).append(registro)

    pendentes = []

    for sexta in sextas:

        feitos_no_dia = registros_por_data.get(sexta, [])

        for responsavel in responsaveis:

            cadastrado_em = responsavel.get("criado_em")

            if cadastrado_em:

                data_cadastro = estilos.horario_local(cadastrado_em).date()

                if sexta < data_cadastro:
                    continue

            numero = str(responsavel["numero"]).strip()

            ja_fez = any(
                str(registro["numero"]).strip() == numero
                and _nomes_compativeis(registro["nome"], responsavel["nome"])
                for registro in feitos_no_dia
            )

            if not ja_fez:

                pendentes.append({
                    "data": sexta,
                    "nome": responsavel["nome"],
                    "numero": numero
                })

    pendentes.sort(
        key=lambda item: (item["data"], item["nome"]),
        reverse=True
    )

    return pendentes


def _mostrar_nao_preenchidos(pendentes_mes, rotulo_numero):
    """
    Em vez de uma linha por pendência, agrupa por sexta-feira e mostra
    cada pessoa como uma "etiqueta" compacta — fica muito mais limpo
    quando há muitas pendências.
    """

    st.markdown(
        """
        <div class="lxc-aviso">
            🚫 <strong>Não preenchidos — ficará negativo em seu PDL.</strong>
            O checklist é previsto para toda sexta-feira. Quem não
            registrou na data prevista ficará negativo em seu PDL
            (vale a partir de outubro/2026).
        </div>
        """,
        unsafe_allow_html=True
    )

    grupos = {}

    for item in pendentes_mes:
        grupos.setdefault(item["data"], []).append(item)

    rotulo_curto = rotulo_numero.replace("Número do ", "Nº ").replace("Número da ", "Nº ")

    html_grupos = ""

    for data_grupo in sorted(grupos, reverse=True):

        itens = grupos[data_grupo]

        chips = "".join(
            f'<span class="lxc-chip">{html.escape(str(item["nome"]))} '
            f'<b>{html.escape(rotulo_curto)} {html.escape(item["numero"])}</b></span>'
            for item in itens
        )

        html_grupos += f"""
        <div class="lxc-grupo">
            <div class="lxc-grupo-titulo">
                📅 {data_grupo.strftime('%d/%m/%Y')}
                <span>· {len(itens)} pendente(s)</span>
            </div>
            {chips}
        </div>
        """

    if len(pendentes_mes) > 12:

        with st.container(height=300):

            st.markdown(html_grupos, unsafe_allow_html=True)

    else:

        st.markdown(html_grupos, unsafe_allow_html=True)


# =====================================================
# CHECKLIST GENÉRICO (Hidráulicos, Carrinhos, Empilhadeira)
# =====================================================

def renderizar_checklist(
    titulo,
    icone,
    rotulo_numero,
    funcao_adicionar,
    funcao_ler,
    prefixo_key,
    nome_arquivo_excel,
    armazem_id,
    funcao_editar=None,
    funcao_excluir=None,
    funcao_enviar_manutencao=None,
    funcao_retornar_manutencao=None,
    funcao_concluir_manutencao=None,
    funcao_responsaveis=None
):
    """
    funcao_responsaveis: se informada (Hidráulicos e Carrinhos), ativa a
    regra de "não preenchido = ficará negativo em seu PDL" com base nos
    responsáveis cadastrados em Equipamentos (a partir de outubro/2026).
    """

    _titulo_secao(f"{icone} {titulo}", "Preencha os campos e registre a inspeção")

    with st.form(
        f"form_{prefixo_key}",
        clear_on_submit=True
    ):

        col1, col2, col3, col4 = st.columns([2, 1.3, 1.2, 1.3])

        with col1:
            nome = st.text_input(
                "Nome",
                placeholder="Quem fez a inspeção",
                key=f"nome_{prefixo_key}"
            )

        with col2:
            numero = st.text_input(
                rotulo_numero,
                placeholder="Ex.: 04",
                key=f"numero_{prefixo_key}"
            )

        with col3:
            data_checklist = st.date_input(
                "Data",
                value=date.today(),
                format="DD/MM/YYYY",
                key=f"data_{prefixo_key}"
            )

        with col4:
            status = st.selectbox(
                "Situação",
                ["Conforme", "Não Conforme"],
                key=f"status_{prefixo_key}"
            )

        descricao = st.text_area(
            "Descrição",
            placeholder="Observações da inspeção (opcional)",
            height=80,
            key=f"descricao_{prefixo_key}"
        )

        enviar = st.form_submit_button(
            f"➕ Registrar {titulo}",
            width="stretch"
        )

        if enviar:

            if not nome or not numero:

                st.error(
                    "Preencha o Nome e o Número antes de registrar."
                )

            else:

                # Normaliza o nome digitado: se bater com o Perfil de
                # alguém cadastrado, salva o nome completo (nome +
                # sobrenome) já certo; senão, só corrige a
                # capitalização (ex.: "larissa santos" -> "Larissa
                # Santos"). Isso também resolve o vínculo com quem
                # está logado quando o nome vem completo.
                nome_normalizado = banco.normalizar_nome_pessoa(
                    nome, armazem_id
                )

                with estilos.mostrar_processando("registrando checklist..."):
                    funcao_adicionar(
                        nome_normalizado,
                        numero,
                        data_checklist,
                        status,
                        descricao,
                        armazem_id
                    )

                estilos.notificar_sucesso("checklist registrado com sucesso.")
                st.rerun(scope="fragment")

    registros = funcao_ler(armazem_id)

    if not registros:

        st.info(
            "Nenhum checklist registrado ainda."
        )

        return

    # =====================================================
    # NÃO PREENCHIDOS — ficará negativo em seu PDL
    # (só Hidráulicos e Carrinhos, a partir de outubro/2026)
    # =====================================================

    controla_nao_preenchidos = funcao_responsaveis is not None

    nao_preenchidos = []

    if controla_nao_preenchidos:

        nao_preenchidos = calcular_nao_preenchidos(
            funcao_responsaveis(armazem_id),
            registros
        )

    conformes = len(
        [r for r in registros if r["status"] == "Conforme"]
    )

    nao_conformes = len(registros) - conformes

    # =====================================================
    # VISÃO GERAL
    # =====================================================

    _titulo_secao("Visão geral")

    cartoes = [
        ("📋", "Total", len(registros), COR_TOTAL, "registros no histórico"),
        ("✅", "Conformes", conformes, COR_CONFORME, "sem problemas"),
        ("⚠️", "Não conformes", nao_conformes, COR_NAO_CONFORME, "precisam de atenção"),
    ]

    if controla_nao_preenchidos:

        cartoes.append((
            "🚫", "Não preenchidos", len(nao_preenchidos), COR_PENDENTE,
            "sextas sem registro"
        ))

    _mostrar_kpis(cartoes)

    _mostrar_barra_conformidade(conformes, len(registros))

    # =====================================================
    # REGISTROS SEPARADOS POR MÊS
    # O mês mais recente já abre; os anteriores ficam fechados.
    # =====================================================

    _titulo_secao("Registros por mês")

    registros_por_mes = {}

    for registro in registros:

        registros_por_mes.setdefault(
            _chave_mes(registro["data_checklist"]),
            []
        ).append(registro)

    pendentes_por_mes = {}

    for pendente in nao_preenchidos:

        pendentes_por_mes.setdefault(
            _chave_mes(pendente["data"]),
            []
        ).append(pendente)

    meses_ordenados = sorted(
        set(registros_por_mes) | set(pendentes_por_mes),
        reverse=True
    )

    for indice_mes, chave_mes in enumerate(meses_ordenados):

        registros_mes = registros_por_mes.get(chave_mes, [])
        pendentes_mes = pendentes_por_mes.get(chave_mes, [])

        rotulo_expander = (
            f"🗓️ {_rotulo_mes(chave_mes)} · "
            f"{len(registros_mes)} registro(s)"
        )

        if pendentes_mes:

            rotulo_expander += f" · 🚫 {len(pendentes_mes)} não preenchido(s)"

        with st.expander(
            rotulo_expander,
            expanded=(indice_mes == 0)
        ):

            if pendentes_mes:

                _mostrar_nao_preenchidos(pendentes_mes, rotulo_numero)

                st.write("")

            if not registros_mes:

                st.caption("Nenhum checklist registrado neste mês.")

                continue

            df_mes = pd.DataFrame(registros_mes)

            ids_registros = df_mes["id"].tolist()

            df_exibir = df_mes.rename(columns={
                "nome": "Nome",
                "numero": rotulo_numero,
                "data_checklist": "Data",
                "status": "Situação",
                "descricao": "Descrição"
            })[["Nome", rotulo_numero, "Data", "Situação", "Descrição"]]

            if funcao_editar:

                st.caption(
                    "✏️ Clique em uma célula para editar. Depois de ajustar, "
                    "clique em **Salvar alterações**."
                )

                column_config = {
                    "Nome": st.column_config.TextColumn(width="medium"),
                    "Situação": st.column_config.SelectboxColumn(
                        options=["Conforme", "Não Conforme"],
                        required=True
                    ),
                    "Data": st.column_config.DateColumn(
                        format="DD/MM/YYYY"
                    ),
                    "Descrição": st.column_config.TextColumn(width="large")
                }

                df_editado = st.data_editor(
                    df_exibir,
                    width='stretch',
                    hide_index=True,
                    key=f"editor_{prefixo_key}_{chave_mes}",
                    column_config=column_config
                )

                if st.button(
                    "💾 Salvar alterações",
                    key=f"salvar_{prefixo_key}_{chave_mes}"
                ):

                    houve_alteracao = False

                    for posicao, id_registro in enumerate(ids_registros):

                        linha_editada = df_editado.iloc[posicao]
                        linha_original = df_exibir.iloc[posicao]

                        if not linha_original.equals(linha_editada):

                            # Mesma normalização aplicada também na edição
                            # direta pela tabela — assim um nome corrigido
                            # manualmente aqui também casa com o Perfil.
                            nome_editado_normalizado = banco.normalizar_nome_pessoa(
                                linha_editada["Nome"], armazem_id
                            )

                            with estilos.mostrar_processando("salvando alterações..."):
                                funcao_editar(
                                    id_registro,
                                    nome_editado_normalizado,
                                    linha_editada[rotulo_numero],
                                    linha_editada["Data"],
                                    linha_editada["Situação"],
                                    linha_editada["Descrição"],
                                    armazem_id
                                )

                            houve_alteracao = True

                    if houve_alteracao:

                        estilos.notificar_sucesso("alterações salvas com sucesso.")
                        st.rerun(scope="fragment")

                    else:

                        st.info("Nenhuma alteração encontrada para salvar.")

            else:

                st.dataframe(
                    df_exibir,
                    width='stretch',
                    hide_index=True
                )

            # =====================================================
            # EXCLUIR REGISTROS
            # Usa um multiselect nativo (em vez de checkbox dentro da
            # tabela) porque o grid da tabela (data_editor) sempre
            # renderiza no tema escuro internamente, e ficava invisível
            # com o app no modo claro. O multiselect é um componente
            # normal do Streamlit e já segue o tema claro/escuro do app.
            # =====================================================

            if funcao_excluir:

                st.write("")

                rotulos_registros = {
                    id_registro: (
                        f"{df_exibir.iloc[posicao]['Nome']} — "
                        f"{rotulo_numero}: {df_exibir.iloc[posicao][rotulo_numero]} "
                        f"({pd.to_datetime(df_exibir.iloc[posicao]['Data']).strftime('%d/%m/%Y')})"
                    )
                    for posicao, id_registro in enumerate(ids_registros)
                }

                selecionados_excluir = st.multiselect(
                    "🗑️ Selecionar registro(s) para excluir",
                    options=ids_registros,
                    format_func=lambda id_registro, rotulos=rotulos_registros: rotulos.get(id_registro, str(id_registro)),
                    key=f"excluir_sel_{prefixo_key}_{chave_mes}"
                )

                if st.button(
                    "🗑️ Excluir selecionado(s)",
                    key=f"excluir_btn_{prefixo_key}_{chave_mes}",
                    disabled=not selecionados_excluir
                ):

                    with estilos.mostrar_processando("excluindo registro(s)..."):
                        for id_excluir in selecionados_excluir:
                            funcao_excluir(id_excluir, armazem_id)

                    estilos.notificar_sucesso(
                        f"{len(selecionados_excluir)} registro(s) excluído(s)."
                    )
                    st.rerun(scope="fragment")

    # =====================================================
    # MANUTENÇÃO
    # =====================================================
    # A visibilidade de "quais itens estão em manutenção" é liberada
    # para todos que têm acesso ao checklist. Só os comandos que
    # alteram o estado (enviar para manutenção / concluir / retornar)
    # continuam restritos ao Fundador e à Gestão.

    usuario_atual = st.session_state.get("usuario", "")

    admin_master = (
        usuario_atual.startswith("Fundador.")
        or usuario_atual.startswith("Gestao.")
    )

    if funcao_enviar_manutencao and funcao_retornar_manutencao:

        itens_em_manutencao = [
            r for r in registros
            if r.get("em_manutencao")
        ]

        itens_nao_conformes = [
            r for r in registros
            if r["status"] == "Não Conforme" and not r.get("em_manutencao")
        ]

        mostrar_envio = admin_master and bool(itens_nao_conformes)

        if itens_em_manutencao or mostrar_envio:

            _titulo_secao("Manutenção")

            with st.expander(
                f"🚧 Manutenção · {len(itens_em_manutencao)} em andamento",
                expanded=bool(itens_em_manutencao)
            ):

                if itens_em_manutencao:

                    st.markdown("##### 🚧 Em manutenção")

                    for item in itens_em_manutencao:

                        with st.container(border=True):

                            if admin_master:
                                col_texto, col_botoes = st.columns([5, 2])
                            else:
                                col_texto = st.container()

                            with col_texto:

                                st.markdown(
                                    f"**{item['nome']}** — {rotulo_numero}: {item['numero']}"
                                )

                                if item.get("manutencao_motivo"):

                                    st.caption(f"Motivo: {item['manutencao_motivo']}")

                                if item.get("manutencao_enviado_em"):

                                    enviado_em_local = estilos.horario_local(
                                        item["manutencao_enviado_em"]
                                    )

                                    st.caption(
                                        f"Enviado por {item.get('manutencao_enviado_por') or '—'} "
                                        f"em {enviado_em_local.strftime('%d/%m/%Y %H:%M')}"
                                    )

                            if admin_master:

                                with col_botoes:

                                    sub_col1, sub_col2 = st.columns(2)

                                    with sub_col1:

                                        if funcao_concluir_manutencao and st.button(
                                            "✅",
                                            key=f"concluir_manut_{prefixo_key}_{item['id']}",
                                            help=(
                                                f"Marcar manutenção de {item['nome']} "
                                                f"({rotulo_numero} {item['numero']}) como concluída"
                                            )
                                        ):

                                            with estilos.mostrar_processando("registrando manutenção concluída..."):
                                                funcao_concluir_manutencao(
                                                    item["id"],
                                                    usuario_atual,
                                                    armazem_id
                                                )

                                            estilos.notificar_sucesso(
                                                f"✅ Manutenção de {item['nome']} concluída."
                                            )
                                            st.rerun(scope="fragment")

                                    with sub_col2:

                                        if st.button(
                                            "↩️",
                                            key=f"retornar_manut_{prefixo_key}_{item['id']}",
                                            help=(
                                                f"Marcar {item['nome']} ({rotulo_numero} "
                                                f"{item['numero']}) como retornado da manutenção, "
                                                f"sem alterar a situação registrada"
                                            )
                                        ):

                                            with estilos.mostrar_processando("registrando retorno..."):
                                                funcao_retornar_manutencao(
                                                    item["id"],
                                                    usuario_atual,
                                                    armazem_id
                                                )

                                            estilos.notificar_sucesso(f"↩️ {item['nome']} retornado da manutenção.")
                                            st.rerun(scope="fragment")

                if mostrar_envio:

                    st.write("")

                    st.markdown("##### 🔧 Enviar para manutenção")

                    for item in itens_nao_conformes:

                        col_texto, col_botao = st.columns([5, 1])

                        with col_texto:

                            st.caption(
                                f"**{item['nome']}** — {rotulo_numero}: {item['numero']} "
                                f"({item['data_checklist'].strftime('%d/%m/%Y')})"
                            )

                        with col_botao:

                            if st.button(
                                "🔧",
                                key=f"enviar_manut_{prefixo_key}_{item['id']}",
                                help=(
                                    f"Enviar {item['nome']} ({rotulo_numero} "
                                    f"{item['numero']}) para manutenção"
                                )
                            ):

                                with estilos.mostrar_processando("enviando para manutenção..."):
                                    funcao_enviar_manutencao(
                                        item["id"],
                                        item.get("descricao"),
                                        usuario_atual,
                                        armazem_id
                                    )

                                estilos.notificar_sucesso(f"🔧 {item['nome']} enviado para manutenção.")
                                st.rerun(scope="fragment")

    # =====================================================
    # EXPORTAÇÃO (todos os meses)
    # =====================================================

    def _formatar_evento_manutencao(pessoa, momento):

        if not momento:
            return ""

        momento_local = estilos.horario_local(momento)

        texto = momento_local.strftime("%d/%m/%Y %H:%M")

        if pessoa:
            texto += f" ({pessoa})"

        return texto

    df_total = pd.DataFrame(registros)

    df_exportar = df_total.rename(columns={
        "nome": "Nome",
        "numero": rotulo_numero,
        "data_checklist": "Data",
        "status": "Situação",
        "descricao": "Descrição"
    })[["Nome", rotulo_numero, "Data", "Situação", "Descrição"]]

    if funcao_enviar_manutencao:

        df_exportar["Enviado p/ Manutenção"] = [
            _formatar_evento_manutencao(
                registro.get("manutencao_enviado_por"),
                registro.get("manutencao_enviado_em")
            )
            for registro in registros
        ]

        df_exportar["Retornado da Manutenção"] = [
            _formatar_evento_manutencao(
                registro.get("manutencao_retornado_por"),
                registro.get("manutencao_retornado_em")
            )
            for registro in registros
        ]

    buffer_excel = io.BytesIO()

    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:

        df_exportar.to_excel(
            writer,
            index=False,
            sheet_name=titulo[:31]
        )

        if nao_preenchidos:

            pd.DataFrame([
                {
                    "Data prevista": item["data"],
                    "Responsável": item["nome"],
                    rotulo_numero: item["numero"],
                    "Situação": "Não preenchido — ficará negativo em seu PDL"
                }
                for item in nao_preenchidos
            ]).to_excel(
                writer,
                index=False,
                sheet_name="Não preenchidos"
            )

    _titulo_secao("Exportar")

    st.download_button(
        "📥 Exportar para Excel",
        data=buffer_excel.getvalue(),
        file_name=nome_arquivo_excel,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"exportar_{prefixo_key}"
    )


# =====================================================
# CHECKLIST DE PIGMENTAÇÃO
# =====================================================

def renderizar_checklist_pigmentacao(
    funcao_adicionar,
    funcao_ler,
    prefixo_key,
    nome_arquivo_excel,
    armazem_id,
    funcao_editar=None,
    funcao_excluir=None
):

    titulo = "Checklist de Pigmentação"

    _titulo_secao(f"🎨 {titulo}", "Preencha os campos e registre a inspeção")

    with st.form(
        f"form_{prefixo_key}",
        clear_on_submit=True
    ):

        col1, col2, col3 = st.columns([2.4, 1.3, 1.3])

        with col1:
            nome = st.text_input(
                "Nome",
                placeholder="Quem fez a inspeção",
                key=f"nome_{prefixo_key}"
            )

        with col2:
            data_checklist = st.date_input(
                "Data",
                value=date.today(),
                format="DD/MM/YYYY",
                key=f"data_{prefixo_key}"
            )

        with col3:
            status = st.selectbox(
                "Situação",
                ["Conforme", "Não Conforme"],
                key=f"status_{prefixo_key}"
            )

        descricao = st.text_area(
            "Descrição",
            placeholder="Observações da inspeção (opcional)",
            height=80,
            key=f"descricao_{prefixo_key}"
        )

        enviar = st.form_submit_button(
            f"➕ Registrar {titulo}",
            width="stretch"
        )

        if enviar:

            if not nome:

                st.error(
                    "Preencha o Nome antes de registrar."
                )

            else:

                # Mesma normalização usada em renderizar_checklist:
                # se bater com um Perfil, salva o nome completo já
                # certo; senão, só corrige a capitalização.
                nome_normalizado = banco.normalizar_nome_pessoa(
                    nome, armazem_id
                )

                with estilos.mostrar_processando("registrando checklist..."):
                    funcao_adicionar(
                        nome_normalizado,
                        data_checklist,
                        status,
                        descricao,
                        armazem_id
                    )

                estilos.notificar_sucesso("checklist registrado com sucesso.")
                st.rerun(scope="fragment")

    registros = funcao_ler(armazem_id)

    if not registros:

        st.info(
            "Nenhum checklist registrado ainda."
        )

        return

    conformes = len(
        [r for r in registros if r["status"] == "Conforme"]
    )

    nao_conformes = len(registros) - conformes

    _titulo_secao("Visão geral")

    _mostrar_kpis([
        ("📋", "Total", len(registros), COR_TOTAL, "registros no histórico"),
        ("✅", "Conformes", conformes, COR_CONFORME, "sem problemas"),
        ("⚠️", "Não conformes", nao_conformes, COR_NAO_CONFORME, "precisam de atenção"),
    ])

    _mostrar_barra_conformidade(conformes, len(registros))

    # =====================================================
    # REGISTROS SEPARADOS POR MÊS
    # =====================================================

    _titulo_secao("Registros por mês")

    registros_por_mes = {}

    for registro in registros:

        registros_por_mes.setdefault(
            _chave_mes(registro["data_checklist"]),
            []
        ).append(registro)

    meses_ordenados = sorted(registros_por_mes.keys(), reverse=True)

    for indice_mes, chave_mes in enumerate(meses_ordenados):

        registros_mes = registros_por_mes[chave_mes]

        with st.expander(
            f"🗓️ {_rotulo_mes(chave_mes)} · {len(registros_mes)} registro(s)",
            expanded=(indice_mes == 0)
        ):

            df_mes = pd.DataFrame(registros_mes)

            ids_registros = df_mes["id"].tolist()

            df_exibir = df_mes.rename(columns={
                "nome": "Nome",
                "data_checklist": "Data",
                "status": "Situação",
                "descricao": "Descrição"
            })[["Nome", "Data", "Situação", "Descrição"]]

            if funcao_editar:

                st.caption(
                    "✏️ Clique em uma célula para editar. Depois de ajustar, "
                    "clique em **Salvar alterações**."
                )

                column_config = {
                    "Nome": st.column_config.TextColumn(width="medium"),
                    "Situação": st.column_config.SelectboxColumn(
                        options=["Conforme", "Não Conforme"],
                        required=True
                    ),
                    "Data": st.column_config.DateColumn(
                        format="DD/MM/YYYY"
                    ),
                    "Descrição": st.column_config.TextColumn(width="large")
                }

                df_editado = st.data_editor(
                    df_exibir,
                    width='stretch',
                    hide_index=True,
                    key=f"editor_{prefixo_key}_{chave_mes}",
                    column_config=column_config
                )

                if st.button(
                    "💾 Salvar alterações",
                    key=f"salvar_{prefixo_key}_{chave_mes}"
                ):

                    houve_alteracao = False

                    for posicao, id_registro in enumerate(ids_registros):

                        linha_editada = df_editado.iloc[posicao]
                        linha_original = df_exibir.iloc[posicao]

                        if not linha_original.equals(linha_editada):

                            nome_editado_normalizado = banco.normalizar_nome_pessoa(
                                linha_editada["Nome"], armazem_id
                            )

                            with estilos.mostrar_processando("salvando alterações..."):
                                funcao_editar(
                                    id_registro,
                                    nome_editado_normalizado,
                                    linha_editada["Data"],
                                    linha_editada["Situação"],
                                    linha_editada["Descrição"],
                                    armazem_id
                                )

                            houve_alteracao = True

                    if houve_alteracao:

                        estilos.notificar_sucesso("alterações salvas com sucesso.")
                        st.rerun(scope="fragment")

                    else:

                        st.info("Nenhuma alteração encontrada para salvar.")

            else:

                st.dataframe(
                    df_exibir,
                    width='stretch',
                    hide_index=True
                )

            if funcao_excluir:

                st.write("")

                rotulos_registros = {
                    id_registro: (
                        f"{df_exibir.iloc[posicao]['Nome']} — "
                        f"({pd.to_datetime(df_exibir.iloc[posicao]['Data']).strftime('%d/%m/%Y')})"
                    )
                    for posicao, id_registro in enumerate(ids_registros)
                }

                selecionados_excluir = st.multiselect(
                    "🗑️ Selecionar registro(s) para excluir",
                    options=ids_registros,
                    format_func=lambda id_registro, rotulos=rotulos_registros: rotulos.get(id_registro, str(id_registro)),
                    key=f"excluir_sel_{prefixo_key}_{chave_mes}"
                )

                if st.button(
                    "🗑️ Excluir selecionado(s)",
                    key=f"excluir_btn_{prefixo_key}_{chave_mes}",
                    disabled=not selecionados_excluir
                ):

                    with estilos.mostrar_processando("excluindo registro(s)..."):
                        for id_excluir in selecionados_excluir:
                            funcao_excluir(id_excluir, armazem_id)

                    estilos.notificar_sucesso(
                        f"{len(selecionados_excluir)} registro(s) excluído(s)."
                    )
                    st.rerun(scope="fragment")

    df_total = pd.DataFrame(registros).rename(columns={
        "nome": "Nome",
        "data_checklist": "Data",
        "status": "Situação",
        "descricao": "Descrição"
    })[["Nome", "Data", "Situação", "Descrição"]]

    buffer_excel = io.BytesIO()

    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
        df_total.to_excel(
            writer,
            index=False,
            sheet_name=titulo[:31]
        )

    _titulo_secao("Exportar")

    st.download_button(
        "📥 Exportar para Excel",
        data=buffer_excel.getvalue(),
        file_name=nome_arquivo_excel,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"exportar_{prefixo_key}"
    )


# =====================================================
# PÁGINA
# =====================================================

def render():

    estilos.exibir_notificacao_pendente()

    st.markdown(
        _css_checklist(st.session_state.get("tema", "escuro")),
        unsafe_allow_html=True
    )

    estilos.cabecalho_pagina(
        "✅",
        "Checklist",
        "Registro de inspeções de equipamentos pelos colaboradores.",
        cor="#a855f7"
    )

    st.write("")

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    aba_hidraulicos, aba_carrinhos, aba_empilhadeira, aba_pigmentacao = st.tabs([
        "🔧 Hidráulicos",
        "🛒 Carrinhos",
        "🚜 Empilhadeira",
        "🎨 Pigmentação"
    ])

    with aba_hidraulicos:

        renderizar_checklist(
            titulo="Checklist de Hidráulicos",
            icone="🔧",
            rotulo_numero="Número do Hidráulico",
            funcao_adicionar=banco.adicionar_checklist_hidraulico,
            funcao_ler=banco.ler_checklist_hidraulicos,
            prefixo_key="hidraulico",
            nome_arquivo_excel="checklist_hidraulicos_luxiz.xlsx",
            armazem_id=armazem_id_atual,
            funcao_editar=banco.editar_checklist_hidraulico,
            funcao_excluir=banco.excluir_checklist_hidraulico,
            funcao_enviar_manutencao=banco.enviar_manutencao_hidraulico,
            funcao_retornar_manutencao=banco.retornar_manutencao_hidraulico,
            funcao_concluir_manutencao=banco.concluir_manutencao_hidraulico,
            funcao_responsaveis=banco.ler_responsaveis_hidraulicos
        )

    with aba_carrinhos:

        renderizar_checklist(
            titulo="Checklist de Carrinhos",
            icone="🛒",
            rotulo_numero="Número do Carrinho",
            funcao_adicionar=banco.adicionar_checklist_carrinho,
            funcao_ler=banco.ler_checklist_carrinhos,
            prefixo_key="carrinho",
            nome_arquivo_excel="checklist_carrinhos_luxiz.xlsx",
            armazem_id=armazem_id_atual,
            funcao_editar=banco.editar_checklist_carrinho,
            funcao_excluir=banco.excluir_checklist_carrinho,
            funcao_enviar_manutencao=banco.enviar_manutencao_carrinho,
            funcao_retornar_manutencao=banco.retornar_manutencao_carrinho,
            funcao_concluir_manutencao=banco.concluir_manutencao_carrinho,
            funcao_responsaveis=banco.ler_responsaveis_carrinhos
        )

    with aba_empilhadeira:

        renderizar_checklist(
            titulo="Checklist de Empilhadeira",
            icone="🚜",
            rotulo_numero="Número da Empilhadeira",
            funcao_adicionar=banco.adicionar_checklist_empilhadeira,
            funcao_ler=banco.ler_checklist_empilhadeiras,
            prefixo_key="empilhadeira",
            nome_arquivo_excel="checklist_empilhadeiras_luxiz.xlsx",
            armazem_id=armazem_id_atual,
            funcao_editar=banco.editar_checklist_empilhadeira,
            funcao_excluir=banco.excluir_checklist_empilhadeira,
            funcao_enviar_manutencao=banco.enviar_manutencao_empilhadeira,
            funcao_retornar_manutencao=banco.retornar_manutencao_empilhadeira,
            funcao_concluir_manutencao=banco.concluir_manutencao_empilhadeira
        )

    with aba_pigmentacao:

        renderizar_checklist_pigmentacao(
            funcao_adicionar=banco.adicionar_checklist_pigmentacao,
            funcao_ler=banco.ler_checklist_pigmentacao,
            prefixo_key="pigmentacao",
            nome_arquivo_excel="checklist_pigmentacao_luxiz.xlsx",
            armazem_id=armazem_id_atual,
            funcao_editar=banco.editar_checklist_pigmentacao,
            funcao_excluir=banco.excluir_checklist_pigmentacao
        )

    st.write("")

    st.caption(
        "Luxiz IA • Checklist de Equipamentos"
    )

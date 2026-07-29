import streamlit as st
import banco
import estilos

import dashboard
import remanejamento
import sac
import administrativo
import auditoria
import rotativo
import checklist
import equipamentos

from datetime import datetime

# =====================================================
# CONFIGURAÇÃO
# =====================================================

st.set_page_config(
    page_title="Luxiz IA",
    page_icon="✨",
    layout="wide"
)

# =====================================================
# RODAPÉ DE STATUS (fragmento com autorefresh isolado)
# =====================================================
# Antes o st_autorefresh recarregava o app INTEIRO a cada 80s
# (e cada clique/tecla digitada também disparava um rerun completo,
# incluindo idas ao banco). Agora só este pedacinho do rodapé
# atualiza sozinho a cada 80s, sem afetar o resto da tela.

@st.fragment(run_every=120)
def render_status_footer():

    # Também serve como "heartbeat" de presença: a cada renovação
    # automática (e assim que a página carrega logada), marcamos o
    # usuário como ativo agora — é o que alimenta o "quem está
    # logado" na aba Usuários do Administrativo.
    if st.session_state.get("usuario"):
        banco.atualizar_ultimo_acesso(st.session_state.usuario)

    st.markdown(
        f"""
        <div class="footer-luxiz">
            <span class="online">🟢 Sistema Online</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span class="cloud">☁️ Supabase Conectado</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span class="refresh">🔄 Atualização Automática</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            Última sincronização:
            {datetime.now().strftime('%H:%M:%S')}
        </div>
        """,
        unsafe_allow_html=True
    )

# =====================================================
# SESSION STATE
# =====================================================

if "logado" not in st.session_state:
    st.session_state.logado = False

if "usuario" not in st.session_state:
    st.session_state.usuario = ""

# O rodapé "Sistema Online" só precisa se auto-atualizar
# depois de logar — antes disso, não há necessidade de
# ficar recarregando sozinho a cada 120s.

if st.session_state.logado:
    render_status_footer()

# =====================================================
# BANCO
# =====================================================

banco.inicializar_banco()

if "tipo_usuario" not in st.session_state:
    st.session_state.tipo_usuario = "usuario"

if "trocar_senha" not in st.session_state:
    st.session_state.trocar_senha = False

if "tema" not in st.session_state:
    st.session_state.tema = "escuro"

# =====================================================
# SELETOR DE TEMA (discreto, canto superior direito)
# =====================================================

# O toggle fica fixado (via CSS) dentro da mesma faixa da barra
# de status do rodapé — não precisa mais de coluna own própria.

tema_claro = st.toggle(
    "☀️" if st.session_state.tema == "escuro" else "🌙",
    value=(st.session_state.tema == "claro"),
    key="toggle_tema",
    help="Alternar entre modo claro e escuro"
)

st.session_state.tema = "claro" if tema_claro else "escuro"

# =====================================================
# ESTILO
# =====================================================

estilos.aplicar_fundo(
    tema=st.session_state.tema,
    tela="login" if not st.session_state.logado else "app"
)

# =====================================================
# LOGIN
# =====================================================

@st.dialog("✨ Sobre o Luxiz IA", width="large")
def mostrar_sobre_luxiz():

    with st.container(height=480):

        st.markdown("""

O **Luxiz IA** foi desenvolvido para auxiliar líderes, supervisores, coordenadores e gestores na administração operacional diária de armazéns e centros logísticos.

---

## 📊 Dashboard Organizacional

O Dashboard foi criado para gerar motivação e engajamento das equipes.

O líder realiza inspeções presenciais em cada rua, setor ou área operacional e atribui uma nota conforme a organização, limpeza e padrão operacional encontrado.

Isso cria maior senso de responsabilidade, incentivo saudável entre equipes, melhoria contínua e acompanhamento visual da evolução operacional.

---

## ⚡ Central de Remanejamento

Monitora prioridades operacionais em tempo real — docas prioritárias, coletas urgentes, itens pendentes, separações críticas, carregamentos e atividades administrativas.

Ferramenta ideal para faturistas, administrativo, supervisores e gestores operacionais.

---

## 😊 Central SAC

Controla reclamações, falhas operacionais e ocorrências logísticas.

O objetivo é definir uma meta mensal e trabalhar continuamente para permanecer dentro dela, medindo a qualidade operacional, acompanhando tendências e agindo preventivamente.

---

## 🎯 Auditoria de Atividades

Registra acertos e erros de cada colaborador por função (Conferente, Empilhador, Assistente Logístico), com histórico individual e nível de aproveitamento.

O objetivo é identificar quem precisa de reforço e reconhecer quem está com excelência.

---

## 🔄 Rodízio de Fim de Expediente

Gera automaticamente a escala semanal de quem faz cada atividade de fim de expediente, alternando as pessoas de forma justa (rodízio), além de mostrar as atividades fixas.

---

## ✅ Checklist de Equipamentos

Registro das inspeções de hidráulicos, carrinhos, empilhadeiras e pigmentação feitas pelos colaboradores, com histórico de conformidade e exportação para Excel.

---

## 🧰 Equipamentos

Mostra quem é o responsável por cada hidráulico e carrinho, e quais carrinhos ficam fixos em cada local, sem precisar de remanejamento.

---

## ⚙️ Administrativo

Área de gestão completa da operação: cadastro de usuários, responsáveis, atividades do rodízio, carrinhos fixos e demais parâmetros do sistema.

---

## 🎯 Objetivo do Luxiz IA

Transformar indicadores operacionais em informações simples, rápidas e visuais, auxiliando líderes e gestores na tomada de decisão diária.
        """)


if not st.session_state.logado:

    _, col_centro, _ = st.columns([1, 1.1, 1])

    with col_centro:

        st.markdown(
            "<div style='height:3rem'></div>",
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div style="display:flex;justify-content:center;">
            """,
            unsafe_allow_html=True
        )

        estilos.logo_header()

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="luxiz-teaser-wrap" style="justify-content:center;">
                <div class="luxiz-teaser">
                    🚀 A Luxiz IA está desenvolvendo o <strong>LX&nbsp;Roteiriza</strong> —
                    em breve, mais novidades.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("")

        with st.container(border=True, key="login-card"):

            st.markdown("#### 🔐 Acesso ao sistema")

            usuario = st.text_input(
                "Usuário"
            )

            senha = st.text_input(
                "Senha",
                type="password"
            )

            if st.button(
                "Entrar",
                use_container_width=True
            ):

                resultado = banco.autenticar(
                    usuario,
                    senha
                )

                if resultado:

                    st.session_state.logado = True
                    st.session_state.usuario = usuario

                    # retorno:
                    # (id, tipo, trocar_senha, armazem_id, nome_armazem)

                    st.session_state.tipo_usuario = resultado[1]
                    st.session_state.trocar_senha = resultado[2]
                    st.session_state.armazem_id = resultado[3]
                    st.session_state.armazem_nome = resultado[4]

                    # Fundador começa vendo o próprio armazém, mas
                    # pode trocar depois pelo seletor no topo.
                    st.session_state.armazem_visualizado_id = resultado[3]
                    st.session_state.armazem_visualizado_nome = resultado[4]

                    st.rerun()

                else:

                    st.error(
                        "Usuário ou senha inválidos."
                    )

        st.write("")

        if st.button(
            "❓ Para que serve o Luxiz IA?",
            use_container_width=True
        ):

            mostrar_sobre_luxiz()

    st.stop()

# =====================================================
# PERFIL
# =====================================================

tipo = st.session_state.tipo_usuario

usuario_atual = st.session_state.usuario

eh_fundador_prefixo = usuario_atual.startswith("Fundador.")
eh_gestao_prefixo = usuario_atual.startswith("Gestao.")
eh_separador = usuario_atual.startswith("Separador.")
eh_conferente = usuario_atual.startswith("Conferente.")
eh_recebimento = usuario_atual.startswith("Recebimento.")

acesso_restrito = eh_separador or eh_conferente

if tipo == "fundador" or eh_fundador_prefixo:
    badge = "👑 Fundador"

elif tipo == "gestao" or eh_gestao_prefixo:
    badge = "🛡️ Gestão"

elif eh_separador:
    badge = "📦 Separador"

elif eh_conferente:
    badge = "🔎 Conferente"

elif eh_recebimento:
    badge = "📥 Recebimento"

else:
    badge = "👤 Usuário"

nome_exibicao = (
    usuario_atual.split(".", 1)[1].strip().title()
    if "." in usuario_atual
    else usuario_atual
)

# =====================================================
# ARMAZÉM EM VISUALIZAÇÃO
# =====================================================
# Para a maioria dos usuários, é sempre o próprio armazém. Só o
# Fundador pode trocar (pelo seletor mostrado mais abaixo) e ver
# os dados de qualquer armazém cadastrado.

armazem_id_atual = st.session_state.get(
    "armazem_visualizado_id",
    st.session_state.get("armazem_id")
)

def botao_sair_rodape(identificador):

    st.write("")

    _, col_sair = st.columns([3, 1])

    with col_sair:

        if st.button(
            "🚪 Sair",
            use_container_width=True,
            key=f"sair_{identificador}"
        ):

            st.session_state.clear()
            st.rerun()


def render_cabecalho_inicio():

    col1, col2 = st.columns([7, 2])

    with col1:

        estilos.logo_header()

    with col2:

        st.success("🟢 Online")

        st.caption(
            f"☁️ Sincronizado com o servidor\n\n"
            f"Última atualização: "
            f"{datetime.now().strftime('%H:%M:%S')}"
        )

    st.success(
        f"Bem-vindo, {nome_exibicao} • {badge}"
    )

    if tipo == "fundador" or eh_fundador_prefixo:

        lista_armazens = banco.listar_armazens()

        nomes_armazens = [nome for _, nome in lista_armazens]
        ids_armazens = [id_ for id_, _ in lista_armazens]

        indice_atual = (
            ids_armazens.index(st.session_state.armazem_visualizado_id)
            if st.session_state.armazem_visualizado_id in ids_armazens
            else 0
        )

        nome_escolhido = st.selectbox(
            "📍 Visualizando dados de:",
            nomes_armazens,
            index=indice_atual,
            key="seletor_armazem_fundador"
        )

        indice_escolhido = nomes_armazens.index(nome_escolhido)

        if ids_armazens[indice_escolhido] != st.session_state.armazem_visualizado_id:

            st.session_state.armazem_visualizado_id = ids_armazens[indice_escolhido]
            st.session_state.armazem_visualizado_nome = nome_escolhido
            st.rerun()

    with st.popover("🆕 Novidades da versão 1.0.5"):

        st.markdown(
            """
**O que há de novo no Luxiz IA:**

- 🕒 Os cards do Dashboard agora mostram a **data e hora** da última atualização de cada rua, além de quem atualizou.
- 🔐 Tela de login redesenhada: mais limpa, com foco na logo (agora com um efeito de brilho pulsante) e um fundo com movimento suave.
- ❓ Texto "Para que serve o Luxiz IA?" atualizado, agora explicando todos os módulos do sistema (Auditoria, Rodízio, Checklist, Equipamentos e Administrativo, além de Dashboard, Remanejamento e SAC).
- 📖 Nova seção **"Modo de Usar"** na tela inicial, logo abaixo das Permissões, explicando como usar cada módulo e qual é a meta dele.
- ⚡ Ações do dia a dia (salvar, adicionar, excluir) ficaram mais rápidas: o app agora reaproveita a conexão com o banco de dados em vez de abrir uma nova a cada clique.
- 🖥️ O fundo do app não depende mais das configurações de tema do navegador — o visual é sempre o mesmo, controlado só pelo Luxiz IA.
- 🎨 Os cards do Dashboard e do Remanejamento ficam **coloridos por inteiro** conforme a nota ou a prioridade — dá para ver a situação de longe, sem precisar ler o texto.
- 🕒 O histórico de Remanejamentos foi movido para um botão discreto no final da página, deixando a tela mais limpa.
- ✨ Feedback visual em tempo real: ao salvar, adicionar ou excluir algo, o sistema mostra "Luxiz IA atualizando..." e confirma com um aviso rápido na tela.
- ⏱️ Atualização automática das telas a cada 120 segundos, reduzindo o "piscar" da tela.
- 🔍 Análise Técnica no SAC com muito mais detalhe: Chamado, Cliente, Nota Fiscal, Cód Produto, Produto, Tratativa, Hora, Separador, Volume, Carga, Região, Motorista, Balança e Conferente.
- 📥 Botão para exportar toda a Análise Técnica para uma planilha Excel.
- 🗑️ É possível excluir vários registros de Remanejamento e de Análise Técnica de uma vez, usando as caixinhas de seleção.
- 👥 Perfis de acesso **Separador**, **Conferente** e **Recebimento**, cada um com visão restrita aos módulos que fazem parte da sua rotina.
        """
    )

# =====================================================
# ABAS PRINCIPAIS
# =====================================================

if acesso_restrito:

    NAV_ITENS = [
        ("nav_inicio", "🏠", "Início"),
        ("nav_dashboard", "📊", "Dashboard"),
        ("nav_sac", "😊", "SAC"),
        ("nav_rotativo", "🔄", "Rodízio"),
        ("nav_checklist", "✅", "Checklist"),
        ("nav_equipamentos", "🧰", "Equipamentos"),
    ]

elif eh_recebimento:

    NAV_ITENS = [
        ("nav_inicio", "🏠", "Início"),
        ("nav_auditoria", "🎯", "Auditoria"),
        ("nav_checklist", "✅", "Checklist"),
        ("nav_equipamentos", "🧰", "Equipamentos"),
    ]

else:

    NAV_ITENS = [
        ("nav_inicio", "🏠", "Início"),
        ("nav_dashboard", "📊", "Dashboard"),
        ("nav_remanejamento", "⚡", "Remanejamento"),
        ("nav_sac", "😊", "SAC"),
        ("nav_auditoria", "🎯", "Auditoria"),
        ("nav_rotativo", "🔄", "Rodízio"),
        ("nav_checklist", "✅", "Checklist"),
        ("nav_equipamentos", "🧰", "Equipamentos"),
        ("nav_administrativo", "⚙️", "Administrativo"),
    ]

CHAVES_VALIDAS = [chave for chave, _, _ in NAV_ITENS]

if (
    "aba_atual" not in st.session_state
    or st.session_state.aba_atual not in CHAVES_VALIDAS
):
    st.session_state.aba_atual = CHAVES_VALIDAS[0]

# =====================================================
# BARRA LATERAL (construída com CSS, não usa st.sidebar)
# =====================================================

if "sidebar_aberta" not in st.session_state:
    st.session_state.sidebar_aberta = True

LARGURA_PAINEL_PX = 208 if st.session_state.sidebar_aberta else 64
TOPO_INICIAL_PX = 104
ESPACAMENTO_PX = 56

# Altura aproximada da barra global "🟢 Sistema Online" fixa no rodapé
# da página inteira (definida em estilos.py, classe .footer-luxiz).
ALTURA_RODAPE_GLOBAL_PX = 40

# Altura do rodapé próprio da barra lateral (bolinha + nome do usuário),
# que fica encaixado logo acima da barra global.
ALTURA_RODAPE_SIDEBAR_PX = 46

# A barra lateral é um painel próprio (não usa st.sidebar), então
# precisa seguir manualmente o tema claro/escuro escolhido no topo.
if st.session_state.tema == "claro":
    COR_FUNDO_SIDEBAR = "linear-gradient(180deg, rgba(255,255,255,.98), rgba(248,250,252,.94))"
    COR_BORDA_SIDEBAR = "rgba(0,0,0,.08)"
    COR_SOMBRA_SIDEBAR = "2px 0 18px rgba(0,0,0,.06)"
    COR_TEXTO_TOGGLE = "#0f172a"
else:
    COR_FUNDO_SIDEBAR = "linear-gradient(180deg, rgba(8,12,24,.95), rgba(8,12,24,.88))"
    COR_BORDA_SIDEBAR = "rgba(255,255,255,.08)"
    COR_SOMBRA_SIDEBAR = "2px 0 18px rgba(0,0,0,.25)"
    COR_TEXTO_TOGGLE = "#e2e8f0"

st.markdown(
    f"""
    <style>
    .luxiz-sidebar-fundo{{
        position:fixed;
        left:0;
        top:0;
        width:{LARGURA_PAINEL_PX}px;
        height:100vh;
        background:{COR_FUNDO_SIDEBAR};
        border-right:1px solid {COR_BORDA_SIDEBAR};
        box-shadow:{COR_SOMBRA_SIDEBAR};
        z-index:999996;
        transition:width .18s ease, background .18s ease;
    }}
    .luxiz-sidebar-sub{{
        position:fixed;
        left:0;
        top:70px;
        width:{LARGURA_PAINEL_PX}px;
        text-align:center;
        z-index:999997;
        color:#64748b;
        font-size:.68rem;
        letter-spacing:1px;
        text-transform:uppercase;
        pointer-events:none;
    }}
    div[class*="st-key-toggle_sidebar_luxiz"]{{
        position:fixed;
        left:0;
        top:16px;
        width:{LARGURA_PAINEL_PX}px;
        z-index:999999;
        text-align:center;
        transition:width .18s ease;
    }}
    div[class*="st-key-toggle_sidebar_luxiz"] button{{
        background:transparent !important;
        border:none !important;
        box-shadow:none !important;
        color:{COR_TEXTO_TOGGLE} !important;
        font-weight:800 !important;
        font-size:1.05rem !important;
        letter-spacing:.4px;
        width:100%;
        padding:.3rem 0 !important;
    }}
    div[class*="st-key-toggle_sidebar_luxiz"] button:hover{{
        filter:brightness(1.4);
        transform:scale(1.05);
    }}
    div[class*="st-key-painel_navegacao_scroll"]{{
        position:fixed;
        left:0;
        top:{TOPO_INICIAL_PX + 26}px;
        width:{LARGURA_PAINEL_PX}px;
        bottom:{ALTURA_RODAPE_GLOBAL_PX + ALTURA_RODAPE_SIDEBAR_PX}px;
        overflow-y:auto;
        overflow-x:hidden;
        padding:0 16px;
        box-sizing:border-box;
        z-index:999998;
        transition:width .18s ease;
    }}
    div[class*="st-key-painel_navegacao_scroll"]::-webkit-scrollbar{{
        width:5px;
    }}
    div[class*="st-key-painel_navegacao_scroll"]::-webkit-scrollbar-thumb{{
        background:rgba(148,163,184,.45);
        border-radius:999px;
    }}
    div[class*="st-key-painel_navegacao_scroll"]::-webkit-scrollbar-track{{
        background:transparent;
    }}
    div[class*="st-key-nav_"]{{
        margin-bottom:12px;
    }}
    div[class*="st-key-nav_"] button{{
        width:100%;
        height:44px;
        border-radius:10px !important;
        text-align:left;
        padding-left:16px !important;
        font-size:.92rem;
        white-space:nowrap;
        transition:transform .15s ease, filter .15s ease;
    }}
    div[class*="st-key-nav_"] button:hover{{
        transform:translateX(3px);
        filter:brightness(1.15);
    }}
    .block-container{{
        padding-left:{LARGURA_PAINEL_PX + (32 if st.session_state.sidebar_aberta else 24)}px !important;
        transition:padding-left .18s ease;
    }}
    </style>
    <div class="luxiz-sidebar-fundo"></div>
    """,
    unsafe_allow_html=True
)

rotulo_toggle = "✨  Luxiz IA" if st.session_state.sidebar_aberta else "✨"

if st.button(rotulo_toggle, key="toggle_sidebar_luxiz"):
    st.session_state.sidebar_aberta = not st.session_state.sidebar_aberta
    st.rerun()

if st.session_state.sidebar_aberta:

    st.markdown(
        '<div class="luxiz-sidebar-sub">Navegação</div>',
        unsafe_allow_html=True
    )

    with st.container(key="painel_navegacao_scroll"):

        for indice, (chave, icone, nome) in enumerate(NAV_ITENS):

            ativo = st.session_state.aba_atual == chave

            if st.button(
                f"{icone}   {nome}",
                key=chave,
                type="primary" if ativo else "secondary"
            ):
                st.session_state.aba_atual = chave
                st.rerun()

# =====================================================
# RODAPÉ DA BARRA LATERAL (bolinha online + usuário logado)
# =====================================================
# Fica sempre fixo, acima da barra global "Sistema Online" do
# rodapé da página — só a área de navegação (acima) rola.

rotulo_rodape_sidebar = (
    f"🟢 {nome_exibicao}"
    if st.session_state.sidebar_aberta
    else "🟢"
)

st.markdown(
    f"""
    <style>
    .luxiz-sidebar-rodape{{
        position:fixed;
        left:0;
        bottom:{ALTURA_RODAPE_GLOBAL_PX}px;
        width:{LARGURA_PAINEL_PX}px;
        height:{ALTURA_RODAPE_SIDEBAR_PX}px;
        box-sizing:border-box;
        display:flex;
        align-items:center;
        justify-content:center;
        z-index:999998;
        font-size:.78rem;
        font-weight:700;
        color:{COR_TEXTO_TOGGLE};
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
        padding:0 12px;
        border-top:1px solid {COR_BORDA_SIDEBAR};
        background:{COR_FUNDO_SIDEBAR};
        transition:width .18s ease;
    }}
    </style>
    <div class="luxiz-sidebar-rodape">{rotulo_rodape_sidebar}</div>
    """,
    unsafe_allow_html=True
)

aba_inicio = st.session_state.aba_atual == "nav_inicio"
aba_dashboard = st.session_state.aba_atual == "nav_dashboard"
aba_remanejamento = st.session_state.aba_atual == "nav_remanejamento"
aba_sac = st.session_state.aba_atual == "nav_sac"
aba_auditoria = st.session_state.aba_atual == "nav_auditoria"
aba_rotativo = st.session_state.aba_atual == "nav_rotativo"
aba_checklist = st.session_state.aba_atual == "nav_checklist"
aba_equipamentos = st.session_state.aba_atual == "nav_equipamentos"
aba_admin = st.session_state.aba_atual == "nav_administrativo"


# =====================================================
# INÍCIO
# =====================================================

def render_conteudo_inicio():

    st.info(
        "Utilize a barra lateral esquerda para navegar pelo sistema."
    )

    DESCRICOES_MODULOS = {
        "nav_dashboard": "Notas de organização por rua, em tempo real.",
        "nav_remanejamento": "Prioridades operacionais monitoradas ao vivo.",
        "nav_sac": "Metas de reclamações e análise técnica por pessoa.",
        "nav_auditoria": "Acertos e erros de cada colaborador, com histórico.",
        "nav_rotativo": "Escala automática das atividades de fim de expediente.",
        "nav_checklist": "Inspeção de hidráulicos, carrinhos, empilhadeiras e pigmentação.",
        "nav_equipamentos": "Responsáveis por hidráulicos e carrinhos, e carrinhos fixos por local.",
        "nav_administrativo": "Gestão completa da operação em um só lugar.",
    }

    CORES_MODULOS = {
        "nav_dashboard": "#3b82f6",
        "nav_remanejamento": "#f59e0b",
        "nav_sac": "#22c55e",
        "nav_auditoria": "#ec4899",
        "nav_rotativo": "#06b6d4",
        "nav_checklist": "#a855f7",
        "nav_equipamentos": "#0ea5e9",
        "nav_administrativo": "#64748b",
    }

    modulos_disponiveis = [
        (chave, icone, nome)
        for chave, icone, nome in NAV_ITENS
        if chave != "nav_inicio"
    ]

    st.write("")

    for inicio_linha in range(0, len(modulos_disponiveis), 3):

        linha = st.columns(3)

        for offset in range(3):

            indice = inicio_linha + offset

            if indice >= len(modulos_disponiveis):
                continue

            chave, icone, nome = modulos_disponiveis[indice]

            cor = CORES_MODULOS.get(chave, "#3b82f6")

            with linha[offset]:

                with st.container(border=True):

                    st.markdown(
                        f"""
                        <div style="
                            width:48px;height:48px;border-radius:12px;
                            background:{cor}22;
                            display:flex;align-items:center;justify-content:center;
                            font-size:1.4rem;margin-bottom:.5rem;
                        ">{icone}</div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"**{nome}**"
                    )

                    st.caption(
                        DESCRICOES_MODULOS.get(chave, "")
                    )

                    st.markdown(
                        f"""
                        <span style="
                            background:{cor}22;
                            color:{cor};
                            padding:.15rem .55rem;
                            border-radius:999px;
                            font-size:.72rem;
                            font-weight:700;
                        ">🟢 Online</span>
                        """,
                        unsafe_allow_html=True
                    )

    st.divider()

    st.subheader(
        "Permissões do Perfil"
    )

    if tipo == "fundador" or eh_fundador_prefixo:

        st.success("""
### 👑 Fundador

- Criar usuários
- Criar gestores
- Excluir usuários
- Excluir gestores
- Resetar senhas
- Controle total do sistema
        """)

    elif tipo == "gestao" or eh_gestao_prefixo:

        st.info("""
### 🛡️ Gestão

- Criar usuários
- Excluir usuários comuns
- Resetar senhas
- Gerenciar operação
        """)

    elif eh_separador:

        st.warning("""
### 📦 Separador

- Dashboard
- SAC
- Rodízio
- Checklist
        """)

    elif eh_conferente:

        st.warning("""
### 🔎 Conferente

- Dashboard
- SAC
- Rodízio
- Checklist
        """)

    elif eh_recebimento:

        st.warning("""
### 📥 Recebimento

- Auditoria (apenas o próprio card)
- Checklist
        """)

    else:

        st.warning("""
### 👤 Usuário

- Dashboard
- SAC
- Remanejamento
- Auditoria
- Rodízio
- Checklist
- Administrativo operacional
        """)

    st.divider()

    st.subheader(
        "📖 Modo de Usar"
    )

    st.caption(
        "O que cada módulo faz e qual é o seu objetivo dentro da operação."
    )

    MODO_DE_USAR = [
        (
            "📊", "Dashboard", "#3b82f6",
            "O líder inspeciona presencialmente cada rua/setor e atribui uma nota "
            "de organização, limpeza e padrão operacional.",
            "Gerar engajamento e senso de responsabilidade entre as equipes, "
            "reconhecendo quem está com o melhor desempenho."
        ),
        (
            "⚡", "Remanejamento", "#f59e0b",
            "Cadastre uma prioridade (docas, coletas urgentes, separações críticas "
            "etc.) e classifique a urgência: Alta, Média ou Normal.",
            "Deixar visível, em tempo real, o que precisa de atenção imediata na operação."
        ),
        (
            "😊", "SAC", "#22c55e",
            "Registre o número de reclamações do mês e a meta estabelecida, e "
            "acompanhe as ocorrências por pessoa na Análise Técnica.",
            "Medir a qualidade operacional, identificar gargalos e agir antes que "
            "as reclamações aumentem."
        ),
        (
            "🎯", "Auditoria", "#ec4899",
            "Registre os acertos e erros de cada colaborador por função "
            "(Conferente, Empilhador, Assistente Logístico).",
            "Acompanhar o aproveitamento individual e direcionar treinamento para "
            "quem mais precisa."
        ),
        (
            "🔄", "Rodízio", "#06b6d4",
            "Cadastre as pessoas e as atividades de fim de expediente no "
            "Administrativo; o sistema gera a escala da semana sozinho.",
            "Garantir um rodízio justo das atividades de fim de expediente, "
            "sem depender de planilha manual."
        ),
        (
            "✅", "Checklist", "#a855f7",
            "Registre a inspeção de hidráulicos, carrinhos, empilhadeiras e "
            "pigmentação, marcando Conforme ou Não Conforme.",
            "Manter o histórico de conformidade dos equipamentos e permitir a "
            "exportação para Excel."
        ),
        (
            "🧰", "Equipamentos", "#0ea5e9",
            "Consulte quem é responsável por cada hidráulico/carrinho e quais "
            "carrinhos ficam fixos em cada local.",
            "Facilitar a localização de equipamentos e de quem é o responsável "
            "por cada um."
        ),
        (
            "⚙️", "Administrativo", "#64748b",
            "Cadastre usuários, responsáveis, atividades do rodízio, carrinhos "
            "fixos e demais parâmetros do sistema.",
            "Centralizar toda a configuração da operação em um só lugar."
        ),
    ]

    modulos_visiveis = {chave for chave, _, _ in NAV_ITENS}

    mapa_modo_de_usar = {
        "Dashboard": "nav_dashboard",
        "Remanejamento": "nav_remanejamento",
        "SAC": "nav_sac",
        "Auditoria": "nav_auditoria",
        "Rodízio": "nav_rotativo",
        "Checklist": "nav_checklist",
        "Equipamentos": "nav_equipamentos",
        "Administrativo": "nav_administrativo",
    }

    for icone, nome, cor, como_usar, objetivo in MODO_DE_USAR:

        if mapa_modo_de_usar.get(nome) not in modulos_visiveis:
            continue

        with st.expander(f"{icone}  {nome}"):

            st.markdown(f"**🧭 Como usar:** {como_usar}")

            st.markdown(
                f"""
                <div style="
                    background:{cor}18;
                    border-left:4px solid {cor};
                    padding:.5rem .7rem;
                    border-radius:.4rem;
                    margin-top:.4rem;
                ">
                🎯 <strong>Meta:</strong> {objetivo}
                </div>
                """,
                unsafe_allow_html=True
            )

    st.divider()

    estilos.rodape()

if aba_inicio:
    render_cabecalho_inicio()
    render_conteudo_inicio()

@st.fragment(run_every=120)
def render_aba_dashboard():

    with st.spinner("🔄 Luxiz IA atualizando: Dashboard..."):
        dashboard.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("dashboard")

if aba_dashboard:
    render_aba_dashboard()

# =====================================================
# REMANEJAMENTO
# =====================================================

@st.fragment(run_every=120)
def render_aba_remanejamento():

    with st.spinner("🔄 Luxiz IA atualizando: Remanejamento..."):
        remanejamento.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("remanejamento")

if aba_remanejamento:
    render_aba_remanejamento()

# =====================================================
# SAC
# =====================================================

@st.fragment(run_every=120)
def render_aba_sac():

    with st.spinner("🔄 Luxiz IA atualizando: Central SAC..."):
        sac.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("sac")

if aba_sac:
    render_aba_sac()

# =====================================================
# AUDITORIA DE ATIVIDADES
# =====================================================

@st.fragment(run_every=120)
def render_aba_auditoria():

    with st.spinner("🔄 Luxiz IA atualizando: Auditoria de Atividades..."):
        auditoria.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("auditoria")

if aba_auditoria:
    render_aba_auditoria()

# =====================================================
# RODÍZIO - FIM DE EXPEDIENTE
# =====================================================

@st.fragment(run_every=120)
def render_aba_rotativo():

    with st.spinner("🔄 Luxiz IA atualizando: Rodízio de Fim de Expediente..."):
        rotativo.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("rotativo")

if aba_rotativo:
    render_aba_rotativo()

# =====================================================
# CHECKLIST
# =====================================================

@st.fragment
def render_aba_checklist():

    checklist.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("checklist")

if aba_checklist:
    render_aba_checklist()

# =====================================================
# EQUIPAMENTOS
# =====================================================

@st.fragment(run_every=120)
def render_aba_equipamentos():

    with st.spinner("🔄 Luxiz IA atualizando: Equipamentos..."):
        equipamentos.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("equipamentos")

if aba_equipamentos:
    render_aba_equipamentos()

# =====================================================
# ADMINISTRATIVO
# =====================================================
# Sem run_every: esta aba é cheia de formulários e inputs.
# O fragmento aqui serve só para isolar cliques/digitação
# nesta aba, evitando que eles recarreguem o app inteiro.

@st.fragment
def render_aba_admin():

    administrativo.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("admin")

if aba_admin:
    render_aba_admin()

# =====================================================
# RODAPÉ
# =====================================================

st.write("")
st.divider()

estilos.rodape()

st.markdown(
    "<p style='text-align:center;font-size:.7rem;color:#94a3b8;margin-top:2px;'>Versão 1.0.5</p>",
    unsafe_allow_html=True
)
import streamlit as st
import banco
import estilos

import dashboard
import remanejamento
import sac
import administrativo

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

render_status_footer()

# =====================================================
# BANCO
# =====================================================

banco.inicializar_banco()

# =====================================================
# SESSION STATE
# =====================================================

if "logado" not in st.session_state:
    st.session_state.logado = False

if "usuario" not in st.session_state:
    st.session_state.usuario = ""

if "tipo_usuario" not in st.session_state:
    st.session_state.tipo_usuario = "usuario"

if "trocar_senha" not in st.session_state:
    st.session_state.trocar_senha = False

if "tema" not in st.session_state:
    st.session_state.tema = "escuro"

# =====================================================
# SELETOR DE TEMA (discreto, canto superior direito)
# =====================================================

_, col_tema = st.columns([9, 1])

with col_tema:

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

if not st.session_state.logado:

    estilos.logo_header()

    st.write("")
    st.write("")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:

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
                # (id, tipo, trocar_senha)

                st.session_state.tipo_usuario = resultado[1]
                st.session_state.trocar_senha = resultado[2]

                st.rerun()

            else:

                st.error(
                    "Usuário ou senha inválidos."
                )

        st.write("")

        with st.expander(
            "❓ Para que serve o Luxiz IA?"
        ):

            st.markdown("""

# ✨ Sobre o Luxiz IA

O **Luxiz IA** foi desenvolvido para auxiliar líderes, supervisores, coordenadores e gestores na administração operacional diária de armazéns e centros logísticos.

---

## 📊 Dashboard Organizacional

O Dashboard foi criado para gerar motivação e engajamento das equipes.

Sabemos da dificuldade de manter um armazém organizado diariamente, principalmente em operações com alto volume e grande movimentação.

Por isso, o líder realiza inspeções presenciais em cada rua, setor ou área operacional e atribui uma nota conforme a organização, limpeza e padrão operacional encontrado.

Isso cria:

- maior senso de responsabilidade;
- incentivo saudável entre equipes;
- melhoria contínua;
- acompanhamento visual da evolução operacional;
- reconhecimento das melhores equipes.

---

## ⚡ Central de Remanejamento

A Central de Remanejamento foi criada para monitorar prioridades operacionais em tempo real.

Exemplos:

- docas prioritárias;
- coletas urgentes;
- itens pendentes;
- separações críticas;
- carregamentos prioritários;
- atividades administrativas.

Ferramenta ideal para:

- faturistas;
- administrativo;
- supervisores;
- gestores operacionais.

---

## 😊 Central SAC

A Central SAC permite controlar reclamações, falhas operacionais e ocorrências logísticas.

O objetivo é definir uma meta mensal e trabalhar continuamente para permanecer dentro dela.

Isso permite:

- medir a qualidade operacional;
- acompanhar tendências;
- identificar gargalos;
- agir preventivamente;
- reduzir reincidências.

---

## 🎯 Objetivo do Luxiz IA

Transformar indicadores operacionais em informações simples, rápidas e visuais, auxiliando líderes e gestores na tomada de decisão diária.
            """)

    st.stop()

# =====================================================
# CABEÇALHO
# =====================================================

col1, col2 = st.columns([7,2])

with col1:

    estilos.logo_header()

with col2:

    st.success("🟢 Online")

    st.caption(
        f"☁️ Sincronizado com o servidor\n\n"
        f"Última atualização: "
        f"{datetime.now().strftime('%H:%M:%S')}"
    )

    if st.button(
        "🚪 Sair",
        use_container_width=True
    ):

        st.session_state.clear()
        st.rerun()

# =====================================================
# PERFIL
# =====================================================

tipo = st.session_state.tipo_usuario

usuario_atual = st.session_state.usuario

eh_separador = usuario_atual.startswith("Separador.")
eh_conferente = usuario_atual.startswith("Conferente.")

acesso_restrito = eh_separador or eh_conferente

if tipo == "fundador":
    badge = "👑 Fundador"

elif tipo == "gestao":
    badge = "🛡️ Gestão"

elif eh_separador:
    badge = "📦 Separador"

elif eh_conferente:
    badge = "🔎 Conferente"

else:
    badge = "👤 Usuário"

st.success(
    f"Bem-vindo, {st.session_state.usuario} • {badge}"
)

with st.popover("🆕 Novidades da versão 1.0.3"):

    st.markdown(
        """
**O que há de novo no Luxiz IA:**

- 🎨 Os cards do Dashboard e do Remanejamento agora ficam **coloridos por inteiro** conforme a nota ou a prioridade — dá para ver a situação de longe, sem precisar ler o texto.
- 📝 O campo "Nome" da Análise Técnica foi removido; Separador e Conferente já cobrem essa informação, evitando registrar o mesmo erro duas vezes.
- 🔧 Corrigido: quando a mesma pessoa aparecia em mais de um campo (ex: Separador e Conferente iguais), o erro contava em dobro no card dela — agora conta só 1 vez por registro.
- 🕒 O histórico de Remanejamentos foi movido para um botão discreto no final da página, deixando a tela mais limpa.
- ✨ Feedback visual em tempo real: ao salvar, adicionar ou excluir algo, o sistema mostra "Luxiz IA atualizando..." e confirma com um aviso rápido na tela.
- ⏱️ Atualização automática das telas ajustada para a cada 120 segundos, reduzindo o "piscar" da tela.
- 🔍 Análise Técnica no SAC ganhou muito mais detalhe: Chamado, Cliente, Nota Fiscal, Cód Produto, Produto, Tratativa, Hora, Separador, Volume, Carga, Região, Motorista, Balança e Conferente.
- 🔔 Ao informar um Separador ou Conferente na Análise Técnica, o sistema pergunta se deseja notificá-lo(a) — se confirmado, a ocorrência aparece também no card dessa pessoa.
- 📥 Novo botão para exportar toda a Análise Técnica para uma planilha Excel.
- 🗑️ Agora é possível excluir vários registros de Remanejamento e de Análise Técnica de uma vez, usando as caixinhas de seleção.
- 🏷️ O tipo de erro agora tem opções mais completas: Pigmentação, Componente, Contagem, Deixou no Picking, Impróprio, Inversão de Doca, Inversão de Etiqueta, Inversão de Picking e Inversão de Produto.
- 👥 Perfis de acesso **Separador** e **Conferente**, com visão restrita ao Dashboard e ao SAC — e, na Análise Técnica, cada um vê apenas o próprio card.
        """
    )

# =====================================================
# ABAS PRINCIPAIS
# =====================================================

if acesso_restrito:

    labels_abas = [
        "📊 Dashboard",
        "😊 SAC"
    ]

else:

    labels_abas = [
        "🏠 Início",
        "📊 Dashboard",
        "⚡ Remanejamento",
        "😊 SAC",
        "⚙️ Administrativo"
    ]

tabs_criadas = st.tabs(
    labels_abas
)

tab_map = dict(
    zip(
        labels_abas,
        tabs_criadas
    )
)

aba_inicio = tab_map.get("🏠 Início")
aba_dashboard = tab_map["📊 Dashboard"]
aba_remanejamento = tab_map.get("⚡ Remanejamento")
aba_sac = tab_map["😊 SAC"]
aba_admin = tab_map.get("⚙️ Administrativo")

# =====================================================
# INÍCIO
# =====================================================

def render_conteudo_inicio():

    st.info(
        "Utilize as abas superiores para navegar pelo sistema."
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "5S",
            "Online"
        )

    with c2:
        st.metric(
            "Remanejamento",
            "Online"
        )

    with c3:
        st.metric(
            "SAC",
            "Online"
        )

    with c4:
        st.metric(
            "Administrativo",
            "Online"
        )

    st.divider()

    st.subheader(
        "Resumo da Plataforma"
    )

    st.markdown("""
- ✅ Dashboard operacional em tempo real
- ✅ Gestão inteligente de remanejamentos
- ✅ Monitoramento do SAC
- ✅ Administração centralizada
- ✅ Indicadores estratégicos
- ✅ Ambiente corporativo inteligente
    """)

    st.divider()

    st.subheader(
        "Permissões do Perfil"
    )

    if tipo == "fundador":

        st.success("""
### 👑 Fundador

- Criar usuários
- Criar gestores
- Excluir usuários
- Excluir gestores
- Resetar senhas
- Controle total do sistema
        """)

    elif tipo == "gestao":

        st.info("""
### 🛡️ Gestão

- Criar usuários
- Excluir usuários comuns
- Resetar senhas
- Gerenciar operação
        """)

    else:

        st.warning("""
### 👤 Usuário

- Dashboard
- SAC
- Remanejamento
- Administrativo operacional
        """)

    st.divider()

    estilos.rodape()

if aba_inicio:
    with aba_inicio:
        render_conteudo_inicio()

@st.fragment(run_every=120)
def render_aba_dashboard():

    dashboard.render()

    st.write("")
    estilos.rodape()

with aba_dashboard:
    render_aba_dashboard()

# =====================================================
# REMANEJAMENTO
# =====================================================

@st.fragment(run_every=120)
def render_aba_remanejamento():

    remanejamento.render()

    st.write("")
    estilos.rodape()

if aba_remanejamento:
    with aba_remanejamento:
        render_aba_remanejamento()

# =====================================================
# SAC
# =====================================================

@st.fragment(run_every=120)
def render_aba_sac():

    sac.render()

    st.write("")
    estilos.rodape()

with aba_sac:
    render_aba_sac()

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

if aba_admin:
    with aba_admin:
        render_aba_admin()

# =====================================================
# RODAPÉ
# =====================================================

st.write("")
st.divider()

estilos.rodape()

st.markdown(
    "<p style='text-align:center;font-size:.7rem;color:#94a3b8;margin-top:2px;'>Versão 1.0.3</p>",
    unsafe_allow_html=True
)

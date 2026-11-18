import streamlit as st
import banco
import estilos
import os

from datetime import datetime, timezone

import dashboard
import remanejamento
import sac
import administrativo
import auditoria
import rotativo
import checklist
import equipamentos
import epi
import estoque
import solicitacoes
import recordes
import sac_automatico
import efeito_login
import notificacoes
import perfil
import historico
import loja

# =====================================================
# CONFIGURAÇÃO
# =====================================================

_CAMINHO_FAVICON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets",
    "favicon.png"
)

st.set_page_config(
    page_title="Luxiz IA",
    page_icon=_CAMINHO_FAVICON,
    layout="wide"
)

# =====================================================
# AVISO DE CONEXÃO (queda de rede / rede reestabelecida)
# =====================================================
# Isso é puramente client-side (JavaScript no navegador), porque uma
# queda de rede de verdade impede qualquer script Python de rodar —
# não tem como o servidor "avisar" que a rede caiu enquanto ela está
# caída. O truque é ouvir os eventos nativos do navegador
# (window.addEventListener('offline'/'online')) e mostrar uma faixa
# fixa no topo da tela, sem depender do Streamlit rodar nada.
#
# injetado uma única vez por sessão de navegador (guarda de
# `window.__luxizNetStatusInit`) para não empilhar vários avisos a
# cada rerun/clique.

def _injetar_aviso_de_rede():

    st.components.v1.html(
        """
        <script>
        (function() {
            try {
                var win = window.parent;
                var doc = win.document;

                if (win.__luxizNetStatusInit) {
                    return;
                }
                win.__luxizNetStatusInit = true;

                var banner = doc.createElement('div');
                banner.id = 'luxiz-net-status';
                banner.style.position = 'fixed';
                banner.style.top = '0';
                banner.style.left = '0';
                banner.style.width = '100%';
                banner.style.zIndex = '4000000';
                banner.style.textAlign = 'center';
                banner.style.padding = '10px 16px';
                banner.style.fontFamily = 'sans-serif';
                banner.style.fontWeight = '700';
                banner.style.fontSize = '14px';
                banner.style.display = 'none';
                banner.style.transition = 'opacity .35s ease';
                banner.style.boxShadow = '0 2px 12px rgba(0,0,0,.25)';
                doc.body.appendChild(banner);

                var esconderTimeout = null;

                function mostrarOffline() {
                    clearTimeout(esconderTimeout);
                    banner.style.background = '#dc2626';
                    banner.style.color = '#ffffff';
                    banner.innerHTML = '📡 Sem rede no momento... aguardando reconexão';
                    banner.style.display = 'block';
                    banner.style.opacity = '1';
                }

                function mostrarOnline() {
                    clearTimeout(esconderTimeout);
                    banner.style.background = '#16a34a';
                    banner.style.color = '#ffffff';
                    banner.innerHTML = '✅ Rede estabelecida novamente';
                    banner.style.display = 'block';
                    banner.style.opacity = '1';

                    esconderTimeout = setTimeout(function() {
                        banner.style.opacity = '0';
                        setTimeout(function() {
                            banner.style.display = 'none';
                        }, 400);
                    }, 4000);
                }

                win.addEventListener('offline', mostrarOffline);
                win.addEventListener('online', mostrarOnline);

                if (win.navigator && win.navigator.onLine === false) {
                    mostrarOffline();
                }
            } catch (erro) {
                // Se o navegador bloquear o acesso ao parent por
                // qualquer motivo, falha em silêncio — nunca deve
                // quebrar o resto do app.
            }
        })();
        </script>
        """,
        height=0
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
        try:
            banco.atualizar_ultimo_acesso(st.session_state.usuario)
        except Exception:
            pass

    if st.session_state.get("token_sessao"):
        try:
            banco.renovar_sessao(st.session_state.token_sessao)
        except Exception:
            pass

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
            {estilos.agora_local().strftime('%H:%M:%S')}
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

# =====================================================
# BANCO
# =====================================================

banco.inicializar_banco()

# Antes de qualquer exclusão de registros de Auditoria, grava as
# medalhas dos períodos já fechados (o gestor exporta e apaga os
# registros no começo de cada trimestre — o histórico não pode se perder).
recordes.proteger_medalhas_na_exclusao()

# SAC automático: as reclamações do mês passam a ser contadas sozinhas
# pelos cards da Análise Técnica (só a meta continua manual).
sac_automatico.ativar()

# =====================================================
# RESTAURA SESSÃO PELO TOKEN DA URL
# =====================================================
# O Streamlit perde o session_state toda vez que a página
# recarrega sozinha (F5, uma queda de rede rápida, o navegador
# reconectando o "fio" da aplicação). Só que a URL continua a
# mesma no navegador — por isso, no login, guardamos um token
# nela (?sessao=...). Se a pessoa cair e a página recarregar,
# usamos esse token para reconhecer quem era e devolvê-la
# exatamente para onde estava, sem pedir login de novo.
#
# O MESMO vale para a aba em que a pessoa estava (?aba=...): sem
# isso, ao restaurar a sessão o app não sabia em qual tela ela
# estava e sempre voltava para "Início" — péssimo para quem deixa
# o app aberto num monitor de operação. Guardando a aba na URL
# também, a restauração devolve a pessoa para a MESMA aba de onde
# ela estava assim que a rede volta.

if not st.session_state.logado:

    token_sessao_url = st.query_params.get("sessao")

    if token_sessao_url:

        sessao_restaurada = banco.validar_sessao(token_sessao_url)

        if sessao_restaurada:

            (
                usuario_restaurado,
                tipo_restaurado,
                trocar_senha_restaurado,
                armazem_id_restaurado,
                armazem_nome_restaurado
            ) = sessao_restaurada

            st.session_state.logado = True
            st.session_state.usuario = usuario_restaurado
            st.session_state.tipo_usuario = tipo_restaurado
            st.session_state.trocar_senha = trocar_senha_restaurado
            st.session_state.armazem_id = armazem_id_restaurado
            st.session_state.armazem_nome = armazem_nome_restaurado
            st.session_state.armazem_visualizado_id = armazem_id_restaurado
            st.session_state.armazem_visualizado_nome = armazem_nome_restaurado
            st.session_state.token_sessao = token_sessao_url

            # Restaura também a aba em que a pessoa estava (se houver
            # uma salva na URL) — a validação final contra as abas
            # que esse usuário pode ver acontece mais abaixo, depois
            # que CHAVES_VALIDAS é montado.
            aba_url_restaurada = st.query_params.get("aba")

            if aba_url_restaurada:
                st.session_state.aba_atual = aba_url_restaurada

        else:

            # Token inválido/expirado: tira da URL para não ficar
            # tentando de novo a cada recarregamento.
            del st.query_params["sessao"]

# O rodapé "Sistema Online" só precisa se auto-atualizar
# depois de logar — antes disso, não há necessidade de
# ficar recarregando sozinho a cada 120s.

if st.session_state.logado:
    render_status_footer()

if "tipo_usuario" not in st.session_state:
    st.session_state.tipo_usuario = "usuario"

if "trocar_senha" not in st.session_state:
    st.session_state.trocar_senha = False

# =====================================================
# TEMA INICIAL: SEGUE O DO NAVEGADOR / SISTEMA
# =====================================================
# O config.toml fixa theme.base="dark" no Streamlit (vale para todo
# mundo), então st.context.theme.type SEMPRE responderia "dark" e
# não serve para descobrir a preferência de quem acessa. Por isso a
# detecção é feita no próprio navegador, com JavaScript
# (matchMedia "prefers-color-scheme"), uma única vez:
#
#   1. Sem ?tema= (escolha manual) nem ?tn= (tema do navegador) na
#      URL, um pequeno script lê a preferência do navegador e
#      recarrega a página já com ?tn=claro ou ?tn=escuro.
#   2. O app lê o ?tn= e abre no tema certo ("modo automático").
#   3. Quando a pessoa mexe no botão de tema, o modo automático
#      desliga e a escolha dela vai para ?tema= (vence o ?tn= e
#      sobrevive a F5 ou queda de rede).

def _detectar_tema_navegador():

    st.components.v1.html(
        """
        <script>
        (function() {
            try {
                var win = window.parent;
                var url = new win.URL(win.location.href);

                if (url.searchParams.has('tn') || url.searchParams.has('tema')) {
                    return;
                }

                var claro = win.matchMedia
                    && win.matchMedia('(prefers-color-scheme: light)').matches;

                url.searchParams.set('tn', claro ? 'claro' : 'escuro');
                win.location.replace(url.toString());
            } catch (erro) {
                // Sem acesso ao navegador: o app segue no tema escuro padrão.
            }
        })();
        </script>
        """,
        height=0
    )


def _tema_do_navegador():

    tema_navegador = st.query_params.get("tn")

    if tema_navegador in ("claro", "escuro"):
        return tema_navegador

    return None


if "tema" not in st.session_state:

    tema_url = st.query_params.get("tema")

    if tema_url in ("claro", "escuro"):

        st.session_state.tema = tema_url
        st.session_state.tema_automatico = False

    else:

        st.session_state.tema = _tema_do_navegador() or "escuro"
        st.session_state.tema_automatico = True

# Só dispara a detecção enquanto a URL ainda não tem nenhuma das
# duas marcas — depois do primeiro recarregamento isso nunca mais roda.
if (
    st.session_state.get("tema_automatico")
    and not st.query_params.get("tn")
    and not st.query_params.get("tema")
):
    _detectar_tema_navegador()

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

novo_tema = "claro" if tema_claro else "escuro"

if novo_tema != st.session_state.tema:

    # A pessoa mexeu no botão: a escolha manual passa a valer e fica
    # guardada na URL, para sobreviver a um F5 ou queda de rede.
    st.session_state.tema_automatico = False
    st.query_params["tema"] = novo_tema

st.session_state.tema = novo_tema

# =====================================================
# ESTILO
# =====================================================

estilos.aplicar_fundo(
    tema=st.session_state.tema,
    tela=(
        "login" if not st.session_state.logado
        or st.session_state.get("trocar_senha")
        else "inicio" if st.session_state.get("aba_atual", "nav_inicio") == "nav_inicio"
        else "app"
    )
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

## 📦 Controle de Estoque

Registra as entradas de mercadoria e as retiradas para uso, mostrando o saldo de cada produto e quem fez cada movimentação.

---

## 🏆 Recordes

Mostra os destaques da operação em três rankings: o SAC (quem tem menos chamados vinculados ao nome fica na frente), a Auditoria (mais acertos e menos erros) e o Top 3 de ruas do Dashboard, sempre do último mês, com busca para ver os meses anteriores. No fechamento de cada período (mês no SAC e no Dashboard, trimestre na Auditoria), quem fica entre os 3 primeiros ganha medalhas de ouro, prata e bronze, que ficam guardadas para sempre no quadro de medalhas, mesmo depois que os registros da Auditoria são apagados.

---

## 📨 Solicitações

Os colaboradores pedem folga, saída antecipada e outras solicitações direto ao supervisor escolhido (Gestão ou Fundador). O supervisor aceita ou recusa, e, em caso de recusa, o motivo fica visível para quem pediu.

---

## 📈 Histórico Produtivo

Reúne, em gráficos simples, o empenho de cada pessoa em todo o sistema — SAC, Dashboard, Checklist, Auditoria e Controle de EPI's — e aponta o que precisa melhorar.

---

## ⚙️ Administrativo

Área de gestão completa da operação: cadastro de usuários, responsáveis, atividades do rodízio, carrinhos fixos e demais parâmetros do sistema.

---

## 🎯 Objetivo do Luxiz IA

Transformar indicadores operacionais em informações simples, rápidas e visuais, auxiliando líderes e gestores na tomada de decisão diária.
        """)


if not st.session_state.logado:

    estilos.marca_desenvolvedor_login()
    efeito_login.aplicar(st.session_state.tema)

    _, col_centro, _ = st.columns([1.2, 1, 1.2])

    with col_centro:

        estilos.logo_header()

        st.markdown(
            """
            <div class="luxiz-teaser-wrap" style="justify-content:center;">
                <div class="luxiz-teaser">
                    🚀 Conheça também o
                    <a href="https://sites.google.com/view/lx-roteiriza/in%C3%ADcio"
                       target="_blank" rel="noopener noreferrer"
                       style="color:inherit;font-weight:800;text-decoration:underline;">LX&nbsp;Roteiriza</a>
                    <a href="https://sites.google.com/view/lx-roteiriza/in%C3%ADcio"
                       target="_blank" rel="noopener noreferrer"
                       title="Abrir o site do LX Roteiriza"
                       style="color:inherit;text-decoration:none;font-weight:800;">➡️</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.container(border=True, key="login-card"):

            st.markdown(
                """
                <div class="lx-card-titulo">Bem-vindo de volta 👋</div>
                <div class="lx-card-sub">
                    Entre com seu usuário e senha para acessar o painel.
                </div>
                """,
                unsafe_allow_html=True
            )

            # st.form: o Enter do teclado também faz o login
            with st.form("form_login", border=False):

                usuario = st.text_input(
                    "Usuário",
                    placeholder="Ex.: Gestao.Maria",
                    key="login_usuario"
                )

                senha = st.text_input(
                    "Senha",
                    type="password",
                    placeholder="Digite sua senha",
                    key="login_senha"
                )

                entrar = st.form_submit_button(
                    "Entrar no sistema  →",
                    width='stretch'
                )

            if entrar:

                usuario = (usuario or "").strip()

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

                    # Token de sessão salvo na URL: se a página
                    # recarregar sozinha (F5, queda de rede), o
                    # login é restaurado automaticamente.
                    token_sessao = banco.criar_sessao(usuario)
                    st.session_state.token_sessao = token_sessao
                    st.query_params["sessao"] = token_sessao

                    st.rerun()

                else:

                    st.error(
                        "Usuário ou senha inválidos."
                    )

        if st.button(
            "❓ Para que serve o Luxiz IA?",
            width='stretch',
            key="login-sobre"
        ):

            mostrar_sobre_luxiz()

        st.markdown(
            """
            <div class="lx-chips">
                <span>📊 Dashboard</span>
                <span>⚡ Remanejamento</span>
                <span>😊 SAC</span>
                <span>🎯 Auditoria</span>
                <span>📦 Estoque</span>
                <span>📈 Histórico</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.stop()

# =====================================================
# TROCA DE SENHA OBRIGATÓRIA
# (primeiro acesso com senha temporária, ou senha resetada
# por um Fundador/Gestão)
# =====================================================

if st.session_state.logado and st.session_state.get("trocar_senha"):

    estilos.marca_desenvolvedor_login()
    efeito_login.aplicar(st.session_state.tema)

    _, col_centro_senha, _ = st.columns([1, 1.1, 1])

    with col_centro_senha:

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

        with st.container(border=True, key="login-card"):

            st.markdown("#### 🔑 Defina sua nova senha")

            st.caption(
                "Este é o seu primeiro acesso (ou sua senha foi "
                "redefinida). Por segurança, crie uma senha nova "
                "antes de continuar."
            )

            nova_senha_primeiro_acesso = st.text_input(
                "Nova senha",
                type="password",
                key="nova_senha_primeiro_acesso"
            )

            confirmar_nova_senha = st.text_input(
                "Confirmar nova senha",
                type="password",
                key="confirmar_nova_senha_primeiro_acesso"
            )

            if st.button(
                "💾 Salvar nova senha",
                width='stretch'
            ):

                if not nova_senha_primeiro_acesso or not confirmar_nova_senha:

                    st.error(
                        "Preencha os dois campos para continuar."
                    )

                elif nova_senha_primeiro_acesso != confirmar_nova_senha:

                    st.error(
                        "As senhas não coincidem."
                    )

                elif len(nova_senha_primeiro_acesso) < 4:

                    st.error(
                        "A nova senha precisa ter pelo menos 4 caracteres."
                    )

                else:

                    with estilos.mostrar_processando("salvando nova senha..."):
                        banco.alterar_senha(
                            st.session_state.usuario,
                            nova_senha_primeiro_acesso
                        )

                    st.session_state.trocar_senha = False

                    estilos.notificar_sucesso("senha alterada com sucesso.")
                    st.rerun()

        st.write("")

        _, col_sair_senha = st.columns([3, 1])

        with col_sair_senha:

            if st.button(
                "🚪 Sair",
                width='stretch',
                key="sair_troca_senha"
            ):

                banco.encerrar_sessao(
                    st.session_state.get("token_sessao")
                )

                st.query_params.clear()
                st.session_state.clear()
                st.rerun()

    st.stop()

# =====================================================
# AVISO DE CONEXÃO (só depois de logado)
# =====================================================

_injetar_aviso_de_rede()

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
eh_painel = usuario_atual.startswith("Painel.")

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

elif eh_painel:
    badge = "📟 Painel Logístico"

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
            width='stretch',
            key=f"sair_{identificador}"
        ):

            banco.encerrar_sessao(
                st.session_state.get("token_sessao")
            )

            st.query_params.clear()
            st.session_state.clear()
            st.rerun()


MESES_EXTENSO = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
]


def render_cabecalho_inicio():

    from html import escape as _esc

    agora = estilos.agora_local()

    if agora.hour < 5:
        saudacao, emoji_saudacao = "Boa madrugada", "🌙"
        frase_dia = "Operação silenciosa, atenção em dobro."
    elif agora.hour < 12:
        saudacao, emoji_saudacao = "Bom dia", "☀️"
        frase_dia = "Vamos começar o dia com tudo em ordem."
    elif agora.hour < 18:
        saudacao, emoji_saudacao = "Boa tarde", "🌤️"
        frase_dia = "Acompanhe a operação em tempo real."
    else:
        saudacao, emoji_saudacao = "Boa noite", "🌆"
        frase_dia = "Fechando o dia com a operação sob controle."

    nome_armazem_atual = (
        st.session_state.get("armazem_visualizado_nome")
        or st.session_state.get("armazem_nome")
        or ""
    )

    DIAS_EXTENSO = [
        "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"
    ]

    dia_semana = DIAS_EXTENSO[agora.weekday()]
    mes_extenso = MESES_EXTENSO[agora.month - 1]

    # Usa o nome do Perfil (se a pessoa já preencheu) na saudação.
    try:
        perfil_hero_atual = banco.ler_perfil(usuario_atual)
    except Exception:
        perfil_hero_atual = None

    nome_hero = (
        (perfil_hero_atual.get("nome") or nome_exibicao)
        if perfil_hero_atual else nome_exibicao
    )

    # Foto do perfil (se existir) ou logo do app dentro do banner
    foto_hero = perfil_hero_atual.get("foto") if perfil_hero_atual else None

    if foto_hero:
        avatar_hero_html = f'<img src="{foto_hero}" alt="Perfil" style="width:100%;height:100%;object-fit:cover;border-radius:22px;">'
    else:
        try:
            avatar_hero_html = (
                f'<img src="data:image/png;base64,{estilos._logo_base64()}" '
                f'alt="Luxiz IA" style="height:46px;width:auto;">'
            )
        except Exception:
            avatar_hero_html = "✨"

    claro = st.session_state.tema == "claro"

    if claro:
        HERO_GRADIENTE = "linear-gradient(120deg, #1e40af 0%, #4f46e5 50%, #9333ea 100%)"
        HERO_SOMBRA = "0 18px 40px rgba(79,70,229,.28)"
        HERO_TEXTO_SUB = "rgba(255,255,255,.85)"
        BARRA_BG = "rgba(255,255,255,.75)"
        BARRA_BORDA = "rgba(15,23,42,.10)"
        BOTAO_BG = "rgba(15,23,42,.04)"
        BOTAO_BORDA = "rgba(15,23,42,.12)"
        BOTAO_HOVER = "rgba(79,70,229,.10)"
        BOTAO_TEXTO = "#0f172a"
    else:
        HERO_GRADIENTE = "linear-gradient(120deg, #0b1230 0%, #1e3a8a 50%, #6d28d9 100%)"
        HERO_SOMBRA = "0 18px 40px rgba(0,0,0,.5)"
        HERO_TEXTO_SUB = "rgba(226,232,240,.80)"
        BARRA_BG = "rgba(15,23,42,.55)"
        BARRA_BORDA = "rgba(255,255,255,.10)"
        BOTAO_BG = "rgba(255,255,255,.05)"
        BOTAO_BORDA = "rgba(255,255,255,.14)"
        BOTAO_HOVER = "rgba(99,102,241,.22)"
        BOTAO_TEXTO = "#e2e8f0"

    css_inicio = """
    <style>

    /* ---------- remove o "vazio" no topo da página ---------- */
    .stElementContainer:has([data-testid="stMarkdownContainer"] > style):not(:has([data-testid="stMarkdownContainer"] > :not(style))),
    .stElementContainer:has(iframe[height="0"]){
        display:none !important;
    }
    .stElementContainer:has(.luxiz-sidebar-fundo),
    .stElementContainer:has(.luxiz-sidebar-toggle-visual),
    .stElementContainer:has(.luxiz-sidebar-sub),
    .stElementContainer:has(.luxiz-sidebar-rodape),
    .stElementContainer:has(.footer-luxiz){
        margin-bottom:-1rem !important;
    }

    @keyframes lxFlutuar{
        0%,100%{ transform:translate(0,0) scale(1); }
        50%{ transform:translate(-30px,22px) scale(1.12); }
    }
    @keyframes lxBrilho{
        0%{ transform:translateX(-120%) skewX(-20deg); }
        60%,100%{ transform:translateX(320%) skewX(-20deg); }
    }
    @keyframes lxPulso{
        0%,100%{ box-shadow:0 0 0 0 rgba(34,197,94,.55); }
        50%{ box-shadow:0 0 0 7px rgba(34,197,94,0); }
    }

    /* ---------- banner ---------- */
    .lx-hero{
        position:relative;
        isolation:isolate;
        overflow:hidden;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:1.5rem;
        flex-wrap:wrap;
        padding:2rem 2.4rem;
        border-radius:1.6rem;
        background:__HERO_GRADIENTE__;
        box-shadow:__HERO_SOMBRA__;
        border:1px solid rgba(255,255,255,.14);
    }
    .lx-hero-blob{
        position:absolute;
        border-radius:50%;
        filter:blur(46px);
        opacity:.5;
        z-index:0;
        pointer-events:none;
    }
    .lx-hero-b1{
        width:280px; height:280px;
        right:12%; top:-110px;
        background:#22d3ee;
        animation:lxFlutuar 10s ease-in-out infinite;
    }
    .lx-hero-b2{
        width:320px; height:320px;
        left:34%; bottom:-190px;
        background:#d946ef;
        animation:lxFlutuar 13s ease-in-out infinite reverse;
    }
    .lx-hero-grade{
        position:absolute;
        inset:0;
        z-index:0;
        pointer-events:none;
        background-image:radial-gradient(rgba(255,255,255,.20) 1px, transparent 1px);
        background-size:22px 22px;
        -webkit-mask-image:linear-gradient(90deg, transparent 10%, #000 85%);
        mask-image:linear-gradient(90deg, transparent 10%, #000 85%);
    }
    .lx-hero-brilho{
        position:absolute;
        top:0; left:0;
        width:25%; height:100%;
        z-index:0;
        pointer-events:none;
        background:linear-gradient(100deg, transparent, rgba(255,255,255,.12), transparent);
        animation:lxBrilho 7s ease-in-out infinite;
    }
    .lx-hero-esq{
        position:relative;
        z-index:1;
        display:flex;
        align-items:center;
        gap:1.4rem;
        min-width:0;
    }
    .lx-hero-avatar{
        flex-shrink:0;
        width:84px;
        height:84px;
        border-radius:24px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:2rem;
        background:rgba(255,255,255,.14);
        border:1px solid rgba(255,255,255,.28);
        backdrop-filter:blur(10px);
        -webkit-backdrop-filter:blur(10px);
        box-shadow:0 8px 24px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.3);
    }
    .lx-hero-over{
        display:inline-flex;
        align-items:center;
        gap:.5rem;
        font-size:.74rem;
        font-weight:700;
        letter-spacing:2.2px;
        text-transform:uppercase;
        color:__HERO_TEXTO_SUB__;
    }
    .lx-hero-nome{
        font-size:2.7rem;
        font-weight:800;
        line-height:1.1;
        margin:.25rem 0 .35rem 0;
        background:linear-gradient(90deg, #ffffff 30%, #a5f3fc 100%);
        -webkit-background-clip:text;
        background-clip:text;
        -webkit-text-fill-color:transparent;
        color:transparent;
    }
    .lx-hero-frase{
        font-size:.9rem;
        color:__HERO_TEXTO_SUB__;
        margin-bottom:.85rem;
    }
    .lx-hero-chips{
        display:flex;
        flex-wrap:wrap;
        gap:.5rem;
    }
    .lx-hero-chip{
        background:rgba(255,255,255,.14);
        border:1px solid rgba(255,255,255,.24);
        backdrop-filter:blur(6px);
        -webkit-backdrop-filter:blur(6px);
        color:#ffffff;
        padding:.28rem .85rem;
        border-radius:999px;
        font-size:.78rem;
        font-weight:600;
    }
    .lx-hero-data{
        position:relative;
        z-index:1;
        text-align:center;
        min-width:170px;
        overflow:hidden;
        border-radius:1.2rem;
        background:rgba(255,255,255,.13);
        border:1px solid rgba(255,255,255,.26);
        backdrop-filter:blur(12px);
        -webkit-backdrop-filter:blur(12px);
        box-shadow:0 10px 28px rgba(0,0,0,.22);
    }
    .lx-hero-data-topo{
        padding:.35rem 1rem;
        font-size:.7rem;
        font-weight:800;
        letter-spacing:1.8px;
        text-transform:uppercase;
        color:#ffffff;
        background:rgba(255,255,255,.18);
    }
    .lx-hero-dia{
        font-size:3.6rem;
        font-weight:800;
        line-height:1;
        padding:.7rem 1rem 0 1rem;
        color:#ffffff;
    }
    .lx-hero-mes{
        margin-top:.3rem;
        font-size:.72rem;
        font-weight:700;
        letter-spacing:1.6px;
        text-transform:uppercase;
        color:__HERO_TEXTO_SUB__;
    }
    .lx-hero-hora{
        display:inline-flex;
        align-items:center;
        gap:.4rem;
        margin:.55rem 0 .8rem 0;
        padding:.2rem .7rem;
        border-radius:999px;
        font-size:.8rem;
        font-weight:700;
        color:#ffffff;
        background:rgba(0,0,0,.2);
    }
    .lx-hero-hora b{
        width:8px; height:8px;
        border-radius:50%;
        background:#22c55e;
        display:inline-block;
        animation:lxPulso 2s infinite;
    }

    @media (max-width: 760px){
        .lx-hero{ padding:1.4rem 1.2rem; }
        .lx-hero-nome{ font-size:2rem; }
        .lx-hero-avatar{ width:64px; height:64px; border-radius:18px; }
        .lx-hero-data{ width:100%; }
    }

    /* ---------- barra de status (online, sino, novidades) ---------- */
    .st-key-lx-statusbar{
        margin-top:.9rem;
        padding:.45rem .7rem;
        border-radius:1rem;
        background:__BARRA_BG__;
        border:1px solid __BARRA_BORDA__;
        backdrop-filter:blur(10px);
        -webkit-backdrop-filter:blur(10px);
    }
    .st-key-lx-statusbar [data-testid="stPopover"] button,
    .st-key-lx-statusbar [data-testid="stPopover"] > div > button{
        height:40px !important;
        min-height:40px !important;
        padding:0 1rem !important;
        border-radius:999px !important;
        background:__BOTAO_BG__ !important;
        border:1px solid __BOTAO_BORDA__ !important;
        color:__BOTAO_TEXTO__ !important;
        font-weight:600 !important;
        font-size:.85rem !important;
        box-shadow:none !important;
        white-space:nowrap;
        transition:background .15s ease, transform .15s ease, border-color .15s ease;
    }
    .st-key-lx-statusbar [data-testid="stPopover"] button:hover{
        background:__BOTAO_HOVER__ !important;
        border-color:rgba(99,102,241,.6) !important;
        transform:translateY(-1px);
    }
    .lx-sync{
        text-align:right;
        font-size:.78rem;
        opacity:.75;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
    }
    .lx-sync b{
        display:inline-block;
        width:8px; height:8px;
        margin-right:.4rem;
        border-radius:50%;
        background:#22c55e;
        animation:lxPulso 2s infinite;
    }

    /* ---------- indicadores ---------- */
    .lx-kpi{
        display:flex;
        align-items:center;
        gap:.9rem;
        min-height:88px;
        padding:.95rem 1.1rem;
        border-radius:1rem;
    }
    .lx-kpi-ico{
        flex-shrink:0;
        width:44px;
        height:44px;
        border-radius:12px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.35rem;
    }
    .lx-kpi-txt{
        min-width:0;
    }
    .lx-kpi-val{
        font-size:1.5rem;
        font-weight:800;
        line-height:1.1;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
    }
    .lx-kpi-rot{
        font-size:.76rem;
        opacity:.72;
        margin-top:.2rem;
    }

    </style>
    """

    css_inicio = (
        css_inicio
        .replace("__HERO_GRADIENTE__", HERO_GRADIENTE)
        .replace("__HERO_SOMBRA__", HERO_SOMBRA)
        .replace("__HERO_TEXTO_SUB__", HERO_TEXTO_SUB)
        .replace("__BARRA_BG__", BARRA_BG)
        .replace("__BARRA_BORDA__", BARRA_BORDA)
        .replace("__BOTAO_BG__", BOTAO_BG)
        .replace("__BOTAO_BORDA__", BOTAO_BORDA)
        .replace("__BOTAO_HOVER__", BOTAO_HOVER)
        .replace("__BOTAO_TEXTO__", BOTAO_TEXTO)
    )

    st.markdown(css_inicio, unsafe_allow_html=True)

    chip_armazem = (
        f'<span class="lx-hero-chip">🏢 {_esc(nome_armazem_atual)}</span>'
        if nome_armazem_atual else ""
    )

    st.markdown(
        f'<div class="lx-hero">'
        f'<div class="lx-hero-blob lx-hero-b1"></div>'
        f'<div class="lx-hero-blob lx-hero-b2"></div>'
        f'<div class="lx-hero-grade"></div>'
        f'<div class="lx-hero-brilho"></div>'
        f'<div class="lx-hero-esq">'
        f'<div class="lx-hero-avatar">{avatar_hero_html}</div>'
        f'<div>'
        f'<div class="lx-hero-over">{emoji_saudacao} {saudacao}</div>'
        f'<div class="lx-hero-nome">{_esc(nome_hero)}</div>'
        f'<div class="lx-hero-frase">{frase_dia}</div>'
        f'<div class="lx-hero-chips">'
        f'<span class="lx-hero-chip">{badge}</span>{chip_armazem}'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<div class="lx-hero-data">'
        f'<div class="lx-hero-data-topo">{dia_semana}</div>'
        f'<div class="lx-hero-dia">{agora.day:02d}</div>'
        f'<div class="lx-hero-mes">{mes_extenso} {agora.year}</div>'
        f'<div class="lx-hero-hora"><b></b>{agora.strftime("%H:%M")}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ---------------- usuários online ----------------

    usuarios_armazem_hero = banco.listar_usuarios(armazem_id_atual)

    perfis_armazem_hero = {
        perfil["usuario"]: perfil
        for perfil in banco.ler_perfis(armazem_id_atual)
    }

    usuarios_online_hero = []

    for uid_hero, nome_usuario_hero, tipo_usuario_hero, ultimo_acesso_hero in usuarios_armazem_hero:

        if not nome_usuario_hero or not ultimo_acesso_hero:
            continue

        segundos_desde_acesso_hero = (
            datetime.now(timezone.utc)
            - ultimo_acesso_hero.replace(tzinfo=timezone.utc)
        ).total_seconds()

        if segundos_desde_acesso_hero > 240:
            continue

        perfil_usuario_hero = perfis_armazem_hero.get(nome_usuario_hero)

        nome_exibicao_hero = (
            banco.nome_completo_perfil(perfil_usuario_hero)
            if perfil_usuario_hero else
            (
                nome_usuario_hero.split(".", 1)[1].strip().title()
                if "." in nome_usuario_hero
                else nome_usuario_hero
            )
        )

        usuarios_online_hero.append(nome_exibicao_hero)

    # ---------------- barra de status ----------------
    # Tudo dentro de UMA barra de vidro: à esquerda os três botões
    # lado a lado (mesma altura, mesmo formato), à direita a sincronização.

    with st.container(key="lx-statusbar"):

        c_online, c_sino, c_nov, c_sync = st.columns(
            [1.5, 0.6, 2.5, 3.4],
            vertical_alignment="center",
            gap="small"
        )

        with c_online:

            with st.popover(
                f"🟢 Online ({len(usuarios_online_hero)})",
                help="Online agora"
            ):

                st.caption("👥 Quem está online agora")

                if usuarios_online_hero:

                    for nome_online_hero in sorted(usuarios_online_hero):

                        st.markdown(f"🟢 {nome_online_hero}")

                else:

                    st.caption("Ninguém online no momento.")

        with c_sino:

            notificacoes.sino(usuario_atual, armazem_id_atual)

        with c_sync:

            st.markdown(
                f'<div class="lx-sync"><b></b>Sincronizado com o servidor · '
                f'atualizado às {agora.strftime("%H:%M:%S")}</div>',
                unsafe_allow_html=True
            )

    # ---------------- indicadores ----------------

    modulos_visiveis_hero = {chave for chave, _, _ in NAV_ITENS}

    kpis = []

    kpis.append((
        "🧩", "Módulos disponíveis",
        str(len(NAV_ITENS) - 1), "#a855f7"
    ))

    kpis.append((
        "🔔", "Notificações pendentes",
        str(notificacoes.contar_pendentes(usuario_atual, armazem_id_atual)),
        "#ef4444"
    ))

    if "nav_dashboard" in modulos_visiveis_hero:

        ruas_hero = banco.listar_ruas(armazem_id_atual)
        notas_hero = banco.ler_notas(armazem_id_atual)

        media_hero = (
            round(sum(notas_hero.values()) / len(notas_hero), 1)
            if notas_hero else 0
        )

        kpis.append((
            "📍", "Ruas monitoradas", str(len(ruas_hero)), "#3b82f6"
        ))

        kpis.append((
            "⭐", "Média geral das ruas", str(media_hero), "#22c55e"
        ))

    else:

        kpis.append((
            "🏢", "Armazém atual",
            nome_armazem_atual or "—", "#0ea5e9"
        ))

        kpis.append((
            "🕒", "Horário atual",
            agora.strftime("%H:%M"), "#f59e0b"
        ))

    cols_kpi = st.columns(len(kpis))

    for (icone_kpi, rotulo_kpi, valor_kpi, cor_kpi), col_kpi in zip(kpis, cols_kpi):

        with col_kpi:

            st.markdown(
                f'<div class="lx-kpi" style="background:{cor_kpi}12;'
                f'border:1px solid {cor_kpi}33;border-left:4px solid {cor_kpi};">'
                f'<div class="lx-kpi-ico" style="background:{cor_kpi}22;">{icone_kpi}</div>'
                f'<div class="lx-kpi-txt">'
                f'<div class="lx-kpi-val" style="color:{cor_kpi};">{_esc(str(valor_kpi))}</div>'
                f'<div class="lx-kpi-rot">{rotulo_kpi}</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    # ---------------- seletor de armazém (Fundador) ----------------

    if tipo == "fundador" or eh_fundador_prefixo:

        lista_armazens = banco.listar_armazens()

        nomes_armazens = [nome for _, nome in lista_armazens]
        ids_armazens = [id_ for id_, _ in lista_armazens]

        indice_atual = (
            ids_armazens.index(st.session_state.armazem_visualizado_id)
            if st.session_state.armazem_visualizado_id in ids_armazens
            else 0
        )

        col_seletor_armazem, _col_seletor_vazio = st.columns([1.3, 3])

        with col_seletor_armazem:

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

    with c_nov.popover("🆕 Novidades da versão 1.0.5"):

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
- 📈 Nova aba **Histórico Produtivo**: gráficos do seu empenho no SAC, Dashboard, Checklist, Auditoria e Controle de EPI's, mostrando o que precisa melhorar.
- 📦 Nova aba **Controle de Estoque**: entrada de mercadoria e retirada para uso, com saldo em tempo real e registro de quem deu a entrada e de quem retirou.
- 📨 Nova aba **Solicitações**: Separador, Conferente e Recebimento pedem folga, saída antecipada e outros pedidos ao supervisor (Gestão ou Fundador), que aceita ou recusa — na recusa, o motivo fica visível para quem pediu.
- 🏆 Nova aba **Recordes**: ranking do SAC (menos chamados no nome, melhor), ranking da Auditoria (mais acertos e menos erros) e o Top 3 do Dashboard do último mês, com busca para ver os meses anteriores. Cada colaborador acompanha a quantidade de medalhas 🥇🥈🥉 que conquistou nos fechamentos (mensais no SAC e no Dashboard, trimestrais na Auditoria).
- 🛍️ Nova aba **Loja Virtual** (Fundador e usuários liberados): cadastro de produtos com preço pago e preço de venda, entrada de estoque, vendas com cliente e data de pagamento, pagamentos a receber e gráficos do andamento das vendas e do lucro.
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
        ("nav_epi", "🦺", "Controle de EPI's"),
    ]

elif eh_recebimento:

    NAV_ITENS = [
        ("nav_inicio", "🏠", "Início"),
        ("nav_auditoria", "🎯", "Auditoria"),
        ("nav_checklist", "✅", "Checklist"),
        ("nav_equipamentos", "🧰", "Equipamentos"),
        ("nav_epi", "🦺", "Controle de EPI's"),
    ]

elif eh_painel:

    NAV_ITENS = [
        ("nav_inicio", "🏠", "Início"),
        ("nav_dashboard", "📊", "Dashboard"),
        ("nav_remanejamento", "⚡", "Remanejamento"),
        ("nav_sac", "😊", "SAC"),
        ("nav_auditoria", "🎯", "Auditoria"),
        ("nav_rotativo", "🔄", "Rodízio"),
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
        ("nav_epi", "🦺", "Controle de EPI's"),
        ("nav_estoque", "📦", "Controle de Estoque"),
        ("nav_administrativo", "⚙️", "Administrativo"),
    ]

# Recordes: aparece para todos os perfis.
NAV_ITENS.append(("nav_recordes", "🏆", "Recordes"))

# Solicitações: aparece para quem envia (Separador, Conferente,
# Recebimento) e para quem responde (Gestão e Fundador). Para o
# supervisor, o nome da aba mostra quantas estão aguardando resposta.
if (
    solicitacoes.eh_solicitante(usuario_atual)
    or solicitacoes.eh_supervisor(usuario_atual, tipo)
):

    nome_nav_solicitacoes = "Solicitações"

    if solicitacoes.eh_supervisor(usuario_atual, tipo):

        try:
            pendentes_solicitacoes = solicitacoes.contar_pendentes_supervisor(
                armazem_id_atual,
                usuario_atual
            )
        except Exception:
            pendentes_solicitacoes = 0

        if pendentes_solicitacoes:
            nome_nav_solicitacoes = f"Solicitações ({pendentes_solicitacoes})"

    NAV_ITENS.append(("nav_solicitacoes", "📨", nome_nav_solicitacoes))

# Loja Virtual: controle de vendas e revendas. Visível somente para
# logins "Fundador.Nome" e para os usuários liberados em
# loja.USUARIOS_LIBERADOS (ex.: Adm.Vanessa).
if loja.tem_acesso(usuario_atual, tipo):
    NAV_ITENS.append(("nav_loja", "🛍️", "Loja Virtual"))

NAV_ITENS.append(("nav_historico", "📈", "Histórico Produtivo"))
NAV_ITENS.append(("nav_perfil", "🪪", "Perfil"))
CHAVES_VALIDAS = [chave for chave, _, _ in NAV_ITENS]

if (
    "aba_atual" not in st.session_state
    or st.session_state.aba_atual not in CHAVES_VALIDAS
):
    st.session_state.aba_atual = CHAVES_VALIDAS[0]

# Mantém a URL sempre sincronizada com a aba atual — é o que
# permite, numa queda de rede seguida de reconexão, devolver a
# pessoa exatamente para a mesma tela (ver bloco de restauração de
# sessão, mais acima).
if st.query_params.get("aba") != st.session_state.aba_atual:
    st.query_params["aba"] = st.session_state.aba_atual


def ir_para_aba(chave_destino):
    """
    Troca a aba atual e já grava a escolha na URL (?aba=...), para
    que uma queda de rede seguida de reconexão devolva a pessoa
    para essa mesma aba em vez de cair na tela Início.
    """

    st.session_state.aba_atual = chave_destino
    st.query_params["aba"] = chave_destino
    st.rerun()


@st.fragment
def render_sidebar():

    # =====================================================
    # BARRA LATERAL (construída com CSS, não usa st.sidebar)
    # =====================================================

    if "sidebar_aberta" not in st.session_state:
        st.session_state.sidebar_aberta = True

    # O clique no toggle é resolvido AQUI, antes de qualquer CSS ou
    # rótulo que dependa de sidebar_aberta. Assim, quando o estado
    # muda, todo o resto da função (largura do painel, CSS, rótulo
    # do botão, nomes dos itens de navegação) já enxerga o valor
    # novo — tudo numa única passada consistente, sem precisar de
    # st.rerun() (que já dispara sozinho, uma vez, por ser um botão
    # dentro de um fragment).
    if st.button(
        "\u200b",
        key="toggle_sidebar_luxiz"
    ):
        st.session_state.sidebar_aberta = not st.session_state.sidebar_aberta

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
        COR_BOTAO_NAV_INATIVO = "rgba(15,23,42,.035)"
        COR_BOTAO_NAV_INATIVO_HOVER = "rgba(15,23,42,.07)"
        COR_BORDA_BOTAO_NAV = "rgba(15,23,42,.08)"
        COR_TEXTO_BOTAO_NAV = "#334155"
    else:
        COR_FUNDO_SIDEBAR = "linear-gradient(180deg, rgba(8,12,24,.95), rgba(8,12,24,.88))"
        COR_BORDA_SIDEBAR = "rgba(255,255,255,.08)"
        COR_SOMBRA_SIDEBAR = "2px 0 18px rgba(0,0,0,.25)"
        COR_TEXTO_TOGGLE = "#e2e8f0"
        COR_BOTAO_NAV_INATIVO = "rgba(255,255,255,.04)"
        COR_BOTAO_NAV_INATIVO_HOVER = "rgba(255,255,255,.09)"
        COR_BORDA_BOTAO_NAV = "rgba(255,255,255,.08)"
        COR_TEXTO_BOTAO_NAV = "#cbd5e1"

    extra_css_fechado = "" if st.session_state.sidebar_aberta else """
        div[class*="st-key-nav_"] button{
            text-align:center !important;
            padding-left:0 !important;
            font-size:1.15rem !important;
        }
    """

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
            color:transparent !important;
            width:100%;
            height:40px;
            padding:.3rem 0 !important;
        }}
        div[class*="st-key-toggle_sidebar_luxiz"] button:hover ~ .luxiz-sidebar-toggle-visual,
        .luxiz-sidebar-toggle-visual:hover{{
            filter:brightness(1.25);
        }}
        .luxiz-sidebar-toggle-visual{{
            position:fixed;
            left:0;
            top:16px;
            width:{LARGURA_PAINEL_PX}px;
            height:40px;
            z-index:999998;
            display:flex;
            align-items:center;
            justify-content:center;
            gap:0;
            pointer-events:none;
            overflow:hidden;
            transition:width .18s ease;
        }}
        .luxiz-sidebar-toggle-visual img{{
            height:28px;
            width:auto;
            display:block;
            flex-shrink:0;
        }}
        .luxiz-sidebar-toggle-visual span{{
            font-weight:800;
            font-size:1.05rem;
            letter-spacing:.4px;
            color:{COR_TEXTO_TOGGLE};
            white-space:nowrap;
            margin-left:-10px;
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
            margin-bottom:8px;
            width:100%;
        }}
        div[class*="st-key-nav_"] > div{{
            width:100%;
        }}
        div[class*="st-key-nav_"] div[data-testid="stButton"]{{
            width:100%;
        }}
        div[class*="st-key-nav_"] button{{
            width:100% !important;
            display:block;
            height:44px;
            min-height:44px;
            max-height:44px;
            border-radius:12px !important;
            border-width:1px !important;
            border-style:solid !important;
            text-align:left;
            padding-left:16px !important;
            font-size:.92rem;
            font-weight:600 !important;
            white-space:nowrap;
            position:relative;
            overflow:hidden;
            box-sizing:border-box;
            transition:transform .15s ease, filter .15s ease,
                background .15s ease, box-shadow .15s ease, border-color .15s ease;
        }}
        div[class*="st-key-nav_"] button p{{
            font-weight:inherit !important;
            position:relative;
            z-index:1;
        }}

        /* Reflexo de vidro: uma faixa de brilho que desliza sobre o
           botão quando o mouse passa por cima — igual nos dois estados. */
        div[class*="st-key-nav_"] button::before{{
            content:"";
            position:absolute;
            top:0;
            left:-130%;
            width:55%;
            height:100%;
            background:linear-gradient(115deg, transparent, rgba(255,255,255,.55), transparent);
            transform:skewX(-18deg);
            transition:left .55s ease;
            pointer-events:none;
            z-index:0;
        }}
        div[class*="st-key-nav_"] button:hover::before{{
            left:140%;
        }}

        div[class*="st-key-nav_"] button[kind="secondary"]{{
            background:{COR_BOTAO_NAV_INATIVO} !important;
            border-color:{COR_BORDA_BOTAO_NAV} !important;
            color:{COR_TEXTO_BOTAO_NAV} !important;
            box-shadow:none !important;
        }}
        div[class*="st-key-nav_"] button[kind="secondary"]:hover{{
            background:{COR_BOTAO_NAV_INATIVO_HOVER} !important;
            border-color:rgba(0,200,255,.35) !important;
            color:{COR_TEXTO_TOGGLE} !important;
        }}
        div[class*="st-key-nav_"] button[kind="primary"]{{
            background:linear-gradient(135deg,#00c8ff,#a855f7) !important;
            border-color:transparent !important;
            color:#ffffff !important;
            box-shadow:0 2px 8px rgba(124,58,237,.30) !important;
        }}
        div[class*="st-key-nav_"] button[kind="primary"]:hover{{
            filter:brightness(1.08);
        }}
        {extra_css_fechado}
        .block-container{{
            padding-left:{LARGURA_PAINEL_PX + (32 if st.session_state.sidebar_aberta else 24)}px !important;
            transition:padding-left .18s ease;
        }}
        </style>
        <div class="luxiz-sidebar-fundo"></div>
        """,
        unsafe_allow_html=True
    )

    _logo_toggle_b64 = estilos._logo_base64()

    st.markdown(
        f"""
        <div class="luxiz-sidebar-toggle-visual">
            <img src="data:image/png;base64,{_logo_toggle_b64}" alt="Luxiz IA">
            {'<span>Luxiz IA</span>' if st.session_state.sidebar_aberta else ''}
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.sidebar_aberta:

        st.markdown(
            '<div class="luxiz-sidebar-sub">Navegação</div>',
            unsafe_allow_html=True
        )

    with st.container(key="painel_navegacao_scroll"):

        for indice, (chave, icone, nome) in enumerate(NAV_ITENS):

            ativo = st.session_state.aba_atual == chave

            rotulo_nav = (
                f"{icone}   {nome}"
                if st.session_state.sidebar_aberta
                else icone
            )

            if st.button(
                rotulo_nav,
                key=chave,
                type="primary" if ativo else "secondary"
            ):
                ir_para_aba(chave)

    # =====================================================
    # RODAPÉ DA BARRA LATERAL (bolinha online + usuário logado)
    # =====================================================
    # Fica sempre fixo, acima da barra global "Sistema Online" do
    # rodapé da página — só a área de navegação (acima) rola.

    perfil_atual_sidebar = banco.ler_perfil(usuario_atual)

    if perfil_atual_sidebar:
        nome_perfil_sidebar = banco.nome_completo_perfil(perfil_atual_sidebar)
        foto_perfil_sidebar = perfil_atual_sidebar.get("foto")
    else:
        nome_perfil_sidebar = nome_exibicao
        foto_perfil_sidebar = None

    if foto_perfil_sidebar:

        avatar_html_sidebar = (
            f'<img src="{foto_perfil_sidebar}" style="'
            f'width:24px;height:24px;border-radius:50%;object-fit:cover;'
            f'flex-shrink:0;">'
        )

    else:

        iniciais_sidebar = "".join(
            p[0].upper() for p in nome_perfil_sidebar.split()[:2]
        ) or "?"

        avatar_html_sidebar = (
            f'<div style="'
            f'width:24px;height:24px;border-radius:50%;flex-shrink:0;'
            f'background:linear-gradient(135deg,#3b82f6,#a855f7);'
            f'display:flex;align-items:center;justify-content:center;'
            f'color:white;font-weight:800;font-size:.62rem;'
            f'">{iniciais_sidebar}</div>'
        )

    rotulo_rodape_sidebar = (
        f'{avatar_html_sidebar}<span class="luxiz-sidebar-rodape-nome">{nome_perfil_sidebar}</span>'
        if st.session_state.sidebar_aberta
        else avatar_html_sidebar
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
            gap:8px;
            z-index:999998;
            font-size:.78rem;
            font-weight:700;
            color:{COR_TEXTO_TOGGLE};
            white-space:nowrap;
            overflow:hidden;
            padding:0 12px;
            border-top:1px solid {COR_BORDA_SIDEBAR};
            background:{COR_FUNDO_SIDEBAR};
            transition:width .18s ease;
        }}
        .luxiz-sidebar-rodape-nome{{
            overflow:hidden;
            text-overflow:ellipsis;
            white-space:nowrap;
            min-width:0;
        }}
        </style>
        <div class="luxiz-sidebar-rodape">{rotulo_rodape_sidebar}</div>
        """,
        unsafe_allow_html=True
    )


render_sidebar()
aba_inicio = st.session_state.aba_atual == "nav_inicio"
aba_dashboard = st.session_state.aba_atual == "nav_dashboard"
aba_remanejamento = st.session_state.aba_atual == "nav_remanejamento"
aba_sac = st.session_state.aba_atual == "nav_sac"
aba_auditoria = st.session_state.aba_atual == "nav_auditoria"
aba_rotativo = st.session_state.aba_atual == "nav_rotativo"
aba_checklist = st.session_state.aba_atual == "nav_checklist"
aba_equipamentos = st.session_state.aba_atual == "nav_equipamentos"
aba_epi = st.session_state.aba_atual == "nav_epi"
aba_estoque = st.session_state.aba_atual == "nav_estoque"
aba_solicitacoes = st.session_state.aba_atual == "nav_solicitacoes"
aba_recordes = st.session_state.aba_atual == "nav_recordes"
aba_loja = st.session_state.aba_atual == "nav_loja"
aba_historico = st.session_state.aba_atual == "nav_historico"
aba_perfil = st.session_state.aba_atual == "nav_perfil"
aba_admin = st.session_state.aba_atual == "nav_administrativo"


# =====================================================
# INÍCIO
# =====================================================

def render_conteudo_inicio():

    claro_inicio = st.session_state.tema == "claro"

    COR_TEXTO_INICIO = "#0f172a" if claro_inicio else "#e2e8f0"

    DESCRICOES_MODULOS = {
        "nav_dashboard": "Notas de organização por rua, em tempo real.",
        "nav_remanejamento": "Prioridades operacionais monitoradas ao vivo.",
        "nav_sac": "Metas de reclamações e análise técnica por pessoa.",
        "nav_auditoria": "Acertos e erros de cada colaborador, com histórico.",
        "nav_rotativo": "Escala automática das atividades de fim de expediente.",
        "nav_checklist": "Inspeção de hidráulicos, carrinhos, empilhadeiras e pigmentação.",
        "nav_equipamentos": "Responsáveis por hidráulicos e carrinhos, e carrinhos fixos por local.",
        "nav_epi": "Registro de entrega de EPIs, com assinatura digital do colaborador.",
        "nav_estoque": "Entradas e retiradas de mercadoria, com saldo em tempo real.",
        "nav_solicitacoes": "Pedidos de folga e saída antecipada, com resposta do supervisor.",
        "nav_recordes": "Rankings do SAC, da Auditoria e Top 3 do Dashboard por mês.",
        "nav_loja": "Produtos, estoque, vendas e pagamentos a receber, com gráficos.",
        "nav_historico": "Gráficos do seu empenho e do que precisa melhorar.",
        "nav_perfil": "Seus dados, foto e função dentro do sistema.",
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
        "nav_epi": "#f97316",
        "nav_estoque": "#10b981",
        "nav_solicitacoes": "#e11d48",
        "nav_recordes": "#eab308",
        "nav_loja": "#d946ef",
        "nav_historico": "#14b8a6",
        "nav_perfil": "#8b5cf6",
        "nav_administrativo": "#64748b",
    }

    # Os módulos são mostrados em grupos, para a tela ficar organizada
    # mesmo quando o perfil tem muitos acessos.
    GRUPOS_MODULOS = [
        ("Operação", [
            "nav_dashboard", "nav_remanejamento", "nav_sac",
            "nav_auditoria", "nav_rotativo",
        ]),
        ("Equipamentos e materiais", [
            "nav_checklist", "nav_equipamentos", "nav_epi", "nav_estoque",
        ]),
        ("Pessoas e desempenho", [
            "nav_solicitacoes", "nav_recordes", "nav_historico", "nav_perfil",
        ]),
        ("Gestão", [
            "nav_administrativo", "nav_loja",
        ]),
    ]

    modulos_disponiveis = {
        chave: (icone, nome)
        for chave, icone, nome in NAV_ITENS
        if chave != "nav_inicio"
    }

    grupos_visiveis = []
    ja_agrupados = set()

    for titulo_grupo, chaves_grupo in GRUPOS_MODULOS:

        itens_grupo = [
            (chave, modulos_disponiveis[chave][0], modulos_disponiveis[chave][1])
            for chave in chaves_grupo
            if chave in modulos_disponiveis
        ]

        if itens_grupo:
            grupos_visiveis.append((titulo_grupo, itens_grupo))
            ja_agrupados.update(chave for chave, _, _ in itens_grupo)

    itens_restantes = [
        (chave, icone, nome)
        for chave, (icone, nome) in modulos_disponiveis.items()
        if chave not in ja_agrupados
    ]

    if itens_restantes:
        grupos_visiveis.append(("Outros", itens_restantes))

    # ---------------- estilo da página ----------------

    css_cards_modulos = "".join(
        f"""
        .st-key-home-mod-{chave}{{
            border:1px solid {CORES_MODULOS.get(chave, "#3b82f6")}33 !important;
            background:{CORES_MODULOS.get(chave, "#3b82f6")}0a !important;
            border-radius:1rem !important;
            transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }}
        .st-key-home-mod-{chave}:hover{{
            border-color:{CORES_MODULOS.get(chave, "#3b82f6")}88 !important;
            box-shadow:0 10px 26px {CORES_MODULOS.get(chave, "#3b82f6")}26;
            transform:translateY(-2px);
        }}
        .st-key-home-ir-{chave} button{{
            height:38px !important;
            min-height:38px !important;
            border-radius:10px !important;
            background:transparent !important;
            border:1px solid {CORES_MODULOS.get(chave, "#3b82f6")}55 !important;
            color:{COR_TEXTO_INICIO} !important;
            font-weight:700 !important;
            font-size:.8rem !important;
            box-shadow:none !important;
        }}
        .st-key-home-ir-{chave} button:hover{{
            background:{CORES_MODULOS.get(chave, "#3b82f6")}1c !important;
            border-color:{CORES_MODULOS.get(chave, "#3b82f6")} !important;
            transform:none !important;
        }}
        """
        for chave in modulos_disponiveis
    )

    css_base_inicio = """
    <style>
    .lx-secao{
        margin:1.8rem 0 .1rem 0;
    }
    .lx-secao-titulo{
        font-size:1.35rem;
        font-weight:800;
        letter-spacing:.2px;
    }
    .lx-secao-sub{
        font-size:.86rem;
        opacity:.65;
        margin-top:.15rem;
    }
    .lx-grupo{
        display:flex;
        align-items:center;
        gap:.8rem;
        margin:1.2rem 0 .1rem 0;
    }
    .lx-grupo span{
        font-size:.7rem;
        font-weight:800;
        letter-spacing:1.6px;
        text-transform:uppercase;
        opacity:.6;
        white-space:nowrap;
    }
    .lx-grupo i{
        flex:1;
        height:1px;
        background:rgba(148,163,184,.28);
    }
    .lx-mod-topo{
        display:flex;
        align-items:center;
        gap:.75rem;
    }
    .lx-mod-ico{
        flex-shrink:0;
        width:42px;
        height:42px;
        border-radius:12px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.3rem;
    }
    .lx-mod-nome{
        font-weight:700;
        font-size:1rem;
        line-height:1.2;
    }
    .lx-mod-desc{
        font-size:.8rem;
        opacity:.7;
        line-height:1.4;
        margin:.6rem 0 .2rem 0;
        min-height:3em;
    }
    .lx-perfil{
        border-radius:1.1rem;
        padding:1.3rem 1.5rem;
    }
    .lx-perfil-cab{
        display:flex;
        align-items:center;
        gap:1rem;
    }
    .lx-perfil-ico{
        flex-shrink:0;
        width:50px;
        height:50px;
        border-radius:14px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
    }
    .lx-perfil-titulo{
        font-size:1.15rem;
        font-weight:800;
    }
    .lx-perfil-desc{
        font-size:.84rem;
        opacity:.75;
        margin-top:.1rem;
    }
    .lx-perfil-rotulo{
        font-size:.68rem;
        font-weight:800;
        letter-spacing:1.4px;
        text-transform:uppercase;
        opacity:.55;
        margin:1.1rem 0 .4rem 0;
    }
    .lx-chip{
        display:inline-flex;
        align-items:center;
        gap:.4rem;
        padding:.35rem .8rem;
        border-radius:999px;
        font-size:.8rem;
        font-weight:600;
        margin:.2rem .35rem .2rem 0;
    }
    </style>
    """

    st.markdown(
        css_base_inicio + "<style>" + css_cards_modulos + "</style>",
        unsafe_allow_html=True
    )

    def _titulo_secao(titulo, subtitulo):

        st.markdown(
            f'<div class="lx-secao">'
            f'<div class="lx-secao-titulo">{titulo}</div>'
            f'<div class="lx-secao-sub">{subtitulo}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ---------------- acesso rápido ----------------

    _titulo_secao(
        "🚀 Acesso rápido",
        "Clique em um módulo para abrir direto, ou use a barra lateral."
    )

    for titulo_grupo, itens_grupo in grupos_visiveis:

        st.markdown(
            f'<div class="lx-grupo"><span>{titulo_grupo}</span><i></i></div>',
            unsafe_allow_html=True
        )

        for inicio_linha in range(0, len(itens_grupo), 3):

            linha = st.columns(3)

            for offset in range(3):

                indice = inicio_linha + offset

                if indice >= len(itens_grupo):
                    continue

                chave, icone, nome = itens_grupo[indice]

                cor = CORES_MODULOS.get(chave, "#3b82f6")

                with linha[offset]:

                    with st.container(border=True, key=f"home-mod-{chave}"):

                        st.markdown(
                            f'<div class="lx-mod-topo">'
                            f'<div class="lx-mod-ico" style="background:{cor}22;">{icone}</div>'
                            f'<div class="lx-mod-nome">{nome}</div>'
                            f'</div>'
                            f'<div class="lx-mod-desc">{DESCRICOES_MODULOS.get(chave, "")}</div>',
                            unsafe_allow_html=True
                        )

                        if st.button(
                            "Abrir módulo →",
                            key=f"home-ir-{chave}",
                            width='stretch'
                        ):
                            ir_para_aba(chave)

    # ---------------- permissões do perfil ----------------

    _titulo_secao(
        "🔐 Permissões do perfil",
        "O que o seu login pode ver e fazer dentro do Luxiz IA."
    )

    PERFIS_PERMISSOES = {
        "fundador": (
            "👑", "Fundador", "#f59e0b",
            "Controle total do sistema, sem restrições.",
            [
                ("👥", "Criar usuários"),
                ("🛡️", "Criar gestores"),
                ("🗑️", "Excluir usuários"),
                ("🗑️", "Excluir gestores"),
                ("🔑", "Resetar senhas"),
                ("📨", "Responder solicitações"),
                ("🛍️", "Loja Virtual"),
                ("⚙️", "Controle total do sistema"),
            ]
        ),
        "gestao": (
            "🛡️", "Gestão", "#3b82f6",
            "Gerencia a operação e o time no dia a dia.",
            [
                ("👥", "Criar usuários"),
                ("🗑️", "Excluir usuários comuns"),
                ("🔑", "Resetar senhas"),
                ("📨", "Responder solicitações"),
                ("📋", "Gerenciar operação"),
            ]
        ),
        "painel": (
            "📟", "Painel Logístico", "#6366f1",
            "Visão consolidada e ao vivo da operação, sem acesso administrativo.",
            [
                ("📊", "Dashboard"),
                ("⚡", "Remanejamento"),
                ("😊", "SAC"),
                ("🎯", "Auditoria"),
                ("🔄", "Rodízio"),
            ]
        ),
        "separador": (
            "📦", "Separador", "#22c55e",
            "Acesso focado na rotina operacional do separador.",
            [
                ("📊", "Dashboard"),
                ("😊", "SAC"),
                ("🔄", "Rodízio"),
                ("✅", "Checklist"),
                ("📨", "Solicitações"),
            ]
        ),
        "conferente": (
            "🔎", "Conferente", "#06b6d4",
            "Acesso focado na rotina operacional do conferente.",
            [
                ("📊", "Dashboard"),
                ("😊", "SAC"),
                ("🔄", "Rodízio"),
                ("✅", "Checklist"),
                ("📨", "Solicitações"),
            ]
        ),
        "recebimento": (
            "📥", "Recebimento", "#a855f7",
            "Acesso focado na conferência e na própria auditoria.",
            [
                ("🎯", "Auditoria (apenas o próprio card)"),
                ("✅", "Checklist"),
                ("📨", "Solicitações"),
            ]
        ),
        "usuario": (
            "👤", "Usuário", "#64748b",
            "Acesso padrão à operação do dia a dia.",
            [
                ("📊", "Dashboard"),
                ("😊", "SAC"),
                ("⚡", "Remanejamento"),
                ("🎯", "Auditoria"),
                ("🔄", "Rodízio"),
                ("✅", "Checklist"),
                ("📦", "Controle de Estoque"),
                ("⚙️", "Administrativo operacional"),
            ]
        ),
    }

    # Recordes está liberado para todos os perfis
    for _perfil_chave in PERFIS_PERMISSOES:
        PERFIS_PERMISSOES[_perfil_chave][4].append(("🏆", "Recordes"))

    if tipo == "fundador" or eh_fundador_prefixo:
        perfil_chave_atual = "fundador"
    elif tipo == "gestao" or eh_gestao_prefixo:
        perfil_chave_atual = "gestao"
    elif eh_painel:
        perfil_chave_atual = "painel"
    elif eh_separador:
        perfil_chave_atual = "separador"
    elif eh_conferente:
        perfil_chave_atual = "conferente"
    elif eh_recebimento:
        perfil_chave_atual = "recebimento"
    else:
        perfil_chave_atual = "usuario"

    icone_perfil, titulo_perfil, cor_perfil, desc_perfil, lista_permissoes = (
        PERFIS_PERMISSOES[perfil_chave_atual]
    )

    chips_permissoes_html = "".join(
        f'<span class="lx-chip" style="background:{cor_perfil}14;'
        f'border:1px solid {cor_perfil}40;">{emoji_p} {texto_p}</span>'
        for emoji_p, texto_p in lista_permissoes
    )

    st.markdown(
        f'<div class="lx-perfil" style="background:linear-gradient(90deg,{cor_perfil}16,{cor_perfil}05 70%);'
        f'border:1px solid {cor_perfil}33;border-left:4px solid {cor_perfil};">'
        f'<div class="lx-perfil-cab">'
        f'<div class="lx-perfil-ico" style="background:{cor_perfil}25;">{icone_perfil}</div>'
        f'<div>'
        f'<div class="lx-perfil-titulo" style="color:{cor_perfil};">{titulo_perfil}</div>'
        f'<div class="lx-perfil-desc">{desc_perfil}</div>'
        f'</div>'
        f'</div>'
        f'<div class="lx-perfil-rotulo">✅ Acessos liberados</div>'
        f'<div>{chips_permissoes_html}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ---------------- como cadastrar usuários ----------------

    if (tipo == "fundador" or eh_fundador_prefixo) or (tipo == "gestao" or eh_gestao_prefixo):

        _titulo_secao(
            "👥 Como cadastrar usuários",
            "Guia rápido para tirar as dúvidas mais comuns na hora de criar um novo acesso."
        )

        with st.expander("❓ Passo a passo para criar um usuário", expanded=False):

            st.markdown(
                "**1.** Vá em **⚙️ Administrativo → 👥 Usuários → ➕ Criar novo usuário**."
            )

            st.markdown(
                "**2.** No campo **Usuário**, digite sempre no formato "
                "`Função.Nome` — o prefixo antes do ponto define o que a "
                "pessoa pode ver e fazer no sistema, e também gera o "
                "emblema colorido dela na lista de usuários. Funções "
                "disponíveis:"
            )

            col_funcoes_a, col_funcoes_b = st.columns(2)

            with col_funcoes_a:
                st.markdown(
                    """
                    - `Gestao.` 🛡️ — acesso de gestão
                    - `Separador.` 📦
                    - `Conferente.` 🔎
                    - `Painel.` 📟 — Dashboard, Remanejamento,
                      SAC, Auditoria e Rodízio
                    """
                )

            with col_funcoes_b:
                st.markdown(
                    """
                    - `Recebimento.` 📥
                    - `Empilhador.` 🏗️
                    - `Assistente.` 🧑‍💼 (Assistente Logístico)
                    """
                )

            st.markdown(
                "**Exemplos válidos:** `Separador.Joao`, `Conferente.Maria`, "
                "`Empilhador.PedroSilva`."
            )

            st.markdown(
                "**3.** Defina uma **Senha Inicial** — pode ser qualquer "
                "senha temporária, a pessoa poderá trocá-la depois no "
                "primeiro acesso."
            )

            st.markdown(
                "**4.** Clique em **➕ Criar Usuário**. O login já aparece "
                "na lista \"Usuários cadastrados\" logo abaixo, com o "
                "emblema da função."
            )

            st.warning(
                "⚠️ O nome depois do ponto precisa ser igual ao nome usado "
                "nos cadastros de Auditoria, EPI etc. (ex.: se o usuário é "
                "`Separador.Joao`, os registros devem usar \"Joao\"). É "
                "assim que o sistema reconhece que os registros pertencem "
                "àquela pessoa e libera a visão certa para ela."
            )

    # ---------------- modo de usar ----------------

    _titulo_secao(
        "📖 Modo de usar",
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
            "As reclamações do mês são contadas sozinhas, conforme os chamados "
            "são registrados na Análise Técnica. No Administrativo você define "
            "apenas a meta do mês; acompanhe as ocorrências por pessoa nos cards.",
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
            "🦺", "Controle de EPI's", "#f97316",
            "Registre o EPI entregue a cada colaborador. A pessoa (usuário "
            "Separador/Conferente/Recebimento com o mesmo nome) vê a "
            "pendência e assina digitalmente confirmando o recebimento.",
            "Ter um registro confiável, com assinatura, de cada EPI entregue."
        ),
        (
            "📦", "Controle de Estoque", "#10b981",
            "Registre cada entrada de mercadoria e cada retirada para uso, "
            "informando quem deu a entrada ou quem retirou. O saldo de cada "
            "produto é calculado sozinho.",
            "Saber o que temos em estoque, evitar falta de material e ter o "
            "registro de quem movimentou cada item."
        ),
        (
            "🏆", "Recordes", "#eab308",
            "Abra a aba e escolha SAC, Auditoria ou Dashboard. No SAC, quem "
            "tem menos chamados no nome fica na frente; na Auditoria, ganha "
            "quem acerta mais e erra menos; no Dashboard aparece o Top 3 de "
            "ruas do último mês (use a busca para ver meses anteriores). Na sub-aba "
            "Medalhas você vê quantas 🥇🥈🥉 já conquistou nos fechamentos de cada período.",
            "Reconhecer quem mais se empenha e motivar todos a subir de posição."
        ),
        (
            "📨", "Solicitações", "#e11d48",
            "Colaboradores (Separador, Conferente, Recebimento): escolha o "
            "supervisor, o tipo de pedido (folga, saída antecipada etc.), o dia "
            "e explique o motivo. Supervisores (Gestão e Fundador): abra a aba "
            "Recebidas e aceite ou recuse; ao recusar, o motivo é obrigatório.",
            "Dar um canal simples e registrado para os pedidos do dia a dia, "
            "com resposta clara — quem pediu sempre sabe o resultado e, se "
            "recusado, o porquê."
        ),
        (
            "🛍️", "Loja Virtual", "#d946ef",
            "Cadastre cada produto com o preço pago e o preço de venda. Quando "
            "comprar mais, registre em Entrada de estoque. A cada venda, "
            "informe o cliente, a quantidade e se já foi pago ou quando vai "
            "pagar; o estoque e o lucro são calculados sozinhos. Em A receber "
            "você acompanha quem ainda deve, e no Painel vê os gráficos. Na aba "
            "Lingerie, lance cada peça vendida: o total soma sozinho e a comissão "
            "é de 30% até R$ 500,00 e de 40% acima disso.",
            "Ter o controle completo de compras, vendas, estoque, lucro e "
            "pagamentos pendentes em um só lugar."
        ),
        (
            "📈", "Histórico Produtivo", "#14b8a6",
            "Abra a aba para ver os gráficos do seu empenho no SAC, Dashboard, "
            "Checklist, Auditoria e Controle de EPI's. Verde significa em dia; "
            "amarelo e vermelho mostram onde há o que melhorar.",
            "Mostrar a cada pessoa, de forma simples e visual, o que ela precisa "
            "melhorar dentro do sistema."
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
        "Controle de EPI's": "nav_epi",
        "Controle de Estoque": "nav_estoque",
        "Solicitações": "nav_solicitacoes",
        "Recordes": "nav_recordes",
        "Loja Virtual": "nav_loja",
        "Histórico Produtivo": "nav_historico",
        "Administrativo": "nav_administrativo",
    }

    itens_modo_de_usar = [
        item for item in MODO_DE_USAR
        if mapa_modo_de_usar.get(item[1]) in modulos_visiveis
    ]

    col_modo_a, col_modo_b = st.columns(2)

    for posicao, (icone, nome, cor, como_usar, objetivo) in enumerate(itens_modo_de_usar):

        with (col_modo_a if posicao % 2 == 0 else col_modo_b):

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

    botao_sair_rodape("inicio")

if aba_inicio:
    with estilos.mostrar_processando("Carregando..."):
        render_cabecalho_inicio()
        notificacoes.renderizar(usuario_atual, armazem_id_atual)
        render_conteudo_inicio()

@st.fragment(run_every=120)
def render_aba_dashboard():

    with estilos.mostrar_processando("Carregando..."):
        dashboard.render()

    st.write("")
    botao_sair_rodape("dashboard")

if aba_dashboard:
    render_aba_dashboard()

# =====================================================
# REMANEJAMENTO
# =====================================================

@st.fragment
def render_aba_remanejamento():

    with estilos.mostrar_processando("Carregando..."):
        remanejamento.render()

    st.write("")
    botao_sair_rodape("remanejamento")

if aba_remanejamento:
    render_aba_remanejamento()

# =====================================================
# SAC
# =====================================================

@st.fragment(run_every=120)
def render_aba_sac():

    with estilos.mostrar_processando("Carregando..."):
        sac.render()

    st.write("")
    botao_sair_rodape("sac")

if aba_sac:
    render_aba_sac()

# =====================================================
# AUDITORIA DE ATIVIDADES
# =====================================================

@st.fragment(run_every=120)
def render_aba_auditoria():

    with estilos.mostrar_processando("Carregando..."):
        auditoria.render()

    st.write("")
    botao_sair_rodape("auditoria")

if aba_auditoria:
    render_aba_auditoria()

# =====================================================
# RODÍZIO - FIM DE EXPEDIENTE
# =====================================================

@st.fragment(run_every=120)
def render_aba_rotativo():

    with estilos.mostrar_processando("Carregando..."):
        rotativo.render()

    st.write("")
    botao_sair_rodape("rotativo")

if aba_rotativo:
    render_aba_rotativo()

# =====================================================
# CHECKLIST
# =====================================================

@st.fragment
def render_aba_checklist():

    with estilos.mostrar_processando("Carregando..."):
        checklist.render()

    st.write("")
    botao_sair_rodape("checklist")

if aba_checklist:
    render_aba_checklist()

# =====================================================
# EQUIPAMENTOS
# =====================================================

@st.fragment(run_every=120)
def render_aba_equipamentos():

    with estilos.mostrar_processando("Carregando..."):
        equipamentos.render()

    st.write("")
    botao_sair_rodape("equipamentos")

if aba_equipamentos:
    render_aba_equipamentos()

# =====================================================
# CONTROLE DE EPI's
# =====================================================

@st.fragment
def render_aba_epi():

    with estilos.mostrar_processando("Carregando..."):
        epi.render()

    st.write("")
    botao_sair_rodape("epi")

if aba_epi:
    render_aba_epi()

# =====================================================
# CONTROLE DE ESTOQUE
# =====================================================
# Sem run_every de propósito: a aba tem formulários e st.tabs(), e
# um recarregamento automático no meio do preenchimento apagaria o
# que a pessoa estava digitando.

@st.fragment
def render_aba_estoque():

    with estilos.mostrar_processando("Carregando..."):
        estoque.render()

    st.write("")
    botao_sair_rodape("estoque")

if aba_estoque:
    render_aba_estoque()

# =====================================================
# SOLICITAÇÕES
# =====================================================
# Sem run_every, pelo mesmo motivo do estoque: formulários e
# campos de texto (motivo da recusa) não podem ser apagados por um
# recarregamento automático enquanto a pessoa digita.

@st.fragment
def render_aba_solicitacoes():

    with estilos.mostrar_processando("Carregando..."):
        solicitacoes.render()

    st.write("")
    botao_sair_rodape("solicitacoes")

if aba_solicitacoes:
    render_aba_solicitacoes()

# =====================================================
# RECORDES
# =====================================================
# Sem run_every: a aba tem seletores (período, função, mês) e um
# recarregamento automático faria a escolha da pessoa piscar/voltar.

@st.fragment
def render_aba_recordes():

    with estilos.mostrar_processando("Carregando..."):
        recordes.render()

    st.write("")
    botao_sair_rodape("recordes")

if aba_recordes:
    render_aba_recordes()

# =====================================================
# LOJA VIRTUAL
# =====================================================
# Sem run_every: a aba tem formulários, seletores e campos de texto,
# e um recarregamento automático apagaria o que a pessoa estava
# preenchendo no meio de um cadastro ou de uma venda.

@st.fragment
def render_aba_loja():

    with estilos.mostrar_processando("Carregando..."):
        loja.render()

    st.write("")
    botao_sair_rodape("loja")

if aba_loja:
    render_aba_loja()

# =====================================================
# HISTÓRICO PRODUTIVO
# =====================================================

@st.fragment(run_every=120)
def render_aba_historico():

    with estilos.mostrar_processando("Carregando..."):
        historico.render()

    st.write("")
    botao_sair_rodape("historico")

if aba_historico:
    render_aba_historico()

# =====================================================
# PERFIL
# =====================================================

@st.fragment
def render_aba_perfil():

    with estilos.mostrar_processando("Carregando..."):
        perfil.render()

    st.write("")
    botao_sair_rodape("perfil")

if aba_perfil:
    render_aba_perfil()

# =====================================================
# ADMINISTRATIVO
# =====================================================
# Cada aba interna (Dashboard, Remanejamento, SAC, etc.) agora é
# seu próprio fragmento (veja administrativo.py) — salvar algo em
# uma aba só recarrega aquela aba, rápido e isolado, sem precisar
# de um run_every aqui em cima. Isso também evita um bug antigo:
# st.tabs() sendo recarregado sozinho por um run_every enquanto a
# pessoa mexe nele podia deixar a tela "duplicada" (conteúdo antigo
# em cima, novo embaixo).

@st.fragment
def render_aba_admin():

    with estilos.mostrar_processando("Carregando..."):
        administrativo.render()

    st.write("")
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

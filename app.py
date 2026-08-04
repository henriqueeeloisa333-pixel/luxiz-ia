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
import epi
import notificacoes

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

## ⚙️ Administrativo

Área de gestão completa da operação: cadastro de usuários, responsáveis, atividades do rodízio, carrinhos fixos e demais parâmetros do sistema.

---

## 🎯 Objetivo do Luxiz IA

Transformar indicadores operacionais em informações simples, rápidas e visuais, auxiliando líderes e gestores na tomada de decisão diária.
        """)


if not st.session_state.logado:

    estilos.marca_desenvolvedor_login()

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
                width='stretch'
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

        st.write("")

        if st.button(
            "❓ Para que serve o Luxiz IA?",
            width='stretch'
        ):

            mostrar_sobre_luxiz()

    st.stop()

# =====================================================
# TROCA DE SENHA OBRIGATÓRIA
# (primeiro acesso com senha temporária, ou senha resetada
# por um Fundador/Gestão)
# =====================================================

if st.session_state.logado and st.session_state.get("trocar_senha"):

    estilos.marca_desenvolvedor_login()

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


def render_cabecalho_inicio():

    agora = estilos.agora_local()

    if agora.hour < 5:
        saudacao = "Boa madrugada"
    elif agora.hour < 12:
        saudacao = "Bom dia"
    elif agora.hour < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"

    nome_armazem_atual = (
        st.session_state.get("armazem_visualizado_nome")
        or st.session_state.get("armazem_nome")
        or ""
    )

    DIAS_EXTENSO = [
        "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"
    ]

    data_extenso = (
        f"{DIAS_EXTENSO[agora.weekday()]}, {agora.day:02d}/{agora.month:02d}"
    )

    if st.session_state.tema == "claro":
        HERO_GRADIENTE = "linear-gradient(120deg, #0ea5e9, #6366f1 45%, #a855f7 85%)"
        HERO_SOMBRA = "0 18px 40px rgba(99,102,241,.28)"
        HERO_TEXTO_SUB = "rgba(255,255,255,.88)"
    else:
        HERO_GRADIENTE = "linear-gradient(120deg, #0b1224, #1e3a8a 40%, #6d28d9 75%, #0b1224)"
        HERO_SOMBRA = "0 18px 40px rgba(0,0,0,.45)"
        HERO_TEXTO_SUB = "rgba(226,232,240,.82)"

    st.markdown(
        f"""
        <style>
        @keyframes luxizHeroGradiente {{
            0%   {{ background-position:0% 50%; }}
            50%  {{ background-position:100% 50%; }}
            100% {{ background-position:0% 50%; }}
        }}
        @keyframes luxizHeroSubir {{
            from {{ opacity:0; transform:translateY(14px); }}
            to   {{ opacity:1; transform:translateY(0); }}
        }}
        @keyframes luxizHeroBrilho {{
            0%, 100% {{ opacity:.5; transform:scale(1); }}
            50%      {{ opacity:.85; transform:scale(1.08); }}
        }}
        .luxiz-hero {{
            position:relative;
            overflow:hidden;
            border-radius:1.4rem;
            padding:1.8rem 2rem;
            background:{HERO_GRADIENTE};
            background-size:220% 220%;
            animation:luxizHeroGradiente 14s ease infinite;
            box-shadow:{HERO_SOMBRA};
            margin-bottom:1.4rem;
        }}
        .luxiz-hero::before, .luxiz-hero::after {{
            content:"";
            position:absolute;
            border-radius:50%;
            background:rgba(255,255,255,.14);
            filter:blur(6px);
            animation:luxizHeroBrilho 5s ease-in-out infinite;
            pointer-events:none;
        }}
        .luxiz-hero::before {{
            width:220px;height:220px;
            top:-90px; right:-60px;
        }}
        .luxiz-hero::after {{
            width:140px;height:140px;
            bottom:-70px; right:18%;
            animation-delay:1.6s;
        }}
        .luxiz-hero-linha {{
            position:relative;
            z-index:1;
            display:flex;
            align-items:flex-start;
            justify-content:space-between;
            gap:1.2rem;
            flex-wrap:wrap;
            animation:luxizHeroSubir .5s ease;
        }}
        .luxiz-hero-saudacao {{
            font-size:.95rem;
            font-weight:700;
            letter-spacing:.3px;
            color:{HERO_TEXTO_SUB};
            margin:0 0 .15rem 0;
        }}
        .luxiz-hero-nome {{
            font-size:1.9rem;
            font-weight:800;
            color:#ffffff;
            margin:0;
            line-height:1.2;
        }}
        .luxiz-hero-sub {{
            margin-top:.5rem;
            display:flex;
            align-items:center;
            gap:.5rem;
            flex-wrap:wrap;
        }}
        .luxiz-hero-chip {{
            background:rgba(255,255,255,.16);
            color:#fff;
            padding:.22rem .7rem;
            border-radius:999px;
            font-size:.78rem;
            font-weight:700;
            backdrop-filter:blur(2px);
            border:1px solid rgba(255,255,255,.22);
        }}
        .luxiz-hero-direita {{
            text-align:right;
            color:{HERO_TEXTO_SUB};
            font-size:.8rem;
        }}
        </style>
        <div class="luxiz-hero">
            <div class="luxiz-hero-linha">
                <div>
                    <p class="luxiz-hero-saudacao">✨ {saudacao}</p>
                    <p class="luxiz-hero-nome">{nome_exibicao}</p>
                    <div class="luxiz-hero-sub">
                        <span class="luxiz-hero-chip">{badge}</span>
                        {f'<span class="luxiz-hero-chip">🏢 {nome_armazem_atual}</span>' if nome_armazem_atual else ''}
                        <span class="luxiz-hero-chip">📅 {data_extenso}</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([7, 2])

    with col1:

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
                "⭐", "Média geral", str(media_hero), "#22c55e"
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
                    f"""
                    <div style="
                        background:{cor_kpi}14;
                        border:1px solid {cor_kpi}40;
                        border-radius:.9rem;
                        padding:.7rem .9rem;
                        text-align:center;
                    ">
                        <div style="font-size:1.3rem;">{icone_kpi}</div>
                        <div style="font-size:1.15rem;font-weight:800;color:{cor_kpi};margin-top:.1rem;">
                            {valor_kpi}
                        </div>
                        <div style="font-size:.72rem;opacity:.75;margin-top:.1rem;">
                            {rotulo_kpi}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    with col2:

        st.success("🟢 Online")

        notificacoes.sino(usuario_atual, armazem_id_atual)

        st.caption(
            f"☁️ Sincronizado com o servidor\n\n"
            f"Última atualização: "
            f"{agora.strftime('%H:%M:%S')}"
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
        ("nav_administrativo", "⚙️", "Administrativo"),
    ]

CHAVES_VALIDAS = [chave for chave, _, _ in NAV_ITENS]

if (
    "aba_atual" not in st.session_state
    or st.session_state.aba_atual not in CHAVES_VALIDAS
):
    st.session_state.aba_atual = CHAVES_VALIDAS[0]

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
        "✨  Luxiz IA" if st.session_state.sidebar_aberta else "✨",
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
aba_admin = st.session_state.aba_atual == "nav_administrativo"


# =====================================================
# INÍCIO
# =====================================================

def render_conteudo_inicio():

    st.markdown(
        """
        <style>
        div[class*="st-key-home-mod-"]{
            transition:transform .18s ease, box-shadow .18s ease;
        }
        div[class*="st-key-home-mod-"]:hover{
            transform:translateY(-3px);
        }
        div[class*="st-key-home-ir-"] button{
            width:100% !important;
            border-radius:999px !important;
            font-weight:700 !important;
            font-size:.8rem !important;
            padding:.25rem 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.subheader("🚀 Acesso Rápido")

    st.caption(
        "Clique em qualquer módulo abaixo para abrir direto, ou use a barra lateral."
    )

    DESCRICOES_MODULOS = {
        "nav_dashboard": "Notas de organização por rua, em tempo real.",
        "nav_remanejamento": "Prioridades operacionais monitoradas ao vivo.",
        "nav_sac": "Metas de reclamações e análise técnica por pessoa.",
        "nav_auditoria": "Acertos e erros de cada colaborador, com histórico.",
        "nav_rotativo": "Escala automática das atividades de fim de expediente.",
        "nav_checklist": "Inspeção de hidráulicos, carrinhos, empilhadeiras e pigmentação.",
        "nav_equipamentos": "Responsáveis por hidráulicos e carrinhos, e carrinhos fixos por local.",
        "nav_epi": "Registro de entrega de EPIs, com assinatura digital do colaborador.",
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

                chave_card_home = f"home-mod-{chave}"

                st.markdown(
                    f"""
                    <style>
                    .st-key-{chave_card_home}{{
                        border:1px solid {cor}40 !important;
                        background:{cor}0c !important;
                        border-radius:1rem !important;
                    }}
                    .st-key-{chave_card_home}:hover{{
                        border-color:{cor} !important;
                        box-shadow:0 10px 24px {cor}33;
                    }}
                    </style>
                    """,
                    unsafe_allow_html=True
                )

                with st.container(border=True, key=chave_card_home):

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

                    st.write("")

                    if st.button(
                        "Abrir →",
                        key=f"home-ir-{chave}",
                        width='stretch'
                    ):
                        st.session_state.aba_atual = chave
                        st.rerun()

    st.divider()

    st.subheader(
        "🔐 Permissões do Perfil"
    )

    st.caption(
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
            ]
        ),
        "recebimento": (
            "📥", "Recebimento", "#a855f7",
            "Acesso focado na conferência e na própria auditoria.",
            [
                ("🎯", "Auditoria (apenas o próprio card)"),
                ("✅", "Checklist"),
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
                ("⚙️", "Administrativo operacional"),
            ]
        ),
    }

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
        f"""
        <span style="
            display:inline-flex;align-items:center;gap:.4rem;
            background:{cor_perfil}16;
            border:1px solid {cor_perfil}45;
            padding:.4rem .85rem;
            border-radius:999px;
            font-size:.82rem;
            font-weight:700;
            margin:.25rem .4rem .25rem 0;
        ">{emoji_p} {texto_p}</span>
        """
        for emoji_p, texto_p in lista_permissoes
    )

    st.markdown(
        f"""
        <style>
        @keyframes luxizPerfilSubir {{
            from {{ opacity:0; transform:translateY(10px); }}
            to   {{ opacity:1; transform:translateY(0); }}
        }}
        .luxiz-perfil-card {{
            position:relative;
            overflow:hidden;
            border-radius:1.2rem;
            padding:1.5rem 1.7rem;
            border:1px solid {cor_perfil}40;
            background:linear-gradient(135deg, {cor_perfil}18, {cor_perfil}05 65%);
            animation:luxizPerfilSubir .4s ease;
        }}
        .luxiz-perfil-card::before {{
            content:"";
            position:absolute;
            width:200px;height:200px;
            border-radius:50%;
            background:{cor_perfil}14;
            top:-90px; right:-60px;
            pointer-events:none;
        }}
        .luxiz-perfil-cabecalho {{
            display:flex;
            align-items:center;
            gap:1rem;
            position:relative;
            z-index:1;
        }}
        .luxiz-perfil-icone {{
            flex-shrink:0;
            width:56px;height:56px;
            border-radius:16px;
            background:{cor_perfil}25;
            display:flex;align-items:center;justify-content:center;
            font-size:1.7rem;
            box-shadow:0 8px 18px {cor_perfil}35;
        }}
        .luxiz-perfil-titulo {{
            font-size:1.3rem;
            font-weight:800;
            color:{cor_perfil};
            margin:0;
        }}
        .luxiz-perfil-desc {{
            font-size:.85rem;
            opacity:.8;
            margin:.15rem 0 0 0;
        }}
        .luxiz-perfil-rotulo-lista {{
            font-size:.72rem;
            font-weight:800;
            letter-spacing:.5px;
            text-transform:uppercase;
            opacity:.6;
            margin:1.2rem 0 .5rem 0;
            position:relative;
            z-index:1;
        }}
        .luxiz-perfil-permissoes {{
            position:relative;
            z-index:1;
        }}
        </style>
        <div class="luxiz-perfil-card">
            <div class="luxiz-perfil-cabecalho">
                <div class="luxiz-perfil-icone">{icone_perfil}</div>
                <div>
                    <p class="luxiz-perfil-titulo">{titulo_perfil}</p>
                    <p class="luxiz-perfil-desc">{desc_perfil}</p>
                </div>
            </div>
            <p class="luxiz-perfil-rotulo-lista">✅ Acessos liberados</p>
            <div class="luxiz-perfil-permissoes">{chips_permissoes_html}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if (tipo == "fundador" or eh_fundador_prefixo) or (tipo == "gestao" or eh_gestao_prefixo):

        st.write("")

        st.subheader(
            "👥 Como Cadastrar Usuários"
        )

        st.caption(
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
            "🦺", "Controle de EPI's", "#f97316",
            "Registre o EPI entregue a cada colaborador. A pessoa (usuário "
            "Separador/Conferente/Recebimento com o mesmo nome) vê a "
            "pendência e assina digitalmente confirmando o recebimento.",
            "Ter um registro confiável, com assinatura, de cada EPI entregue."
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
    notificacoes.renderizar(usuario_atual, armazem_id_atual)
    render_conteudo_inicio()

@st.fragment(run_every=120)
def render_aba_dashboard():

    with estilos.mostrar_processando("Dashboard..."):
        dashboard.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("dashboard")

if aba_dashboard:
    render_aba_dashboard()

# =====================================================
# REMANEJAMENTO
# =====================================================

@st.fragment
def render_aba_remanejamento():

    with estilos.mostrar_processando("Remanejamento..."):
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

    with estilos.mostrar_processando("Central SAC..."):
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

    with estilos.mostrar_processando("Auditoria de Atividades..."):
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

    with estilos.mostrar_processando("Rodízio de Fim de Expediente..."):
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

    with estilos.mostrar_processando("Equipamentos..."):
        equipamentos.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("equipamentos")

if aba_equipamentos:
    render_aba_equipamentos()

# =====================================================
# CONTROLE DE EPI's
# =====================================================

@st.fragment
def render_aba_epi():

    epi.render()

    st.write("")
    estilos.rodape()
    botao_sair_rodape("epi")

if aba_epi:
    render_aba_epi()

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

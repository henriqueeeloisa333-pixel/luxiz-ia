import streamlit as st
import banco
import time


def render():

    banco.inicializar_banco()

    usuario_logado = st.session_state.get(
        "usuario",
        ""
    )

    fundador = usuario_logado.startswith(
        "Fundador."
    )

    gestao = usuario_logado.startswith(
        "Gestao."
    )

    admin_master = fundador or gestao

    st.title(
        "⚙️ Painel Administrativo Luxiz IA"
    )

    st.caption(
        "Gerenciamento central da operação"
    )

    st.divider()

    total_ruas = 9

    total_remanejamentos = len(
        banco.ler_remanejamentos()
    )

    historico = banco.ler_historico_sac()

    ultimo_sac = 0

    if historico:
        ultimo_sac = historico[-1][1]

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "📍 Ruas",
            total_ruas
        )

    with c2:
        st.metric(
            "⚡ Remanejamentos",
            total_remanejamentos
        )

    with c3:
        st.metric(
            "📢 Reclamações",
            ultimo_sac
        )

    st.divider()

    abas = [
        "📊 Dashboard",
        "⚡ Remanejamento",
        "😊 SAC"
    ]

    if admin_master:
        abas.append("👥 Usuários")

    tabs = st.tabs(abas)

    tab_dashboard = tabs[0]
    tab_remanejamento = tabs[1]
    tab_sac = tabs[2]

    if admin_master:
        tab_usuarios = tabs[3]

    # =====================================================
    # DASHBOARD
    # =====================================================

    with tab_dashboard:

        st.subheader(
            "Atualização das Equipes"
        )

        ruas = [
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

        dados = banco.ler_tudo()

        rua = st.selectbox(
            "Selecione a Rua",
            ruas
        )

        info = dados.get(
            rua,
            {
                "nota": 0,
                "dupla": ""
            }
        )

        dupla = st.text_input(
            "Nome da dupla",
            value=info["dupla"]
        )

        nota = st.slider(
            "Nota",
            0.0,
            5.0,
            float(info["nota"]),
            0.1
        )

        if st.button(
            "💾 Salvar Dashboard"
        ):

            banco.salvar_dados(
                rua,
                nota,
                dupla
            )

            st.success(
                "Dados atualizados."
            )

            time.sleep(1)
            st.rerun()

    # =====================================================
    # REMANEJAMENTO
    # =====================================================

    with tab_remanejamento:

        st.subheader(
            "Gerenciar Prioridades"
        )

        col1, col2 = st.columns([3, 2])

        with col1:
            novo_item = st.text_input(
                "Nova prioridade"
            )

        with col2:
            prioridade = st.selectbox(
                "Prioridade",
                [
                    "Normal",
                    "Média",
                    "Alta"
                ]
            )

        if st.button(
            "➕ Adicionar Prioridade"
        ):

            if novo_item:

                banco.adicionar_remanejamento(
                    novo_item,
                    prioridade
                )

                st.success(
                    "Prioridade adicionada."
                )

                time.sleep(1)
                st.rerun()

        st.divider()

        itens = banco.ler_remanejamentos()

        if not itens:
            st.info(
                "Nenhuma prioridade cadastrada."
            )

        for item in itens:

            c1, c2 = st.columns([8, 1])

            with c1:

                if item["prioridade"] == "Alta":

                    st.error(
                        f"🚨 {item['nome']} • PRIORIDADE ALTA"
                    )

                elif item["prioridade"] == "Média":

                    st.warning(
                        f"⚠️ {item['nome']} • PRIORIDADE MÉDIA"
                    )

                else:

                    st.success(
                        f"✅ {item['nome']} • PRIORIDADE NORMAL"
                    )

            with c2:

                if st.button(
                    "❌",
                    key=f"del_{item['id']}"
                ):

                    banco.excluir_remanejamento(
                        item["id"]
                    )

                    st.rerun()

    # =====================================================
    # SAC
    # =====================================================

    with tab_sac:

        st.subheader(
            "Atualização Mensal do SAC"
        )

        with st.form(
            "form_sac"
        ):

            reclamacoes = st.number_input(
                "Reclamações",
                min_value=0,
                step=1
            )

            meta = st.number_input(
                "Meta",
                min_value=0,
                step=1
            )

            salvar = st.form_submit_button(
                "💾 Salvar SAC"
            )

            if salvar:

                banco.atualizar_sac_mensal(
                    reclamacoes,
                    meta
                )

                st.success(
                    "Dados salvos."
                )

                time.sleep(1)
                st.rerun()

    # =====================================================
    # USUÁRIOS
    # =====================================================

    if admin_master:

        with tab_usuarios:

            st.subheader(
                "Gerenciamento de Usuários"
            )

            novo_usuario = st.text_input(
                "Usuário"
            )

            senha_usuario = st.text_input(
                "Senha Inicial",
                type="password"
            )

            if st.button(
                "➕ Criar Usuário"
            ):

                try:

                    banco.criar_usuario(
                        novo_usuario,
                        senha_usuario
                    )

                    st.success(
                        "Usuário criado com sucesso."
                    )

                    st.rerun()

                except Exception as erro:

                    st.error(
                        str(erro)
                    )

            st.divider()

            usuarios = banco.listar_usuarios()

            for usuario in usuarios:

                uid = usuario[0]
                nome = usuario[1]

                c1, c2 = st.columns([8, 1])

                with c1:
                    st.write(nome)

                with c2:

                    if nome == "Fundador.henrique":
                        st.write("👑")
                        continue

                    if st.button(
                        "🗑️",
                        key=f"user_{uid}"
                    ):

                        banco.excluir_usuario(
                            nome
                        )

                        st.rerun()

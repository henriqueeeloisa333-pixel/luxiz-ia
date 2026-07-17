import streamlit as st
import banco


# =====================================================
# DIÁLOGOS DE CONFIRMAÇÃO DE EXCLUSÃO
# =====================================================

@st.dialog("Confirmar exclusão")
def confirmar_exclusao_remanejamento(id_item, nome_item):

    st.write(
        f"Tem certeza que deseja excluir **{nome_item}**?"
    )

    st.caption(
        "Essa ação não pode ser desfeita."
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "✅ Confirmar exclusão",
            use_container_width=True,
            key=f"confirma_del_remanejamento_{id_item}"
        ):
            with st.spinner(f"✨ Luxiz IA atualizando: excluindo '{nome_item}'..."):
                banco.excluir_remanejamento(id_item)
            st.toast(f"✨ Luxiz IA: '{nome_item}' excluído.")
            st.rerun(scope="fragment")

    with c2:
        if st.button(
            "❌ Cancelar",
            use_container_width=True,
            key=f"cancela_del_remanejamento_{id_item}"
        ):
            st.rerun(scope="fragment")


@st.dialog("Confirmar exclusão de usuário")
def confirmar_exclusao_usuario(nome_usuario):

    st.write(
        f"Tem certeza que deseja excluir o usuário **{nome_usuario}**?"
    )

    st.caption(
        "Essa ação não pode ser desfeita."
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "✅ Confirmar exclusão",
            use_container_width=True,
            key=f"confirma_del_usuario_{nome_usuario}"
        ):
            with st.spinner(f"✨ Luxiz IA atualizando: excluindo usuário '{nome_usuario}'..."):
                banco.excluir_usuario(nome_usuario)
            st.toast(f"✨ Luxiz IA: usuário '{nome_usuario}' excluído.")
            st.rerun(scope="fragment")

    with c2:
        if st.button(
            "❌ Cancelar",
            use_container_width=True,
            key=f"cancela_del_usuario_{nome_usuario}"
        ):
            st.rerun(scope="fragment")


@st.dialog("Confirmar exclusão de registro")
def confirmar_exclusao_analise_tecnica(id_registro, nome_registro):

    st.write(
        f"Tem certeza que deseja excluir o registro de **{nome_registro}**?"
    )

    st.caption(
        "Essa ação não pode ser desfeita."
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "✅ Confirmar exclusão",
            use_container_width=True,
            key=f"confirma_del_analise_{id_registro}"
        ):
            with st.spinner(f"✨ Luxiz IA atualizando: excluindo registro de {nome_registro}..."):
                banco.excluir_analise_tecnica(id_registro)
            st.toast(f"✨ Luxiz IA: registro de {nome_registro} excluído.")
            st.rerun(scope="fragment")

    with c2:
        if st.button(
            "❌ Cancelar",
            use_container_width=True,
            key=f"cancela_del_analise_{id_registro}"
        ):
            st.rerun(scope="fragment")


@st.dialog("Confirmar exclusão em lote")
def confirmar_exclusao_multipla_analise_tecnica(ids_selecionados):

    st.write(
        f"Tem certeza que deseja excluir **{len(ids_selecionados)}** "
        "registro(s) selecionado(s)?"
    )

    st.caption(
        "Essa ação não pode ser desfeita."
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "✅ Confirmar exclusão",
            use_container_width=True,
            key="confirma_del_lote_analise"
        ):
            with st.spinner(f"✨ Luxiz IA atualizando: excluindo {len(ids_selecionados)} registro(s)..."):
                banco.excluir_analise_tecnica_lote(ids_selecionados)
            st.toast(f"✨ Luxiz IA: {len(ids_selecionados)} registro(s) excluído(s).")
            st.rerun(scope="fragment")

    with c2:
        if st.button(
            "❌ Cancelar",
            use_container_width=True,
            key="cancela_del_lote_analise"
        ):
            st.rerun(scope="fragment")


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

            with st.spinner(f"✨ Luxiz IA atualizando: Dashboard da {rua}..."):
                banco.salvar_dados(
                    rua,
                    nota,
                    dupla,
                    usuario=usuario_logado
                )

            st.toast(f"✨ Luxiz IA: Dashboard da {rua} atualizado.")
            st.rerun(scope="fragment")

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

                with st.spinner(f"✨ Luxiz IA atualizando: adicionando '{novo_item}'..."):
                    banco.adicionar_remanejamento(
                        novo_item,
                        prioridade,
                        usuario=usuario_logado
                    )

                st.toast(f"✨ Luxiz IA: '{novo_item}' adicionado.")
                st.rerun(scope="fragment")

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

                    confirmar_exclusao_remanejamento(
                        item["id"],
                        item["nome"]
                    )

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

                with st.spinner("✨ Luxiz IA atualizando: dados do SAC..."):
                    banco.atualizar_sac_mensal(
                        reclamacoes,
                        meta,
                        usuario=usuario_logado
                    )

                st.toast("✨ Luxiz IA: SAC atualizado.")
                st.rerun(scope="fragment")

        st.divider()

        st.subheader(
            "🔍 Análise Técnica"
        )

        st.caption(
            "Registre quem cometeu o erro, o tipo de erro e a data da ocorrência."
        )

        TIPOS_ERRO_SAC = [
            "Pigmentação",
            "Inversão",
            "Mandou produto a mais",
            "Mandou produto a menos",
            "Não enviou componentes",
            "Remanejou na doca errada"
        ]

        with st.form(
            "form_analise_tecnica"
        ):

            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                nome_erro = st.text_input(
                    "Nome"
                )

            with col2:
                tipo_erro = st.selectbox(
                    "O que errou",
                    TIPOS_ERRO_SAC
                )

            with col3:
                data_erro = st.date_input(
                    "Data"
                )

            descricao_erro = st.text_area(
                "Descrição do ocorrido"
            )

            registrar = st.form_submit_button(
                "➕ Registrar Análise Técnica"
            )

            if registrar:

                if nome_erro:

                    with st.spinner(f"✨ Luxiz IA atualizando: registrando ocorrência de {nome_erro}..."):
                        banco.adicionar_analise_tecnica(
                            nome_erro,
                            tipo_erro,
                            data_erro,
                            descricao=descricao_erro,
                            usuario=usuario_logado
                        )

                    st.toast(f"✨ Luxiz IA: ocorrência de {nome_erro} registrada.")
                    st.rerun(scope="fragment")

                else:

                    st.warning(
                        "Informe o nome antes de registrar."
                    )

        st.divider()

        registros_tecnica = banco.ler_analise_tecnica()

        if registros_tecnica:

            st.caption(
                "Marque as caixinhas para excluir vários de uma vez, "
                "ou clique em ❌ para excluir um lançamento só:"
            )

            ids_selecionados = []

            for registro in registros_tecnica:

                c0, c1, c2 = st.columns([0.6, 7.4, 1])

                with c0:

                    marcado = st.checkbox(
                        "selecionar",
                        key=f"select_analise_{registro['id']}",
                        label_visibility="collapsed"
                    )

                    if marcado:
                        ids_selecionados.append(registro["id"])

                with c1:

                    st.caption(
                        f"👤 {registro['nome']} • {registro['tipo_erro']} • "
                        f"{registro['data_erro'].strftime('%d/%m/%Y')}"
                    )

                with c2:

                    if st.button(
                        "❌",
                        key=f"del_analise_{registro['id']}"
                    ):

                        confirmar_exclusao_analise_tecnica(
                            registro["id"],
                            registro["nome"]
                        )

            if ids_selecionados:

                st.write("")

                if st.button(
                    f"🗑️ Excluir {len(ids_selecionados)} selecionado(s)"
                ):

                    confirmar_exclusao_multipla_analise_tecnica(
                        ids_selecionados
                    )

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

                    with st.spinner(f"✨ Luxiz IA atualizando: criando usuário '{novo_usuario}'..."):
                        banco.criar_usuario(
                            novo_usuario,
                            senha_usuario
                        )

                    st.toast(f"✨ Luxiz IA: usuário '{novo_usuario}' criado.")
                    st.rerun(scope="fragment")

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

                        confirmar_exclusao_usuario(
                            nome
                        )

import streamlit as st
import banco
import pandas as pd
import io


# =====================================================
# DIÁLOGOS DE CONFIRMAÇÃO DE EXCLUSÃO
# =====================================================

@st.dialog("Confirmar notificação")
def perguntar_notificacao(pendente, campo):

    nome_pessoa = pendente[campo]

    rotulo = "Separador(a)" if campo == "separador" else "Conferente"

    st.write(
        f"Deseja notificar o(a) {rotulo} **{nome_pessoa}** sobre o erro?"
    )

    st.caption(
        "Se confirmar, essa ocorrência também vai aparecer no card dessa pessoa."
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "✅ Sim",
            use_container_width=True,
            key=f"notificar_sim_{campo}"
        ):
            st.session_state["pendente_analise_tecnica"][f"notificar_{campo}"] = True
            st.rerun()

    with c2:
        if st.button(
            "❌ Não",
            use_container_width=True,
            key=f"notificar_nao_{campo}"
        ):
            st.session_state["pendente_analise_tecnica"][f"notificar_{campo}"] = False
            st.rerun()


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


@st.dialog("Confirmar exclusão em lote")
def confirmar_exclusao_multipla_remanejamento(ids_selecionados):

    st.write(
        f"Tem certeza que deseja excluir **{len(ids_selecionados)}** "
        "prioridade(s) selecionada(s)?"
    )

    st.caption(
        "Essa ação não pode ser desfeita."
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "✅ Confirmar exclusão",
            use_container_width=True,
            key="confirma_del_lote_remanejamento"
        ):
            with st.spinner(f"✨ Luxiz IA atualizando: excluindo {len(ids_selecionados)} prioridade(s)..."):
                banco.excluir_remanejamento_lote(ids_selecionados)
            st.toast(f"✨ Luxiz IA: {len(ids_selecionados)} prioridade(s) excluída(s).")
            st.rerun(scope="fragment")

    with c2:
        if st.button(
            "❌ Cancelar",
            use_container_width=True,
            key="cancela_del_lote_remanejamento"
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

        ids_selecionados_remanejamento = []

        for item in itens:

            c0, c1, c2 = st.columns([0.6, 7.4, 1])

            with c0:

                marcado_remanejamento = st.checkbox(
                    "selecionar",
                    key=f"select_remanejamento_{item['id']}",
                    label_visibility="collapsed"
                )

                if marcado_remanejamento:
                    ids_selecionados_remanejamento.append(item["id"])

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

        if ids_selecionados_remanejamento:

            st.write("")

            if st.button(
                f"🗑️ Excluir {len(ids_selecionados_remanejamento)} selecionado(s)",
                key="btn_excluir_lote_remanejamento"
            ):

                confirmar_exclusao_multipla_remanejamento(
                    ids_selecionados_remanejamento
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
            "Registre os detalhes completos da ocorrência."
        )

        TIPOS_ERRO_SAC = [
            "Pigmentação",
            "Componente",
            "Contagem",
            "Deixou no Picking",
            "Impróprio",
            "Inversão de Doca",
            "Inversão de Etiqueta",
            "Inversão de Picking",
            "Inversão de Produto"
        ]

        TRATATIVA_OPCOES = [
            "Crédito disponível",
            "Minuta",
            "Coleta",
            "Pedido"
        ]

        BALANCA_OPCOES = [
            "Sim",
            "Não"
        ]

        # -----------------------------------------------
        # Fluxo de confirmação de notificação
        # (roda antes do formulário para não perder o
        # estado pendente entre reruns)
        # -----------------------------------------------

        pendente = st.session_state.get(
            "pendente_analise_tecnica"
        )

        if pendente:

            if pendente.get("separador") and pendente.get("notificar_separador") is None:

                perguntar_notificacao(
                    pendente,
                    campo="separador"
                )

            elif pendente.get("conferente") and pendente.get("notificar_conferente") is None:

                perguntar_notificacao(
                    pendente,
                    campo="conferente"
                )

            else:

                vinculos = []

                if pendente.get("separador") and pendente.get("notificar_separador"):

                    vinculos.append({
                        "nome": pendente["separador"],
                        "papel": "Separador"
                    })

                if pendente.get("conferente") and pendente.get("notificar_conferente"):

                    vinculos.append({
                        "nome": pendente["conferente"],
                        "papel": "Conferente"
                    })

                # Deduplica por nome (ignorando maiúsculas/minúsculas):
                # se a mesma pessoa aparecer em mais de um campo,
                # essa ocorrência conta 1 vez só, com os papéis mesclados.
                vinculos_por_nome = {}

                for vinculo in vinculos:

                    chave = vinculo["nome"].strip().title()

                    if chave in vinculos_por_nome:

                        if vinculo["papel"] not in vinculos_por_nome[chave]["papel"]:

                            vinculos_por_nome[chave]["papel"] += f" e {vinculo['papel']}"

                    else:

                        vinculos_por_nome[chave] = {
                            "nome": vinculo["nome"],
                            "papel": vinculo["papel"]
                        }

                vinculos = list(vinculos_por_nome.values())

                rotulo_ocorrencia = (
                    pendente.get("separador")
                    or pendente.get("conferente")
                    or pendente.get("chamado")
                    or "nova ocorrência"
                )

                with st.spinner(f"✨ Luxiz IA atualizando: registrando {rotulo_ocorrencia}..."):
                    banco.adicionar_analise_tecnica(
                        pendente,
                        vinculos,
                        usuario=usuario_logado
                    )

                st.toast(f"✨ Luxiz IA: {rotulo_ocorrencia} registrada.")

                del st.session_state["pendente_analise_tecnica"]

                st.rerun()

        with st.form(
            "form_analise_tecnica"
        ):

            col2, col3 = st.columns(2)

            with col2:
                tipo_erro = st.selectbox(
                    "Tipo",
                    TIPOS_ERRO_SAC
                )

            with col3:
                data_erro = st.date_input(
                    "Data"
                )

            col4, col5, col6 = st.columns(3)

            with col4:
                chamado = st.text_input(
                    "Chamado"
                )

            with col5:
                cliente = st.text_input(
                    "Cliente"
                )

            with col6:
                nota_fiscal = st.text_input(
                    "Nota Fiscal"
                )

            col7, col8, col9 = st.columns(3)

            with col7:
                cod_produto = st.text_input(
                    "Cód Produto"
                )

            with col8:
                produto = st.text_input(
                    "Produto"
                )

            with col9:
                hora = st.time_input(
                    "Hora"
                )

            col10, col11, col12 = st.columns(3)

            with col10:
                separador = st.text_input(
                    "Separador"
                )

            with col11:
                conferente = st.text_input(
                    "Conferente"
                )

            with col12:
                balanca = st.selectbox(
                    "Balança",
                    BALANCA_OPCOES
                )

            col13, col14, col15 = st.columns(3)

            with col13:
                volume = st.text_input(
                    "Volume"
                )

            with col14:
                carga = st.text_input(
                    "Carga"
                )

            with col15:
                regiao = st.text_input(
                    "Região"
                )

            col16, col17 = st.columns(2)

            with col16:
                motorista = st.text_input(
                    "Motorista"
                )

            with col17:
                tratativa = st.selectbox(
                    "Tratativa",
                    TRATATIVA_OPCOES
                )

            descricao_erro = st.text_area(
                "Descrição do ocorrido"
            )

            registrar = st.form_submit_button(
                "➕ Registrar Análise Técnica"
            )

            if registrar:

                st.session_state["pendente_analise_tecnica"] = {
                    "tipo_erro": tipo_erro,
                    "data_erro": data_erro,
                    "descricao": descricao_erro,
                    "chamado": chamado,
                    "cliente": cliente,
                    "nota_fiscal": nota_fiscal,
                    "cod_produto": cod_produto,
                    "produto": produto,
                    "tratativa": tratativa,
                    "hora": hora,
                    "separador": separador if separador else None,
                    "volume": volume,
                    "carga": carga,
                    "regiao": regiao,
                    "motorista": motorista,
                    "balanca": balanca,
                    "conferente": conferente if conferente else None,
                    "notificar_separador": None if separador else False,
                    "notificar_conferente": None if conferente else False
                }

                st.rerun()

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

                    identificador = (
                        registro.get("separador")
                        or registro.get("conferente")
                        or registro.get("chamado")
                        or "Ocorrência"
                    )

                    st.caption(
                        f"👤 {identificador} • {registro['tipo_erro']} • "
                        f"{registro['data_erro'].strftime('%d/%m/%Y')}"
                    )

                with c2:

                    if st.button(
                        "❌",
                        key=f"del_analise_{registro['id']}"
                    ):

                        confirmar_exclusao_analise_tecnica(
                            registro["id"],
                            identificador
                        )

            if ids_selecionados:

                st.write("")

                if st.button(
                    f"🗑️ Excluir {len(ids_selecionados)} selecionado(s)"
                ):

                    confirmar_exclusao_multipla_analise_tecnica(
                        ids_selecionados
                    )

            st.divider()

            df_exportar = pd.DataFrame(registros_tecnica)

            if "vinculos_notificados" in df_exportar.columns:

                df_exportar["vinculos_notificados"] = df_exportar["vinculos_notificados"].apply(
                    lambda lista: ", ".join(
                        f"{item['nome']} ({item['papel']})" for item in lista
                    ) if lista else ""
                )

            buffer_excel = io.BytesIO()

            with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
                df_exportar.to_excel(
                    writer,
                    index=False,
                    sheet_name="Analise Tecnica"
                )

            st.download_button(
                "📥 Exportar para Excel",
                data=buffer_excel.getvalue(),
                file_name="analise_tecnica_luxiz.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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

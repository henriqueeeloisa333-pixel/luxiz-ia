import streamlit as st
import banco
import estilos
import pandas as pd
import io
from datetime import date


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
    funcao_enviar_manutencao=None,
    funcao_retornar_manutencao=None
):

    st.subheader(
        f"{icone} {titulo}"
    )

    with st.form(
        f"form_{prefixo_key}",
        clear_on_submit=True
    ):

        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome",
                key=f"nome_{prefixo_key}"
            )

        with col2:
            numero = st.text_input(
                rotulo_numero,
                key=f"numero_{prefixo_key}"
            )

        col3, col4 = st.columns(2)

        with col3:
            data_checklist = st.date_input(
                "Data",
                value=date.today(),
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
            key=f"descricao_{prefixo_key}"
        )

        enviar = st.form_submit_button(
            f"➕ Registrar {titulo}"
        )

        if enviar:

            if not nome or not numero:

                st.error(
                    "Preencha o Nome e o Número antes de registrar."
                )

            else:

                with estilos.mostrar_processando(f"registrando checklist..."):
                    funcao_adicionar(
                        nome,
                        numero,
                        data_checklist,
                        status,
                        descricao,
                        armazem_id
                    )

                estilos.notificar_sucesso("checklist registrado com sucesso.")
                st.rerun(scope="fragment")

    st.divider()

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

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("📋 Total", len(registros))

    with c2:
        st.metric("✅ Conformes", conformes)

    with c3:
        st.metric("⚠️ Não Conformes", nao_conformes)

    st.write("")

    df = pd.DataFrame(registros)

    ids_registros = df["id"].tolist()

    df_exibir = df.rename(columns={
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

        df_editado = st.data_editor(
            df_exibir,
            use_container_width=True,
            hide_index=True,
            key=f"editor_{prefixo_key}",
            column_config={
                "Situação": st.column_config.SelectboxColumn(
                    options=["Conforme", "Não Conforme"],
                    required=True
                ),
                "Data": st.column_config.DateColumn(
                    format="DD/MM/YYYY"
                )
            }
        )

        if st.button(
            "💾 Salvar alterações",
            key=f"salvar_{prefixo_key}"
        ):

            houve_alteracao = False

            for posicao, id_registro in enumerate(ids_registros):

                linha_original = df_exibir.iloc[posicao]
                linha_editada = df_editado.iloc[posicao]

                if not linha_original.equals(linha_editada):

                    with estilos.mostrar_processando("salvando alterações..."):
                        funcao_editar(
                            id_registro,
                            linha_editada["Nome"],
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
            use_container_width=True,
            hide_index=True
        )

    # =====================================================
    # MANUTENÇÃO
    # =====================================================
    # A visibilidade de "quais itens estão em manutenção" é liberada
    # para todos que têm acesso ao checklist. Só os comandos que
    # alteram o estado (enviar para manutenção / retornar) continuam
    # restritos ao Fundador e à Gestão.

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

        if itens_em_manutencao:

            st.write("")

            st.markdown("##### 🚧 Em Manutenção")

            for item in itens_em_manutencao:

                with st.container(border=True):

                    if admin_master:
                        col_texto, col_botao = st.columns([5, 1])
                    else:
                        col_texto = st.container()

                    with col_texto:

                        st.markdown(
                            f"**{item['nome']}** — {rotulo_numero}: {item['numero']}"
                        )

                        if item.get("manutencao_motivo"):

                            st.caption(f"Motivo: {item['manutencao_motivo']}")

                        if item.get("manutencao_enviado_em"):

                            st.caption(
                                f"Enviado por {item.get('manutencao_enviado_por') or '—'} "
                                f"em {item['manutencao_enviado_em'].strftime('%d/%m/%Y %H:%M')}"
                            )

                    if admin_master:

                        with col_botao:

                            if st.button(
                                "↩️",
                                key=f"retornar_manut_{prefixo_key}_{item['id']}",
                                help=(
                                    f"Marcar {item['nome']} ({rotulo_numero} "
                                    f"{item['numero']}) como retornado da manutenção"
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

        if admin_master:

            itens_nao_conformes = [
                r for r in registros
                if r["status"] == "Não Conforme" and not r.get("em_manutencao")
            ]

            if itens_nao_conformes:

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

    st.write("")

    def _formatar_evento_manutencao(pessoa, momento):

        if not momento:
            return ""

        texto = momento.strftime("%d/%m/%Y %H:%M")

        if pessoa:
            texto += f" ({pessoa})"

        return texto

    df_exportar = df_exibir.copy()

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

    st.download_button(
        "📥 Exportar para Excel",
        data=buffer_excel.getvalue(),
        file_name=nome_arquivo_excel,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"exportar_{prefixo_key}"
    )


def renderizar_checklist_pigmentacao(
    funcao_adicionar,
    funcao_ler,
    prefixo_key,
    nome_arquivo_excel,
    armazem_id,
    funcao_editar=None
):

    titulo = "Checklist de Pigmentação"

    st.subheader(
        f"🎨 {titulo}"
    )

    with st.form(
        f"form_{prefixo_key}",
        clear_on_submit=True
    ):

        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome",
                key=f"nome_{prefixo_key}"
            )

        with col2:
            data_checklist = st.date_input(
                "Data",
                value=date.today(),
                key=f"data_{prefixo_key}"
            )

        status = st.selectbox(
            "Situação",
            ["Conforme", "Não Conforme"],
            key=f"status_{prefixo_key}"
        )

        descricao = st.text_area(
            "Descrição",
            key=f"descricao_{prefixo_key}"
        )

        enviar = st.form_submit_button(
            f"➕ Registrar {titulo}"
        )

        if enviar:

            if not nome:

                st.error(
                    "Preencha o Nome antes de registrar."
                )

            else:

                with estilos.mostrar_processando("registrando checklist..."):
                    funcao_adicionar(
                        nome,
                        data_checklist,
                        status,
                        descricao,
                        armazem_id
                    )

                estilos.notificar_sucesso("checklist registrado com sucesso.")
                st.rerun(scope="fragment")

    st.divider()

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

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("📋 Total", len(registros))

    with c2:
        st.metric("✅ Conformes", conformes)

    with c3:
        st.metric("⚠️ Não Conformes", nao_conformes)

    st.write("")

    df = pd.DataFrame(registros)

    ids_registros = df["id"].tolist()

    df_exibir = df.rename(columns={
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

        df_editado = st.data_editor(
            df_exibir,
            use_container_width=True,
            hide_index=True,
            key=f"editor_{prefixo_key}",
            column_config={
                "Situação": st.column_config.SelectboxColumn(
                    options=["Conforme", "Não Conforme"],
                    required=True
                ),
                "Data": st.column_config.DateColumn(
                    format="DD/MM/YYYY"
                )
            }
        )

        if st.button(
            "💾 Salvar alterações",
            key=f"salvar_{prefixo_key}"
        ):

            houve_alteracao = False

            for posicao, id_registro in enumerate(ids_registros):

                linha_original = df_exibir.iloc[posicao]
                linha_editada = df_editado.iloc[posicao]

                if not linha_original.equals(linha_editada):

                    with estilos.mostrar_processando("salvando alterações..."):
                        funcao_editar(
                            id_registro,
                            linha_editada["Nome"],
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
            use_container_width=True,
            hide_index=True
        )

    st.write("")

    buffer_excel = io.BytesIO()

    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
        df_exibir.to_excel(
            writer,
            index=False,
            sheet_name=titulo[:31]
        )

    st.download_button(
        "📥 Exportar para Excel",
        data=buffer_excel.getvalue(),
        file_name=nome_arquivo_excel,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"exportar_{prefixo_key}"
    )


def render():

    estilos.exibir_notificacao_pendente()

    estilos.cabecalho_pagina(
        "✅",
        "Checklist",
        "Registro de inspeções de equipamentos pelos colaboradores.",
        cor="#a855f7"
    )

    st.divider()

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
            funcao_enviar_manutencao=banco.enviar_manutencao_hidraulico,
            funcao_retornar_manutencao=banco.retornar_manutencao_hidraulico
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
            funcao_enviar_manutencao=banco.enviar_manutencao_carrinho,
            funcao_retornar_manutencao=banco.retornar_manutencao_carrinho
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
            funcao_enviar_manutencao=banco.enviar_manutencao_empilhadeira,
            funcao_retornar_manutencao=banco.retornar_manutencao_empilhadeira
        )

    with aba_pigmentacao:

        renderizar_checklist_pigmentacao(
            funcao_adicionar=banco.adicionar_checklist_pigmentacao,
            funcao_ler=banco.ler_checklist_pigmentacao,
            prefixo_key="pigmentacao",
            nome_arquivo_excel="checklist_pigmentacao_luxiz.xlsx",
            armazem_id=armazem_id_atual,
            funcao_editar=banco.editar_checklist_pigmentacao
        )

    st.divider()

    st.caption(
        "Luxiz IA • Checklist de Equipamentos"
    )
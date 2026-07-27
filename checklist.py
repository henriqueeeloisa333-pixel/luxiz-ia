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
    funcao_editar=None
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

                with st.spinner(f"✨ Luxiz IA atualizando: registrando checklist..."):
                    funcao_adicionar(
                        nome,
                        numero,
                        data_checklist,
                        status,
                        descricao
                    )

                st.toast("✨ Luxiz IA: checklist registrado com sucesso.")
                st.rerun()

    st.divider()

    registros = funcao_ler()

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

                    with st.spinner("✨ Luxiz IA atualizando: salvando alterações..."):
                        funcao_editar(
                            id_registro,
                            linha_editada["Nome"],
                            linha_editada[rotulo_numero],
                            linha_editada["Data"],
                            linha_editada["Situação"],
                            linha_editada["Descrição"]
                        )

                    houve_alteracao = True

            if houve_alteracao:

                st.toast("✨ Luxiz IA: alterações salvas com sucesso.")
                st.rerun()

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


def renderizar_checklist_pigmentacao(
    funcao_adicionar,
    funcao_ler,
    prefixo_key,
    nome_arquivo_excel,
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

                with st.spinner("✨ Luxiz IA atualizando: registrando checklist..."):
                    funcao_adicionar(
                        nome,
                        data_checklist,
                        status,
                        descricao
                    )

                st.toast("✨ Luxiz IA: checklist registrado com sucesso.")
                st.rerun()

    st.divider()

    registros = funcao_ler()

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

                    with st.spinner("✨ Luxiz IA atualizando: salvando alterações..."):
                        funcao_editar(
                            id_registro,
                            linha_editada["Nome"],
                            linha_editada["Data"],
                            linha_editada["Situação"],
                            linha_editada["Descrição"]
                        )

                    houve_alteracao = True

            if houve_alteracao:

                st.toast("✨ Luxiz IA: alterações salvas com sucesso.")
                st.rerun()

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

    estilos.cabecalho_pagina(
        "✅",
        "Checklist",
        "Registro de inspeções de equipamentos pelos colaboradores.",
        cor="#a855f7"
    )

    st.divider()

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
            funcao_editar=banco.editar_checklist_hidraulico
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
            funcao_editar=banco.editar_checklist_carrinho
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
            funcao_editar=banco.editar_checklist_empilhadeira
        )

    with aba_pigmentacao:

        renderizar_checklist_pigmentacao(
            funcao_adicionar=banco.adicionar_checklist_pigmentacao,
            funcao_ler=banco.ler_checklist_pigmentacao,
            prefixo_key="pigmentacao",
            nome_arquivo_excel="checklist_pigmentacao_luxiz.xlsx",
            funcao_editar=banco.editar_checklist_pigmentacao
        )

    st.divider()

    st.caption(
        "Luxiz IA • Checklist de Equipamentos"
    )
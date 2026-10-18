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
    (negativo).

    - A sexta-feira de hoje ainda não conta: a pessoa tem o dia todo.
    - A contagem começa na primeira sexta-feira depois do primeiro
      checklist já registrado, para não cobrar retroativamente de
      antes de o sistema ser usado.
    - Se o responsável tiver "criado_em" (data de cadastro), sextas
      anteriores a esse cadastro não contam contra ele.
    """

    if not responsaveis or not registros:
        return []

    hoje = estilos.agora_local().date()

    primeira_data = min(registro["data_checklist"] for registro in registros)

    dia = primeira_data + timedelta(
        days=(DIA_PREVISTO_CHECKLIST - primeira_data.weekday()) % 7
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

    st.markdown("##### 🚫 Não preenchidos (negativo)")

    st.caption(
        "Checklist previsto para toda sexta-feira. Quem não registrou "
        "na data prevista fica como negativo."
    )

    linhas_html = "".join(
        f"""
        <div style="
            background:rgba(220,38,38,.14);
            border-left:4px solid #dc2626;
            padding:.4rem .7rem;
            border-radius:.4rem;
            margin-bottom:.35rem;
            font-size:.85rem;
        ">
        🚫 <strong>{item['data'].strftime('%d/%m/%Y')}</strong> —
        {html.escape(str(item['nome']))}
        ({html.escape(rotulo_numero)}: {html.escape(item['numero'])})
        — não preencheu o checklist
        </div>
        """
        for item in pendentes_mes
    )

    if len(pendentes_mes) > 8:

        with st.container(height=260):

            st.markdown(linhas_html, unsafe_allow_html=True)

    else:

        st.markdown(linhas_html, unsafe_allow_html=True)


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
    regra de "não preenchido = negativo" com base nos responsáveis
    cadastrados em Equipamentos.
    """

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

                # Normaliza o nome digitado: se bater com o Perfil de
                # alguém cadastrado, salva o nome completo (nome +
                # sobrenome) já certo; senão, só corrige a
                # capitalização (ex.: "larissa santos" -> "Larissa
                # Santos"). Isso também resolve o vínculo com quem
                # está logado quando o nome vem completo.
                nome_normalizado = banco.normalizar_nome_pessoa(
                    nome, armazem_id
                )

                with estilos.mostrar_processando(f"registrando checklist..."):
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

    st.divider()

    registros = funcao_ler(armazem_id)

    if not registros:

        st.info(
            "Nenhum checklist registrado ainda."
        )

        return

    # =====================================================
    # NÃO PREENCHIDOS (só Hidráulicos e Carrinhos)
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

    colunas_metricas = st.columns(4 if controla_nao_preenchidos else 3)

    with colunas_metricas[0]:
        st.metric("📋 Total", len(registros))

    with colunas_metricas[1]:
        st.metric("✅ Conformes", conformes)

    with colunas_metricas[2]:
        st.metric("⚠️ Não Conformes", nao_conformes)

    if controla_nao_preenchidos:

        with colunas_metricas[3]:
            st.metric(
                "🚫 Não preenchidos",
                len(nao_preenchidos),
                help="Sextas-feiras já encerradas em que o responsável não registrou o checklist."
            )

    st.write("")

    # =====================================================
    # REGISTROS SEPARADOS POR MÊS
    # O mês mais recente já abre; os anteriores ficam fechados.
    # =====================================================

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
            f"🗓️ {_rotulo_mes(chave_mes)} "
            f"({len(registros_mes)} registro(s))"
        )

        if pendentes_mes:

            rotulo_expander += f" • 🚫 {len(pendentes_mes)} não preenchido(s)"

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
                    "Situação": st.column_config.SelectboxColumn(
                        options=["Conforme", "Não Conforme"],
                        required=True
                    ),
                    "Data": st.column_config.DateColumn(
                        format="DD/MM/YYYY"
                    )
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

            st.write("")

            with st.expander(
                f"🚧 Manutenção ({len(itens_em_manutencao)} em andamento)",
                expanded=False
            ):

                if itens_em_manutencao:

                    st.markdown("##### 🚧 Em Manutenção")

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

    st.write("")

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
                    "Situação": "Não preenchido"
                }
                for item in nao_preenchidos
            ]).to_excel(
                writer,
                index=False,
                sheet_name="Não preenchidos"
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
    funcao_editar=None,
    funcao_excluir=None
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

    # =====================================================
    # REGISTROS SEPARADOS POR MÊS
    # =====================================================

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
            f"🗓️ {_rotulo_mes(chave_mes)} ({len(registros_mes)} registro(s))",
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
                    "Situação": st.column_config.SelectboxColumn(
                        options=["Conforme", "Não Conforme"],
                        required=True
                    ),
                    "Data": st.column_config.DateColumn(
                        format="DD/MM/YYYY"
                    )
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

    st.write("")

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

    st.divider()

    st.caption(
        "Luxiz IA • Checklist de Equipamentos"
    )

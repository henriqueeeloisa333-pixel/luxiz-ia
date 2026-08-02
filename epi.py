import streamlit as st
import banco
import estilos
from datetime import date


def render():

    estilos.exibir_notificacao_pendente()

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    usuario_atual = st.session_state.get("usuario", "")

    estilos.cabecalho_pagina(
        "🦺",
        "Controle de EPI's",
        "Registro de entrega de EPIs, com assinatura digital do colaborador.",
        cor="#f97316"
    )

    st.divider()

    registros = banco.ler_epis(armazem_id_atual)

    # =====================================================
    # PENDENTES PARA O USUÁRIO LOGADO ASSINAR
    # =====================================================
    # Um EPI cadastrado para "Nome" gera pendência para os
    # usuários Separador.Nome, Conferente.Nome e Recebimento.Nome
    # — quem estiver logado com um desses usuários vê aqui.

    pendentes_meus = [
        registro for registro in registros
        if not registro["assinatura"]
        and banco.epi_pertence_ao_usuario(registro["nome"], usuario_atual)
    ]

    if pendentes_meus:

        st.warning(
            f"🔔 Você tem {len(pendentes_meus)} EPI(s) aguardando sua "
            f"assinatura de recebimento."
        )

        for registro in pendentes_meus:

            with st.container(border=True):

                st.markdown(
                    f"**{registro['epi']}**"
                )

                st.caption(
                    f"📅 Recebido em "
                    f"{registro['data'].strftime('%d/%m/%Y')}"
                )

                if st.button(
                    "✅ Assinar recebimento",
                    key=f"assinar_epi_{registro['id']}"
                ):
                    with estilos.mostrar_processando("registrando assinatura..."):
                        banco.assinar_epi(
                            registro["id"],
                            usuario_atual,
                            armazem_id_atual
                        )
                    estilos.notificar_sucesso("Assinatura registrada.")
                    st.rerun()

        st.divider()

    # =====================================================
    # KPIs
    # =====================================================

    total = len(registros)
    assinados = len([r for r in registros if r["assinatura"]])
    pendentes = total - assinados

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("📋 Total de EPI's", total)

    with c2:
        st.metric("✅ Assinados", assinados)

    with c3:
        st.metric("⏳ Pendentes", pendentes)

    st.divider()

    # =====================================================
    # REGISTRAR NOVO EPI
    # =====================================================

    with st.expander("➕ Registrar novo EPI"):

        nome = st.text_input(
            "Nome do colaborador",
            key="epi_input_nome"
        )

        tipo_epi = st.text_input(
            "EPI",
            key="epi_input_tipo",
            placeholder="Ex.: Luva de proteção, Óculos de segurança..."
        )

        data_epi = st.date_input(
            "Data",
            value=date.today(),
            key="epi_input_data"
        )

        st.caption(
            "Ao registrar, os usuários Separador." + (nome.strip() or "Nome") +
            ", Conferente." + (nome.strip() or "Nome") +
            " e Recebimento." + (nome.strip() or "Nome") +
            " (os que existirem) verão a pendência de assinatura."
        )

        if st.button(
            "💾 Registrar EPI",
            key="epi_botao_salvar"
        ):

            if not nome.strip() or not tipo_epi.strip():

                st.warning(
                    "Preencha o nome do colaborador e o EPI."
                )

            else:

                with estilos.mostrar_processando(f"registrando EPI de {nome.strip()}..."):
                    banco.criar_epi(
                        nome.strip(),
                        tipo_epi.strip(),
                        data_epi,
                        armazem_id_atual,
                        usuario_atual
                    )

                estilos.notificar_sucesso(
                    f"EPI de {nome.strip()} registrado. Aguardando assinatura."
                )
                st.rerun()

    st.divider()

    # =====================================================
    # HISTÓRICO
    # =====================================================

    st.subheader("📜 Histórico")

    if not registros:

        st.info(
            "Nenhum EPI registrado ainda."
        )
        return

    for registro in registros:

        assinado = bool(registro["assinatura"])

        with st.container(border=True):

            col_conteudo, col_status = st.columns([3, 1])

            with col_conteudo:

                st.markdown(
                    f"**{registro['nome']}** — {registro['epi']}"
                )

                st.caption(
                    f"📅 {registro['data'].strftime('%d/%m/%Y')}"
                )

                if registro.get("criado_por"):

                    st.caption(
                        f"👤 Registrado por {registro['criado_por']}"
                    )

            with col_status:

                if assinado:
                    st.success("✅ Assinado")
                else:
                    st.warning("⏳ Pendente")

            if assinado:

                st.markdown(
                    f"""
                    <div style="
                        background:rgba(34,197,94,.12);
                        border-left:4px solid #22c55e;
                        padding:.5rem .7rem;
                        border-radius:.4rem;
                        font-size:.85rem;
                        margin-top:.4rem;
                    ">
                    ✍️ {registro['assinatura']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                assinado_em_local = estilos.horario_local(
                    registro["assinado_em"]
                )

                st.caption(
                    f"Assinado em "
                    f"{assinado_em_local.strftime('%d/%m/%Y %H:%M')}"
                )

    st.divider()

    st.caption(
        "Luxiz IA • Controle de EPI's"
    )
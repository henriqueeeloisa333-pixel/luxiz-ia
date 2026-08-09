import streamlit as st
import banco
import estilos


# =====================================================
# FUNÇÕES SUGERIDAS (mesmas categorias já usadas nos
# prefixos de usuário — só como sugestão no seletor,
# a pessoa pode digitar outra coisa em "Outra função")
# =====================================================

FUNCOES_SUGERIDAS = [
    "Separador",
    "Conferente",
    "Recebimento",
    "Empilhador",
    "Assistente Logístico",
    "Gestão",
    "Painel Logístico",
    "Outra função",
]


def _iniciais(nome, sobrenome):

    partes = [p for p in [nome, sobrenome] if p]

    return "".join(p[0].upper() for p in partes[:2]) or "?"


def _avatar_html(perfil, tamanho=96):

    foto = perfil.get("foto") if perfil else None

    if foto:

        return (
            f'<img src="{foto}" style="'
            f'width:{tamanho}px;height:{tamanho}px;border-radius:50%;'
            f'object-fit:cover;border:3px solid #3b82f6;'
            f'box-shadow:0 4px 14px rgba(59,130,246,.35);">'
        )

    iniciais = _iniciais(
        perfil.get("nome") if perfil else "",
        perfil.get("sobrenome") if perfil else ""
    )

    tamanho_fonte = tamanho * 0.38

    return (
        f'<div style="'
        f'width:{tamanho}px;height:{tamanho}px;border-radius:50%;'
        f'background:linear-gradient(135deg,#3b82f6,#a855f7);'
        f'display:flex;align-items:center;justify-content:center;'
        f'color:white;font-weight:800;font-size:{tamanho_fonte}px;'
        f'box-shadow:0 4px 14px rgba(59,130,246,.35);">{iniciais}</div>'
    )


def _formulario_perfil(usuario_alvo, armazem_id, chave_prefixo=""):
    """
    Formulário de edição de um perfil (o próprio, ou — se quem está
    editando for Fundador/Gestão — o de outra pessoa). chave_prefixo
    evita conflito de key quando o mesmo formulário é usado mais de
    uma vez na página (perfil próprio + edição de outra pessoa).
    """

    perfil_atual = banco.ler_perfil(usuario_alvo)

    col_foto, col_campos = st.columns([1, 3])

    with col_foto:

        st.markdown(
            _avatar_html(perfil_atual, tamanho=96),
            unsafe_allow_html=True
        )

    with col_campos:

        nome = st.text_input(
            "Nome",
            value=(perfil_atual or {}).get("nome", ""),
            key=f"{chave_prefixo}perfil_nome_{usuario_alvo}"
        )

        sobrenome = st.text_input(
            "Sobrenome",
            value=(perfil_atual or {}).get("sobrenome", ""),
            key=f"{chave_prefixo}perfil_sobrenome_{usuario_alvo}"
        )

    funcao_salva = (perfil_atual or {}).get("funcao", "")

    indice_funcao = (
        FUNCOES_SUGERIDAS.index(funcao_salva)
        if funcao_salva in FUNCOES_SUGERIDAS
        else len(FUNCOES_SUGERIDAS) - 1
    )

    funcao_escolhida = st.selectbox(
        "Função",
        FUNCOES_SUGERIDAS,
        index=indice_funcao,
        key=f"{chave_prefixo}perfil_funcao_sel_{usuario_alvo}"
    )

    if funcao_escolhida == "Outra função":

        funcao_final = st.text_input(
            "Digite a função",
            value=funcao_salva if funcao_salva not in FUNCOES_SUGERIDAS else "",
            key=f"{chave_prefixo}perfil_funcao_livre_{usuario_alvo}"
        )

    else:

        funcao_final = funcao_escolhida

    foto_upload = st.file_uploader(
        "Foto de perfil (opcional)",
        type=["png", "jpg", "jpeg"],
        key=f"{chave_prefixo}perfil_foto_{usuario_alvo}"
    )

    if st.button(
        "💾 Salvar perfil",
        key=f"{chave_prefixo}perfil_salvar_{usuario_alvo}"
    ):

        if not nome.strip() or not sobrenome.strip():

            st.warning("Preencha nome e sobrenome.")

        else:

            foto_base64 = (
                banco.foto_para_base64(foto_upload)
                if foto_upload is not None
                else None
            )

            with estilos.mostrar_processando("salvando perfil..."):
                banco.salvar_perfil(
                    usuario_alvo,
                    nome,
                    sobrenome,
                    funcao_final,
                    foto_base64,
                    armazem_id
                )

            estilos.notificar_sucesso("perfil salvo.")
            st.rerun(scope="fragment")


def render():

    usuario_atual = st.session_state.get("usuario", "")

    armazem_id_atual = st.session_state.get(
        "armazem_visualizado_id",
        st.session_state.get("armazem_id")
    )

    fundador = st.session_state.get("fundador", False)

    gestao = usuario_atual.startswith("Gestao.") or fundador

    estilos.cabecalho_pagina(
        "🪪",
        "Perfil",
        "Seu nome, sobrenome e foto — usados para o sistema te "
        "reconhecer certinho, mesmo quando há colegas com o mesmo "
        "primeiro nome.",
        cor="#3b82f6"
    )

    st.divider()

    perfil_atual = banco.ler_perfil(usuario_atual)

    if not perfil_atual:

        st.info(
            "Você ainda não preencheu seu perfil. Isso ajuda o sistema "
            "a te reconhecer corretamente em EPIs, auditorias e outros "
            "registros — mesmo se houver outra pessoa com o mesmo "
            "primeiro nome."
        )

    else:

        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:.5rem;">
                {_avatar_html(perfil_atual, tamanho=64)}
                <div>
                    <div style="font-size:1.2rem;font-weight:800;">
                        {banco.nome_completo_perfil(perfil_atual)}
                    </div>
                    <div style="opacity:.7;font-size:.85rem;">
                        {perfil_atual.get('funcao') or 'Função não informada'}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.expander("✏️ Editar meu perfil", expanded=not perfil_atual):

        _formulario_perfil(usuario_atual, armazem_id_atual, chave_prefixo="proprio_")

    st.divider()

    # =====================================================
    # ADMINISTRAÇÃO DE PERFIS (só Fundador/Gestão)
    # =====================================================

    if gestao:

        st.subheader("👥 Perfis da equipe")

        st.caption(
            "Como Gestão/Fundador, você pode preencher ou corrigir o "
            "perfil de qualquer pessoa daqui — útil quando alguém "
            "ainda não preencheu o próprio."
        )

        usuarios_cadastrados = banco.listar_usuarios(armazem_id_atual)

        perfis_existentes = {
            perfil["usuario"]: perfil
            for perfil in banco.ler_perfis(armazem_id_atual)
        }

        if not usuarios_cadastrados:

            st.info("Nenhum usuário cadastrado ainda.")

        else:

            com_perfil = [
                u for u in usuarios_cadastrados if u[1] in perfis_existentes
            ]

            sem_perfil = [
                u for u in usuarios_cadastrados if u[1] not in perfis_existentes
            ]

            c1, c2 = st.columns(2)

            with c1:
                st.metric("✅ Com perfil preenchido", len(com_perfil))

            with c2:
                st.metric("⏳ Sem perfil ainda", len(sem_perfil))

            nomes_usuarios = [u[1] for u in usuarios_cadastrados]

            usuario_escolhido = st.selectbox(
                "Escolha quem editar",
                nomes_usuarios,
                format_func=lambda u: (
                    f"{u} — {banco.nome_completo_perfil(perfis_existentes[u])}"
                    if u in perfis_existentes
                    else f"{u} — perfil não preenchido"
                )
            )

            with st.container(border=True):

                _formulario_perfil(
                    usuario_escolhido,
                    armazem_id_atual,
                    chave_prefixo="admin_"
                )

    st.divider()

    st.caption(
        "Luxiz IA • Perfil"
    )
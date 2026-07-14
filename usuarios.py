import streamlit as st
import banco


# ==================================================
# INICIALIZAÇÃO DA SESSÃO
# ==================================================

def iniciar_sessao():

    if "logado" not in st.session_state:
        st.session_state.logado = False

    if "usuario" not in st.session_state:
        st.session_state.usuario = ""

    if "fundador" not in st.session_state:
        st.session_state.fundador = False

    if "trocar_senha" not in st.session_state:
        st.session_state.trocar_senha = False


# ==================================================
# LOGIN
# ==================================================

def login(usuario, senha):

    resultado = banco.autenticar(
        usuario,
        senha
    )

    if not resultado:
        return False

    st.session_state.logado = True
    st.session_state.usuario = usuario

    st.session_state.trocar_senha = bool(
        resultado[1]
    )

    st.session_state.fundador = bool(
        resultado[2]
    )

    return True


# ==================================================
# LOGOUT
# ==================================================

def logout():

    st.session_state.logado = False
    st.session_state.usuario = ""
    st.session_state.fundador = False
    st.session_state.trocar_senha = False


# ==================================================
# VERIFICA LOGIN
# ==================================================

def usuario_logado():

    return st.session_state.get(
        "logado",
        False
    )


# ==================================================
# VERIFICA FUNDADOR
# ==================================================

def eh_fundador():

    return st.session_state.get(
        "fundador",
        False
    )


# ==================================================
# NOME DO USUÁRIO
# ==================================================

def nome_usuario():

    return st.session_state.get(
        "usuario",
        ""
    )


# ==================================================
# PRIMEIRO ACESSO
# ==================================================

def precisa_trocar_senha():

    return st.session_state.get(
        "trocar_senha",
        False
    )


# ==================================================
# ALTERAR SENHA
# ==================================================

def alterar_senha(
    nova_senha
):

    banco.alterar_senha(
        st.session_state.usuario,
        nova_senha
    )

    st.session_state.trocar_senha = False


# ==================================================
# CRIAR USUÁRIO
# ==================================================

def criar_usuario(
    usuario,
    senha
):

    try:

        banco.criar_usuario(
            usuario,
            senha
        )

        return True

    except:

        return False


# ==================================================
# RESETAR SENHA
# ==================================================

def resetar_senha(
    usuario,
    senha_temporaria
):

    banco.resetar_senha(
        usuario,
        senha_temporaria
    )


# ==================================================
# LISTA DE USUÁRIOS
# ==================================================

def listar_usuarios():

    return banco.listar_usuarios()

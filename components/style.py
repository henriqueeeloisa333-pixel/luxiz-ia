import streamlit as st

def inject_styles():
    st.markdown("""
        <style>
        /* Força o fundo em todo o contêiner principal */
        .stApp {
            background-color: #050505 !important;
        }
        
        /* Remove o padding padrão que o Streamlit coloca */
        .main .block-container {
            padding-top: 2rem !important;
        }
        
        /* CSS para Cards com Efeito de Vidro Profissional */
        div[data-testid="stVerticalBlock"] > div:has(div.glass-card) {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
import streamlit as st
import banco
import estilos


# =====================================================
# NOTIFICAÇÕES PENDENTES DO USUÁRIO LOGADO
# =====================================================
# Cada notificação é um dicionário com "tipo", "id", "titulo" e
# "mensagem" (e campos extras dependendo do tipo). A lista é
# pensada para receber outros tipos no futuro, além de EPI,
# checklist e top 3 do mês.

def _notificacoes_pendentes(usuario_atual, armazem_id):

    notificacoes = []

    registros_epi = banco.ler_epis(armazem_id)

    for registro in registros_epi:

        if registro["assinatura"]:
            continue

        if banco.epi_pertence_ao_usuario(registro["nome"], usuario_atual):

            notificacoes.append({
                "tipo": "epi",
                "id": registro["id"],
                "titulo": "🦺 EPI aguardando sua assinatura",
                "mensagem": (
                    f"{registro['epi']} — recebido em "
                    f"{registro['data'].strftime('%d/%m/%Y')}"
                )
            })

    # =====================================================
    # CHECKLIST DA SEXTA-FEIRA NÃO REALIZADO
    # =====================================================
    # Antes esse alerta aparecia direto nas páginas de Checklist e
    # Equipamentos. Agora ele entra na mesma central de notificações,
    # como uma notificação única que lista todas as pendências.

    pendentes_checklist, sexta_referencia = banco.listar_pendentes_checklist_sexta(
        armazem_id
    )

    if pendentes_checklist:

        notificacoes.append({
            "tipo": "checklist",
            "id": f"checklist_sexta_{sexta_referencia.isoformat()}",
            "titulo": "🚨 Checklist da Sexta-feira pendente",
            "mensagem": (
                f"{len(pendentes_checklist)} pessoa(s) vinculada(s) a "
                f"equipamentos não realizaram o Checklist da Sexta-feira "
                f"({sexta_referencia.strftime('%d/%m/%Y')}):"
            ),
            "itens": [
                f"{item['nome']} — {item['tipo']} {item['numero']}"
                for item in pendentes_checklist
            ]
        })

    # =====================================================
    # TOP 3 DO MÊS QUE FECHOU (RANKING DO DASHBOARD)
    # =====================================================
    # No último dia de cada mês (ou a partir do dia seguinte, até o
    # próximo fechamento) essa notificação parabeniza as 3 ruas/duplas
    # que fecharam o mês no topo do ranking do Dashboard.

    top3, data_fechamento = banco.ler_top3_fechamento_mes(armazem_id)

    if top3:

        MESES_EXTENSO = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro",
            "Dezembro"
        ]

        nome_mes = MESES_EXTENSO[data_fechamento.month - 1]
        rotulo_mes = f"{nome_mes}/{data_fechamento.year}"

        notificacoes.append({
            "tipo": "top3_mensal",
            "id": f"top3_{data_fechamento.year}_{data_fechamento.month:02d}",
            "titulo": f"🏆 Top 3 de {rotulo_mes}",
            "mensagem": (
                f"Parabéns às duplas que fecharam {rotulo_mes} no topo "
                f"do ranking do Dashboard!"
            ),
            "podio": [
                {
                    "posicao": indice + 1,
                    "rua": item["rua"],
                    "dupla": item["dupla"],
                    "nota": item["nota"]
                }
                for indice, item in enumerate(top3)
            ]
        })

    return notificacoes


# =====================================================
# CARD DO TOP 3 (visual dedicado, tipo "pódio")
# =====================================================

_CORES_PODIO = {
    1: {"cor": "#facc15", "medalha": "🥇", "rotulo": "1º lugar", "brilho": "rgba(250,204,21,.55)"},
    2: {"cor": "#cbd5e1", "medalha": "🥈", "rotulo": "2º lugar", "brilho": "rgba(203,213,225,.45)"},
    3: {"cor": "#d97706", "medalha": "🥉", "rotulo": "3º lugar", "brilho": "rgba(217,119,6,.5)"},
}


def _renderizar_card_top3(notificacao):

    chave_card = f"notif-top3-{notificacao['id']}"

    st.markdown(
        f"""
        <style>
        div[class*="st-key-{chave_card}"] {{
            background: linear-gradient(
                160deg,
                rgba(250,204,21,0.16),
                rgba(217,119,6,0.05) 60%
            ) !important;
            border: 2px solid #f59e0b !important;
            border-radius: 1.1rem;
            box-shadow: 0 8px 28px rgba(245,158,11,.18);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.container(border=True, key=chave_card):

        col_troféu, col_titulo = st.columns([1, 5], vertical_alignment="center")

        with col_troféu:

            st.markdown(
                """
                <div style="
                    width:58px;height:58px;border-radius:50%;
                    background:linear-gradient(135deg,#fde047,#f59e0b);
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.8rem;
                    box-shadow:0 0 20px rgba(245,158,11,.6);
                ">🏆</div>
                """,
                unsafe_allow_html=True
            )

        with col_titulo:

            titulo_sem_emoji = notificacao["titulo"].replace("🏆 ", "")

            st.markdown(
                f"""
                <div style="font-size:1.25rem;font-weight:800;
                    background:linear-gradient(90deg,#fde047,#f59e0b);
                    -webkit-background-clip:text;
                    background-clip:text;
                    color:transparent;
                    letter-spacing:.2px;
                ">{titulo_sem_emoji}</div>
                """,
                unsafe_allow_html=True
            )

            st.caption(
                notificacao["mensagem"]
            )

        st.write("")

        podio = sorted(
            notificacao.get("podio", []),
            key=lambda item: item["posicao"]
        )

        for item in podio:

            estilo = _CORES_PODIO.get(
                item["posicao"],
                _CORES_PODIO[3]
            )

            with st.container(border=False):

                st.markdown(
                    f"""
                    <div style="
                        display:flex;
                        align-items:center;
                        justify-content:space-between;
                        gap:.8rem;
                        background:{estilo['cor']}14;
                        border:1px solid {estilo['cor']}55;
                        border-left:5px solid {estilo['cor']};
                        border-radius:.7rem;
                        padding:.6rem .9rem;
                        margin-bottom:.5rem;
                    ">
                        <div style="display:flex;align-items:center;gap:.7rem;">
                            <div style="
                                width:42px;height:42px;border-radius:50%;
                                background:{estilo['cor']}22;
                                border:2px solid {estilo['cor']};
                                display:flex;align-items:center;justify-content:center;
                                font-size:1.3rem;
                                box-shadow:0 0 12px {estilo['brilho']};
                                flex-shrink:0;
                            ">{estilo['medalha']}</div>
                            <div>
                                <div style="font-weight:800;font-size:.98rem;">
                                    📍 {item['rua']}
                                </div>
                                <div style="font-size:.82rem;opacity:.75;">
                                    👥 {item['dupla']}
                                </div>
                            </div>
                        </div>
                        <div style="
                            background:{estilo['cor']};
                            color:#1f2937;
                            font-weight:800;
                            font-size:.85rem;
                            padding:.3rem .65rem;
                            border-radius:999px;
                            white-space:nowrap;
                        ">⭐ {item['nota']:.1f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.markdown(
            """
            <div style="
                text-align:center;
                font-size:.8rem;
                opacity:.7;
                margin-top:.2rem;
            ">✨ Continuem com esse desempenho de excelência! ✨</div>
            """,
            unsafe_allow_html=True
        )


def _eh_gestao_ou_fundador(usuario_atual):

    return (
        usuario_atual.startswith("Fundador.")
        or usuario_atual.startswith("Gestao.")
    )


def _renderizar_notificacao(notificacao, usuario_atual, armazem_id):

    if notificacao["tipo"] == "top3_mensal":

        _renderizar_card_top3(notificacao)
        return

    with st.container(border=True):

        st.markdown(
            f"**{notificacao['titulo']}**"
        )

        st.caption(
            notificacao["mensagem"]
        )

        if notificacao["tipo"] == "epi":

            if st.button(
                "✅ Assinar recebimento",
                key=f"notif_assinar_epi_{notificacao['id']}"
            ):
                with estilos.mostrar_processando("registrando assinatura..."):
                    banco.assinar_epi(
                        notificacao["id"],
                        usuario_atual,
                        armazem_id
                    )
                estilos.notificar_sucesso("Assinatura registrada.")
                st.rerun()

        elif notificacao["tipo"] == "checklist":

            for item_texto in notificacao.get("itens", []):

                st.caption(
                    f"• {item_texto}"
                )


def _botao_excluir(notificacao, armazem_id, usuario_atual, sufixo):
    """
    Some para TODOS os usuários do armazém (diferente de "lida",
    que é individual). Só aparece para Gestão/Fundador.
    """

    if st.button(
        "🗑️ Excluir para todos",
        key=f"notif_excluir_{sufixo}_{notificacao['id']}",
        width='stretch'
    ):
        banco.excluir_notificacao(
            notificacao["id"],
            armazem_id,
            usuario_atual
        )
        estilos.notificar_sucesso("Notificação excluída para todos.")
        st.rerun()


@st.dialog("🔔 Notificações")
def _painel_notificacoes(usuario_atual, armazem_id, notificacao, posicao, total, pode_excluir):
    """
    Mostra UMA notificação por vez (fila de não lidas). O botão
    marca como lida — individualmente, só para quem clicou — e
    avança para a próxima da fila, se houver.
    """

    if total > 1:

        st.caption(
            f"📬 Notificação {posicao} de {total}"
        )

    _renderizar_notificacao(
        notificacao,
        usuario_atual,
        armazem_id
    )

    st.write("")

    rotulo_botao = "➡️ Próxima" if posicao < total else "✅ Marcar como lida e fechar"

    if pode_excluir:
        col_lida, col_excluir = st.columns(2)
    else:
        col_lida = st.container()
        col_excluir = None

    with col_lida:

        if st.button(
            rotulo_botao,
            key=f"notif_lida_{notificacao['id']}",
            width='stretch'
        ):
            banco.marcar_notificacao_lida(
                usuario_atual,
                notificacao["id"],
                armazem_id
            )
            st.rerun()

    if col_excluir is not None:

        with col_excluir:

            _botao_excluir(notificacao, armazem_id, usuario_atual, "fila")


@st.dialog("🔔 Central de Notificações")
def _painel_revisao(usuario_atual, armazem_id, notificacoes, lidas, pode_excluir):
    """
    Aberta ao clicar no sino: mostra TODAS as notificações ativas no
    momento (lidas ou não), só para consulta — não interfere no
    status individual de "lida" de ninguém.
    """

    if not notificacoes:

        st.success(
            "Nenhuma notificação no momento. ✅"
        )

        if st.button("Fechar", width='stretch', key="notif_central_fechar_vazia"):
            st.session_state["_luxiz_abrir_central_notif"] = False
            st.rerun()

        return

    for notificacao in notificacoes:

        _renderizar_notificacao(
            notificacao,
            usuario_atual,
            armazem_id
        )

        if notificacao["id"] in lidas:

            st.caption("✅ Você já marcou como lida.")

        elif st.button(
            "✅ Marcar como lida",
            key=f"notif_lida_rev_{notificacao['id']}",
            width='stretch'
        ):
            banco.marcar_notificacao_lida(
                usuario_atual,
                notificacao["id"],
                armazem_id
            )
            st.rerun()

        if pode_excluir:

            _botao_excluir(notificacao, armazem_id, usuario_atual, "rev")

        st.divider()

    if st.button("Fechar", width='stretch', key="notif_central_fechar"):
        st.session_state["_luxiz_abrir_central_notif"] = False
        st.rerun()


def _notificacoes_ativas(usuario_atual, armazem_id):
    """
    Notificações pendentes do usuário, já sem as que a Gestão/
    Fundador excluiu globalmente para este armazém.
    """

    excluidas = banco.notificacoes_excluidas(armazem_id)

    return [
        notificacao
        for notificacao in _notificacoes_pendentes(usuario_atual, armazem_id)
        if notificacao["id"] not in excluidas
    ]


def contar_pendentes(usuario_atual, armazem_id):
    """
    Quantidade de notificações ainda não lidas por este usuário.
    Usada no painel da tela Início (KPIs), sem precisar desenhar
    o sino inteiro de novo.
    """

    notificacoes = _notificacoes_ativas(usuario_atual, armazem_id)
    lidas = banco.notificacoes_lidas_usuario(usuario_atual, armazem_id)

    return len([
        notificacao for notificacao in notificacoes
        if notificacao["id"] not in lidas
    ])


def renderizar(usuario_atual, armazem_id):
    """
    Chamada na tela Início. Decide, nesta ordem, no máximo UM
    diálogo para abrir na rodada atual (o Streamlit não permite
    dois diálogos abertos na mesma execução do script):

    1) Se o sino foi clicado (flag em session_state), abre a
       Central de Notificações completa, com tudo que está ativo
       no momento (lido ou não).
    2) Senão, se houver notificação ainda não lida por ESTE
       usuário, abre a fila automática — uma de cada vez — e ao
       marcar como lida fica lida para sempre (mesmo depois de
       deslogar e logar de novo). Só reaparece se for uma
       ocorrência nova (ex.: checklist da sexta seguinte, ou o
       Top 3 do mês seguinte).
    """

    notificacoes = _notificacoes_ativas(usuario_atual, armazem_id)
    lidas = banco.notificacoes_lidas_usuario(usuario_atual, armazem_id)

    if st.session_state.get("_luxiz_abrir_central_notif", False):

        _painel_revisao(
            usuario_atual,
            armazem_id,
            notificacoes,
            lidas,
            _eh_gestao_ou_fundador(usuario_atual)
        )

        return

    total = len(notificacoes)

    restantes = [
        notificacao for notificacao in notificacoes
        if notificacao["id"] not in lidas
    ]

    if restantes:

        posicao_atual = total - len(restantes) + 1

        _painel_notificacoes(
            usuario_atual,
            armazem_id,
            restantes[0],
            posicao_atual,
            total,
            _eh_gestao_ou_fundador(usuario_atual)
        )


def sino(usuario_atual, armazem_id):
    """
    Sino compacto para ficar no cabeçalho, ao lado do "🟢 Online".
    Fica vermelho com a contagem quando há notificação(ões) ainda
    não lida(s) por este usuário, e verde quando não há nenhuma.
    Passar o mouse por cima mostra a dica (tooltip); clicar apenas
    sinaliza a intenção e reinicia a rodada — quem de fato abre o
    diálogo é o renderizar(), pra nunca haver dois diálogos
    tentando abrir na mesma execução.
    """

    notificacoes = _notificacoes_ativas(usuario_atual, armazem_id)
    lidas = banco.notificacoes_lidas_usuario(usuario_atual, armazem_id)

    pendentes = [
        notificacao for notificacao in notificacoes
        if notificacao["id"] not in lidas
    ]

    tem_pendente = len(pendentes) > 0

    cor = "#ef4444" if tem_pendente else "#22c55e"
    fundo = "rgba(239,68,68,.16)" if tem_pendente else "rgba(34,197,94,.14)"

    st.markdown(
        f"""
        <style>
        div[class*="st-key-sino_notificacoes"] button {{
            border-radius: 50% !important;
            width: 2.4rem !important;
            height: 2.4rem !important;
            min-height: 2.4rem !important;
            padding: 0 !important;
            border: 2px solid {cor} !important;
            background: {fundo} !important;
            color: {cor} !important;
            font-size: .95rem !important;
            font-weight: 800 !important;
            line-height: 1 !important;
            box-shadow: 0 0 10px {cor}55;
        }}
        div[class*="st-key-sino_notificacoes"] button:hover {{
            filter: brightness(1.15);
            transform: scale(1.05);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    rotulo = f"🔔{len(pendentes)}" if tem_pendente else "🔔"

    dica = (
        f"🔔 Notificação — {len(pendentes)} pendente(s)"
        if tem_pendente
        else "🔔 Notificação — nenhuma pendente"
    )

    if st.button(
        rotulo,
        key="sino_notificacoes",
        help=dica
    ):
        st.session_state["_luxiz_abrir_central_notif"] = True
        st.rerun()
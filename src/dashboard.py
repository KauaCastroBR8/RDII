"""
src/dashboard.py
=================
DASHBOARD INTERATIVO COM STREAMLIT
----------------------------------
Cria uma interface web bonita para visualizar a carteira de investimentos.

COMO RODAR:
    streamlit run src/dashboard.py

ACESSAR:
    http://localhost:8501
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
import os

# ============================================================
# CORREÇÃO DE IMPORT (funciona executando direto OU como pacote)
# ============================================================
if __package__ is None or __package__ == '':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from portfolio import CarteiraInvestimentos
else:
    from .portfolio import CarteiraInvestimentos


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="RDII - Rastreador de Investimentos",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS PERSONALIZADO
# ============================================================
st.markdown("""
<style>
    .main > div { padding-top: 2rem; }
    .stMetric {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #333;
    }
    h1 { color: #00ff88 !important; }
    h2 { color: #ffffff !important; }
    h3 { color: #cccccc !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():
    """Renderiza todo o dashboard."""
    
    # --- TÍTULO ---
    st.title("📊 Rastreador de Investimentos Inteligente")
    st.markdown("**Acompanhe sua carteira em tempo real** | Dados com delay de 15-20 min")
    st.markdown("---")
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        if st.button("🔄 Atualizar Cotações", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("**📁 Arquivo:** `data/carteira.json`")
        st.markdown("**💾 Cache:** 5 minutos")
        st.markdown("**🌐 Fonte:** Yahoo Finance + BCB")
        st.markdown("---")
        st.markdown("Desenvolvido com ❤️ em Python")
    
    # --- CARREGA DADOS (cache 5 min) ---
    @st.cache_data(ttl=300, show_spinner=False)
    def carregar_dados():
        with st.spinner("🔄 Buscando cotações..."):
            carteira = CarteiraInvestimentos("data/carteira.json")
            return carteira.gerar_relatorio()
    
    relatorio = carregar_dados()
    resumo = relatorio['resumo_geral']
    
    # --- CARDS DE RESUMO ---
    st.subheader("📈 Resumo da Carteira")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    def formatar_reais(valor):
        """Formata número no padrão brasileiro: R$ 17.125,00"""
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    with col1:
        st.metric("💰 Patrimônio Total", formatar_reais(resumo['patrimonio_total']),
                 delta=formatar_reais(resumo['lucro_prejuizo_total']))
    
    with col2:
        delta_color = "normal" if resumo['rentabilidade_total_pct'] >= 0 else "inverse"
        st.metric("📊 Rentabilidade", f"{resumo['rentabilidade_total_pct']}%",
                 delta=f"{resumo['rentabilidade_total_pct']}%", delta_color=delta_color)
    
    with col3:
        st.metric("🏦 Investido Inicial", formatar_reais(resumo['patrimonio_investido']))
    
    with col4:
        st.metric("📈 Renda Variável", formatar_reais(resumo['total_renda_variavel']))
    
    with col5:
        st.metric("🏛️ CDI Atual", relatorio['benchmarks']['cdi_anual_atual'])
    
    st.markdown("---")
    
    # --- GRÁFICOS E TABELAS ---
    col_esq, col_dir = st.columns([1, 1])
    
    with col_esq:
        st.subheader("🥧 Composição da Carteira")
        
        dados_pizza = []
        for ativo in relatorio['detalhamento_rv']:
            dados_pizza.append({"Ativo": ativo['ticker'], "Valor": ativo['valor_atual'], "Tipo": "Renda Variável"})
        for rf in relatorio['detalhamento_rf']:
            dados_pizza.append({"Ativo": rf['nome'], "Valor": rf['valor_investido'], "Tipo": "Renda Fixa"})
        
        df_pizza = pd.DataFrame(dados_pizza)
        
        fig_pizza = px.pie(
            df_pizza,
            values='Valor',
            names='Ativo',
            hole=0.4,
            color='Tipo',
            color_discrete_map={'Renda Variável': '#00cc66', 'Renda Fixa': '#1f77b4'}
        )
        fig_pizza.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
        )
        fig_pizza.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.1),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        st.plotly_chart(fig_pizza, use_container_width=True)
    
    with col_dir:
        st.subheader("📋 Detalhamento dos Ativos")
        
        df_rv = pd.DataFrame(relatorio['detalhamento_rv'])
        if not df_rv.empty:
            df_display = df_rv[['ticker', 'tipo', 'quantidade', 'preco_medio', 'preco_atual', 'valor_atual', 'rentabilidade_pct']].copy()
            df_display.columns = ['Ticker', 'Tipo', 'Qtd', 'Preço Médio', 'Preço Atual', 'Valor Atual', 'Rent %']
            
            # CORREÇÃO PANDAS 3.0: applymap virou map
            def color_rent(val):
                if val > 0:
                    return 'color: #00ff88'
                elif val < 0:
                    return 'color: #ff4444'
                return 'color: #ffffff'
            
            st.dataframe(
                df_display.style.map(color_rent, subset=['Rent %']),
                use_container_width=True,
                hide_index=True
            )
    
    st.markdown("---")
    
    # --- GRÁFICO DE RENTABILIDADE ---
    st.subheader("📊 Rentabilidade por Ativo (%)")
    
    df_rent = pd.DataFrame(relatorio['detalhamento_rv'])
    if not df_rent.empty:
        cores_bar = ['#00ff88' if x >= 0 else '#ff4444' for x in df_rent['rentabilidade_pct']]
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=df_rent['ticker'],
            y=df_rent['rentabilidade_pct'],
            marker_color=cores_bar,
            text=[f"{x:.1f}%" for x in df_rent['rentabilidade_pct']],
            textposition='auto',
            textfont=dict(color='white', size=14),
            hovertemplate='<b>%{x}</b><br>%{y:.2f}%<<extra></extra>'
        ))
        fig_bar.update_layout(
            yaxis_title="Rentabilidade (%)",
            xaxis_title="Ativo",
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)')
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # --- RENDA FIXA ---
    st.markdown("---")
    st.subheader("🏛️ Renda Fixa")
    
    for rf in relatorio['detalhamento_rf']:
        col_rf1, col_rf2, col_rf3 = st.columns(3)
        with col_rf1:
            st.metric(rf['nome'], formatar_reais(rf['valor_investido']))
        with col_rf2:
            st.metric("Taxa", rf['taxa'])
        with col_rf3:
            st.metric("Tipo", rf['tipo'])
    
    # --- RODAPÉ ---
    st.markdown("---")
    st.caption(f"📅 Última atualização: {relatorio['data_geracao']} | Dados: Yahoo Finance + Banco Central do Brasil")


# ============================================================
# PONTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    main()
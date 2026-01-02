import streamlit as st
import pandas as pd
from analysis_engine import CryptoDataEngine
from sqlalchemy import create_engine
import datetime

# Configuração da Página
st.set_page_config(page_title="CryptoIntel Pro", layout="wide", page_icon="🛡️")

# Injeção de CSS para ficar bonito
st.markdown("""
<style>
   .metric-card {background-color: #f0f2f6; border-radius: 10px; padding: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);}
   .high-score {color: green; font-weight: bold;}
   .low-score {color: red; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

st.title("🛡️ CryptoIntel: Sistema de Análise Fundamentalista & Quantitativa")
st.markdown("---")

# --- SIDEBAR: Configurações do Usuário ---
with st.sidebar:
    st.header("⚙️ Parâmetros da Análise")
    
    # Input Valor Monetário
    max_price = st.number_input("Preço Máximo por Ativo ($)", value=10.0, step=0.1, min_value=0.000001)
    
    # Input Lista Personalizada
    st.subheader("🕵️ Lista Personalizada")
    custom_input = st.text_area("IDs (ex: kaspa, monero)", "kaspa, render-token")
    custom_ids = [x.strip() for x in custom_input.split(',')] if custom_input else
    
    # Botão de Ação
    analyze_btn = st.button("🚀 Iniciar Análise Completa", type="primary")
    
    st.info("Nota: A análise varre as Top 500 moedas e aplica filtros de preço e métricas de 12 meses.")

# --- LÓGICA PRINCIPAL ---
if analyze_btn:
    engine = CryptoDataEngine()
    
    with st.status("Executando Pipeline de Dados...", expanded=True) as status:
        # 1. Coleta
        st.write("📡 Conectando CoinGecko API (Mercado)...")
        df_market = engine.fetch_market_data(max_price, custom_ids)
        st.write(f"✅ {len(df_market)} ativos encontrados abaixo de ${max_price}")
        
        # 2. Dados Fundamentais
        st.write("🔗 Conectando DefiLlama (TVL & Segurança)...")
        df_defi = engine.fetch_defi_data()
        
        # 3. Cálculo
        st.write("🧮 Calculando os 25 Indicadores (Matriz de Pontuação)...")
        df_final = engine.calculate_scores(df_market, df_defi)
        
        # 4. Armazenamento (Base de Conhecimento)
        st.write("💾 Gravando na Base de Conhecimento Histórica...")
        # Aqui usamos SQLite local. Para online real, mude a string para seu Postgres (Supabase/Neon)
        db_engine = create_engine('sqlite:///crypto_knowledge_base.db') 
        
        # Salva snapshot com data
        save_df = df_final.copy()
        save_df['timestamp'] = datetime.datetime.now()
        save_df.to_sql('historical_analysis', db_engine, if_exists='append', index=False)
        
        status.update(label="Análise Concluída com Sucesso!", state="complete", expanded=False)

    # --- DASHBOARD DE RESULTADOS ---
    
    # Top Métricas
    col1, col2, col3 = st.columns(3)
    best_asset = df_final.loc.idxmax()]
    with col1:
        st.metric("Melhor Ativo (Score)", best_asset['name'], f"{best_asset:.2f}/20")
    with col2:
        st.metric("Maior Potencial 12m", f"{best_asset['price_change_percentage_1y_in_currency']:.1f}%")
    with col3:
        st.metric("Total Analisado", len(df_final))

    # Tabela Final
    st.subheader("🏆 Tabela Final: Classificação de Potencial")
    
    # Colunas para exibir
    display_cols =
    
    # Formatação condicional e exibição
    st.dataframe(
        df_final[display_cols].sort_values(by='FINAL_SCORE', ascending=False).style.background_gradient(subset=, cmap='RdYlGn'),
        use_container_width=True,
        column_config={
            "current_price": st.column_config.NumberColumn("Preço ($)", format="$%.4f"),
            "market_cap": st.column_config.NumberColumn("Mkt Cap", format="$%d"),
            "tvl": st.column_config.NumberColumn("TVL (DeFi)", format="$%d"),
            "FINAL_SCORE": st.column_config.ProgressColumn("Nota Final (0-20)", min_value=0, max_value=20, format="%.2f"),
        }
    )

    # --- DRILL DOWN (Detalhes) ---
    st.markdown("---")
    st.subheader("🔍 Análise Detalhada & Sentimento")
    selected_coin = st.selectbox("Selecione um ativo para ver o relatório completo:", df_final['name'].unique())
    
    coin_data = df_final[df_final['name'] == selected_coin].iloc
    
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.image(coin_data['image'], width=100)
        st.markdown(f"### {coin_data['name']} ({coin_data['symbol'].upper()})")
        st.write(f"**Preço:** ${coin_data['current_price']}")
        st.write(f"**ATH:** ${coin_data['ath']} (Queda de {coin_data['ath_change_percentage']:.1f}%)")
        
    with c2:
        # Radar Chart dos Indicadores
        categories =
        values = [
            coin_data['score_security'], coin_data['score_tokenomics'], 
            coin_data['score_adoption'], coin_data['score_performance_1y'], 
            coin_data['score_tech_dev']
        
        chart_data = pd.DataFrame(dict(
            r=values,
            theta=categories
        ))
        import plotly.express as px
        fig = px.line_polar(chart_data, r='r', theta='theta', line_close=True, range_r=)
        fig.update_traces(fill='toself')
        st.plotly_chart(fig, use_container_width=True)

    # Fonte de Dados e Auditoria
    with st.expander("📂 Ver Fontes de Dados e Auditoria"):
        st.json({
            "Data da Coleta": str(datetime.datetime.now()),
            "Fonte Primária": "CoinGecko API v3",
            "Fonte Secundária": "DefiLlama API",
            "ID do Ativo": coin_data['id'],
            "Última Atualização": coin_data['last_updated']
        })

# --- ABA HISTÓRICO (Base de Conhecimento) ---
if st.checkbox("Ver Base de Conhecimento Histórica (Dados Salvos)"):
    try:
        db_engine = create_engine('sqlite:///crypto_knowledge_base.db')
        history_df = pd.read_sql("SELECT timestamp, name, FINAL_SCORE, current_price FROM historical_analysis", db_engine)
        st.line_chart(history_df, x='timestamp', y='FINAL_SCORE', color='name')
    except:
        st.warning("Ainda não há dados históricos salvos. Execute uma análise primeiro.")
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from analysis_engine import CryptoDataEngine
from sqlalchemy import create_engine
import datetime

# Configuração da Página
st.set_page_config(page_title="CryptoIntel Pro", layout="wide", page_icon="🛡️")

st.title("🛡️ CryptoIntel: Sistema de Análise Fundamentalista")
st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Parâmetros")
    max_price = st.number_input("Preço Máximo ($)", value=10.0, step=0.1, min_value=0.000001)
    
    st.subheader("🕵️ Lista Personalizada")
    custom_input = st.text_area("IDs (ex: kaspa, monero)", "kaspa, render-token")
    
    # --- CORREÇÃO DO ERRO ---
    if custom_input:
        custom_ids = [x.strip() for x in custom_input.split(',')]
    else:
        custom_ids =  # Agora tem os parêntesis retos (lista vazia)
    # ------------------------
    
    analyze_btn = st.button("🚀 Iniciar Análise", type="primary")

# --- LÓGICA PRINCIPAL ---
if analyze_btn:
    engine = CryptoDataEngine()
    
    with st.status("A processar dados...", expanded=True) as status:
        st.write("📡 A ler CoinGecko API...")
        df_market = engine.fetch_market_data(max_price, custom_ids)
        st.write(f"✅ {len(df_market)} ativos encontrados")
        
        st.write("🔗 A ler DefiLlama...")
        df_defi = engine.fetch_defi_data()
        
        st.write("🧮 A calcular indicadores...")
        df_final = engine.calculate_scores(df_market, df_defi)
        
        if not df_final.empty:
            # Armazenamento (SQLite)
            st.write("💾 A guardar histórico...")
            try:
                db_engine = create_engine('sqlite:///crypto_knowledge_base.db') 
                save_df = df_final.copy()
                # Converter colunas complexas para string
                for col in save_df.columns:
                    if save_df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                        save_df[col] = save_df[col].astype(str)
                
                save_df['timestamp'] = datetime.datetime.now()
                save_df.to_sql('historical_analysis', db_engine, if_exists='append', index=False)
            except Exception as e:
                st.warning(f"Aviso BD: {e}")
            
            status.update(label="Concluído!", state="complete", expanded=False)
        else:
            status.update(label="Sem dados.", state="error")
            st.stop()

    # --- DASHBOARD ---
    if not df_final.empty and 'FINAL_SCORE' in df_final.columns:
        col1, col2, col3 = st.columns(3)
        
        # Encontrar melhor ativo de forma segura
        best_idx = df_final.idxmax()
        best_asset = df_final.loc[best_idx]
        
        with col1:
            st.metric("Melhor Ativo", best_asset['name'], f"{best_asset:.2f}/20")
        with col2:
            val = best_asset.get('price_change_percentage_1y_in_currency', 0)
            st.metric("Variação 1 Ano", f"{val:.1f}%")
        with col3:
            st.metric("Total Analisado", len(df_final))

        st.subheader("🏆 Tabela de Classificação")
        
        # Colunas para exibir (apenas as que existem)
        desired_cols =
        valid_cols = [c for c in desired_cols if c in df_final.columns]
        
        st.dataframe(
            df_final[valid_cols].sort_values(by='FINAL_SCORE', ascending=False).style.background_gradient(subset=, cmap='RdYlGn'),
            use_container_width=True,
            column_config={
                "current_price": st.column_config.NumberColumn("Preço", format="$%.4f"),
                "market_cap": st.column_config.NumberColumn("Mkt Cap", format="$%d"),
                "FINAL_SCORE": st.column_config.ProgressColumn("Nota (0-20)", min_value=0, max_value=20, format="%.2f"),
            }
        )

        st.markdown("---")
        st.subheader("🔍 Detalhes do Ativo")
        
        selected = st.selectbox("Escolha um ativo:", df_final['name'].unique())
        coin_data = df_final[df_final['name'] == selected].iloc
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            if 'image' in coin_data and coin_data['image']:
                st.image(coin_data['image'], width=100)
            st.markdown(f"### {coin_data['name']}")
            st.write(f"**Preço:** ${coin_data['current_price']}")
            
        with c2:
            categories =
            # Usar.get() para evitar erros se a coluna não existir
            values = [
                float(coin_data.get('score_security', 0)), 
                float(coin_data.get('score_tokenomics', 0)), 
                float(coin_data.get('score_adoption', 0)), 
                float(coin_data.get('score_performance_1y', 0)), 
                float(coin_data.get('score_tech_dev', 0))
            ]
            
            fig = px.line_polar(pd.DataFrame({'r': values, 'theta': categories}), r='r', theta='theta', line_close=True, range_r=)
            fig.update_traces(fill='toself')
            st.plotly_chart(fig, use_container_width=True)

# --- HISTÓRICO ---
if st.checkbox("Ver Base de Conhecimento (Histórico)"):
    try:
        db_engine = create_engine('sqlite:///crypto_knowledge_base.db')
        history_df = pd.read_sql("SELECT timestamp, name, FINAL_SCORE FROM historical_analysis", db_engine)
        if not history_df.empty:
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
            st.line_chart(history_df, x='timestamp', y='FINAL_SCORE', color='name')
        else:
            st.info("Ainda sem histórico.")
    except:
        st.info("Execute uma análise primeiro para criar o histórico.")

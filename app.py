import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from analysis_engine import CryptoDataEngine
from sqlalchemy import create_engine
import datetime

# Configuração da Página
st.set_page_config(page_title="CryptoIntel Pro", layout="wide", page_icon="🛡️")

# Injeção de CSS
st.markdown("""
<style>
.metric-card {background-color: #f0f2f6; border-radius: 10px; padding: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

st.title("🛡️ CryptoIntel: Sistema de Análise Fundamentalista & Quantitativa")
st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Parâmetros da Análise")
    max_price = st.number_input("Preço Máximo por Ativo ($)", value=10.0, step=0.1, min_value=0.000001)
    
    st.subheader("🕵️ Lista Personalizada")
    custom_input = st.text_area("IDs (ex: kaspa, monero)", "kaspa, render-token")
    
    # CORREÇÃO DA LINHA QUE DEU ERRO: Adicionado o "" no final
    custom_ids = [x.strip() for x in custom_input.split(',')] if custom_input else
    
    analyze_btn = st.button("🚀 Iniciar Análise Completa", type="primary")
    st.info("Nota: A análise varre as Top 500 moedas e aplica filtros de preço e métricas de 12 meses.")

# --- LÓGICA PRINCIPAL ---
if analyze_btn:
    engine = CryptoDataEngine()
    
    with st.status("Executando Pipeline de Dados...", expanded=True) as status:
        st.write("📡 Conectando CoinGecko API (Mercado)...")
        df_market = engine.fetch_market_data(max_price, custom_ids)
        st.write(f"✅ {len(df_market)} ativos encontrados abaixo de ${max_price}")
        
        st.write("🔗 Conectando DefiLlama (TVL & Segurança)...")
        df_defi = engine.fetch_defi_data()
        
        st.write("🧮 Calculando os 25 Indicadores (Matriz de Pontuação)...")
        df_final = engine.calculate_scores(df_market, df_defi)
        
        if not df_final.empty:
            # Armazenamento (SQLite Local)
            st.write("💾 Gravando na Base de Conhecimento Histórica...")
            try:
                db_engine = create_engine('sqlite:///crypto_knowledge_base.db') 
                save_df = df_final.copy()
                # Converter colunas complexas para string para evitar erros no SQL
                for col in save_df.columns:
                    if save_df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                        save_df[col] = save_df[col].astype(str)
                
                save_df['timestamp'] = datetime.datetime.now()
                save_df.to_sql('historical_analysis', db_engine, if_exists='append', index=False)
            except Exception as e:
                st.warning(f"Aviso ao salvar banco de dados: {e}")
            
            status.update(label="Análise Concluída com Sucesso!", state="complete", expanded=False)
        else:
            status.update(label="Nenhum dado encontrado.", state="error")
            st.stop()

    # --- DASHBOARD DE RESULTADOS ---
    if not df_final.empty and 'FINAL_SCORE' in df_final.columns:
        col1, col2, col3 = st.columns(3)
        
        # Encontrar melhor ativo
        best_idx = df_final.idxmax()
        best_asset = df_final.loc[best_idx]
        
        with col1:
            st.metric("Melhor Ativo (Score)", best_asset['name'], f"{best_asset:.2f}/20")
        with col2:
            val_change = best_asset.get('price_change_percentage_1y_in_currency', 0)
            st.metric("Maior Potencial 12m", f"{val_change:.1f}%")
        with col3:
            st.metric("Total Analisado", len(df_final))

        # Tabela Final
        st.subheader("🏆 Tabela Final: Classificação de Potencial")
        
        # Definição das colunas (CORREÇÃO: Lista preenchida)
        display_cols =
        
        # Garantir que colunas existem antes de mostrar
        valid_cols = [c for c in display_cols if c in df_final.columns]
        
        st.dataframe(
            df_final[valid_cols].sort_values(by='FINAL_SCORE', ascending=False).style.background_gradient(subset=, cmap='RdYlGn'),
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
        
        selected_coin_name = st.selectbox("Selecione um ativo para ver o relatório completo:", df_final['name'].unique())
        coin_data = df_final[df_final['name'] == selected_coin_name].iloc
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.image(coin_data['image'], width=100)
            st.markdown(f"### {coin_data['name']} ({coin_data['symbol'].upper()})")
            st.write(f"**Preço:** ${coin_data['current_price']}")
            ath_change = coin_data.get('ath_change_percentage', 0)
            st.write(f"**ATH:** ${coin_data.get('ath', 0)} ({ath_change:.1f}%)")
            
        with c2:
            # Radar Chart
            categories =
            values = [
                float(coin_data.get('score_security', 0)), 
                float(coin_data.get('score_tokenomics', 0)), 
                float(coin_data.get('score_adoption', 0)), 
                float(coin_data.get('score_performance_1y', 0)), 
                float(coin_data.get('score_tech_dev', 0))
            ]
            
            chart_data = pd.DataFrame(dict(
                r=values,
                theta=categories
            ))
            fig = px.line_polar(chart_data, r='r', theta='theta', line_close=True, range_r=)
            fig.update_traces(fill='toself')
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("📂 Ver Fontes de Dados e Auditoria"):
            st.json({
                "Data da Coleta": str(datetime.datetime.now()),
                "Fonte Primária": "CoinGecko API v3",
                "Fonte Secundária": "DefiLlama API",
                "ID do Ativo": coin_data['id'],
                "Última Atualização": coin_data['last_updated']
            })

# --- ABA HISTÓRICO ---
if st.checkbox("Ver Base de Conhecimento Histórica (Dados Salvos)"):
    try:
        db_engine = create_engine('sqlite:///crypto_knowledge_base.db')
        history_df = pd.read_sql("SELECT timestamp, name, FINAL_SCORE FROM historical_analysis", db_engine)
        if not history_df.empty:
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
            st.line_chart(history_df, x='timestamp', y='FINAL_SCORE', color='name')
        else:
            st.info("Tabela vazia por enquanto.")
    except Exception as e:
        st.warning("Ainda não há dados históricos salvos. Execute uma análise primeiro.")

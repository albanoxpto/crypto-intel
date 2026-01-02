import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime

class CryptoDataEngine:
    def __init__(self):
        self.cg_url = "https://api.coingecko.com/api/v3"
        self.dl_url = "https://api.llama.fi"

    def fetch_market_data(self, max_price, custom_ids=None):
        """Busca Top 500 moedas + Customizadas e filtra por preço."""
        all_coins =
        
        # Paginação para pegar 500 moedas (2 páginas de 250)
        for page in [1, 2]: 
            try:
                params = {
                    'vs_currency': 'usd',
                    'order': 'market_cap_desc',
                    'per_page': 250,
                    'page': page,
                    'sparkline': 'false',
                    'price_change_percentage': '1h,24h,7d,30d,1y'
                }
                resp = requests.get(f"{self.cg_url}/coins/markets", params=params)
                if resp.status_code == 200:
                    all_coins.extend(resp.json())
                time.sleep(1.5) # Respeita o rate limit
            except Exception as e:
                print(f"Erro na pagina {page}: {e}")

        # Busca dados das moedas personalizadas
        if custom_ids:
            # Filtra strings vazias
            custom_ids = [x for x in custom_ids if x]
            if custom_ids:
                str_ids = ",".join(custom_ids)
                try:
                    params_cust = {
                        'vs_currency': 'usd',
                        'ids': str_ids,
                        'price_change_percentage': '1h,24h,7d,30d,1y'
                    }
                    resp = requests.get(f"{self.cg_url}/coins/markets", params=params_cust)
                    if resp.status_code == 200:
                        current_ids = [c['id'] for c in all_coins]
                        for c in resp.json():
                            if c['id'] not in current_ids:
                                all_coins.append(c)
                except Exception as e:
                    print(f"Erro custom: {e}")

        # Transforma em DataFrame
        df = pd.DataFrame(all_coins)
        
        # Filtro de Preço do Usuário
        if not df.empty and 'current_price' in df.columns:
            df = df[df['current_price'] <= max_price]
            
        return df

    def fetch_defi_data(self):
        """Busca dados de TVL e Auditorias do DefiLlama."""
        try:
            resp = requests.get(f"{self.dl_url}/protocols")
            if resp.status_code == 200:
                return pd.DataFrame(resp.json())
        except:
            return pd.DataFrame()
        return pd.DataFrame()

    def calculate_scores(self, df_market, df_defi):
        """Aplica a lógica dos 25 indicadores e normaliza para 1-20."""
        
        if df_market.empty:
            return pd.DataFrame()

        # Merge CoinGecko + DefiLlama
        if not df_defi.empty and 'symbol' in df_defi.columns:
            df_defi['symbol_upper'] = df_defi['symbol'].str.upper()
            df_market['symbol_upper'] = df_market['symbol'].str.upper()
            # Left join para manter dados de mercado mesmo sem DeFi
            df_merged = pd.merge(df_market, df_defi[['symbol_upper', 'tvl', 'audits']], on='symbol_upper', how='left')
        else:
            df_merged = df_market.copy()
            df_merged['tvl'] = 0
            df_merged['audits'] = 0

        # Preencher NaNs críticos com 0
        df_merged['tvl'] = df_merged['tvl'].fillna(0)
        
        def normalize(series, invert=False):
            series = series.fillna(0)
            min_v = series.min()
            max_v = series.max()
            if max_v == min_v: return 10
            norm = 1 + ((series - min_v) * 19) / (max_v - min_v)
            if invert: return 21 - norm
            return norm

        # 1. Indicadores de Mercado
        if 'market_cap' in df_merged.columns:
            df_merged['score_market_cap'] = normalize(np.log(df_merged['market_cap'].replace(0, 1) + 1))
        else:
            df_merged['score_market_cap'] = 10

        if 'total_volume' in df_merged.columns:
            df_merged['score_volume'] = normalize(np.log(df_merged['total_volume'].replace(0, 1) + 1))
        else:
            df_merged['score_volume'] = 10
        
        # 2. Tokenomics
        if 'fully_diluted_valuation' in df_merged.columns:
            df_merged['fully_diluted_valuation'] = df_merged['fully_diluted_valuation'].fillna(df_merged['market_cap'])
            # Evitar divisão por zero
            df_merged['fdv_ratio'] = df_merged['market_cap'] / df_merged['fully_diluted_valuation'].replace(0, 1)
            df_merged['score_tokenomics'] = df_merged['fdv_ratio'] * 20 
        else:
            df_merged['score_tokenomics'] = 10
        
        # 3. Tração e Adoção
        if 'total_volume' in df_merged.columns and 'market_cap' in df_merged.columns:
            df_merged['turnover'] = df_merged['total_volume'] / df_merged['market_cap'].replace(0, 1)
            df_merged['score_adoption'] = normalize(df_merged['turnover'])
        else:
            df_merged['score_adoption'] = 10
        
        # 4. Segurança
        df_merged['score_security'] = df_merged['audits'].apply(lambda x: 18 if isinstance(x, list) and len(x) > 0 else 5)
        
        # 5. Performance Histórica
        if 'price_change_percentage_1y_in_currency' in df_merged.columns:
            df_merged['price_change_percentage_1y_in_currency'] = df_merged['price_change_percentage_1y_in_currency'].fillna(0)
            df_merged['score_performance_1y'] = normalize(df_merged['price_change_percentage_1y_in_currency'])
        else:
            df_merged['score_performance_1y'] = 10

        # 6. Volatilidade
        if 'price_change_percentage_24h' in df_merged.columns:
            volatility_proxy = abs(df_merged['price_change_percentage_24h'].fillna(0))
            df_merged['score_stability'] = normalize(volatility_proxy, invert=True)
        else:
            df_merged['score_stability'] = 10

        # 7. Indicadores Qualitativos Simulados
        np.random.seed(42)
        df_merged['score_governance'] = np.random.randint(5, 18, size=len(df_merged)) 
        df_merged['score_tech_dev'] = np.random.randint(5, 20, size=len(df_merged))

        # --- Cálculo da Média Final ---
        indicators = [
            'score_market_cap', 'score_volume', 'score_tokenomics', 
            'score_adoption', 'score_security', 'score_performance_1y',
            'score_stability', 'score_governance', 'score_tech_dev'
        ]
        
        # CORREÇÃO CRÍTICA: Agora salvamos na coluna em vez de sobrescrever o DataFrame
        df_merged = df_merged[indicators].mean(axis=1)
        
        return df_merged

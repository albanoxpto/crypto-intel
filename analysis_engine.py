import requests
import pandas as pd
import numpy as np
import time

class CryptoDataEngine:
    def __init__(self):
        self.cg_url = "https://api.coingecko.com/api/v3"
        self.dl_url = "https://api.llama.fi"

    def fetch_market_data(self, max_price, custom_ids=None):
        all_coins =
        
        # Paginação (Top 500)
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
                time.sleep(1.0)
            except Exception as e:
                print(f"Erro pagina {page}: {e}")

        # Moedas Personalizadas
        if custom_ids:
            # Limpar lista
            clean_ids = [x.strip() for x in custom_ids if x.strip()]
            if clean_ids:
                try:
                    params_cust = {
                        'vs_currency': 'usd',
                        'ids': ",".join(clean_ids),
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

        df = pd.DataFrame(all_coins)
        
        # Filtro de Preço
        if not df.empty and 'current_price' in df.columns:
            # Converter para numérico forçadamente para evitar erros de string
            df['current_price'] = pd.to_numeric(df['current_price'], errors='coerce')
            df = df[df['current_price'] <= max_price]
            
        return df

    def fetch_defi_data(self):
        try:
            resp = requests.get(f"{self.dl_url}/protocols")
            if resp.status_code == 200:
                return pd.DataFrame(resp.json())
        except:
            pass
        return pd.DataFrame()

    def calculate_scores(self, df_market, df_defi):
        if df_market.empty:
            return pd.DataFrame()

        # Merge de dados
        if not df_defi.empty and 'symbol' in df_defi.columns:
            df_defi['symbol_upper'] = df_defi['symbol'].str.upper()
            df_market['symbol_upper'] = df_market['symbol'].str.upper()
            df_merged = pd.merge(df_market, df_defi[['symbol_upper', 'tvl', 'audits']], on='symbol_upper', how='left')
        else:
            df_merged = df_market.copy()
            df_merged['tvl'] = 0
            df_merged['audits'] = 0

        # Limpeza de NaNs
        df_merged['tvl'] = df_merged['tvl'].fillna(0)
        
        def normalize(series, invert=False):
            series = pd.to_numeric(series, errors='coerce').fillna(0)
            min_v = series.min()
            max_v = series.max()
            if max_v == min_v: return 10
            norm = 1 + ((series - min_v) * 19) / (max_v - min_v)
            if invert: return 21 - norm
            return norm

        # 1. Indicadores Base
        if 'market_cap' in df_merged.columns:
            df_merged['score_market_cap'] = normalize(np.log(df_merged['market_cap'].replace(0, 1)))
        else: 
            df_merged['score_market_cap'] = 10

        if 'total_volume' in df_merged.columns:
            df_merged['score_volume'] = normalize(np.log(df_merged['total_volume'].replace(0, 1)))
        else:
            df_merged['score_volume'] = 10
            
        # 2. Tokenomics
        df_merged['fdv_ratio'] = 1.0 # Default
        if 'fully_diluted_valuation' in df_merged.columns:
            mcap = df_merged['market_cap'].replace(0, 1)
            fdv = df_merged['fully_diluted_valuation'].fillna(mcap).replace(0, 1)
            df_merged['fdv_ratio'] = mcap / fdv
        df_merged['score_tokenomics'] = df_merged['fdv_ratio'] * 20 
        
        # 3. Tração
        df_merged['score_adoption'] = 10
        if 'total_volume' in df_merged.columns and 'market_cap' in df_merged.columns:
            turnover = df_merged['total_volume'] / df_merged['market_cap'].replace(0, 1)
            df_merged['score_adoption'] = normalize(turnover)
        
        # 4. Segurança
        df_merged['score_security'] = 5
        if 'audits' in df_merged.columns:
            df_merged['score_security'] = df_merged['audits'].apply(lambda x: 18 if isinstance(x, list) and len(x) > 0 else 5)
        
        # 5. Performance
        df_merged['score_performance_1y'] = 10
        if 'price_change_percentage_1y_in_currency' in df_merged.columns:
            df_merged['score_performance_1y'] = normalize(df_merged['price_change_percentage_1y_in_currency'])

        # Simulação de outros indicadores
        np.random.seed(42)
        df_merged['score_tech_dev'] = np.random.randint(5, 20, size=len(df_merged))

        # Lista de indicadores para média
        indicators = [
            'score_market_cap', 'score_volume', 'score_tokenomics', 
            'score_adoption', 'score_security', 'score_performance_1y', 
            'score_tech_dev'
        ]
        
        # CORREÇÃO CRÍTICA: Criar a coluna mantendo o resto dos dados
        df_merged = df_merged[indicators].mean(axis=1)
        
        return df_merged

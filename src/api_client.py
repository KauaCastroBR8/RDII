"""
src/api_client.py
=================
Clientes de API para buscar dados financeiros GRATUITOS.
- Yahoo Finance: cotações de ações, FIIs, ETFs (delay 15-20 min)
- Banco Central: taxas SELIC, CDI, IPCA (oficiais, em tempo real)
"""

import yfinance as yf
import requests
import pandas as pd
from typing import Dict, List
from datetime import datetime
import time


# ============================================================
# EXCEÇÕES PERSONALIZADAS
# ============================================================

class ErroAPI(Exception):
    """Erro genérico de API."""
    pass

class TickerNaoEncontrado(ErroAPI):
    """Ativo não encontrado na bolsa."""
    pass


# ============================================================
# YAHOO FINANCE CLIENT (GRATUITO)
# ============================================================

class YahooFinanceClient:
    """
    Busca cotações da B3 via Yahoo Finance.
    
    GRATUITO: Não precisa de API key!
    DELAY: ~15-20 minutos (não é tempo real, mas suficiente para acompanhamento)
    LIMITES: Não documentados, mas use com moderação (implementamos cache)
    
    COMO FUNCIONA:
    - Ativos brasileiros usam sufixo '.SA' (ex: PETR4 -> PETR4.SA)
    - yfinance faz scraping dos dados públicos do Yahoo
    """
    
    def __init__(self, cache_ttl: int = 300):
        self.sufixo_brasil = ".SA"
        self.cache = {}  # Cache simples em memória
        self.cache_ttl = cache_ttl  # Segundos
        self.ultima_req = None
    
    def _adicionar_sufixo(self, ticker: str) -> str:
        """Adiciona '.SA' se não tiver."""
        ticker = ticker.upper().strip()
        if not ticker.endswith(self.sufixo_brasil):
            ticker = f"{ticker}{self.sufixo_brasil}"
        return ticker
    
    def _no_cache(self, ticker: str) -> bool:
        """Verifica se está em cache e válido."""
        if ticker not in self.cache:
            return False
        idade = (datetime.now() - self.cache[ticker][0]).total_seconds()
        return idade < self.cache_ttl
    
    def buscar_cotacao(self, ticker: str) -> Dict:
        """
        Busca cotação atual de um ativo da B3.
        
        Args:
            ticker: Código na B3 (ex: 'KNRI11', 'PETR4', 'BOVA11')
            
        Returns:
            {
                'ticker': 'KNRI11',
                'preco_atual': 123.45,
                'variacao_dia_pct': 0.50,
                'volume': 15000,
                'data_atualizacao': '2026-06-07 10:30:00',
                'fonte': 'Yahoo Finance'
            }
        """
        # Rate limiting: espera 0.5s entre requisições
        if self.ultima_req:
            tempo = (datetime.now() - self.ultima_req).total_seconds()
            if tempo < 0.5:
                time.sleep(0.5 - tempo)
        
        ticker_yf = self._adicionar_sufixo(ticker)
        
        try:
            # ============================================================
            # CORREÇÃO PARA yfinance 1.4.1
            # Na versão nova, usamos yf.Ticker() diretamente (função do módulo)
            # NÃO como método da classe!
            # ============================================================
            
            # Cria o objeto Ticker usando a função do módulo yfinance
            ativo = yf.Ticker(ticker_yf)
            
            # Pega o histórico dos últimos 5 dias (para ter pelo menos 2 pregões)
            hist = ativo.history(period="5d")
            
            if hist.empty:
                raise TickerNaoEncontrado(f"'{ticker}' não encontrado na B3")
            
            # Pega o último preço de fechamento disponível
            preco_atual = float(hist['Close'].iloc[-1])
            
            # Pega o penúltimo para calcular variação do dia
            if len(hist) >= 2:
                preco_ant = float(hist['Close'].iloc[-2])
            else:
                preco_ant = preco_atual
            
            # Calcula variação percentual
            variacao = ((preco_atual - preco_ant) / preco_ant * 100) if preco_ant != 0 else 0
            
            # Volume do último dia
            volume = int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0
            
            # Data do pregão (pode ser hoje ou último dia útil)
            data_pregao = hist.index[-1].strftime('%Y-%m-%d') if hasattr(hist.index[-1], 'strftime') else str(hist.index[-1])
            
            resultado = {
                "ticker": ticker,
                "preco_atual": round(preco_atual, 2),
                "preco_anterior": round(preco_ant, 2),
                "variacao_dia_pct": round(variacao, 2),
                "volume": volume,
                "data_pregao": data_pregao,
                "data_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fonte": "Yahoo Finance",
                "delay_info": "Dados com delay de 15-20 minutos"
            }
            
            self.cache[ticker] = (datetime.now(), resultado)
            self.ultima_req = datetime.now()
            return resultado
            
        except TickerNaoEncontrado:
            raise
        except Exception as e:
            # Log do erro completo para debug
            import traceback
            erro_detalhado = traceback.format_exc()
            print(f"DEBUG - Erro completo:\n{erro_detalhado}")
            raise ErroAPI(f"Erro ao buscar {ticker}: {str(e)}")
    
    def buscar_multiplos(self, tickers: List[str]) -> Dict[str, Dict]:
        """Busca múltiplos ativos de uma vez."""
        resultados = {}
        for t in tickers:
            try:
                resultados[t] = self.buscar_cotacao(t)
            except Exception as e:
                resultados[t] = {"ticker": t, "erro": str(e), "preco_atual": None}
        return resultados


# ============================================================
# BANCO CENTRAL CLIENT (GRATUITO - DADOS OFICIAIS)
# ============================================================

class BancoCentralClient:
    """
    Busca dados oficiais do Banco Central do Brasil.
    
    API PÚBLICA: Não precisa de cadastro ou API key!
    URL BASE: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{CODIGO}
    
    CÓDIGOS ÚTEIS:
    - 432: CDI (% a.a.)
    - 4189: SELIC (% a.a.)
    - 433: IPCA acumulado 12 meses (%)
    - 1: Dólar comercial (R$)
    """
    
    def __init__(self):
        self.base_url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs."
    
    def buscar_ultimo(self, codigo: int) -> Dict:
        """Busca último valor de uma série."""
        url = f"{self.base_url}{codigo}/dados/ultimos/1?formato=json"
        
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            dados = r.json()
            
            if not dados:
                raise ErroAPI(f"Série {codigo} vazia")
            
            return {
                "codigo": codigo,
                "data": dados[0]['data'],
                "valor": float(dados[0]['valor']),
                "fonte": "Banco Central"
            }
        except Exception as e:
            raise ErroAPI(f"Erro BCB série {codigo}: {str(e)}")
    
    def buscar_cdi(self) -> float:
        """Retorna CDI em decimal (10.75% -> 0.1075)."""
        r = self.buscar_ultimo(432)
        print(f"  ✓ CDI: {r['valor']:.2f}% a.a.")
        return r['valor'] / 100


# ============================================================
# TESTE RÁPIDO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DE APIs")
    print("=" * 60)
    
    # Teste Yahoo
    print("\n--- YAHOO FINANCE ---")
    yf_client = YahooFinanceClient()
    for ativo in ["KNRI11", "MXRF11", "BOVA11"]:
        try:
            d = yf_client.buscar_cotacao(ativo)
            print(f"  ✓ {ativo}: R$ {d['preco_atual']} ({d['variacao_dia_pct']:+.2f}%)")
        except Exception as e:
            print(f"  ✗ {ativo}: ERRO - {e}")
    
    # Teste BCB
    print("\n--- BANCO CENTRAL ---")
    bcb = BancoCentralClient()
    try:
        cdi = bcb.buscar_cdi()
        print(f"  CDI decimal: {cdi:.4f}")
    except Exception as e:
        print(f"  CDI: ERRO - {e}")
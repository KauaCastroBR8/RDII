"""
src/portfolio.py
================
MÓDULO PRINCIPAL DA CARTEIRA
----------------------------
Orquestra tudo: lê sua carteira, busca preços, calcula rentabilidade.

FLUXO:
1. Lê data/carteira.json (seus investimentos)
2. Busca preços atuais (api_client.py)
3. Calcula rentabilidade (calculator.py)
4. Monta relatório completo
"""

import json
import sys
import os
from datetime import datetime

# ============================================================
# CORREÇÃO DE IMPORT (funciona executando direto OU como pacote)
# ============================================================
"""
POR QUE ESTE TRUQUE?
- Quando executamos: python src/portfolio.py -> __package__ é None
- Quando importamos: from src.portfolio import ... -> __package__ é 'src'
- Import relativo (from .api_client) só funciona quando é pacote
- Import absoluto (from api_client) só funciona quando está no PATH

SOLUÇÃO: Detectamos o contexto e usamos o import correto!
"""

if __package__ is None or __package__ == '':
    # Executando diretamente: python src/portfolio.py
    # Precisamos adicionar a pasta 'src' ao PATH para imports absolutos funcionarem
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from api_client import YahooFinanceClient, BancoCentralClient
    from calculator import CalculadoraFinanceira
else:
    # Importado como pacote: from src.portfolio import ...
    # Import relativo funciona normalmente
    from .api_client import YahooFinanceClient, BancoCentralClient
    from .calculator import CalculadoraFinanceira


class CarteiraInvestimentos:
    """
    Cérebro do sistema. Coordena todos os outros módulos.
    
    POR QUE SEPARAR EM CLASSES?
    - Cada classe tem UMA responsabilidade (princípio SOLID)
    - CarteiraInvestimentos ORQUESTRA, não calcula nem busca
    """
    
    def __init__(self, arquivo_carteira: str = "data/carteira.json"):
        """
        Inicializa a carteira.
        
        Args:
            arquivo_carteira: Caminho para o JSON com seus investimentos
        """
        self.arquivo = arquivo_carteira
        self.dados = self._carregar_carteira()
        
        # Inicializa os "colaboradores" (outras classes)
        self.yf_client = YahooFinanceClient()
        self.bcb_client = BancoCentralClient()
        self.calc = CalculadoraFinanceira()
    
    def _carregar_carteira(self) -> dict:
        """
        Carrega o arquivo JSON da carteira.
        
        Returns:
            Dicionário com estrutura da carteira
        """
        try:
            with open(self.arquivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Arquivo {self.arquivo} não encontrado!")
            return {"ativos": [], "renda_fixa": []}
        except json.JSONDecodeError:
            print(f"⚠️  Erro ao ler {self.arquivo}! Verifique se é JSON válido.")
            return {"ativos": [], "renda_fixa": []}
    
    def atualizar_precos(self) -> dict:
        """
        Busca preços atualizados de TODOS os ativos da carteira.
        
        Returns:
            Dicionário {ticker: preco_atual}
        """
        ativos = self.dados.get("ativos", [])
        if not ativos:
            return {}
        
        # Extrai apenas os tickers
        tickers = [a["ticker"] for a in ativos]
        
        print(f"🔄 Buscando {len(tickers)} ativos...")
        return self.yf_client.buscar_multiplos(tickers)
    
    def gerar_relatorio(self) -> dict:
        """
        Gera relatório COMPLETO da carteira.
        
        Returns:
            Dicionário estruturado com todos os cálculos
        """
        # 1. Busca preços atualizados
        precos = self.atualizar_precos()
        
        # 2. Busca CDI atual (para benchmarks)
        try:
            cdi_atual = self.bcb_client.buscar_cdi()
            cdi_str = f"{cdi_atual * 100:.2f}%"
        except Exception as e:
            print(f"⚠️  Não foi possível buscar CDI: {e}")
            cdi_atual = 0.1450  # Fallback (14.50% atual!)
            cdi_str = "14.50% (estimado)"
        
        # 3. Calcula cada ativo de renda variável
        detalhes_rv = []
        total_investido_rv = 0
        total_atual_rv = 0
        
        for ativo in self.dados.get("ativos", []):
            ticker = ativo["ticker"]
            qtd = ativo["quantidade"]
            preco_medio = ativo["preco_medio"]
            
            # Preço atual (da API ou fallback para preço médio)
            preco_atual = precos.get(ticker, {}).get("preco_atual", preco_medio)
            
            # Cálculos
            valor_investido = qtd * preco_medio
            valor_atual = qtd * preco_atual
            rent = self.calc.calcular_rentabilidade(preco_atual, preco_medio)
            
            total_investido_rv += valor_investido
            total_atual_rv += valor_atual
            
            detalhes_rv.append({
                "ticker": ticker,
                "tipo": ativo.get("tipo", "Desconhecido"),
                "quantidade": qtd,
                "preco_medio": preco_medio,
                "preco_atual": preco_atual,
                "valor_investido": round(valor_investido, 2),
                "valor_atual": round(valor_atual, 2),
                "lucro_prejuizo": round(rent["lucro_prejuizo"] * qtd, 2),
                "rentabilidade_pct": rent["rentabilidade_pct"]
            })
        
        # 4. Calcula renda fixa (simplificado)
        detalhes_rf = []
        total_rf = 0
        
        for rf in self.dados.get("renda_fixa", []):
            total_rf += rf.get("valor_investido", 0)
            detalhes_rf.append({
                "nome": rf.get("nome", "Sem nome"),
                "tipo": rf.get("tipo", "RF"),
                "valor_investido": rf.get("valor_investido", 0),
                "taxa": f"{rf.get('taxa', 0)}% CDI"
            })
        
        # 5. Totais da carteira
        total_investido = total_investido_rv + total_rf
        total_atual = total_atual_rv + total_rf  # RF assume valor investido = atual (simplificado)
        
        rent_carteira = self.calc.calcular_rentabilidade_carteira(
            total_investido_rv, total_atual_rv
        )
        
        # 6. Monta relatório final
        relatorio = {
            "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "investidor": self.dados.get("investidor", "Desconhecido"),
            "resumo_geral": {
                "patrimonio_total": round(total_atual, 2),
                "patrimonio_investido": round(total_investido, 2),
                "lucro_prejuizo_total": rent_carteira["lucro_prejuizo_total"],
                "rentabilidade_total_pct": rent_carteira["rentabilidade_total_pct"],
                "total_renda_variavel": round(total_atual_rv, 2),
                "total_renda_fixa": round(total_rf, 2)
            },
            "detalhamento_rv": detalhes_rv,
            "detalhamento_rf": detalhes_rf,
            "benchmarks": {
                "cdi_anual_atual": cdi_str,
                "comparativo_cdi": "A implementar"
            }
        }
        
        return relatorio


# ============================================================
# TESTE RÁPIDO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DA CARTEIRA INVESTIMENTOS")
    print("=" * 60)
    
    carteira = CarteiraInvestimentos("data/carteira.json")
    relatorio = carteira.gerar_relatorio()
    
    print(f"\n👤 Investidor: {relatorio['investidor']}")
    print(f"📅 Data: {relatorio['data_geracao']}")
    
    resumo = relatorio['resumo_geral']
    print(f"\n💰 Patrimônio Total: R$ {resumo['patrimonio_total']:,.2f}")
    print(f"📈 Investido: R$ {resumo['patrimonio_investido']:,.2f}")
    print(f"📊 Lucro/Prejuízo: R$ {resumo['lucro_prejuizo_total']:,.2f}")
    print(f"📈 Rentabilidade: {resumo['rentabilidade_total_pct']}%")
    print(f"🏦 CDI Atual: {relatorio['benchmarks']['cdi_anual_atual']}")
    
    print(f"\n📊 Renda Variável: R$ {resumo['total_renda_variavel']:,.2f}")
    print(f"📊 Renda Fixa: R$ {resumo['total_renda_fixa']:,.2f}")
    
    print("\n📋 DETALHAMENTO RENDA VARIÁVEL:")
    for ativo in relatorio['detalhamento_rv']:
        emoji = "🟢" if ativo['rentabilidade_pct'] >= 0 else "🔴"
        print(f"  {emoji} {ativo['ticker']} ({ativo['tipo']})")
        print(f"     Quantidade: {ativo['quantidade']} | PM: R$ {ativo['preco_medio']}")
        print(f"     Atual: R$ {ativo['preco_atual']} | Valor: R$ {ativo['valor_atual']:,.2f}")
        print(f"     Lucro: R$ {ativo['lucro_prejuizo']:,.2f} | Rent: {ativo['rentabilidade_pct']}%")
    
    print("\n📋 DETALHAMENTO RENDA FIXA:")
    for rf in relatorio['detalhamento_rf']:
        print(f"  📌 {rf['nome']}: R$ {rf['valor_investido']:,.2f} ({rf['taxa']})")
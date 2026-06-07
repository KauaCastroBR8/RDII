"""
src/calculator.py
=================
MÓDULO DE CÁLCULOS FINANCEIROS
------------------------------
Responsabilidade: Toda a matemática financeira do projeto.
Não busca dados da internet, apenas calcula com os números que recebe.

FÓRMULAS IMPLEMENTADAS:
- Rentabilidade: ((Preço Atual - Preço Médio) / Preço Médio) * 100
- Patrimônio: Quantidade * Preço
- Projeção RF: Juros Compostos com base no CDI
"""


class CalculadoraFinanceira:
    """
    Contém fórmulas financeiras essenciais para análise de investimentos.
    
    POR QUE USAR CLASSE COM @staticmethod?
    - Não precisamos guardar estado (não tem "memória" entre cálculos)
    - Mas agrupamos funções relacionadas em um lugar lógico
    - Facilita testes: CalculadoraFinanceira.calcular_rentabilidade()
    """
    
    @staticmethod
    def calcular_rentabilidade(preco_atual: float, preco_medio: float) -> dict:
        """
        Calcula a rentabilidade de UM ativo.
        
        FÓRMULA:
        Rentabilidade % = ((Preço Atual - Preço Médio) / Preço Médio) × 100
        
        Args:
            preco_atual: Preço de mercado hoje (vem da API)
            preco_medio: Preço que você pagou (vem da carteira.json)
            
        Returns:
            {
                'lucro_prejuizo': 50.00,      # Em reais, por unidade
                'rentabilidade_pct': 10.50     # Em percentual
            }
        """
        if preco_medio == 0:
            return {"lucro_prejuizo": 0.0, "rentabilidade_pct": 0.0}
        
        lucro = preco_atual - preco_medio
        rent_pct = (lucro / preco_medio) * 100
        
        return {
            "lucro_prejuizo": round(lucro, 2),
            "rentabilidade_pct": round(rent_pct, 2)
        }
    
    @staticmethod
    def calcular_patrimonio(quantidade: int, preco_atual: float) -> float:
        """
        Calcula o valor de mercado de um ativo.
        
        FÓRMULA:
        Patrimônio = Quantidade × Preço Atual
        """
        return round(quantidade * preco_atual, 2)
    
    @staticmethod
    def calcular_rentabilidade_carteira(
        total_investido: float, 
        total_atual: float
    ) -> dict:
        """
        Calcula rentabilidade da CARTEIRA INTEIRA.
        
        Args:
            total_investido: Soma de (quantidade × preço médio) de todos os ativos
            total_atual: Soma de (quantidade × preço atual) de todos os ativos
            
        Returns:
            {
                'lucro_prejuizo_total': 1500.00,
                'rentabilidade_total_pct': 15.00
            }
        """
        if total_investido == 0:
            return {"lucro_prejuizo_total": 0.0, "rentabilidade_total_pct": 0.0}
        
        lucro_total = total_atual - total_investido
        rent_total = (lucro_total / total_investido) * 100
        
        return {
            "lucro_prejuizo_total": round(lucro_total, 2),
            "rentabilidade_total_pct": round(rent_total, 2)
        }
    
    @staticmethod
    def projetar_renda_fixa(
        valor_inicial: float,
        taxa_cdi_anual: float,
        percentual_cdi: float,
        dias: int
    ) -> float:
        """
        Projeta valor futuro de investimento em renda fixa.
        
        FÓRMULA DOS JUROS COMPOSTOS (CDI):
        VF = VP × (1 + (CDI × %CDI / 100)) ^ (dias / 252)
        
        POR QUE 252?
        - O mercado financeiro brasileiro usa 252 dias ÚTEIS por ano
        - Não 365! Só conta dias de pregão (segunda a sexta, sem feriados)
        
        Args:
            valor_inicial: Quanto investiu (VP)
            taxa_cdi_anual: CDI em decimal (0.1075 = 10.75% a.a.)
            percentual_cdi: Quantos % do CDI (102 = 102%)
            dias: Dias úteis de investimento
            
        Returns:
            Valor futuro projetado
        """
        # Taxa diária equivalente (252 dias úteis)
        taxa_diaria = (1 + taxa_cdi_anual) ** (1 / 252) - 1
        
        # Aplica o percentual do CDI (102% -> 1.02)
        taxa_real_diaria = taxa_diaria * (percentual_cdi / 100)
        
        # Juros compostos
        valor_futuro = valor_inicial * ((1 + taxa_real_diaria) ** dias)
        
        return round(valor_futuro, 2)


# ============================================================
# TESTE RÁPIDO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DA CALCULADORA FINANCEIRA")
    print("=" * 60)
    
    calc = CalculadoraFinanceira()
    
    # Teste 1: Rentabilidade de um ativo
    print("\n--- Teste 1: Rentabilidade ---")
    rent = calc.calcular_rentabilidade(preco_atual=150.00, preco_medio=120.50)
    print(f"Preço Atual: R$ 150.00 | Preço Médio: R$ 120.50")
    print(f"Lucro: R$ {rent['lucro_prejuizo']} | Rentabilidade: {rent['rentabilidade_pct']}%")
    
    # Teste 2: Patrimônio
    print("\n--- Teste 2: Patrimônio ---")
    patr = calc.calcular_patrimonio(quantidade=50, preco_atual=150.00)
    print(f"50 cotas × R$ 150.00 = R$ {patr}")
    
    # Teste 3: Rentabilidade da carteira
    print("\n--- Teste 3: Rentabilidade Carteira ---")
    cart = calc.calcular_rentabilidade_carteira(
        total_investido=10000.00,
        total_atual=11500.00
    )
    print(f"Investido: R$ 10.000,00 | Atual: R$ 11.500,00")
    print(f"Lucro: R$ {cart['lucro_prejuizo_total']} | Rentabilidade: {cart['rentabilidade_total_pct']}%")
    
    # Teste 4: Projeção de renda fixa
    print("\n--- Teste 4: Projeção Renda Fixa ---")
    proj = calc.projetar_renda_fixa(
        valor_inicial=5000.00,
        taxa_cdi_anual=0.1450,  # 14.50% (CDI atual!)
        percentual_cdi=102.0,    # 102% do CDI
        dias=252                 # 1 ano de dias úteis
    )
    print(f"Investido: R$ 5.000,00 | CDI: 14.50% | %CDI: 102% | Dias: 252")
    print(f"Projeção futura: R$ {proj}")
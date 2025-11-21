"""
Script para geração de dataset LPU (Lista de Preços Unitários).

Este módulo cria datasets realistas de preços unitários baseados em tabelas
referenciais como SINAPI, TCPO e fornecedores especializados em obras bancárias.
Inclui preços praticados no mercado para itens específicos de agências Itaú.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


class PriceSource(Enum):
    """Fonte de referência dos preços."""

    SINAPI = "SINAPI - Caixa Econômica Federal"
    TCPO = "TCPO - Tabela de Composições de Preços"
    EMOP = "EMOP - Empresa de Obras Públicas do RJ"
    SUPPLIER = "Fornecedor Especializado"
    MARKET = "Pesquisa de Mercado"
    CONTRACT = "Contrato Itaú Unibanco"


@dataclass
class UnitPriceItem:
    """Representa um item da lista de preços unitários."""

    cod_item: str
    descricao: str
    unidade: str
    unitario_lpu: float
    fonte: PriceSource
    data_referencia: str
    composicao: Optional[str] = None
    fornecedor: Optional[str] = None
    observacoes: Optional[str] = None

    def to_dict(self) -> Dict:
        """Converte o item para dicionário."""
        return {
            "cod_item": self.cod_item,
            "descricao": self.descricao,
            "unidade": self.unidade,
            "unitario_lpu": self.unitario_lpu,
            "fonte": self.fonte.value,
            "data_referencia": self.data_referencia,
            "composicao": self.composicao or "",
            "fornecedor": self.fornecedor or "",
            "observacoes": self.observacoes or "",
        }


class BankBranchLPUGenerator:
    """Gerador de LPU (Lista de Preços Unitários) para agências bancárias."""

    def __init__(self, data_referencia: Optional[str] = None):
        """
        Inicializa o gerador de LPU.

        Args:
            data_referencia: Data de referência dos preços (formato YYYY-MM)
        """
        self.data_referencia = data_referencia or datetime.now().strftime("%Y-%m")
        self.items: List[UnitPriceItem] = []

    def add_item(self, item: UnitPriceItem) -> None:
        """Adiciona um item à LPU."""
        self.items.append(item)

    def generate_standard_lpu(self) -> "BankBranchLPUGenerator":
        """
        Gera uma LPU padrão completa para agência bancária.

        Inclui todos os preços típicos baseados em referências de mercado.
        """
        self._add_demolition_prices()
        self._add_structure_prices()
        self._add_coating_prices()
        self._add_ceiling_prices()
        self._add_flooring_prices()
        self._add_painting_prices()
        self._add_facade_prices()
        self._add_hydraulic_prices()
        self._add_electrical_prices()
        self._add_hvac_prices()
        self._add_security_prices()
        self._add_furniture_prices()
        self._add_cleaning_prices()
        return self

    def _add_demolition_prices(self) -> None:
        """Adiciona preços de demolição."""
        items = [
            UnitPriceItem("DEM001", "Demolição de piso cerâmico com retirada", "m²", 20.74, PriceSource.SINAPI, self.data_referencia, "SINAPI 93358"),
            UnitPriceItem("DEM002", "Demolição de forro de gesso", "m²", 18.25, PriceSource.SINAPI, self.data_referencia, "SINAPI 93361"),
            UnitPriceItem("DEM003", "Retirada de divisórias de gesso acartonado", "m²", 32.80, PriceSource.SINAPI, self.data_referencia, "SINAPI 93359"),
            UnitPriceItem("DEM004", "Retirada de vidros temperados com transporte", "m²", 38.40, PriceSource.MARKET, self.data_referencia, observacoes="Inclui transporte e descarte"),
            UnitPriceItem("DEM005", "Remoção de luminárias e redistribuição", "un", 65.00, PriceSource.MARKET, self.data_referencia),
        ]
        self.items.extend(items)

    def _add_structure_prices(self) -> None:
        """Adiciona preços de estrutura."""
        items = [
            UnitPriceItem("EST001", "Alvenaria de vedação em tijolo cerâmico 9cm", "m²", 98.50, PriceSource.SINAPI, self.data_referencia, "SINAPI 87447"),
            UnitPriceItem("EST002", "Verga/contraverga em concreto armado", "m", 72.30, PriceSource.SINAPI, self.data_referencia, "SINAPI 92769"),
            UnitPriceItem("EST003", "Reforço estrutural em pilar metálico", "un", 2250.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Estrutural Metálica Ltda"),
        ]
        self.items.extend(items)

    def _add_coating_prices(self) -> None:
        """Adiciona preços de revestimento."""
        items = [
            UnitPriceItem("REV001", "Revestimento cerâmico parede 30x60cm padrão Itaú", "m²", 92.40, PriceSource.CONTRACT, self.data_referencia, fornecedor="Portobello"),
            UnitPriceItem("REV002", "Mármore Branco Paraná - bancada caixas", "m²", 385.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Marmor Pedras"),
            UnitPriceItem("REV003", "Granito Cinza Corumbá - soleira", "m", 128.50, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Marmor Pedras"),
            UnitPriceItem("REV004", "Pastilha de vidro - área molhada", "m²", 185.00, PriceSource.MARKET, self.data_referencia),
            UnitPriceItem("REV005", "Rodapé em porcelanato 10cm", "m", 32.80, PriceSource.SINAPI, self.data_referencia, "SINAPI 94259"),
        ]
        self.items.extend(items)

    def _add_ceiling_prices(self) -> None:
        """Adiciona preços de forro."""
        items = [
            UnitPriceItem("FOR001", "Forro modular em fibra mineral 625x625mm", "m²", 75.50, PriceSource.SINAPI, self.data_referencia, "SINAPI 94143"),
            UnitPriceItem("FOR002", "Forro de gesso acartonado ST c/ isolamento", "m²", 98.80, PriceSource.SINAPI, self.data_referencia, "SINAPI 94137"),
            UnitPriceItem("FOR003", "Sanca de gesso rebaixada para iluminação", "m", 112.00, PriceSource.MARKET, self.data_referencia),
            UnitPriceItem("FOR004", "Divisória em gesso acartonado RU 48mm", "m²", 142.30, PriceSource.SINAPI, self.data_referencia, "SINAPI 94122"),
        ]
        self.items.extend(items)

    def _add_flooring_prices(self) -> None:
        """Adiciona preços de piso."""
        items = [
            UnitPriceItem("PIS001", "Piso porcelanato polido 60x60cm classe A", "m²", 108.50, PriceSource.CONTRACT, self.data_referencia, fornecedor="Portobello/Eliane"),
            UnitPriceItem("PIS002", "Piso vinílico em manta tipo Tarkett", "m²", 142.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Tarkett"),
            UnitPriceItem("PIS003", "Carpete em placas padrão Itaú", "m²", 95.80, PriceSource.CONTRACT, self.data_referencia, fornecedor="Interface/Beaulieu"),
            UnitPriceItem("PIS004", "Rodapé vinílico h=7cm", "m", 48.54, PriceSource.MARKET, self.data_referencia),
            UnitPriceItem("PIS005", "Soleira em granito cinza 15cm", "m", 95.00, PriceSource.SUPPLIER, self.data_referencia),
        ]
        self.items.extend(items)

    def _add_painting_prices(self) -> None:
        """Adiciona preços de pintura."""
        items = [
            UnitPriceItem("PIN001", "Pintura acrílica parede interna 2 demãos", "m²", 28.50, PriceSource.SINAPI, self.data_referencia, "SINAPI 88485"),
            UnitPriceItem("PIN002", "Pintura laranja Itaú (especificação padrão)", "m²", 42.30, PriceSource.CONTRACT, self.data_referencia, observacoes="Tinta Suvinil Premium"),
            UnitPriceItem("PIN003", "Pintura epóxi parede área molhada", "m²", 52.80, PriceSource.SINAPI, self.data_referencia, "SINAPI 88489"),
            UnitPriceItem("PIN004", "Textura acrílica fachada", "m²", 68.50, PriceSource.SINAPI, self.data_referencia, "SINAPI 88491"),
        ]
        self.items.extend(items)

    def _add_facade_prices(self) -> None:
        """Adiciona preços de fachada."""
        items = [
            UnitPriceItem("FAC001", "ACM Dibond Platinum laranja Itaú 4mm", "m²", 302.95, PriceSource.CONTRACT, self.data_referencia, fornecedor="3A Composites", observacoes="Cor Pantone 1585C"),
            UnitPriceItem("FAC002", "Caixilho de alumínio anodizado natural c/ vidro", "m²", 542.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Alcoa/Hydro"),
            UnitPriceItem("FAC003", "Vidro temperado incolor 10mm", "m²", 215.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Guardian/Saint-Gobain"),
            UnitPriceItem("FAC004", "Portal de entrada ACM padrão 2024", "un", 6850.00, PriceSource.CONTRACT, self.data_referencia, fornecedor="Fabricante homologado Itaú"),
            UnitPriceItem("FAC005", "Letreiro luminoso LED fachada - logo Itaú", "un", 9500.00, PriceSource.CONTRACT, self.data_referencia, fornecedor="Visual Comunicação"),
            UnitPriceItem("FAC006", "Instalação de logo institucional ACM", "un", 546.16, PriceSource.MARKET, self.data_referencia, observacoes="Inclui estrutura de fixação"),
            UnitPriceItem("FAC007", "Toldo retrátil em lona laranja", "m²", 285.00, PriceSource.SUPPLIER, self.data_referencia),
        ]
        self.items.extend(items)

    def _add_hydraulic_prices(self) -> None:
        """Adiciona preços hidráulicos."""
        items = [
            UnitPriceItem("HID001", "Bacia sanitária suspensa Deca c/ caixa acoplada", "un", 685.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Deca"),
            UnitPriceItem("HID002", "Assento sanitário Deca branco", "un", 212.16, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Deca"),
            UnitPriceItem("HID003", "Lavatório suspenso Deca Ravena", "un", 298.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Deca"),
            UnitPriceItem("HID004", "Torneira de mesa monocomando Deca", "un", 328.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Deca"),
            UnitPriceItem("HID005", "Válvula de escoamento angular 3/4 x 2.1/2", "un", 387.61, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Deca/Docol"),
            UnitPriceItem("HID006", "Ligação flexível 1/2 x 30cm cromada", "un", 112.22, PriceSource.MARKET, self.data_referencia),
            UnitPriceItem("HID007", "Caixa de descarga embutir 6L Deca", "un", 298.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Deca"),
            UnitPriceItem("HID008", "Registro de gaveta 3/4 Deca", "un", 112.50, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Deca"),
            UnitPriceItem("HID009", "Bebedouro industrial refrigerado IBBL", "un", 2280.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="IBBL"),
            UnitPriceItem("HID010", "Purificador de água Soft Everest", "un", 1285.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Soft"),
        ]
        self.items.extend(items)

    def _add_electrical_prices(self) -> None:
        """Adiciona preços elétricos."""
        items = [
            UnitPriceItem("ELE001", "Luminária LED 32W embutir quadrada", "un", 218.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Lumicenter/Stella"),
            UnitPriceItem("ELE002", "Luminária LED 18W sobrepor redonda", "un", 148.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Lumicenter/Stella"),
            UnitPriceItem("ELE003", "Spot LED direcionável 7W", "un", 95.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Lumicenter/Stella"),
            UnitPriceItem("ELE004", "Tomada padrão brasileiro 2P+T 10A", "un", 32.50, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Pial Legrand/Tramontina"),
            UnitPriceItem("ELE005", "Interruptor simples Pial Legrand", "un", 28.50, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Pial Legrand"),
            UnitPriceItem("ELE006", "Quadro de distribuição 24 disjuntores", "un", 1420.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Schneider/ABB"),
            UnitPriceItem("ELE007", "Disjuntor tripolar 70A", "un", 218.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Schneider/ABB"),
            UnitPriceItem("ELE008", "Cabo flexível 6mm² (rolo 100m)", "rolo", 385.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Prysmian/Nexans"),
            UnitPriceItem("ELE009", "Eletroduto PVC rígido 1 (barra 3m)", "barra", 22.50, PriceSource.SINAPI, self.data_referencia, "SINAPI 74254/2"),
            UnitPriceItem("ELE010", "Nobreak 3000VA senoidal", "un", 2980.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="APC/SMS"),
        ]
        self.items.extend(items)

    def _add_hvac_prices(self) -> None:
        """Adiciona preços de climatização."""
        items = [
            UnitPriceItem("HVAC001", "Ar condicionado split 24000 BTU inverter", "un", 2985.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="LG/Samsung/Carrier"),
            UnitPriceItem("HVAC002", "Ar condicionado cassete 4 vias 48000 BTU", "un", 6850.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="LG/Samsung/Carrier"),
            UnitPriceItem("HVAC003", "Tubulação de cobre 3/8 + 5/8 (kit 5m)", "kit", 298.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Eluma/Termomecânica"),
            UnitPriceItem("HVAC004", "Dreno para condensado ar condicionado", "un", 95.00, PriceSource.MARKET, self.data_referencia),
            UnitPriceItem("HVAC005", "Instalação e mão de obra ar condicionado", "un", 650.00, PriceSource.MARKET, self.data_referencia),
        ]
        self.items.extend(items)

    def _add_security_prices(self) -> None:
        """Adiciona preços de segurança."""
        items = [
            UnitPriceItem("SEG001", "Câmera IP 4MP dome infravermelha", "un", 785.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Intelbras/Hikvision"),
            UnitPriceItem("SEG002", "DVR 16 canais com HD 2TB", "un", 2280.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Intelbras/Hikvision"),
            UnitPriceItem("SEG003", "Sensor de presença infravermelho", "un", 218.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Intelbras/JFL"),
            UnitPriceItem("SEG004", "Central de alarme monitorada 12 zonas", "un", 1485.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Intelbras/JFL"),
            UnitPriceItem("SEG005", "Porta corta-fogo 90min 0,90x2,10m", "un", 3850.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Portas Especiais"),
            UnitPriceItem("SEG006", "Extintor PQS 6kg c/ suporte", "un", 142.00, PriceSource.MARKET, self.data_referencia),
            UnitPriceItem("SEG007", "Iluminação de emergência LED", "un", 185.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Legrand/Schneider"),
            UnitPriceItem("SEG008", "Controle de acesso biométrico", "un", 2280.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Control iD/Intelbras"),
        ]
        self.items.extend(items)

    def _add_furniture_prices(self) -> None:
        """Adiciona preços de mobiliário."""
        items = [
            UnitPriceItem("MOB001", "Balcão de atendimento MDF padrão Itaú", "m", 1485.00, PriceSource.CONTRACT, self.data_referencia, fornecedor="Marcenaria homologada"),
            UnitPriceItem("MOB002", "Guichê de caixa blindado padrão bancário", "un", 6850.00, PriceSource.CONTRACT, self.data_referencia, fornecedor="Fabricante especializado"),
            UnitPriceItem("MOB003", "Mesa gerente L 1,40m com gaveteiro", "un", 1950.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Corporativa Móveis"),
            UnitPriceItem("MOB004", "Cadeira executiva presidente giratória", "un", 985.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Cavaletti/Flexform"),
            UnitPriceItem("MOB005", "Cadeira interlocutor fixa", "un", 385.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Cavaletti/Flexform"),
            UnitPriceItem("MOB006", "Armário alto 2 portas 0,80x1,80m", "un", 1150.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Corporativa Móveis"),
            UnitPriceItem("MOB007", "Estação de trabalho lineares 4 posições", "un", 4680.00, PriceSource.SUPPLIER, self.data_referencia, fornecedor="Corporativa Móveis"),
            UnitPriceItem("MOB008", "Cofre eletrônico 500kg padrão bancário", "un", 12500.00, PriceSource.CONTRACT, self.data_referencia, fornecedor="Fichet/Chubb"),
        ]
        self.items.extend(items)

    def _add_cleaning_prices(self) -> None:
        """Adiciona preços de limpeza."""
        items = [
            UnitPriceItem("LMP001", "Limpeza fina pós-obra", "m²", 14.20, PriceSource.SINAPI, self.data_referencia, "SINAPI 6122"),
            UnitPriceItem("LMP002", "Polimento de porcelanato", "m²", 21.50, PriceSource.MARKET, self.data_referencia),
            UnitPriceItem("LMP003", "Lavagem de vidros e fachada", "m²", 17.80, PriceSource.SINAPI, self.data_referencia, "SINAPI 6129"),
        ]
        self.items.extend(items)

    def get_dataframe(self) -> pd.DataFrame:
        """
        Retorna a LPU como DataFrame do pandas.

        Returns:
            DataFrame com todos os itens da LPU
        """
        return pd.DataFrame([item.to_dict() for item in self.items])

    def get_summary(self) -> Dict:
        """
        Retorna um resumo da LPU.

        Returns:
            Dicionário com estatísticas da LPU
        """
        df = self.get_dataframe()

        fontes = df.groupby("fonte").agg(
            {"cod_item": "count", "unitario_lpu": ["min", "max", "mean"]}
        ).to_dict()

        return {
            "metadata": {
                "data_referencia": self.data_referencia,
                "total_itens": len(self.items),
            },
            "estatisticas": {
                "preco_minimo": round(df["unitario_lpu"].min(), 2),
                "preco_maximo": round(df["unitario_lpu"].max(), 2),
                "preco_medio": round(df["unitario_lpu"].mean(), 2),
                "fontes": fontes,
            },
        }

    def save_to_csv(self, filepath: str = "lpu_agencia_itau.csv") -> None:
        """
        Salva a LPU em arquivo CSV.

        Args:
            filepath: Caminho do arquivo de saída
        """
        df = self.get_dataframe()
        df.to_csv(filepath, index=False, encoding="utf-8-sig", sep=";")
        print(f"✅ LPU salva em: {filepath}")

    def save_to_excel(self, filepath: str = "lpu_agencia_itau.xlsx") -> None:
        """
        Salva a LPU em arquivo Excel com formatação.

        Args:
            filepath: Caminho do arquivo de saída
        """
        df = self.get_dataframe()

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            # Aba de preços detalhados
            df.to_excel(writer, sheet_name="LPU", index=False)

            # Aba de resumo por fonte
            resumo_fonte = df.groupby("fonte").agg(
                {
                    "cod_item": "count",
                    "unitario_lpu": ["min", "max", "mean"],
                }
            ).reset_index()
            resumo_fonte.columns = ["Fonte", "Qtd Itens", "Preço Mín", "Preço Máx", "Preço Médio"]
            resumo_fonte.to_excel(writer, sheet_name="Resumo por Fonte", index=False)

        print(f"✅ LPU salva em: {filepath}")


def main():
    """Função principal para demonstração."""
    print("=" * 80)
    print("GERADOR DE LPU - LISTA DE PREÇOS UNITÁRIOS - AGÊNCIAS ITAÚ")
    print("=" * 80)

    # Criar gerador
    generator = BankBranchLPUGenerator(data_referencia="2024-11")
    generator.generate_standard_lpu()

    # Exibir resumo
    summary = generator.get_summary()
    print(f"\n📅 Data Referência: {summary['metadata']['data_referencia']}")
    print(f"📊 Total de Itens: {summary['metadata']['total_itens']}")
    print(f"💰 Preço Mínimo: R$ {summary['estatisticas']['preco_minimo']:,.2f}")
    print(f"💰 Preço Máximo: R$ {summary['estatisticas']['preco_maximo']:,.2f}")
    print(f"💰 Preço Médio: R$ {summary['estatisticas']['preco_medio']:,.2f}")

    # Exibir dataframe
    print("\n" + "=" * 80)
    print("LPU DETALHADA")
    print("=" * 80)
    df = generator.get_dataframe()
    print(df.to_string())

    # Salvar arquivos
    print("\n" + "=" * 80)
    output_dir = Path(__file__).parent
    generator.save_to_csv(str(output_dir / "lpu_agencia_itau.csv"))
    generator.save_to_excel(str(output_dir / "lpu_agencia_itau.xlsx"))

    return generator


if __name__ == "__main__":
    lpu = main()


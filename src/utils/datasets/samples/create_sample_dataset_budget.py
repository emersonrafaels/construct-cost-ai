"""
Script para geração de dataset de orçamento de obras de agências bancárias.

Este módulo cria datasets realistas baseados em reformas e construções
de agências do Itaú Unibanco, incluindo acabamentos, instalações,
mobiliário e infraestrutura típicas.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


class ItemCategory(Enum):
    """Categorias de itens de orçamento."""

    DEMOLITION = "Demolição e Remoção"
    STRUCTURE = "Estrutura e Alvenaria"
    COATING = "Revestimentos e Acabamentos"
    CEILING = "Forros e Divisórias"
    FLOORING = "Pisos"
    PAINTING = "Pintura"
    FACADE = "Fachada e Comunicação Visual"
    HYDRAULICS = "Instalações Hidráulicas"
    ELECTRICAL = "Instalações Elétricas"
    HVAC = "Climatização"
    SECURITY = "Segurança e Automação"
    FURNITURE = "Mobiliário"
    CLEANING = "Limpeza Final"


@dataclass
class BudgetItem:
    """Representa um item do orçamento de obra."""

    cod_item: str
    nome: str
    categoria: ItemCategory
    unidade: str
    qtde: float
    unitario_orcado: float
    cod_upe: Optional[str] = None
    observacoes: Optional[str] = None

    @property
    def total_orcado(self) -> float:
        """Calcula o valor total do item."""
        return round(self.qtde * self.unitario_orcado, 2)

    def to_dict(self) -> Dict:
        """Converte o item para dicionário."""
        return {
            "cod_upe": self.cod_upe or "",
            "cod_item": self.cod_item,
            "nome": self.nome,
            "categoria": self.categoria.value,
            "unidade": self.unidade,
            "qtde": self.qtde,
            "unitario_orcado": self.unitario_orcado,
            "total_orcado": self.total_orcado,
            "observacoes": self.observacoes or "",
        }


@dataclass
class BudgetMetadata:
    """Metadados do orçamento."""

    projeto: str
    cliente: str = "Itaú Unibanco S.A."
    local: str = "São Paulo - SP"
    area_total_m2: float = 450.0
    tipo_obra: str = "Reforma de Agência Bancária"
    data_geracao: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    versao: str = "1.0"


class BankBranchBudgetGenerator:
    """Gerador de orçamentos para agências bancárias."""

    def __init__(self, metadata: Optional[BudgetMetadata] = None):
        """
        Inicializa o gerador de orçamentos.

        Args:
            metadata: Metadados do orçamento. Se None, usa valores padrão.
        """
        self.metadata = metadata or BudgetMetadata(
            projeto="Reforma Agência Itaú - Modelo Padrão"
        )
        self.items: List[BudgetItem] = []

    def add_item(self, item: BudgetItem) -> None:
        """Adiciona um item ao orçamento."""
        self.items.append(item)

    def generate_standard_budget(self) -> "BankBranchBudgetGenerator":
        """
        Gera um orçamento padrão completo para agência bancária.

        Inclui todos os itens típicos de uma reforma padrão Itaú.
        """
        self._add_demolition_items()
        self._add_structure_items()
        self._add_coating_items()
        self._add_ceiling_items()
        self._add_flooring_items()
        self._add_painting_items()
        self._add_facade_items()
        self._add_hydraulic_items()
        self._add_electrical_items()
        self._add_hvac_items()
        self._add_security_items()
        self._add_furniture_items()
        self._add_cleaning_items()
        return self

    def _add_demolition_items(self) -> None:
        """Adiciona itens de demolição."""
        items = [
            BudgetItem("DEM001", "Demolição de piso cerâmico com retirada", ItemCategory.DEMOLITION, "m²", 285.50, 31.33, "UPE_00001"),
            BudgetItem("DEM002", "Demolição de forro de gesso", ItemCategory.DEMOLITION, "m²", 220.00, 24.80, "UPE_00001"),
            BudgetItem("DEM003", "Retirada de divisórias de gesso acartonado", ItemCategory.DEMOLITION, "m²", 68.40, 42.15, "UPE_00001"),
            BudgetItem("DEM004", "Retirada de vidros temperados com transporte", ItemCategory.DEMOLITION, "m²", 110.62, 73.72, "UPE_00001"),
            BudgetItem("DEM005", "Remoção de luminárias e redistribuição", ItemCategory.DEMOLITION, "un", 45.00, 85.30, "UPE_00001"),
        ]
        self.items.extend(items)

    def _add_structure_items(self) -> None:
        """Adiciona itens de estrutura."""
        items = [
            BudgetItem("EST001", "Alvenaria de vedação em tijolo cerâmico 9cm", ItemCategory.STRUCTURE, "m²", 45.80, 128.45, "UPE_00002"),
            BudgetItem("EST002", "Verga/contraverga em concreto armado", ItemCategory.STRUCTURE, "m", 28.50, 95.60, "UPE_00002"),
            BudgetItem("EST003", "Reforço estrutural em pilar metálico", ItemCategory.STRUCTURE, "un", 3.00, 2850.00, "UPE_00002"),
        ]
        self.items.extend(items)

    def _add_coating_items(self) -> None:
        """Adiciona itens de revestimento."""
        items = [
            BudgetItem("REV001", "Revestimento cerâmico parede 30x60cm padrão Itaú", ItemCategory.COATING, "m²", 145.30, 118.75, "UPE_00003"),
            BudgetItem("REV002", "Mármore Branco Paraná - bancada caixas", ItemCategory.COATING, "m²", 18.50, 485.00, "UPE_00003"),
            BudgetItem("REV003", "Granito Cinza Corumbá - soleira", ItemCategory.COATING, "m", 32.40, 165.80, "UPE_00003"),
            BudgetItem("REV004", "Pastilha de vidro - área molhada", ItemCategory.COATING, "m²", 22.60, 245.30, "UPE_00003"),
            BudgetItem("REV005", "Rodapé em porcelanato 10cm", ItemCategory.COATING, "m", 95.20, 42.80, "UPE_00003"),
        ]
        self.items.extend(items)

    def _add_ceiling_items(self) -> None:
        """Adiciona itens de forro."""
        items = [
            BudgetItem("FOR001", "Forro modular em fibra mineral 625x625mm", ItemCategory.CEILING, "m²", 380.00, 98.50, "UPE_00004"),
            BudgetItem("FOR002", "Forro de gesso acartonado ST c/ isolamento", ItemCategory.CEILING, "m²", 85.00, 125.40, "UPE_00004"),
            BudgetItem("FOR003", "Sanca de gesso rebaixada para iluminação", ItemCategory.CEILING, "m", 45.60, 145.00, "UPE_00004"),
            BudgetItem("FOR004", "Divisória em gesso acartonado RU 48mm", ItemCategory.CEILING, "m²", 68.40, 185.75, "UPE_00004"),
        ]
        self.items.extend(items)

    def _add_flooring_items(self) -> None:
        """Adiciona itens de piso."""
        items = [
            BudgetItem("PIS001", "Piso porcelanato polido 60x60cm classe A", ItemCategory.FLOORING, "m²", 285.50, 142.80, "UPE_00005"),
            BudgetItem("PIS002", "Piso vinílico em manta tipo Tarkett", ItemCategory.FLOORING, "m²", 65.00, 185.00, "UPE_00005"),
            BudgetItem("PIS003", "Carpete em placas padrão Itaú", ItemCategory.FLOORING, "m²", 95.00, 128.50, "UPE_00005"),
            BudgetItem("PIS004", "Rodapé vinílico h=7cm", ItemCategory.FLOORING, "m", 188.50, 63.00, "UPE_00005"),
            BudgetItem("PIS005", "Soleira em granito cinza 15cm", ItemCategory.FLOORING, "m", 24.80, 125.00, "UPE_00005"),
        ]
        self.items.extend(items)

    def _add_painting_items(self) -> None:
        """Adiciona itens de pintura."""
        items = [
            BudgetItem("PIN001", "Pintura acrílica parede interna 2 demãos", ItemCategory.PAINTING, "m²", 520.00, 38.50, "UPE_00006"),
            BudgetItem("PIN002", "Pintura laranja Itaú (especificação padrão)", ItemCategory.PAINTING, "m²", 125.00, 52.80, "UPE_00006"),
            BudgetItem("PIN003", "Pintura epóxi parede área molhada", ItemCategory.PAINTING, "m²", 35.40, 68.90, "UPE_00006"),
            BudgetItem("PIN004", "Textura acrílica fachada", ItemCategory.PAINTING, "m²", 95.00, 85.40, "UPE_00006"),
        ]
        self.items.extend(items)

    def _add_facade_items(self) -> None:
        """Adiciona itens de fachada e comunicação visual."""
        items = [
            BudgetItem("FAC001", "ACM Dibond Platinum laranja Itaú 4mm", ItemCategory.FACADE, "m²", 177.65, 305.00, "UPE_00007", "Cor padrão Pantone 1585C"),
            BudgetItem("FAC002", "Caixilho de alumínio anodizado natural c/ vidro", ItemCategory.FACADE, "m²", 85.30, 685.00, "UPE_00007"),
            BudgetItem("FAC003", "Vidro temperado incolor 10mm", ItemCategory.FACADE, "m²", 125.40, 285.00, "UPE_00007"),
            BudgetItem("FAC004", "Portal de entrada ACM padrão 2024", ItemCategory.FACADE, "un", 1.00, 8500.00, "UPE_00007", "Modelo Portal 2024"),
            BudgetItem("FAC005", "Letreiro luminoso LED fachada - logo Itaú", ItemCategory.FACADE, "un", 1.00, 12500.00, "UPE_00007"),
            BudgetItem("FAC006", "Instalação de logo institucional ACM", ItemCategory.FACADE, "un", 3.00, 1452.53, "UPE_00007"),
            BudgetItem("FAC007", "Toldo retrátil em lona laranja", ItemCategory.FACADE, "m²", 28.50, 385.00, "UPE_00007"),
        ]
        self.items.extend(items)

    def _add_hydraulic_items(self) -> None:
        """Adiciona itens de instalações hidráulicas."""
        items = [
            BudgetItem("HID001", "Bacia sanitária suspensa Deca c/ caixa acoplada", ItemCategory.HYDRAULICS, "un", 4.00, 850.00, "UPE_00008"),
            BudgetItem("HID002", "Assento sanitário Deca branco", ItemCategory.HYDRAULICS, "un", 4.00, 493.28, "UPE_00008"),
            BudgetItem("HID003", "Lavatório suspenso Deca Ravena", ItemCategory.HYDRAULICS, "un", 4.00, 385.00, "UPE_00008"),
            BudgetItem("HID004", "Torneira de mesa monocomando Deca", ItemCategory.HYDRAULICS, "un", 4.00, 425.00, "UPE_00008"),
            BudgetItem("HID005", "Válvula de escoamento angular 3/4 x 2.1/2", ItemCategory.HYDRAULICS, "un", 4.00, 890.00, "UPE_00008"),
            BudgetItem("HID006", "Ligação flexível 1/2 x 30cm cromada", ItemCategory.HYDRAULICS, "un", 8.00, 122.22, "UPE_00008"),
            BudgetItem("HID007", "Caixa de descarga embutir 6L Deca", ItemCategory.HYDRAULICS, "un", 4.00, 385.00, "UPE_00008"),
            BudgetItem("HID008", "Registro de gaveta 3/4 Deca", ItemCategory.HYDRAULICS, "un", 12.00, 145.00, "UPE_00008"),
            BudgetItem("HID009", "Bebedouro industrial refrigerado IBBL", ItemCategory.HYDRAULICS, "un", 2.00, 2850.00, "UPE_00008"),
            BudgetItem("HID010", "Purificador de água Soft Everest", ItemCategory.HYDRAULICS, "un", 1.00, 1650.00, "UPE_00008"),
        ]
        self.items.extend(items)

    def _add_electrical_items(self) -> None:
        """Adiciona itens de instalações elétricas."""
        items = [
            BudgetItem("ELE001", "Luminária LED 32W embutir quadrada", ItemCategory.ELECTRICAL, "un", 85.00, 285.00, "UPE_00009"),
            BudgetItem("ELE002", "Luminária LED 18W sobrepor redonda", ItemCategory.ELECTRICAL, "un", 35.00, 195.00, "UPE_00009"),
            BudgetItem("ELE003", "Spot LED direcionável 7W", ItemCategory.ELECTRICAL, "un", 48.00, 125.00, "UPE_00009"),
            BudgetItem("ELE004", "Tomada padrão brasileiro 2P+T 10A", ItemCategory.ELECTRICAL, "un", 120.00, 42.50, "UPE_00009"),
            BudgetItem("ELE005", "Interruptor simples Pial Legrand", ItemCategory.ELECTRICAL, "un", 35.00, 38.00, "UPE_00009"),
            BudgetItem("ELE006", "Quadro de distribuição 24 disjuntores", ItemCategory.ELECTRICAL, "un", 2.00, 1850.00, "UPE_00009"),
            BudgetItem("ELE007", "Disjuntor tripolar 70A", ItemCategory.ELECTRICAL, "un", 4.00, 285.00, "UPE_00009"),
            BudgetItem("ELE008", "Cabo flexível 6mm² (rolo 100m)", ItemCategory.ELECTRICAL, "rolo", 8.00, 485.00, "UPE_00009"),
            BudgetItem("ELE009", "Eletroduto PVC rígido 1 (barra 3m)", ItemCategory.ELECTRICAL, "barra", 45.00, 28.50, "UPE_00009"),
            BudgetItem("ELE010", "Nobreak 3000VA senoidal", ItemCategory.ELECTRICAL, "un", 3.00, 3850.00, "UPE_00009"),
        ]
        self.items.extend(items)

    def _add_hvac_items(self) -> None:
        """Adiciona itens de climatização."""
        items = [
            BudgetItem("HVAC001", "Ar condicionado split 24000 BTU inverter", ItemCategory.HVAC, "un", 6.00, 3850.00, "UPE_00010"),
            BudgetItem("HVAC002", "Ar condicionado cassete 4 vias 48000 BTU", ItemCategory.HVAC, "un", 2.00, 8500.00, "UPE_00010"),
            BudgetItem("HVAC003", "Tubulação de cobre 3/8 + 5/8 (kit 5m)", ItemCategory.HVAC, "kit", 8.00, 385.00, "UPE_00010"),
            BudgetItem("HVAC004", "Dreno para condensado ar condicionado", ItemCategory.HVAC, "un", 8.00, 125.00, "UPE_00010"),
            BudgetItem("HVAC005", "Instalação e mão de obra ar condicionado", ItemCategory.HVAC, "un", 8.00, 850.00, "UPE_00010"),
        ]
        self.items.extend(items)

    def _add_security_items(self) -> None:
        """Adiciona itens de segurança e automação."""
        items = [
            BudgetItem("SEG001", "Câmera IP 4MP dome infravermelha", ItemCategory.SECURITY, "un", 12.00, 985.00, "UPE_00011"),
            BudgetItem("SEG002", "DVR 16 canais com HD 2TB", ItemCategory.SECURITY, "un", 1.00, 2850.00, "UPE_00011"),
            BudgetItem("SEG003", "Sensor de presença infravermelho", ItemCategory.SECURITY, "un", 15.00, 285.00, "UPE_00011"),
            BudgetItem("SEG004", "Central de alarme monitorada 12 zonas", ItemCategory.SECURITY, "un", 1.00, 1850.00, "UPE_00011"),
            BudgetItem("SEG005", "Porta corta-fogo 90min 0,90x2,10m", ItemCategory.SECURITY, "un", 2.00, 4850.00, "UPE_00011"),
            BudgetItem("SEG006", "Extintor PQS 6kg c/ suporte", ItemCategory.SECURITY, "un", 6.00, 185.00, "UPE_00011"),
            BudgetItem("SEG007", "Iluminação de emergência LED", ItemCategory.SECURITY, "un", 12.00, 245.00, "UPE_00011"),
            BudgetItem("SEG008", "Controle de acesso biométrico", ItemCategory.SECURITY, "un", 3.00, 2850.00, "UPE_00011"),
        ]
        self.items.extend(items)

    def _add_furniture_items(self) -> None:
        """Adiciona itens de mobiliário."""
        items = [
            BudgetItem("MOB001", "Balcão de atendimento MDF padrão Itaú", ItemCategory.FURNITURE, "m", 12.50, 1850.00, "UPE_00012"),
            BudgetItem("MOB002", "Guichê de caixa blindado padrão bancário", ItemCategory.FURNITURE, "un", 4.00, 8500.00, "UPE_00012"),
            BudgetItem("MOB003", "Mesa gerente L 1,40m com gaveteiro", ItemCategory.FURNITURE, "un", 3.00, 2450.00, "UPE_00012"),
            BudgetItem("MOB004", "Cadeira executiva presidente giratória", ItemCategory.FURNITURE, "un", 3.00, 1285.00, "UPE_00012"),
            BudgetItem("MOB005", "Cadeira interlocutor fixa", ItemCategory.FURNITURE, "un", 12.00, 485.00, "UPE_00012"),
            BudgetItem("MOB006", "Armário alto 2 portas 0,80x1,80m", ItemCategory.FURNITURE, "un", 6.00, 1450.00, "UPE_00012"),
            BudgetItem("MOB007", "Estação de trabalho lineares 4 posições", ItemCategory.FURNITURE, "un", 2.00, 5850.00, "UPE_00012"),
            BudgetItem("MOB008", "Cofre eletrônico 500kg padrão bancário", ItemCategory.FURNITURE, "un", 1.00, 15000.00, "UPE_00012"),
        ]
        self.items.extend(items)

    def _add_cleaning_items(self) -> None:
        """Adiciona itens de limpeza final."""
        items = [
            BudgetItem("LMP001", "Limpeza fina pós-obra", ItemCategory.CLEANING, "m²", 450.00, 18.50, "UPE_00013"),
            BudgetItem("LMP002", "Polimento de porcelanato", ItemCategory.CLEANING, "m²", 285.50, 28.00, "UPE_00013"),
            BudgetItem("LMP003", "Lavagem de vidros e fachada", ItemCategory.CLEANING, "m²", 210.70, 22.50, "UPE_00013"),
        ]
        self.items.extend(items)

    def get_dataframe(self) -> pd.DataFrame:
        """
        Retorna o orçamento como DataFrame do pandas.

        Returns:
            DataFrame com todos os itens do orçamento
        """
        return pd.DataFrame([item.to_dict() for item in self.items])

    def get_summary(self) -> Dict:
        """
        Retorna um resumo do orçamento.

        Returns:
            Dicionário com estatísticas do orçamento
        """
        df = self.get_dataframe()
        total_geral = df["total_orcado"].sum()

        categorias = df.groupby("categoria").agg(
            {"total_orcado": "sum", "cod_item": "count"}
        ).to_dict()

        # Estatísticas por UPE
        upes = df.groupby("cod_upe").agg(
            {"total_orcado": "sum", "cod_item": "count"}
        ).to_dict()

        return {
            "metadata": {
                "projeto": self.metadata.projeto,
                "cliente": self.metadata.cliente,
                "local": self.metadata.local,
                "area_total_m2": self.metadata.area_total_m2,
                "tipo_obra": self.metadata.tipo_obra,
                "data_geracao": self.metadata.data_geracao,
                "versao": self.metadata.versao,
            },
            "estatisticas": {
                "total_itens": len(self.items),
                "total_upes": df["cod_upe"].nunique(),
                "valor_total": round(total_geral, 2),
                "valor_por_m2": round(total_geral / self.metadata.area_total_m2, 2),
                "categorias": categorias,
                "upes": upes,
            },
        }

    def save_to_csv(self, filepath: str = "orcamento_agencia_itau.csv") -> None:
        """
        Salva o orçamento em arquivo CSV.

        Args:
            filepath: Caminho do arquivo de saída
        """
        df = self.get_dataframe()
        df.to_csv(filepath, index=False, encoding="utf-8-sig", sep=";")
        print(f"✅ Orçamento salvo em: {filepath}")

    def save_to_excel(self, filepath: str = "orcamento_agencia_itau.xlsx") -> None:
        """
        Salva o orçamento em arquivo Excel com formatação.

        Args:
            filepath: Caminho do arquivo de saída
        """
        df = self.get_dataframe()
        summary = self.get_summary()

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            # Aba de itens detalhados
            df.to_excel(writer, sheet_name="Orçamento", index=False)

            # Aba de resumo por categoria
            resumo_cat = df.groupby("categoria").agg(
                {
                    "cod_item": "count",
                    "qtde": "sum",
                    "total_orcado": "sum",
                }
            ).reset_index()
            resumo_cat.columns = ["Categoria", "Qtd Itens", "Quantidade Total", "Valor Total"]
            resumo_cat.to_excel(writer, sheet_name="Resumo por Categoria", index=False)

            # Aba de resumo por UPE
            resumo_upe = df.groupby("cod_upe").agg(
                {
                    "cod_item": "count",
                    "categoria": lambda x: x.mode()[0] if not x.empty else "",
                    "total_orcado": "sum",
                }
            ).reset_index()
            resumo_upe.columns = ["Código UPE", "Qtd Itens", "Categoria Principal", "Valor Total"]
            resumo_upe = resumo_upe.sort_values("Código UPE")
            resumo_upe.to_excel(writer, sheet_name="Resumo por UPE", index=False)

        print(f"✅ Orçamento salvo em: {filepath}")


def main():
    """Função principal para demonstração."""
    print("=" * 80)
    print("GERADOR DE ORÇAMENTO - AGÊNCIA BANCÁRIA ITAÚ UNIBANCO")
    print("=" * 80)

    # Criar gerador com metadados customizados
    metadata = BudgetMetadata(
        projeto="Reforma Agência Itaú - Av. Paulista, 1234",
        local="São Paulo - SP",
        area_total_m2=450.0,
        tipo_obra="Reforma Completa - Padrão 2024",
    )

    generator = BankBranchBudgetGenerator(metadata)
    generator.generate_standard_budget()

    # Exibir resumo
    summary = generator.get_summary()
    print(f"\n📋 Projeto: {summary['metadata']['projeto']}")
    print(f"🏢 Cliente: {summary['metadata']['cliente']}")
    print(f"📍 Local: {summary['metadata']['local']}")
    print(f"📏 Área Total: {summary['metadata']['area_total_m2']} m²")
    print(f"🔨 Tipo: {summary['metadata']['tipo_obra']}")
    print(f"\n📊 Total de Itens: {summary['estatisticas']['total_itens']}")
    print(f"� Total de UPEs: {summary['estatisticas']['total_upes']}")
    print(f"�💰 Valor Total: R$ {summary['estatisticas']['valor_total']:,.2f}")
    print(f"💵 Valor por m²: R$ {summary['estatisticas']['valor_por_m2']:,.2f}")

    # Exibir dataframe
    print("\n" + "=" * 80)
    print("ORÇAMENTO DETALHADO")
    print("=" * 80)
    df = generator.get_dataframe()
    print(df.to_string())

    # Salvar arquivos
    print("\n" + "=" * 80)
    output_dir = Path(__file__).parent
    generator.save_to_csv(str(output_dir / "orcamento_agencia_itau.csv"))
    generator.save_to_excel(str(output_dir / "orcamento_agencia_itau.xlsx"))

    return generator


if __name__ == "__main__":
    orcamento = main()

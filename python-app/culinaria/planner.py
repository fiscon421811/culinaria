"""Cardápios semanais e estações do Hemisfério Sul (porta de CardapioSemanalFragment)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from . import config


@dataclass(frozen=True, slots=True)
class DayMenu:
    dia: str
    cafe: str
    almoco: str
    jantar: str

    def refeicoes(self) -> list[tuple[str, str]]:
        return [
            ("🍳  Café da manhã", self.cafe),
            ("🍛  Almoço", self.almoco),
            ("🥗  Jantar", self.jantar),
        ]


@dataclass(frozen=True, slots=True)
class Menu:
    nome: str
    icone: str
    periodo: str
    foco: str
    dias: tuple[DayMenu, ...] = ()


def _menu(*linhas: tuple[str, str, str, str]) -> tuple[DayMenu, ...]:
    return tuple(DayMenu(*linha) for linha in linhas)


PRIMAVERA = Menu(
    "Primavera", "🌸", "23 de setembro a 20 de dezembro",
    "Cores, frescor e pratos leves com vegetais da estação.",
    _menu(
        ("Segunda", "Vitamina de morango com aveia", "Frango grelhado com arroz de brócolis", "Salada de folhas com tiras de carne"),
        ("Terça", "Crepioca de queijo branco", "Iscas de patinho com vagem e cenoura", "Omelete de espinafre com tomate"),
        ("Quarta", "Mamão com iogurte e granola", "Filé de peixe grelhado com purê de mandioquinha", "Wrap integral de frango com rúcula"),
        ("Quinta", "Torrada com ovo mexido e chia", "Macarrão integral ao pesto com tomate-cereja", "Abobrinha recheada com ricota e frango"),
        ("Sexta", "Panqueca de banana com mel", "Sobrecoxa assada com batata-doce", "Sopa leve de legumes com peito de peru"),
        ("Sábado", "Pão de queijo de frigideira", "Risoto de limão-siciliano com filé de Saint Peter", "Salada grega com cubos de queijo e torradinhas"),
        ("Domingo", "Salada de frutas com linhaça", "Lagarto assado com farofa de cenoura", "Sanduíche natural de atum com cenoura ralada"),
    ),
)

VERAO = Menu(
    "Verão", "☀️", "21 de dezembro a 20 de março",
    "Hidratação, pratos frios, rápidos e frutas tropicais.",
    _menu(
        ("Segunda", "Smoothie de abacaxi com hortelã", "Salada de macarrão parafuso com atum e milho", "Crepioca de frango desfiado com requeijão"),
        ("Terça", "Iogurte batido com manga", "Peito de frango grelhado com salada de quinoa", "Omelete com tomate, cebola e manjericão"),
        ("Quarta", "Sanduíche integral de queijo e tomate", "Filé de pescada fria ao vinagrete com arroz", "Salada de grão-de-bico com lascas de bacalhau"),
        ("Quinta", "Salada de frutas com chia", "Carne moída com cubos de chuchu e arroz integral", "Wrap frio de peito de peru e creme de ricota"),
        ("Sexta", "Ovos mexidos com tomate e torrada", "Espetinho de frango com pimentão e arroz", "Tapioca de queijo-coalho com tomate"),
        ("Sábado", "Vitamina de banana com leite de coco", "Ceviche de peixe branco com chips de batata-doce", "Salada de folhas, gomos de laranja e frango"),
        ("Domingo", "Suco verde com torrada integral", "Filé de miolo de alcatra acebolado e salada", "Sanduíche de pão sírio com homus e pepino"),
    ),
)

OUTONO = Menu(
    "Outono", "🍁", "21 de março a 20 de junho",
    "Pratos mais aconchegantes e raízes como abóbora, cará e mandioca.",
    _menu(
        ("Segunda", "Vitamina de banana, aveia e canela", "Escondidinho de carne moída com mandioca", "Creme de abóbora cabotiá com gengibre"),
        ("Terça", "Panqueca de maçã com canela", "Sobrecoxa de frango ensopada com quiabo", "Omelete de cogumelos com torrada"),
        ("Quarta", "Pão integral na chapa com requeijão", "Carne de panela com cenoura e batata", "Caldo verde funcional com couve em tiras"),
        ("Quinta", "Ovos mexidos com queijo meia-cura", "Polenta mole com molho bolonhesa magro", "Berinjela recheada com frango gratinada"),
        ("Sexta", "Crepioca de carne-seca com nata", "Arroz integral com lentilha e filé de frango", "Sopa de feijão com macarrão paiol"),
        ("Sábado", "Bolo de caneca de cacau integral", "Strogonoff de frango com arroz e batata rústica", "Toast de abacate com ovo pochê"),
        ("Domingo", "Iogurte com mel e nozes picadas", "Assado de tiras com maionese caseira", "Tapioca de queijo com fatias de caqui"),
    ),
)

INVERNO = Menu(
    "Inverno", "❄️", "21 de junho a 22 de setembro",
    "Pratos quentes, caldos encorpados e alimentos térmicos.",
    _menu(
        ("Segunda", "Mingau de aveia morno com canela", "Picadinho de carne com arroz e feijão-preto", "Creme de ervilha com cubos de bacon tostadinho"),
        ("Terça", "Chocolate quente funcional e torrada", "Coxa de frango assada com purê de batata", "Canja de galinha tradicional com arroz"),
        ("Quarta", "Pão de queijo de Minas quentinho", "Macarrão à bolonhesa com queijo ralado", "Sopa de goulash"),
        ("Quinta", "Ovos mexidos na manteiga com pão", "Lasanha de berinjela com carne moída", "Caldo de mandioca com costelinha desfiada"),
        ("Sexta", "Panqueca americana integral morna", "Filé de peixe assado com crosta de amêndoas", "Sopa de legumes com músculo bovino"),
        ("Sábado", "Mingau de fubá com queijo ralado", "Feijoada light com couve refogada e laranja", "Polenta frita na airfryer com carne desfiada"),
        ("Domingo", "Cappuccino caseiro e bolo de fubá", "Nhoque de batata ao molho sugo com braciola", "Sanduíche quente de forno com queijo e presunto"),
    ),
)

SAZONAL = Menu(
    "Sazonal", "🌦️", "conforme a estação",
    "Usa automaticamente a estação climática atual do Hemisfério Sul.",
)

CARDAPIOS_ALTERNATIVOS: tuple[Menu, ...] = (
    Menu("Vegano", "🌱", "cardápio semanal",
         "Refeições 100% vegetais, com grãos, legumes e proteínas vegetais.",
         _menu(
             ("Segunda", "Overnight oats com banana", "Curry de grão-de-bico com arroz integral", "Sopa de lentilha com couve"),
             ("Terça", "Tapioca com pasta de amendoim", "Escondidinho de lentilha com mandioca", "Wrap de homus, pepino e rúcula"),
             ("Quarta", "Vitamina de manga com aveia", "Tofu grelhado com legumes e quinoa", "Macarrão integral ao molho de tomate e manjericão"),
             ("Quinta", "Pão integral com abacate", "Feijão-preto, arroz, abóbora assada e salada", "Berinjela recheada com quinoa"),
             ("Sexta", "Cuscuz com coco e frutas", "Falafel assado com tabule", "Creme de abóbora com gengibre"),
             ("Sábado", "Panqueca de banana e aveia", "Moqueca vegana de banana-da-terra", "Pizza de legumes com queijo vegetal"),
             ("Domingo", "Frutas com chia", "Lasanha de abobrinha com molho de lentilha", "Sanduíche de cogumelos e cebola caramelizada"),
         )),
    Menu("Low Carb", "🥑", "cardápio semanal",
         "Menos carboidratos, com proteínas, vegetais e gorduras saudáveis.",
         _menu(
             ("Segunda", "Omelete de espinafre e queijo", "Frango grelhado com brócolis e salada", "Abobrinha recheada com carne moída"),
             ("Terça", "Iogurte natural com nozes", "Salmão assado com aspargos", "Salada Caesar com frango"),
             ("Quarta", "Ovos mexidos com tomate", "Carne de panela com couve-flor", "Sopa de legumes com frango"),
             ("Quinta", "Pudim de chia com coco", "Almôndegas ao molho com abobrinha", "Omelete de cogumelos"),
             ("Sexta", "Crepioca de queijo", "Peixe grelhado com purê de couve-flor", "Salada de atum com ovos"),
             ("Sábado", "Abacate com cacau e chia", "Frango ao curry com legumes", "Hambúrguer caseiro com salada"),
             ("Domingo", "Queijo branco com frutas vermelhas", "Lombo assado com couve refogada", "Caldo de abóbora com carne desfiada"),
         )),
    Menu("Brasileiro", "🇧🇷", "cardápio semanal",
         "Sabores regionais, ingredientes locais e preparos tradicionais brasileiros.",
         _menu(
             ("Segunda", "Cuscuz nordestino com ovo", "Frango com quiabo, arroz e feijão", "Tapioca de queijo coalho"),
             ("Terça", "Pão de queijo com café", "Picadinho de carne, arroz, feijão e couve", "Caldo de mandioca com carne-seca"),
             ("Quarta", "Açaí com banana e granola", "Moqueca de peixe com arroz", "Omelete de legumes"),
             ("Quinta", "Bolo de fubá e leite", "Escondidinho de carne-seca com salada", "Cuscuz paulista com salada verde"),
             ("Sexta", "Tapioca de coco", "Feijoada leve com couve e laranja", "Sopa de feijão"),
             ("Sábado", "Pão na chapa com requeijão", "Galinhada com açafrão e salada", "Pastel assado de palmito"),
             ("Domingo", "Frutas tropicais", "Churrasco com vinagrete e farofa", "Sanduíche natural de frango"),
         )),
    Menu("Mediterrâneo", "🫒", "cardápio semanal",
         "Azeite, peixes, grãos, vegetais e ervas aromáticas.",
         _menu(
             ("Segunda", "Iogurte com frutas e nozes", "Frango mediterrâneo com quinoa", "Salada grega com grão-de-bico"),
             ("Terça", "Torrada integral com tomate", "Peixe assado com legumes e azeite", "Sopa minestrone"),
             ("Quarta", "Omelete com ervas", "Tabule com falafel assado", "Berinjela assada com ricota"),
             ("Quinta", "Aveia com figos e mel", "Macarrão integral ao pesto com tomate", "Salada de atum, feijão-branco e rúcula"),
             ("Sexta", "Pão integral com homus", "Almôndegas de peru com cuscuz marroquino", "Legumes grelhados com queijo feta"),
             ("Sábado", "Frutas, queijo e castanhas", "Risoto de limão com peixe", "Wrap de frango com tzatziki"),
             ("Domingo", "Panqueca de aveia", "Lasanha de berinjela ao molho sugo", "Salada de lentilha com ervas"),
         )),
    Menu("Vegetariano", "🥕", "cardápio semanal",
         "Sem carnes, com ovos, laticínios, leguminosas e vegetais variados.",
         _menu(
             ("Segunda", "Iogurte com granola", "Lentilha com arroz integral e legumes", "Omelete de espinafre com tomate"),
             ("Terça", "Tapioca com queijo branco", "Nhoque de abóbora ao molho sugo", "Salada de grão-de-bico com ricota"),
             ("Quarta", "Vitamina de banana e aveia", "Quiche de alho-poró com salada", "Sopa de legumes com queijo"),
             ("Quinta", "Pão integral com ovos", "Estrogonofe de cogumelos com arroz", "Tapioca de tomate e queijo"),
             ("Sexta", "Panqueca de maçã", "Lasanha de berinjela com ricota", "Creme de ervilha com torradas"),
             ("Sábado", "Cuscuz com queijo coalho", "Risoto de cogumelos", "Hambúrguer de grão-de-bico com salada"),
             ("Domingo", "Frutas com sementes", "Feijão-tropeiro vegetariano", "Wrap de legumes grelhados"),
         )),
)


def estacao_atual(hoje: date | None = None) -> Menu:
    """Estação do Hemisfério Sul para a data informada."""
    hoje = hoje or date.today()
    md = hoje.month * 100 + hoje.day
    if 621 <= md <= 922:
        return INVERNO
    if 923 <= md <= 1220:
        return PRIMAVERA
    if md >= 1221 or md <= 320:
        return VERAO
    return OUTONO


def opcoes_de_cardapio() -> list[Menu]:
    """Sazonal primeiro, como no seletor do app Android."""
    return [SAZONAL, *CARDAPIOS_ALTERNATIVOS]


# ── Persistência do cardápio escolhido (equivalente a MealPlannerStore) ──────


@dataclass
class PlannedMeal:
    title: str
    recipe: str
    link: str | None = None


@dataclass
class MealPlannerState:
    menu: str | None = None
    meals: dict[str, list[PlannedMeal]] = field(default_factory=dict)


class MealPlannerStore:
    """Guarda o estado do cardápio em ~/.culinaria/meal_planner.json."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (config.STATE_DIR / "meal_planner.json")

    def load(self) -> MealPlannerState:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return MealPlannerState()
        meals: dict[str, list[PlannedMeal]] = {}
        for chave, valor in (data.get("meals") or {}).items():
            itens = valor if isinstance(valor, list) else [valor]
            meals[chave] = [
                PlannedMeal(
                    title=i.get("title", ""),
                    recipe=i.get("recipe", ""),
                    link=i.get("link"),
                )
                for i in itens
                if isinstance(i, dict)
            ]
        return MealPlannerState(menu=data.get("menu"), meals=meals)

    def save(self, state: MealPlannerState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "menu": state.menu,
            "meals": {k: [asdict(m) for m in v] for k, v in state.meals.items()},
        }
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

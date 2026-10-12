"""Aba "Cardápio Semanal" (porta de CardapioSemanalFragment)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..ai import RecipeAiClient
from ..models import Categoria, Receita, RecipeAiResult
from ..planner import (
    DayMenu,
    MealPlannerState,
    MealPlannerStore,
    Menu,
    estacao_atual,
    opcoes_de_cardapio,
)
from ..tasks import run_async
from ..viewmodel import AppViewModel
from .widgets import botao, cabecalho, rotulo


class CardapioTab(QWidget):
    def __init__(self, vm: AppViewModel, ai: RecipeAiClient) -> None:
        super().__init__()
        self.vm = vm
        self.ai = ai
        self.store = MealPlannerStore()
        self.menu_escolhido: Menu | None = self._menu_salvo()

        self.faixa = cabecalho("🌦️  Cardápio Semanal", "Carregando…")
        self.btn_menu = botao("ALTERAR CARDÁPIO")
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(10)
        self.container_layout.addStretch(1)

        self._montar()
        self.btn_menu.clicked.connect(self._escolher_menu)
        self.render()

    def _menu_salvo(self) -> Menu | None:
        nome = self.store.load().menu
        if not nome:
            return None
        for opcao in opcoes_de_cardapio()[1:]:
            if opcao.nome == nome:
                return opcao
        return None

    def _montar(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self.faixa)

        topo = QHBoxLayout()
        topo.addWidget(self.btn_menu)
        topo.addStretch(1)
        caixa = QWidget()
        caixa.setLayout(topo)
        layout.addWidget(caixa)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)
        layout.addWidget(scroll, 1)

    # ── Render ───────────────────────────────────────────────────────────────

    @property
    def menu_ativo(self) -> Menu:
        return self.menu_escolhido or estacao_atual()

    def render(self) -> None:
        menu = self.menu_ativo
        subtitulo = (
            "Sugestão preparada pela IA para a estação atual"
            if self.menu_escolhido is None
            else f"Sugestão semanal de {menu.nome.lower()}"
        )
        self.faixa.layout().itemAt(0).widget().setText(
            f"{menu.icone}  {menu.nome.upper()} · {menu.periodo.upper()}"
        )
        self.faixa.layout().itemAt(1).widget().setText(f"{menu.foco}\n{subtitulo}")
        self.btn_menu.setText(f"ALTERAR CARDÁPIO: {menu.nome.upper()}")

        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for dia in menu.dias:
            self.container_layout.addWidget(self._card_dia(dia))
        self.container_layout.addStretch(1)

    def _card_dia(self, dia: DayMenu) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        layout.addWidget(rotulo(dia.dia.upper(), "secao"))
        for titulo, item in dia.refeicoes():
            layout.addWidget(self._linha_refeicao(titulo, item, dia.dia))
        return frame

    def _linha_refeicao(self, titulo: str, item: str, dia: str) -> QWidget:
        caixa = QWidget()
        layout = QHBoxLayout(caixa)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)
        texto = rotulo(f"{titulo}\n{item}", "subtitulo", wrap=True)
        texto.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(texto, 1)
        b = botao("IMPORTAR", "ghost")
        b.setFixedWidth(120)
        b.clicked.connect(lambda _=False: self._gerar(item, titulo, dia, b))
        layout.addWidget(b, 0, Qt.AlignTop)
        return caixa

    # ── IA + importação ──────────────────────────────────────────────────────

    def _escolher_menu(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("ESCOLHA O CARDÁPIO SEMANAL")
        dialog.setMinimumWidth(620)
        layout = QVBoxLayout(dialog)
        for indice, opcao in enumerate(opcoes_de_cardapio()):
            b = botao(f"{opcao.icone}  {opcao.nome} — {opcao.foco}", "ghost")
            b.clicked.connect(
                lambda _=False, i=indice, o=opcao: (dialog.accept(), self._aplicar_menu(i, o))
            )
            layout.addWidget(b)
        layout.addWidget(botao("CANCELAR", "link", dialog.reject))
        dialog.exec()

    def _aplicar_menu(self, indice: int, opcao: Menu) -> None:
        self.menu_escolhido = None if indice == 0 else opcao
        estado = self.store.load()
        self.store.save(
            MealPlannerState(menu=None if indice == 0 else opcao.nome, meals=estado.meals)
        )
        self.render()

    def _gerar(self, titulo: str, refeicao: str, dia: str, b) -> None:
        b.setEnabled(False)
        b.setText("GERANDO…")
        estacao = self.menu_ativo.nome

        def restaurar() -> None:
            b.setEnabled(True)
            b.setText("IMPORTAR")

        run_async(
            lambda: self.ai.generate_seasonal_recipe(titulo, estacao, refeicao, dia),
            on_ok=lambda r: self._escolher_categoria(r, refeicao, dia),
            on_erro=lambda msg: QMessageBox.warning(self, "IA", msg),
            on_fim=restaurar,
        )

    def _escolher_categoria(self, receita_ia: RecipeAiResult, refeicao: str, dia: str) -> None:
        if self.vm.repo.titulo_existe(receita_ia.titulo):
            QMessageBox.information(
                self, "Cardápio", "Essa receita já está no seu Livro de Receitas."
            )
            return

        def com_categorias(categorias: list[Categoria]) -> None:
            if not categorias:
                QMessageBox.warning(
                    self,
                    "Nenhuma categoria cadastrada",
                    "Cadastre uma categoria na aba Categorias e tente importar novamente.",
                )
                return
            dialog = QDialog(self)
            dialog.setWindowTitle("ESCOLHA A CATEGORIA")
            dialog.setMinimumWidth(480)
            layout = QVBoxLayout(dialog)
            layout.addWidget(rotulo(f"Selecione onde salvar: {receita_ia.titulo}", "subtitulo", wrap=True))
            for categoria in categorias:
                b = botao(f"{categoria.cod_cat} - {categoria.cat}", "ghost")
                b.clicked.connect(
                    lambda _=False, c=categoria: (
                        dialog.accept(),
                        self._importar(receita_ia, refeicao, dia, c),
                    )
                )
                layout.addWidget(b)
            layout.addWidget(botao("CANCELAR", "link", dialog.reject))
            dialog.exec()

        self.vm.refresh_categorias(depois=com_categorias)

    def _importar(self, receita_ia: RecipeAiResult, refeicao: str, dia: str, categoria: Categoria) -> None:
        corpo = receita_ia.to_texto(rodape=f"Sugestão sazonal: {refeicao} · {dia}")

        def com_cod(cod: int) -> None:
            self.vm.insert_receita(
                Receita(
                    cod=cod,
                    cod_cat=categoria.cod_cat,
                    titulo=receita_ia.titulo.upper(),
                    receita=corpo,
                    link=receita_ia.video_url or None,
                ),
                aviso="Receita completa adicionada ao Livro de Receitas.",
            )

        self.vm.proximo_cod(com_cod)

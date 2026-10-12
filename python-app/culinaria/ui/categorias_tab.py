"""Aba "Categorias" (porta de CategoriasFragment + CategoriaAdapter)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..models import Categoria
from ..viewmodel import AppViewModel
from .widgets import botao, cabecalho, linha, rotulo


class CategoriasTab(QWidget):
    def __init__(self, vm: AppViewModel) -> None:
        super().__init__()
        self.vm = vm

        self.et_nome = QLineEdit(placeholderText="Nome da nova categoria")
        self.btn_adicionar = botao("ADICIONAR")
        self.btn_renomear = botao("RENOMEAR", "ghost")
        self.btn_excluir = botao("EXCLUIR", "danger")
        self.tv_total = rotulo("0 categoria(s)", "contador")
        self.lista = QListWidget()

        self._montar()
        self._conectar()

    def _montar(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(cabecalho("🏷️  Categorias", "Organize suas receitas. Categorias em uso não podem ser excluídas."))
        layout.addWidget(linha(self.et_nome, self.btn_adicionar, esticar=0))

        topo = QHBoxLayout()
        topo.addWidget(self.tv_total)
        topo.addStretch(1)
        topo.addWidget(self.btn_renomear)
        topo.addWidget(self.btn_excluir)
        caixa = QWidget()
        caixa.setLayout(topo)
        layout.addWidget(caixa)
        layout.addWidget(self.lista, 1)

    def _conectar(self) -> None:
        self.vm.categorias_changed.connect(self._render)
        self.btn_adicionar.clicked.connect(self._adicionar)
        self.et_nome.returnPressed.connect(self._adicionar)
        self.btn_renomear.clicked.connect(self._renomear)
        self.btn_excluir.clicked.connect(self._excluir)
        self.lista.itemDoubleClicked.connect(lambda _: self._renomear())

    # ── Estado ───────────────────────────────────────────────────────────────

    def _render(self, categorias: list[Categoria]) -> None:
        self.lista.clear()
        for c in categorias:
            item = QListWidgetItem(f"{c.cod_cat}  ·  {c.cat}")
            item.setData(Qt.UserRole, c)
            self.lista.addItem(item)
        self.tv_total.setText(f"{len(categorias)} categoria(s)")

    def _selecionada(self) -> Categoria | None:
        item = self.lista.currentItem()
        if item is None:
            QMessageBox.information(self, "Categorias", "Selecione uma categoria na lista.")
            return None
        return item.data(Qt.UserRole)

    # ── Ações ────────────────────────────────────────────────────────────────

    def _adicionar(self) -> None:
        nome = self.et_nome.text().strip()
        if not nome:
            QMessageBox.information(self, "Categorias", "Digite o nome da categoria.")
            self.et_nome.setFocus()
            return

        def com_proximo(cod: int) -> None:
            self.vm.insert_categoria(Categoria(cod_cat=cod, cat=nome))
            self.et_nome.clear()

        self.vm.proximo_cod_cat(com_proximo)

    def _renomear(self) -> None:
        categoria = self._selecionada()
        if categoria is None:
            return
        novo, ok = QInputDialog.getText(
            self, "Renomear categoria", "Novo nome:", QLineEdit.Normal, categoria.cat
        )
        if ok and novo.strip() and novo.strip() != categoria.cat:
            self.vm.update_categoria(categoria.copy(cat=novo.strip()))

    def _excluir(self) -> None:
        categoria = self._selecionada()
        if categoria is None:
            return
        confirma = QMessageBox.question(
            self,
            "Confirmar exclusão",
            f'Deseja realmente DELETAR a categoria "{categoria.cat}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirma == QMessageBox.Yes:
            self.vm.delete_categoria(categoria)

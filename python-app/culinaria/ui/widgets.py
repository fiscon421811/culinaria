"""Widgets reutilizáveis (cards, botões, lista de receitas)."""
from __future__ import annotations

from typing import Callable, Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import Receita
from . import style


def botao(texto: str, variante: str | None = None, on_click: Callable[[], None] | None = None) -> QPushButton:
    b = QPushButton(texto)
    if variante:
        b.setProperty("variant", variante)
    b.setCursor(Qt.PointingHandCursor)
    if on_click:
        b.clicked.connect(lambda: on_click())
    return b


def card(*widgets: QWidget, espacamento: int = 8, margens: tuple[int, int, int, int] = (14, 14, 14, 14)) -> QFrame:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margens)
    layout.setSpacing(espacamento)
    for w in widgets:
        layout.addWidget(w)
    return frame


def rotulo(texto: str, objeto: str | None = None, wrap: bool = False) -> QLabel:
    label = QLabel(texto)
    if objeto:
        label.setObjectName(objeto)
    label.setWordWrap(wrap)
    return label


def linha(*widgets: QWidget, esticar: int | None = None) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for i, w in enumerate(widgets):
        layout.addWidget(w, 1 if esticar == i else 0)
    return container


def cabecalho(titulo: str, subtitulo: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName("faixa")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(2)
    layout.addWidget(rotulo(titulo, "faixaTitulo"))
    layout.addWidget(rotulo(subtitulo, "faixaTexto", wrap=True))
    return frame


class ReceitaList(QListWidget):
    """Lista de receitas (equivalente a ReceitaAdapter + RecyclerView)."""

    receita_escolhida = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._receitas: list[Receita] = []
        self.setAlternatingRowColors(False)
        self.itemDoubleClicked.connect(self._emitir)
        self.itemActivated.connect(self._emitir)

    def submit(self, receitas: Iterable[Receita], nome_categoria: Callable[[int], str] | None = None) -> None:
        self._receitas = list(receitas)
        self.clear()
        for receita in self._receitas:
            categoria = nome_categoria(receita.cod_cat) if nome_categoria else f"Cat. {receita.cod_cat}"
            resumo = " ".join(receita.receita.split())[:110]
            item = QListWidgetItem(
                f"{receita.cod_formatado}  ·  {receita.titulo}\n{categoria} — {resumo}…"
            )
            item.setData(Qt.UserRole, receita)
            self.addItem(item)

    def selecionada(self) -> Receita | None:
        item = self.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _emitir(self, item: QListWidgetItem) -> None:
        receita = item.data(Qt.UserRole)
        if receita is not None:
            self.receita_escolhida.emit(receita)

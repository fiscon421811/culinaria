"""Aba "Receitas" — busca, filtros e detalhe (porta de ReceitasFragment)."""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import pdf
from ..models import Receita
from ..viewmodel import AppViewModel
from .widgets import ReceitaList, botao, cabecalho, linha, rotulo


class ReceitasTab(QWidget):
    def __init__(self, vm: AppViewModel) -> None:
        super().__init__()
        self.vm = vm

        self.et_titulo = QLineEdit(placeholderText="Buscar por título…")
        self.et_ingrediente = QLineEdit(placeholderText="Buscar por ingrediente…")
        self.lista = ReceitaList()
        self.tv_contagem = rotulo("0 receita(s)", "contador")

        self._debounce = QTimer(self, singleShot=True, interval=280)
        self._debounce.timeout.connect(self._buscar)

        self._montar()
        self._conectar()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _montar(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        layout.addWidget(cabecalho("📖  Livro de Receitas", "Busque por título ou ingrediente e abra a receita com duplo clique."))
        layout.addWidget(linha(self.et_titulo, self.et_ingrediente))

        filtros = QHBoxLayout()
        filtros.setSpacing(6)
        self.btn_todas = botao("TODAS", "ghost")
        filtros.addWidget(self.btn_todas)
        self.btns_categoria: dict[int, object] = {}
        for cod in (1, 2, 3, 4):
            b = botao(f"CAT {cod}", "ghost")
            b.clicked.connect(lambda _=False, c=cod: self._filtrar(c))
            self.btns_categoria[cod] = b
            filtros.addWidget(b)
        filtros.addStretch(1)
        filtros.addWidget(self.tv_contagem)
        caixa = QWidget()
        caixa.setLayout(filtros)
        layout.addWidget(caixa)

        layout.addWidget(self.lista, 1)

        acoes = QHBoxLayout()
        self.btn_detalhe = botao("ABRIR RECEITA")
        self.btn_imprimir_lista = botao("IMPRIMIR LISTA (PDF)", "ghost")
        self.btn_atualizar = botao("ATUALIZAR", "ghost")
        acoes.addWidget(self.btn_detalhe)
        acoes.addWidget(self.btn_imprimir_lista)
        acoes.addWidget(self.btn_atualizar)
        acoes.addStretch(1)
        rodape = QWidget()
        rodape.setLayout(acoes)
        layout.addWidget(rodape)

    def _conectar(self) -> None:
        self.vm.home_receitas_changed.connect(self._render)
        self.vm.categorias_changed.connect(lambda _: self._render(self.vm.home_receitas))
        self.et_titulo.textChanged.connect(self._debounce.start)
        self.et_ingrediente.textChanged.connect(self._debounce.start)
        self.btn_todas.clicked.connect(self._todas)
        self.btn_atualizar.clicked.connect(self.vm.recarregar_receitas)
        self.btn_detalhe.clicked.connect(self._abrir_selecionada)
        self.btn_imprimir_lista.clicked.connect(self._imprimir_lista)
        self.lista.receita_escolhida.connect(self.mostrar_detalhe)

    # ── Ações ────────────────────────────────────────────────────────────────

    def _render(self, receitas: list[Receita]) -> None:
        self.lista.submit(receitas, self.vm.nome_categoria)
        self.tv_contagem.setText(f"{len(receitas)} receita(s)")
        for cod, b in self.btns_categoria.items():
            b.setText(self.vm.nome_categoria(cod).upper()[:18] if self.vm.categorias else f"CAT {cod}")

    def _buscar(self) -> None:
        self.vm.search_home(self.et_titulo.text(), self.et_ingrediente.text())

    def _todas(self) -> None:
        self.et_titulo.clear()
        self.et_ingrediente.clear()
        self.vm.mostrar_todas()

    def _filtrar(self, cod_cat: int) -> None:
        self.et_titulo.clear()
        self.et_ingrediente.clear()
        self.vm.filtrar_por_categoria(cod_cat)

    def _abrir_selecionada(self) -> None:
        receita = self.lista.selecionada()
        if receita is None:
            QMessageBox.information(self, "Receitas", "Selecione uma receita na lista.")
            return
        self.mostrar_detalhe(receita)

    def _imprimir_lista(self) -> None:
        receitas = self.vm.home_receitas
        if not receitas:
            QMessageBox.information(self, "Imprimir", "Nenhuma receita para imprimir.")
            return
        try:
            caminho = pdf.gerar_pdf_lista(receitas, "Livro de Receitas")
            pdf.abrir_arquivo(caminho)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Imprimir", f"Erro ao gerar PDF: {exc}")

    def mostrar_detalhe(self, receita: Receita) -> None:
        DetalheDialog(receita, self.vm, self).exec()


class DetalheDialog(QDialog):
    """Equivalente ao dialog_receita_detalhe.xml."""

    def __init__(self, receita: Receita, vm: AppViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.receita = receita
        self.setWindowTitle(receita.titulo or "Receita")
        self.setMinimumSize(620, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        layout.addWidget(rotulo(receita.titulo, "titulo", wrap=True))
        layout.addWidget(
            rotulo(
                f"Cód. {receita.cod_formatado}  ·  {vm.nome_categoria(receita.cod_cat)}",
                "subtitulo",
            )
        )

        corpo = QPlainTextEdit(receita.receita)
        corpo.setReadOnly(True)
        layout.addWidget(corpo, 1)

        acoes = QHBoxLayout()
        if receita.link:
            acoes.addWidget(botao("ABRIR LINK", "ghost", lambda: webbrowser.open(receita.link or "")))
        acoes.addWidget(botao("COPIAR", "ghost", self._copiar))
        acoes.addWidget(botao("IMPRIMIR (PDF)", None, self._imprimir))
        acoes.addStretch(1)
        acoes.addWidget(botao("FECHAR", "ghost", self.accept))
        rodape = QWidget()
        rodape.setLayout(acoes)
        layout.addWidget(rodape)

        self._vm = vm

    def _copiar(self) -> None:
        QGuiApplication.clipboard().setText(f"{self.receita.titulo}\n\n{self.receita.receita}")

    def _imprimir(self) -> None:
        try:
            caminho = pdf.gerar_pdf_receita(self.receita, self._vm.nome_categoria(self.receita.cod_cat))
            pdf.abrir_arquivo(caminho)
            self.accept()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Imprimir", f"Erro ao gerar PDF: {exc}")

"""Aba "Editar" — busca, edição, exclusão e impressão (porta de EditarFragment)."""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import pdf
from ..models import Categoria, Receita
from ..viewmodel import AppViewModel
from .widgets import ReceitaList, botao, cabecalho, linha, rotulo


class EditarTab(QWidget):
    def __init__(self, vm: AppViewModel) -> None:
        super().__init__()
        self.vm = vm
        self.receita_selecionada: Receita | None = None

        self.et_busca_titulo = QLineEdit(placeholderText="Buscar por título…")
        self.et_busca_ingrediente = QLineEdit(placeholderText="Buscar por ingrediente…")
        self.et_busca_cod = QLineEdit(placeholderText="Nº")
        self.et_busca_cod.setFixedWidth(90)
        self.btn_buscar_cod = botao("BUSCAR Nº", "ghost")
        self.tv_total = rotulo("0 receita(s)", "contador")

        self.lista = ReceitaList()

        self.tv_codigo = QLineEdit()
        self.tv_codigo.setEnabled(False)
        self.tv_codigo.setFixedWidth(90)
        self.combo_categoria = QComboBox()
        self.et_titulo = QLineEdit()
        self.et_receita = QPlainTextEdit()
        self.et_link = QLineEdit()

        self.btn_salvar = botao("SALVAR ALTERAÇÕES")
        self.btn_deletar = botao("DELETAR", "danger")
        self.btn_limpar = botao("VOLTAR À LISTA", "ghost")
        self.btn_abrir_link = botao("ABRIR LINK", "ghost")
        self.btn_imprimir = botao("IMPRIMIR (PDF)", "ghost")

        self.stack = QStackedWidget()

        self._debounce = QTimer(self, singleShot=True, interval=280)
        self._debounce.timeout.connect(self._buscar)

        self._montar()
        self._conectar()

    def _montar(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(cabecalho("✏️  Editar Receitas", "Escolha na lista (duplo clique) ou busque pelo número."))
        layout.addWidget(linha(self.et_busca_titulo, self.et_busca_ingrediente))
        layout.addWidget(linha(self.et_busca_cod, self.btn_buscar_cod, self.tv_total))

        # Página 0: lista
        pagina_lista = QWidget()
        vl = QVBoxLayout(pagina_lista)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(self.lista)

        # Página 1: edição
        pagina_edicao = QWidget()
        ve = QVBoxLayout(pagina_edicao)
        ve.setContentsMargins(0, 0, 0, 0)
        ve.setSpacing(8)
        form = QFormLayout()
        form.addRow("Nº", self.tv_codigo)
        form.addRow("Categoria", self.combo_categoria)
        form.addRow("Título", self.et_titulo)
        form.addRow("Link", self.et_link)
        caixa_form = QWidget()
        caixa_form.setLayout(form)
        ve.addWidget(caixa_form)
        ve.addWidget(rotulo("Ingredientes e modo de preparo", "secao"))
        ve.addWidget(self.et_receita, 1)

        acoes = QHBoxLayout()
        for b in (self.btn_salvar, self.btn_deletar, self.btn_abrir_link, self.btn_imprimir, self.btn_limpar):
            acoes.addWidget(b)
        acoes.addStretch(1)
        caixa_acoes = QWidget()
        caixa_acoes.setLayout(acoes)
        ve.addWidget(caixa_acoes)

        self.stack.addWidget(pagina_lista)
        self.stack.addWidget(pagina_edicao)
        layout.addWidget(self.stack, 1)

    def _conectar(self) -> None:
        self.vm.editar_receitas_changed.connect(self._render)
        self.vm.categorias_changed.connect(self._render_categorias)
        self.et_busca_titulo.textChanged.connect(self._debounce.start)
        self.et_busca_ingrediente.textChanged.connect(self._debounce.start)
        self.btn_buscar_cod.clicked.connect(self._buscar_por_cod)
        self.et_busca_cod.returnPressed.connect(self._buscar_por_cod)
        self.lista.receita_escolhida.connect(self.carregar_receita)
        self.btn_salvar.clicked.connect(self._salvar)
        self.btn_deletar.clicked.connect(self._deletar)
        self.btn_limpar.clicked.connect(self.limpar)
        self.btn_abrir_link.clicked.connect(self._abrir_link)
        self.btn_imprimir.clicked.connect(self._imprimir)

    # ── Estado ───────────────────────────────────────────────────────────────

    def _render(self, receitas: list[Receita]) -> None:
        self.lista.submit(receitas, self.vm.nome_categoria)
        self.tv_total.setText(f"{len(receitas)} receita(s)")

    def _render_categorias(self, categorias: list[Categoria]) -> None:
        atual = self.combo_categoria.currentData()
        self.combo_categoria.clear()
        for c in categorias:
            self.combo_categoria.addItem(f"{c.cod_cat} - {c.cat}", c.cod_cat)
        alvo = self.receita_selecionada.cod_cat if self.receita_selecionada else atual
        if alvo is not None:
            idx = self.combo_categoria.findData(alvo)
            if idx >= 0:
                self.combo_categoria.setCurrentIndex(idx)

    def _buscar(self) -> None:
        self.vm.search_editar(self.et_busca_titulo.text(), self.et_busca_ingrediente.text())

    def _buscar_por_cod(self) -> None:
        texto = self.et_busca_cod.text().strip()
        if not texto.isdigit():
            QMessageBox.information(self, "Editar", "Digite o Nº da receita.")
            return

        def resultado(receita: Receita | None) -> None:
            if receita is None:
                QMessageBox.information(self, "Editar", "Nº de receita inexistente.")
                self.et_busca_cod.setFocus()
            else:
                self.carregar_receita(receita)

        self.vm.buscar_por_cod(int(texto), resultado)

    def carregar_receita(self, receita: Receita) -> None:
        self.receita_selecionada = receita
        self.tv_codigo.setText(receita.cod_formatado)
        self._render_categorias(self.vm.categorias)
        self.et_titulo.setText(receita.titulo)
        self.et_receita.setPlainText(receita.receita)
        self.et_link.setText(receita.link or "")
        self.stack.setCurrentIndex(1)

    def limpar(self) -> None:
        self.receita_selecionada = None
        self.et_busca_cod.clear()
        self.tv_codigo.clear()
        self.et_titulo.clear()
        self.et_receita.clear()
        self.et_link.clear()
        self.stack.setCurrentIndex(0)

    # ── Ações ────────────────────────────────────────────────────────────────

    def _receita_do_form(self) -> Receita | None:
        atual = self.receita_selecionada
        if atual is None:
            QMessageBox.information(self, "Editar", "Selecione uma receita primeiro.")
            return None
        cod_cat = self.combo_categoria.currentData()
        return atual.copy(
            cod_cat=int(cod_cat) if cod_cat is not None else atual.cod_cat,
            titulo=self.et_titulo.text().strip(),
            receita=self.et_receita.toPlainText().strip(),
            link=self.et_link.text().strip() or None,
        )

    def _salvar(self) -> None:
        receita = self._receita_do_form()
        if receita is None:
            return
        if not receita.titulo or not receita.receita:
            QMessageBox.information(self, "Editar", "Título e receita são obrigatórios.")
            return
        self.vm.update_receita(receita)
        self.limpar()

    def _deletar(self) -> None:
        atual = self.receita_selecionada
        if atual is None:
            QMessageBox.information(self, "Editar", "Selecione uma receita primeiro.")
            return
        confirma = QMessageBox.question(
            self,
            "Confirmar exclusão",
            f'Deseja realmente DELETAR "{atual.titulo}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirma == QMessageBox.Yes:
            self.vm.delete_receita(atual.cod)
            self.limpar()

    def _abrir_link(self) -> None:
        url = self.et_link.text().strip()
        if url:
            webbrowser.open(url)
        else:
            QMessageBox.information(self, "Editar", "Nenhum link disponível.")

    def _imprimir(self) -> None:
        receita = self._receita_do_form()
        if receita is None:
            return
        try:
            caminho = pdf.gerar_pdf_receita(receita, self.vm.nome_categoria(receita.cod_cat))
            pdf.abrir_arquivo(caminho)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Imprimir", f"Erro ao gerar PDF: {exc}")

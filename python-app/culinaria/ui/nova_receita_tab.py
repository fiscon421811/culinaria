"""Aba "Nova Receita" — cadastro manual e importação por IA (porta de NovaReceitaFragment)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..ai import RecipeAiClient
from ..models import Categoria, Receita, RecipeAiResult, VideoRecipeResult
from ..tasks import run_async
from ..viewmodel import AppViewModel
from .widgets import botao, cabecalho, linha, rotulo


class NovaReceitaTab(QWidget):
    def __init__(self, vm: AppViewModel, ai: RecipeAiClient) -> None:
        super().__init__()
        self.vm = vm
        self.ai = ai
        self._categorias: list[Categoria] = []

        self.et_cod = QLineEdit()
        self.et_cod.setEnabled(False)
        self.combo_categoria = QComboBox()
        self.et_titulo = QLineEdit(placeholderText="Título da receita")
        self.et_receita = QPlainTextEdit(placeholderText="INGREDIENTES\n• …\n\nMODO DE PREPARO\n…")
        self.et_link = QLineEdit(placeholderText="Link do vídeo ou site (opcional)")

        self.btn_importar = botao("IMPORTAR RECEITA COM IA", "ghost")
        self.btn_buscar_video = botao("BUSCAR RECEITAS EM VÍDEO", "ghost")
        self.btn_salvar = botao("SALVAR")
        self.btn_limpar = botao("LIMPAR", "ghost")

        self._montar()
        self._conectar()

    def _montar(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(cabecalho("➕  Nova Receita", "Preencha manualmente ou deixe a IA extrair de um link/vídeo."))

        form = QFormLayout()
        form.setSpacing(8)
        form.addRow("Nº", self.et_cod)
        form.addRow("Categoria", self.combo_categoria)
        form.addRow("Título", self.et_titulo)
        form.addRow("Link", self.et_link)
        caixa = QWidget()
        caixa.setLayout(form)
        layout.addWidget(caixa)

        layout.addWidget(rotulo("Ingredientes e modo de preparo", "secao"))
        layout.addWidget(self.et_receita, 1)

        ia = QHBoxLayout()
        ia.addWidget(self.btn_importar)
        ia.addWidget(self.btn_buscar_video)
        ia.addStretch(1)
        caixa_ia = QWidget()
        caixa_ia.setLayout(ia)
        layout.addWidget(caixa_ia)

        layout.addWidget(linha(self.btn_salvar, self.btn_limpar))

    def _conectar(self) -> None:
        self.vm.categorias_changed.connect(self._render_categorias)
        self.btn_salvar.clicked.connect(self._salvar)
        self.btn_limpar.clicked.connect(self.limpar)
        self.btn_importar.clicked.connect(self._dialog_importar)
        self.btn_buscar_video.clicked.connect(self._dialog_buscar_video)

    def carregar(self) -> None:
        """Chamado ao entrar na aba — recarrega categorias e o próximo Nº."""
        self.vm.refresh_categorias()
        self._atualizar_cod()

    # ── Estado ───────────────────────────────────────────────────────────────

    def _render_categorias(self, categorias: list[Categoria]) -> None:
        self._categorias = list(categorias)
        atual = self.combo_categoria.currentData()
        self.combo_categoria.clear()
        for c in categorias:
            self.combo_categoria.addItem(f"{c.cod_cat} - {c.cat}", c.cod_cat)
        if atual is not None:
            idx = self.combo_categoria.findData(atual)
            if idx >= 0:
                self.combo_categoria.setCurrentIndex(idx)

    def _atualizar_cod(self) -> None:
        self.vm.proximo_cod(lambda cod: self.et_cod.setText(str(cod)))

    def limpar(self) -> None:
        self.et_titulo.clear()
        self.et_receita.clear()
        self.et_link.clear()
        self._atualizar_cod()

    # ── Salvar ───────────────────────────────────────────────────────────────

    def _salvar(self) -> None:
        if self.combo_categoria.currentIndex() < 0:
            QMessageBox.information(self, "Nova receita", "Selecione uma categoria.")
            return
        titulo = self.et_titulo.text().strip()
        corpo = self.et_receita.toPlainText().strip()
        if not titulo or not corpo:
            QMessageBox.information(self, "Nova receita", "Título e modo de preparo são obrigatórios.")
            return
        try:
            cod = int(self.et_cod.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Nova receita", "Nº inválido. Aguarde o carregamento.")
            return

        self.vm.insert_receita(
            Receita(
                cod=cod,
                cod_cat=int(self.combo_categoria.currentData()),
                titulo=titulo,
                receita=corpo,
                link=self.et_link.text().strip() or None,
            )
        )
        self.limpar()

    # ── IA: importar de link ─────────────────────────────────────────────────

    def _dialog_importar(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("IMPORTAR RECEITA COM IA")
        dialog.setMinimumWidth(520)
        layout = QVBoxLayout(dialog)
        layout.addWidget(rotulo("A IA extrai ingredientes e modo de preparo. Revise antes de salvar.", "subtitulo", wrap=True))
        link = QLineEdit(placeholderText="Cole o link de uma receita, site ou vídeo")
        contexto = QPlainTextEdit(placeholderText="Legenda ou transcrição (opcional)")
        contexto.setFixedHeight(90)
        layout.addWidget(link)
        layout.addWidget(contexto)
        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Ok).setText("IMPORTAR")
        botoes.button(QDialogButtonBox.Cancel).setText("CANCELAR")
        botoes.accepted.connect(dialog.accept)
        botoes.rejected.connect(dialog.reject)
        layout.addWidget(botoes)

        if dialog.exec() != QDialog.Accepted:
            return
        url = link.text().strip()
        if not url:
            QMessageBox.information(self, "Importar", "Cole um link para continuar.")
            return
        self._extrair(url, contexto.toPlainText().strip() or None)

    def _extrair(self, url: str, contexto: str | None) -> None:
        self.btn_importar.setEnabled(False)
        self.btn_importar.setText("IMPORTANDO…")

        def restaurar() -> None:
            self.btn_importar.setEnabled(True)
            self.btn_importar.setText("IMPORTAR RECEITA COM IA")

        run_async(
            lambda: self.ai.extract_recipe(url, contexto),
            on_ok=lambda r: self._preencher(r, url),
            on_erro=lambda msg: QMessageBox.warning(self, "IA", msg),
            on_fim=restaurar,
        )

    # ── IA: buscar vídeos ────────────────────────────────────────────────────

    def _dialog_buscar_video(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("BUSCAR RECEITAS EM VÍDEO")
        dialog.setMinimumWidth(480)
        layout = QVBoxLayout(dialog)
        layout.addWidget(rotulo("Pesquise vídeos públicos de receitas na internet.", "subtitulo", wrap=True))
        query = QLineEdit(placeholderText="Ex.: lasanha de berinjela")
        layout.addWidget(query)
        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Ok).setText("BUSCAR")
        botoes.button(QDialogButtonBox.Cancel).setText("CANCELAR")
        botoes.accepted.connect(dialog.accept)
        botoes.rejected.connect(dialog.reject)
        layout.addWidget(botoes)

        if dialog.exec() != QDialog.Accepted:
            return
        termo = query.text().strip()
        if not termo:
            QMessageBox.information(self, "Buscar", "Digite o nome de uma receita.")
            return

        self.btn_buscar_video.setEnabled(False)
        self.btn_buscar_video.setText("BUSCANDO VÍDEOS…")

        def restaurar() -> None:
            self.btn_buscar_video.setEnabled(True)
            self.btn_buscar_video.setText("BUSCAR RECEITAS EM VÍDEO")

        run_async(
            lambda: self.ai.search_video_recipes(termo),
            on_ok=self._escolher_video,
            on_erro=lambda msg: QMessageBox.warning(self, "IA", msg),
            on_fim=restaurar,
        )

    def _escolher_video(self, videos: list[VideoRecipeResult]) -> None:
        if not videos:
            QMessageBox.information(self, "Buscar", "Nenhum vídeo de receita foi encontrado. Tente outro termo.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("ESCOLHA UM VÍDEO")
        dialog.setMinimumWidth(560)
        layout = QVBoxLayout(dialog)
        layout.addWidget(rotulo("A IA criará a receita completa e manterá o link do vídeo.", "subtitulo", wrap=True))
        for video in videos:
            b = botao(video.title, "ghost")
            b.clicked.connect(lambda _=False, v=video: (dialog.accept(), self._gerar_do_video(v)))
            layout.addWidget(b)
        layout.addWidget(botao("CANCELAR", "link", dialog.reject))
        dialog.exec()

    def _gerar_do_video(self, video: VideoRecipeResult) -> None:
        self.btn_buscar_video.setEnabled(False)
        self.btn_buscar_video.setText("CRIANDO RECEITA…")

        def restaurar() -> None:
            self.btn_buscar_video.setEnabled(True)
            self.btn_buscar_video.setText("BUSCAR RECEITAS EM VÍDEO")

        run_async(
            lambda: self.ai.generate_seasonal_recipe(
                video.title, "Receita em vídeo", "Receita encontrada na internet",
                "Seleção do usuário", video.url,
            ),
            on_ok=lambda r: self._preencher(r, video.url),
            on_erro=lambda msg: QMessageBox.warning(self, "IA", msg),
            on_fim=restaurar,
        )

    # ── Preenchimento a partir da IA ─────────────────────────────────────────

    def _preencher(self, resultado: RecipeAiResult, url: str) -> None:
        self.et_titulo.setText(resultado.titulo.upper())
        self.et_receita.setPlainText(resultado.to_texto())
        self.et_link.setText(url)
        QMessageBox.information(self, "IA", "Receita importada. Escolha a categoria e salve.")

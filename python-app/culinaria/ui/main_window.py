"""Janela principal com as abas (porta de MainActivity + bottom_navigation)."""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QProgressBar, QStatusBar, QTabWidget

from ..ai import RecipeAiClient
from ..viewmodel import AppViewModel
from .backup_tab import BackupTab
from .cardapio_tab import CardapioTab
from .categorias_tab import CategoriasTab
from .editar_tab import EditarTab
from .nova_receita_tab import NovaReceitaTab
from .receitas_tab import ReceitasTab


class MainWindow(QMainWindow):
    def __init__(self, vm: AppViewModel | None = None, ai: RecipeAiClient | None = None) -> None:
        super().__init__()
        self.vm = vm or AppViewModel()
        self.ai = ai or RecipeAiClient()

        self.setWindowTitle("Culinária — Livro de Receitas")
        self.resize(1060, 760)

        self.tabs = QTabWidget()
        self.aba_receitas = ReceitasTab(self.vm)
        self.aba_cardapio = CardapioTab(self.vm, self.ai)
        self.aba_nova = NovaReceitaTab(self.vm, self.ai)
        self.aba_editar = EditarTab(self.vm)
        self.aba_categorias = CategoriasTab(self.vm)
        self.aba_backup = BackupTab(self.vm)

        self.tabs.addTab(self.aba_receitas, "📖  Receitas")
        self.tabs.addTab(self.aba_cardapio, "🗓️  Cardápio")
        self.tabs.addTab(self.aba_nova, "➕  Nova")
        self.tabs.addTab(self.aba_editar, "✏️  Editar")
        self.tabs.addTab(self.aba_categorias, "🏷️  Categorias")
        self.tabs.addTab(self.aba_backup, "💾  Backup")
        self.setCentralWidget(self.tabs)

        self.progresso = QProgressBar()
        self.progresso.setRange(0, 0)
        self.progresso.setFixedWidth(120)
        self.progresso.setVisible(False)
        barra = QStatusBar()
        barra.addPermanentWidget(self.progresso)
        self.setStatusBar(barra)

        self.vm.loading_changed.connect(self.progresso.setVisible)
        self.vm.mensagem.connect(lambda m: barra.showMessage(f"✅  {m}", 6000))
        self.vm.erro.connect(lambda m: barra.showMessage(f"⚠️  {m}", 10000))
        self.tabs.currentChanged.connect(self._ao_trocar_aba)

        self.vm.carregar_tudo()

    def _ao_trocar_aba(self, indice: int) -> None:
        alvo = self.tabs.widget(indice)
        if alvo is self.aba_nova:
            self.aba_nova.carregar()
        elif alvo is self.aba_backup:
            self.aba_backup.atualizar_status()

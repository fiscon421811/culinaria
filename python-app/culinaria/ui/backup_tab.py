"""Aba "Backup" — exportar e restaurar o Livro de Receitas."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import backup, config
from ..backup import BackupData, ResultadoRestauracao
from ..planner import MealPlannerStore
from ..tasks import run_async
from ..viewmodel import AppViewModel
from .widgets import botao, cabecalho, card, rotulo

PALAVRA_CONFIRMACAO = "SUBSTITUIR"


class BackupTab(QWidget):
    def __init__(self, vm: AppViewModel) -> None:
        super().__init__()
        self.vm = vm
        self.store = MealPlannerStore()

        self.btn_json = botao("EXPORTAR JSON")
        self.btn_sqlite = botao("EXPORTAR SQLITE")
        self.btn_restaurar = botao("RESTAURAR DE ARQUIVO…", "danger")
        self.btn_pasta = botao("ABRIR PASTA DE BACKUPS", "ghost")
        self.tv_status = rotulo("", "subtitulo", wrap=True)

        self._montar()
        self._conectar()
        self.atualizar_status()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _montar(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(
            cabecalho(
                "💾  Backup e Restauração",
                "Salve uma cópia completa das receitas, categorias e do cardápio escolhido.",
            )
        )

        exportar = QHBoxLayout()
        exportar.addWidget(self.btn_json)
        exportar.addWidget(self.btn_sqlite)
        exportar.addStretch(1)
        caixa_exportar = QWidget()
        caixa_exportar.setLayout(exportar)

        layout.addWidget(
            card(
                rotulo("Exportar", "secao"),
                rotulo(
                    "JSON é legível e fácil de versionar; SQLite é compacto e abre em "
                    "qualquer ferramenta de banco. Os dois guardam exatamente o mesmo conteúdo.",
                    "subtitulo",
                    wrap=True,
                ),
                caixa_exportar,
            )
        )

        restaurar = QHBoxLayout()
        restaurar.addWidget(self.btn_restaurar)
        restaurar.addStretch(1)
        caixa_restaurar = QWidget()
        caixa_restaurar.setLayout(restaurar)

        layout.addWidget(
            card(
                rotulo("Restaurar", "secao"),
                rotulo(
                    "⚠️  A restauração APAGA todas as receitas e categorias do Turso e grava "
                    "o conteúdo do arquivo. Antes de apagar, o app exporta automaticamente "
                    "um backup do estado atual — então nada é perdido sem rede de segurança.",
                    "subtitulo",
                    wrap=True,
                ),
                caixa_restaurar,
            )
        )

        pasta = QHBoxLayout()
        pasta.addWidget(self.btn_pasta)
        pasta.addStretch(1)
        caixa_pasta = QWidget()
        caixa_pasta.setLayout(pasta)

        layout.addWidget(card(rotulo("Situação", "secao"), self.tv_status, caixa_pasta))
        layout.addStretch(1)

    def _conectar(self) -> None:
        self.btn_json.clicked.connect(lambda: self._exportar(".json"))
        self.btn_sqlite.clicked.connect(lambda: self._exportar(".db"))
        self.btn_restaurar.clicked.connect(self._restaurar)
        self.btn_pasta.clicked.connect(self._abrir_pasta)
        self.vm.home_receitas_changed.connect(lambda _: self.atualizar_status())

    # ── Situação ─────────────────────────────────────────────────────────────

    def atualizar_status(self) -> None:
        linhas = [
            f"No banco agora: {len(self.vm.home_receitas)} receita(s), "
            f"{len(self.vm.categorias)} categoria(s).",
            f"Pasta de backups: {config.BACKUP_DIR}",
        ]
        ultimo = self._ultimo_backup()
        linhas.append(
            f"Último backup: {ultimo.name} — {backup.formatar_data(_iso_mtime(ultimo))}"
            if ultimo
            else "Último backup: nenhum ainda."
        )
        self.tv_status.setText("\n".join(linhas))

    @staticmethod
    def _ultimo_backup() -> Path | None:
        if not config.BACKUP_DIR.is_dir():
            return None
        arquivos = [
            p
            for p in config.BACKUP_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in (backup.EXTENSOES_JSON | backup.EXTENSOES_SQLITE)
        ]
        return max(arquivos, key=lambda p: p.stat().st_mtime, default=None)

    def _abrir_pasta(self) -> None:
        config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        caminho = str(config.BACKUP_DIR)
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", caminho])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho])

    # ── Exportar ─────────────────────────────────────────────────────────────

    def _exportar(self, extensao: str) -> None:
        filtro = (
            "Backup JSON (*.json)" if extensao == ".json" else "Banco SQLite (*.db *.sqlite)"
        )
        sugerido = backup.caminho_padrao(extensao)
        escolhido, _ = QFileDialog.getSaveFileName(
            self, "Salvar backup", str(sugerido), filtro
        )
        if not escolhido:
            return
        destino = Path(escolhido)
        if not destino.suffix:
            destino = destino.with_suffix(extensao)

        self._travar(True)

        def acao() -> Path:
            dados = backup.coletar(self.vm.repo, self.store)
            return backup.exportar(dados, destino)

        run_async(
            acao,
            on_ok=self._exportado,
            on_erro=lambda msg: QMessageBox.warning(self, "Backup", msg),
            on_fim=lambda: self._travar(False),
        )

    def _exportado(self, caminho: Path) -> None:
        tamanho = caminho.stat().st_size / 1024
        self.atualizar_status()
        self.vm.mensagem.emit(f"Backup salvo: {caminho.name} ({tamanho:.0f} KB)")
        QMessageBox.information(
            self, "Backup criado", f"Arquivo salvo em:\n{caminho}\n\nTamanho: {tamanho:.0f} KB"
        )

    # ── Restaurar ────────────────────────────────────────────────────────────

    def _restaurar(self) -> None:
        escolhido, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher backup",
            str(config.BACKUP_DIR if config.BACKUP_DIR.is_dir() else Path.home()),
            "Backups (*.json *.db *.sqlite *.sqlite3);;Todos os arquivos (*)",
        )
        if not escolhido:
            return

        self._travar(True)
        run_async(
            lambda: backup.ler_backup(Path(escolhido)),
            on_ok=lambda dados: self._confirmar(Path(escolhido), dados),
            on_erro=lambda msg: QMessageBox.warning(self, "Restaurar", msg),
            on_fim=lambda: self._travar(False),
        )

    def _confirmar(self, origem: Path, dados: BackupData) -> None:
        if not dados.receitas and not dados.categorias:
            QMessageBox.warning(self, "Restaurar", "O backup está vazio — nada a restaurar.")
            return

        avisos = backup.validar(dados)
        if not PreviaDialog(origem, dados, avisos, self).exec():
            return

        # Segunda confirmação: digitar a palavra.
        digitado, ok = QInputDialog.getText(
            self,
            "Confirmação final",
            f"Isto vai APAGAR as {len(self.vm.home_receitas)} receita(s) e "
            f"{len(self.vm.categorias)} categoria(s) que estão no Turso agora.\n\n"
            f"Para confirmar, digite {PALAVRA_CONFIRMACAO}:",
            QLineEdit.Normal,
            "",
        )
        if not ok or digitado.strip().upper() != PALAVRA_CONFIRMACAO:
            self.vm.mensagem.emit("Restauração cancelada — nada foi alterado.")
            return

        self._travar(True)
        run_async(
            lambda: backup.substituir_tudo(self.vm.repo, dados, self.store),
            on_ok=self._restaurado,
            on_erro=self._falha_restauracao,
            on_fim=lambda: self._travar(False),
        )

    def _restaurado(self, resultado: ResultadoRestauracao) -> None:
        self.vm.carregar_tudo()
        self.atualizar_status()
        QMessageBox.information(self, "Restauração concluída", resultado.resumo())

    def _falha_restauracao(self, mensagem: str) -> None:
        self.vm.carregar_tudo()
        QMessageBox.critical(
            self,
            "Falha na restauração",
            f"{mensagem}\n\nO backup automático do estado anterior está em:\n"
            f"{config.BACKUP_DIR}\n\nVerifique a aba Receitas antes de tentar de novo.",
        )

    def _travar(self, ocupado: bool) -> None:
        for b in (self.btn_json, self.btn_sqlite, self.btn_restaurar):
            b.setEnabled(not ocupado)


class PreviaDialog(QDialog):
    """Primeira confirmação: mostra o que há no arquivo e o que será perdido."""

    def __init__(
        self,
        origem: Path,
        dados: BackupData,
        avisos: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Confirmar restauração")
        self.setMinimumWidth(620)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(rotulo(origem.name, "titulo", wrap=True))
        layout.addWidget(rotulo(dados.resumo(), "subtitulo", wrap=True))

        amostra = QPlainTextEdit()
        amostra.setReadOnly(True)
        amostra.setFixedHeight(150)
        linhas = [f"Categorias: {', '.join(c.cat for c in dados.categorias[:12]) or '—'}", ""]
        linhas += [f"{r.cod_formatado}  {r.titulo}" for r in dados.receitas[:12]]
        if len(dados.receitas) > 12:
            linhas.append(f"… e mais {len(dados.receitas) - 12} receita(s)")
        amostra.setPlainText("\n".join(linhas))
        layout.addWidget(amostra)

        if avisos:
            layout.addWidget(
                rotulo("⚠️  " + "\n⚠️  ".join(avisos), "subtitulo", wrap=True)
            )

        layout.addWidget(
            rotulo(
                "Ao continuar, tudo que está no Turso é apagado e substituído por este "
                "arquivo. Um backup do estado atual será gravado automaticamente antes.",
                "subtitulo",
                wrap=True,
            )
        )

        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Ok).setText("CONTINUAR")
        botoes.button(QDialogButtonBox.Cancel).setText("CANCELAR")
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)


def _iso_mtime(caminho: Path) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(caminho.stat().st_mtime).astimezone().isoformat()

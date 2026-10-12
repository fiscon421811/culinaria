"""Ponto de entrada do app Culinária (versão Python/PySide6)."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from culinaria.ui.main_window import MainWindow
from culinaria.ui.style import QSS


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Culinária")
    app.setOrganizationName("Culinária")
    app.setStyleSheet(QSS)

    # Ícone da janela (dentro do .exe os arquivos extras ficam em sys._MEIPASS).
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    for nome in ("icone.ico", "rceita.ico", "receita.ico"):
        icone = base / nome
        if icone.exists():
            app.setWindowIcon(QIcon(str(icone)))
            break

    janela = MainWindow()
    janela.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

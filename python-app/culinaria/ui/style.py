"""Paleta e folha de estilo (portadas de res/values/colors.xml)."""

PRIMARY = "#FF6B35"
PRIMARY_DARK = "#E55A2B"
PRIMARY_LIGHT = "#FF8C42"
BACKGROUND = "#FFF8F0"
SURFACE = "#FFFFFF"
TEXT_PRIMARY = "#212121"
TEXT_SECONDARY = "#757575"
DELETE_RED = "#F44336"
BORDER = "#F0DCC8"

QSS = f"""
QWidget {{
    background: {BACKGROUND};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}}

QLabel#titulo {{
    font-size: 20px;
    font-weight: 700;
    color: {PRIMARY_DARK};
}}
QLabel#subtitulo {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
QLabel#contador {{
    color: {PRIMARY_DARK};
    font-weight: 600;
}}
QLabel#secao {{
    font-weight: 700;
    color: {TEXT_PRIMARY};
    padding-top: 6px;
}}

QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: {PRIMARY_LIGHT};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {PRIMARY};
}}
QLineEdit:disabled {{
    background: #F5EFE8;
    color: {TEXT_SECONDARY};
}}

QPushButton {{
    background: {PRIMARY};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {PRIMARY_LIGHT}; }}
QPushButton:pressed {{ background: {PRIMARY_DARK}; }}
QPushButton:disabled {{ background: #E4D5C6; color: #9E9E9E; }}

QPushButton[variant="ghost"] {{
    background: {SURFACE};
    color: {PRIMARY_DARK};
    border: 1px solid {PRIMARY};
}}
QPushButton[variant="ghost"]:hover {{ background: #FFF0E6; }}

QPushButton[variant="danger"] {{ background: {DELETE_RED}; }}
QPushButton[variant="danger"]:hover {{ background: #E53935; }}

QPushButton[variant="link"] {{
    background: transparent;
    color: {PRIMARY_DARK};
    border: none;
    padding: 4px 0;
    text-align: left;
    font-weight: 600;
}}
QPushButton[variant="link"]:hover {{ color: {PRIMARY}; text-decoration: underline; }}

QTabWidget::pane {{
    border: none;
    background: {BACKGROUND};
}}
QTabBar::tab {{
    background: {SURFACE};
    color: {TEXT_SECONDARY};
    padding: 10px 18px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {PRIMARY};
    color: white;
}}

QListWidget, QTableWidget {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 4px;
}}
QListWidget::item {{
    border-bottom: 1px solid #F7EDE3;
    padding: 8px 6px;
}}
QListWidget::item:selected {{
    background: #FFEFE3;
    color: {TEXT_PRIMARY};
}}

QFrame#card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#faixa {{
    background: {PRIMARY};
    border-radius: 12px;
}}
QLabel#faixaTitulo {{ color: white; font-size: 16px; font-weight: 700; }}
QLabel#faixaTexto {{ color: #FFE7D6; font-size: 12px; }}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #E8CDB6; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QStatusBar {{ background: {SURFACE}; color: {TEXT_SECONDARY}; }}
QProgressBar {{
    border: none; background: #F0E2D3; border-radius: 3px; height: 6px; text-align: center;
}}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 3px; }}
"""

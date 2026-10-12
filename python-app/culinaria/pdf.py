"""Geração de PDF de receitas (equivalente a util/PrintHelper.kt)."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as pdf_canvas

from . import config
from .models import Receita

PAGE_W, PAGE_H = A4  # 595 x 842 pt, como no Android
MARGIN = 40.0
HEADER_H = 70.0

COR_PRIMARIA = HexColor("#E65100")
COR_TEXTO = HexColor("#212121")
COR_SECUNDARIO = HexColor("#757575")
COR_LINK = HexColor("#1565C0")
COR_FAIXA = HexColor("#FFF3E0")
COR_SUBTITULO = HexColor("#FFCC80")
COR_DIVISOR = HexColor("#E0E0E0")

FONTE = "Helvetica"
FONTE_BOLD = "Helvetica-Bold"


def data_atual() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _sanitize(texto: str) -> str:
    """Helvetica não cobre emojis; troca os usados no app por texto."""
    return (
        (texto or "")
        .replace("🔗", "Link:")
        .replace("🍳", "-")
        .replace("🍛", "-")
        .replace("🥗", "-")
    )


def quebrar_linhas(texto: str, larg_max: float, fonte: str, tamanho: float) -> list[str]:
    """Word wrap preservando parágrafos, como quebrarLinhas do Kotlin."""
    resultado: list[str] = []
    for paragrafo in _sanitize(texto).split("\n"):
        if not paragrafo.strip():
            resultado.append("")
            continue
        linha = ""
        for palavra in paragrafo.split(" "):
            teste = palavra if not linha else f"{linha} {palavra}"
            if stringWidth(teste, fonte, tamanho) <= larg_max:
                linha = teste
            else:
                if linha:
                    resultado.append(linha)
                linha = palavra
        if linha:
            resultado.append(linha)
    return resultado


class _Documento:
    """Wrapper de canvas com controle de página e coordenada Y "de cima para baixo"."""

    def __init__(self, caminho: Path) -> None:
        self.c = pdf_canvas.Canvas(str(caminho), pagesize=A4)
        self.pagina = 1
        self.y = MARGIN

    # Converte Y "topo" (estilo Android) para Y do reportlab (base)
    def _ry(self, y: float) -> float:
        return PAGE_H - y

    def texto(self, s: str, x: float, y: float, fonte: str, tamanho: float, cor) -> None:
        self.c.setFont(fonte, tamanho)
        self.c.setFillColor(cor)
        self.c.drawString(x, self._ry(y), _sanitize(s))

    def texto_direita(self, s: str, x: float, y: float, fonte: str, tamanho: float, cor) -> None:
        self.c.setFont(fonte, tamanho)
        self.c.setFillColor(cor)
        self.c.drawRightString(x, self._ry(y), _sanitize(s))

    def linha(self, x1: float, y: float, x2: float, cor, largura: float = 1.0) -> None:
        self.c.setStrokeColor(cor)
        self.c.setLineWidth(largura)
        self.c.line(x1, self._ry(y), x2, self._ry(y))

    def retangulo(self, x: float, y: float, w: float, h: float, cor) -> None:
        self.c.setFillColor(cor)
        self.c.rect(x, self._ry(y + h), w, h, stroke=0, fill=1)

    def caixa_arredondada(self, x: float, y: float, w: float, h: float, r: float,
                          fundo=None, borda=None, largura_borda: float = 1.0) -> None:
        if fundo is not None:
            self.c.setFillColor(fundo)
        if borda is not None:
            self.c.setStrokeColor(borda)
            self.c.setLineWidth(largura_borda)
        self.c.roundRect(
            x, self._ry(y + h), w, h, r,
            stroke=1 if borda is not None else 0,
            fill=1 if fundo is not None else 0,
        )

    def nova_pagina(self, com_rodape: bool = True) -> None:
        if com_rodape:
            self.rodape()
        self.c.showPage()
        self.pagina += 1
        self.y = MARGIN

    def cabecalho(self, titulo: str, subtitulo: str) -> float:
        self.retangulo(0, 0, PAGE_W, HEADER_H, COR_PRIMARIA)
        self.texto(titulo, MARGIN, 36, FONTE_BOLD, 20, white)
        self.texto(subtitulo, MARGIN, 55, FONTE, 11, COR_SUBTITULO)
        return HEADER_H + 10

    def badge(self, texto: str, x: float, y: float) -> float:
        largura = stringWidth(texto, FONTE_BOLD, 9) + 16
        self.caixa_arredondada(x, y, largura, 20, 10, fundo=COR_FAIXA, borda=COR_PRIMARIA)
        self.texto(texto, x + 8, y + 14, FONTE_BOLD, 9, COR_PRIMARIA)
        return y + 22

    def rodape(self) -> None:
        self.linha(MARGIN, PAGE_H - 30, PAGE_W - MARGIN, COR_PRIMARIA)
        self.texto(f"Livro de Receitas  |  {data_atual()}", MARGIN, PAGE_H - 16, FONTE, 9, COR_SECUNDARIO)
        self.texto_direita(f"Pág. {self.pagina}", PAGE_W - MARGIN, PAGE_H - 16, FONTE, 9, COR_SECUNDARIO)

    def salvar(self) -> None:
        self.rodape()
        self.c.save()


def _destino(nome: str) -> Path:
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    seguro = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in nome)
    return config.PDF_DIR / f"{seguro}.pdf"


def gerar_pdf_receita(receita: Receita, nome_categoria: str | None = None) -> Path:
    """PDF de uma receita — layout do gerarPdfReceita original."""
    caminho = _destino(f"Receita_{receita.cod}")
    doc = _Documento(caminho)

    doc.y = doc.cabecalho("Livro de Receitas", f"Receita Nº {receita.cod_formatado}") + 20

    for linha in quebrar_linhas(receita.titulo, PAGE_W - MARGIN * 2, FONTE_BOLD, 18):
        doc.texto(linha, MARGIN, doc.y + 18, FONTE_BOLD, 18, COR_PRIMARIA)
        doc.y += 25
    doc.y += 6

    doc.linha(MARGIN, doc.y, PAGE_W - MARGIN, COR_PRIMARIA, 1.5)
    doc.y += 12

    doc.badge(f"Cód. {receita.cod}", MARGIN, doc.y)
    doc.y = doc.badge(nome_categoria or f"Categoria {receita.cod_cat}", MARGIN + 110, doc.y) + 16

    for linha in quebrar_linhas(receita.receita, PAGE_W - MARGIN * 2, FONTE, 12):
        if doc.y + 18 > PAGE_H - MARGIN - 20:
            doc.nova_pagina()
        doc.texto(linha, MARGIN, doc.y + 12, FONTE, 12, COR_TEXTO)
        doc.y += 18

    if receita.link:
        doc.y += 12
        for linha in quebrar_linhas(f"🔗 {receita.link}", PAGE_W - MARGIN * 2, FONTE, 10):
            if doc.y + 14 > PAGE_H - MARGIN - 20:
                doc.nova_pagina()
            doc.texto(linha, MARGIN, doc.y + 10, FONTE, 10, COR_LINK)
            doc.y += 14

    doc.salvar()
    return caminho


def gerar_pdf_lista(receitas: list[Receita], titulo: str = "Livro de Receitas") -> Path:
    """PDF com a lista completa — layout do gerarPdfLista original."""
    caminho = _destino(titulo.replace(" ", "_"))
    doc = _Documento(caminho)
    doc.y = doc.cabecalho(titulo, f"{len(receitas)} receita(s) — {data_atual()}") + 20

    for receita in receitas:
        if doc.y + 50 > PAGE_H - MARGIN - 20:
            doc.nova_pagina()

        doc.caixa_arredondada(MARGIN, doc.y, PAGE_W - MARGIN * 2, 28, 6,
                              fundo=COR_FAIXA, borda=COR_PRIMARIA, largura_borda=2)
        doc.texto(receita.cod_formatado, MARGIN + 8, doc.y + 19, FONTE_BOLD, 13, COR_PRIMARIA)
        doc.texto(receita.titulo[:70], MARGIN + 52, doc.y + 19, FONTE_BOLD, 13, COR_TEXTO)
        doc.texto_direita(f"Cat.{receita.cod_cat}", PAGE_W - MARGIN - 8, doc.y + 19, FONTE, 9, COR_SECUNDARIO)
        doc.y += 34

        for linha in quebrar_linhas(receita.receita, PAGE_W - MARGIN * 2, FONTE, 11):
            if doc.y + 15 > PAGE_H - MARGIN - 20:
                doc.nova_pagina()
            doc.texto(linha, MARGIN, doc.y + 11, FONTE, 11, COR_TEXTO)
            doc.y += 15

        if receita.link:
            doc.y += 4
            doc.texto(f"🔗 {receita.link}", MARGIN, doc.y + 9, FONTE, 9, COR_LINK)
            doc.y += 14

        doc.y += 6
        doc.linha(MARGIN, doc.y, PAGE_W - MARGIN, COR_DIVISOR)
        doc.y += 12

    doc.salvar()
    return caminho


def abrir_arquivo(caminho: Path) -> None:
    """Abre o PDF no visualizador padrão do sistema."""
    if sys.platform.startswith("win"):
        os.startfile(str(caminho))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(caminho)])
    else:
        subprocess.Popen(["xdg-open", str(caminho)])

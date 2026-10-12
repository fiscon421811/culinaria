"""Modelos de domínio (equivalentes a model/Receita.kt e model/Categoria.kt)."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional


@dataclass(frozen=True, slots=True)
class Categoria:
    id: int = 0
    cod_cat: int = 0
    cat: str = ""

    def copy(self, **kwargs) -> "Categoria":
        return replace(self, **kwargs)

    def __str__(self) -> str:  # usado nos combos "1 - Bolos"
        return f"{self.cod_cat} - {self.cat}"


@dataclass(frozen=True, slots=True)
class Receita:
    id: int = 0
    cod: int = 0
    cod_cat: int = 0
    titulo: str = ""
    receita: str = ""
    link: Optional[str] = None
    nome_categoria: str = ""

    def copy(self, **kwargs) -> "Receita":
        return replace(self, **kwargs)

    @property
    def cod_formatado(self) -> str:
        return str(self.cod).zfill(3)


@dataclass(frozen=True, slots=True)
class Ingrediente:
    nome: str = ""
    quantidade: str = ""


@dataclass(frozen=True, slots=True)
class RecipeAiResult:
    """Resposta da IA (equivalente a RecipeAiResponse)."""

    titulo: str = ""
    ingredientes: list[Ingrediente] = field(default_factory=list)
    modo_preparo: Optional[str] = None
    video_url: Optional[str] = None

    def to_texto(self, rodape: str | None = None) -> str:
        """Formata o corpo da receita como o app Android faz."""
        partes = ["INGREDIENTES"]
        partes.append("\n".join(f"• {i.quantidade} {i.nome}".strip() for i in self.ingredientes))
        if self.modo_preparo and self.modo_preparo.strip():
            partes.append("\nMODO DE PREPARO\n" + self.modo_preparo.strip())
        if self.video_url and self.video_url.strip():
            partes.append("\nVÍDEO\n" + self.video_url.strip())
        if rodape:
            partes.append("\n" + rodape)
        return "\n".join(partes)

    @classmethod
    def from_json(cls, data: dict) -> "RecipeAiResult":
        return cls(
            titulo=data.get("titulo") or "",
            ingredientes=[
                Ingrediente(nome=i.get("nome", ""), quantidade=i.get("quantidade", ""))
                for i in (data.get("ingredientes") or [])
            ],
            modo_preparo=data.get("modoPreparo"),
            video_url=data.get("videoUrl"),
        )


@dataclass(frozen=True, slots=True)
class VideoRecipeResult:
    title: str = ""
    url: str = ""

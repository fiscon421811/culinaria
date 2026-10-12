"""Repositório de receitas e categorias (equivalente a ReceitaRepository + AppRepository)."""
from __future__ import annotations

import re
import threading
import unicodedata
from typing import Optional

from .models import Categoria, Receita
from .turso import TursoClient, TursoError, as_int, as_str

SELECT_RECEITAS = """
SELECT r.ID, r.Cod, r.CodCat, r.Titulo, r.Receita, r.Link, c.Cat AS nomeCategoria
FROM receitas r
LEFT JOIN categorias c ON r.CodCat = c.CodCat
""".strip()

_COMBINING = re.compile(r"[̀-ͯ]")


def normalizar(valor: str) -> str:
    """Remove acentos e normaliza caixa — mesma lógica de normalizeForSearch."""
    decomposto = unicodedata.normalize("NFD", valor or "")
    return _COMBINING.sub("", decomposto).lower()


class AppRepository:
    """Acesso a dados com cache em memória, como no app Android."""

    def __init__(self, client: TursoClient | None = None) -> None:
        self._db = client or TursoClient()
        self._lock = threading.RLock()
        self._cache_categorias: Optional[list[Categoria]] = None
        self._cache_receitas: Optional[list[Receita]] = None

    @property
    def db(self) -> TursoClient:
        """Acesso direto ao cliente — usado pelo módulo de backup."""
        return self._db

    def invalidar_cache(self) -> None:
        """Descarta os caches de receitas e categorias."""
        self._invalidar_receitas()
        self._invalidar_categorias()

    # ── Categorias ───────────────────────────────────────────────────────────

    def get_all_categorias(self, force_refresh: bool = False) -> list[Categoria]:
        with self._lock:
            if not force_refresh and self._cache_categorias is not None:
                return list(self._cache_categorias)

        rows = self._db.query("SELECT CodCat, Cat FROM categorias ORDER BY Cat")
        categorias = [
            Categoria(
                id=as_int(row.get("CodCat")),
                cod_cat=as_int(row.get("CodCat")),
                cat=as_str(row.get("Cat")),
            )
            for row in rows
        ]
        with self._lock:
            self._cache_categorias = categorias
        return list(categorias)

    def get_max_cod_cat(self) -> int:
        return max((c.cod_cat for c in self.get_all_categorias()), default=0)

    def get_next_cod_cat(self) -> int:
        return self.get_max_cod_cat() + 1

    def insert_categoria(self, categoria: Categoria) -> None:
        self._db.execute(
            "INSERT INTO categorias (CodCat, Cat) VALUES (?, ?)",
            [categoria.cod_cat, categoria.cat],
        )
        self._invalidar_categorias()

    def update_categoria(self, categoria: Categoria) -> None:
        self._db.execute(
            "UPDATE categorias SET Cat = ? WHERE CodCat = ?",
            [categoria.cat, categoria.cod_cat],
        )
        self._invalidar_categorias()

    def delete_categoria(self, categoria: Categoria) -> None:
        em_uso = self._db.query(
            "SELECT COUNT(*) AS total FROM receitas WHERE CodCat = ?", [categoria.cod_cat]
        )
        total = as_int(em_uso[0].get("total")) if em_uso else 0
        if total:
            raise TursoError(
                f'A categoria "{categoria.cat}" possui {total} receita(s) e não pode ser excluída.'
            )
        self._db.execute("DELETE FROM categorias WHERE CodCat = ?", [categoria.cod_cat])
        self._invalidar_categorias()

    def nome_categoria(self, cod_cat: int) -> str:
        for categoria in self.get_all_categorias():
            if categoria.cod_cat == cod_cat:
                return categoria.cat
        return f"Categoria {cod_cat}"

    # ── Receitas ─────────────────────────────────────────────────────────────

    def get_all_receitas(self, force_refresh: bool = False) -> list[Receita]:
        with self._lock:
            if not force_refresh and self._cache_receitas is not None:
                return list(self._cache_receitas)

        rows = self._db.query(f"{SELECT_RECEITAS}\nORDER BY r.ID DESC")
        receitas = [self._to_receita(row) for row in rows]
        with self._lock:
            self._cache_receitas = receitas
        return list(receitas)

    def search(self, titulo: str = "", ingrediente: str = "") -> list[Receita]:
        alvo_titulo = normalizar(titulo).strip()
        alvo_ingrediente = normalizar(ingrediente).strip()
        if not alvo_titulo and not alvo_ingrediente:
            return self.get_all_receitas()

        return [
            r
            for r in self.get_all_receitas()
            if (not alvo_titulo or alvo_titulo in normalizar(r.titulo))
            and (not alvo_ingrediente or alvo_ingrediente in normalizar(r.receita))
        ]

    def get_by_categoria(self, cod_cat: int) -> list[Receita]:
        rows = self._db.query(
            f"{SELECT_RECEITAS}\nWHERE r.CodCat = ?\nORDER BY r.Titulo", [cod_cat]
        )
        return [self._to_receita(row) for row in rows]

    def get_by_cod(self, cod: int) -> Optional[Receita]:
        for receita in self.get_all_receitas():
            if receita.cod == cod:
                return receita
        rows = self._db.query(f"{SELECT_RECEITAS}\nWHERE r.Cod = ? LIMIT 1", [cod])
        return self._to_receita(rows[0]) if rows else None

    def get_by_link(self, link: str) -> Optional[Receita]:
        rows = self._db.query(f"{SELECT_RECEITAS}\nWHERE r.Link = ? LIMIT 1", [link])
        return self._to_receita(rows[0]) if rows else None

    def get_max_cod(self) -> int:
        rows = self._db.query("SELECT COALESCE(MAX(Cod), 0) AS maxCod FROM receitas")
        return as_int(rows[0].get("maxCod")) if rows else 0

    def get_next_cod(self) -> int:
        return self.get_max_cod() + 1

    def titulo_existe(self, titulo: str) -> bool:
        alvo = normalizar(titulo).strip()
        return any(normalizar(r.titulo).strip() == alvo for r in self.get_all_receitas())

    def insert_receita(self, receita: Receita) -> None:
        self._db.execute(
            "INSERT INTO receitas (Cod, CodCat, Titulo, Receita, Link) VALUES (?, ?, ?, ?, ?)",
            [receita.cod, receita.cod_cat, receita.titulo, receita.receita, receita.link or ""],
        )
        self._invalidar_receitas()

    def update_receita(self, receita: Receita) -> None:
        self._db.execute(
            "UPDATE receitas SET CodCat = ?, Titulo = ?, Receita = ?, Link = ? WHERE ID = ?",
            [
                receita.cod_cat,
                receita.titulo,
                receita.receita,
                receita.link or "",
                receita.id,
            ],
        )
        self._invalidar_receitas()

    def delete_receita_por_cod(self, cod: int) -> None:
        receita = self.get_by_cod(cod)
        if receita is None:
            raise TursoError(f"Receita nº {cod} não encontrada.")
        self._db.execute("DELETE FROM receitas WHERE ID = ?", [receita.id])
        self._invalidar_receitas()

    # ── Internos ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_receita(row: dict) -> Receita:
        link = as_str(row.get("Link"))
        return Receita(
            id=as_int(row.get("ID")),
            cod=as_int(row.get("Cod")),
            cod_cat=as_int(row.get("CodCat")),
            titulo=as_str(row.get("Titulo")),
            receita=as_str(row.get("Receita")),
            link=link or None,
            nome_categoria=as_str(row.get("nomeCategoria")),
        )

    def _invalidar_receitas(self) -> None:
        with self._lock:
            self._cache_receitas = None

    def _invalidar_categorias(self) -> None:
        with self._lock:
            self._cache_categorias = None

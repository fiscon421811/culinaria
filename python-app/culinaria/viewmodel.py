"""Estado compartilhado da UI (equivalente a viewmodel/AppViewModel.kt)."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .models import Categoria, Receita
from .repository import AppRepository
from .tasks import run_async


class AppViewModel(QObject):
    """Publica listas de receitas/categorias e centraliza as operações de dados."""

    home_receitas_changed = Signal(list)
    editar_receitas_changed = Signal(list)
    categorias_changed = Signal(list)
    loading_changed = Signal(bool)
    erro = Signal(str)
    mensagem = Signal(str)

    def __init__(self, repository: AppRepository | None = None) -> None:
        super().__init__()
        self.repo = repository or AppRepository()
        self._home: list[Receita] = []
        self._editar: list[Receita] = []
        self._categorias: list[Categoria] = []
        self._pendentes = 0

    # ── Acesso sincrono ao último valor publicado ────────────────────────────

    @property
    def home_receitas(self) -> list[Receita]:
        return list(self._home)

    @property
    def editar_receitas(self) -> list[Receita]:
        return list(self._editar)

    @property
    def categorias(self) -> list[Categoria]:
        return list(self._categorias)

    def nome_categoria(self, cod_cat: int) -> str:
        for c in self._categorias:
            if c.cod_cat == cod_cat:
                return c.cat
        return f"Categoria {cod_cat}"

    # ── Carga ────────────────────────────────────────────────────────────────

    def carregar_tudo(self) -> None:
        self._io(
            lambda: (self.repo.get_all_receitas(force_refresh=True), self.repo.get_all_categorias(True)),
            self._publicar_tudo,
        )

    def recarregar_receitas(self) -> None:
        self._io(lambda: self.repo.get_all_receitas(force_refresh=True), self._publicar_receitas)

    def refresh_categorias(self, depois=None) -> None:
        def publicar(cats: list[Categoria]) -> None:
            self._publicar_categorias(cats)
            if depois:
                depois(cats)

        self._io(lambda: self.repo.get_all_categorias(force_refresh=True), publicar)

    # ── Receitas ─────────────────────────────────────────────────────────────

    def search_home(self, titulo: str, ingrediente: str) -> None:
        self._io(lambda: self.repo.search(titulo, ingrediente), self._publicar_home)

    def search_editar(self, titulo: str, ingrediente: str) -> None:
        self._io(lambda: self.repo.search(titulo, ingrediente), self._publicar_editar)

    def filtrar_por_categoria(self, cod_cat: int) -> None:
        self._io(lambda: self.repo.get_by_categoria(cod_cat), self._publicar_home)

    def mostrar_todas(self) -> None:
        self._io(lambda: self.repo.get_all_receitas(), self._publicar_home)

    def insert_receita(self, receita: Receita, aviso: str = "Receita salva com sucesso!") -> None:
        def acao() -> list[Receita]:
            self.repo.insert_receita(receita)
            return self.repo.get_all_receitas(force_refresh=True)

        self._io(acao, self._publicar_receitas, aviso)

    def update_receita(self, receita: Receita, aviso: str = "Receita atualizada!") -> None:
        def acao() -> list[Receita]:
            self.repo.update_receita(receita)
            return self.repo.get_all_receitas(force_refresh=True)

        self._io(acao, self._publicar_receitas, aviso)

    def delete_receita(self, cod: int, aviso: str = "Receita excluída.") -> None:
        def acao() -> list[Receita]:
            self.repo.delete_receita_por_cod(cod)
            return self.repo.get_all_receitas(force_refresh=True)

        self._io(acao, self._publicar_receitas, aviso)

    # ── Categorias ───────────────────────────────────────────────────────────

    def insert_categoria(self, categoria: Categoria, aviso: str = "Categoria adicionada!") -> None:
        def acao() -> list[Categoria]:
            self.repo.insert_categoria(categoria)
            return self.repo.get_all_categorias(force_refresh=True)

        self._io(acao, self._publicar_categorias, aviso)

    def update_categoria(self, categoria: Categoria, aviso: str = "Categoria atualizada!") -> None:
        def acao() -> list[Categoria]:
            self.repo.update_categoria(categoria)
            return self.repo.get_all_categorias(force_refresh=True)

        self._io(acao, self._publicar_categorias, aviso)

    def delete_categoria(self, categoria: Categoria, aviso: str = "Categoria excluída.") -> None:
        def acao() -> list[Categoria]:
            self.repo.delete_categoria(categoria)
            return self.repo.get_all_categorias(force_refresh=True)

        self._io(acao, self._publicar_categorias, aviso)

    # ── Auxiliares assíncronos ───────────────────────────────────────────────

    def proximo_cod(self, callback) -> None:
        self._io(self.repo.get_next_cod, callback)

    def proximo_cod_cat(self, callback) -> None:
        self._io(self.repo.get_next_cod_cat, callback)

    def buscar_por_cod(self, cod: int, callback) -> None:
        self._io(lambda: self.repo.get_by_cod(cod), callback)

    def buscar_por_link(self, link: str, callback) -> None:
        self._io(lambda: self.repo.get_by_link(link), callback)

    # ── Publicação ───────────────────────────────────────────────────────────

    def _publicar_tudo(self, dados) -> None:
        receitas, categorias = dados
        self._publicar_receitas(receitas)
        self._publicar_categorias(categorias)

    def _publicar_receitas(self, receitas: list[Receita]) -> None:
        self._publicar_home(receitas)
        self._publicar_editar(receitas)

    def _publicar_home(self, receitas: list[Receita]) -> None:
        self._home = list(receitas)
        self.home_receitas_changed.emit(self._home)

    def _publicar_editar(self, receitas: list[Receita]) -> None:
        self._editar = list(receitas)
        self.editar_receitas_changed.emit(self._editar)

    def _publicar_categorias(self, categorias: list[Categoria]) -> None:
        self._categorias = list(categorias)
        self.categorias_changed.emit(self._categorias)

    def _io(self, acao, on_ok=None, aviso: str | None = None) -> None:
        self._marcar(1)

        def ok(resultado) -> None:
            if on_ok:
                on_ok(resultado)
            if aviso:
                self.mensagem.emit(aviso)

        run_async(
            acao,
            on_ok=ok,
            on_erro=lambda msg: self.erro.emit(msg),
            on_fim=lambda: self._marcar(-1),
        )

    def _marcar(self, delta: int) -> None:
        antes = self._pendentes > 0
        self._pendentes = max(0, self._pendentes + delta)
        agora = self._pendentes > 0
        if antes != agora:
            self.loading_changed.emit(agora)

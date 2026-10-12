"""Backup e restauração do Livro de Receitas.

Exporta receitas, categorias e o cardápio semanal em JSON (legível) ou SQLite
(compacto). A restauração substitui todo o conteúdo do banco Turso, sempre
gravando um backup de segurança antes.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from . import config
from .models import Categoria, Receita
from .planner import MealPlannerState, MealPlannerStore, PlannedMeal
from .repository import AppRepository
from .turso import as_int, as_str

VERSAO_BACKUP = 1
APP = "Culinaria"

EXTENSOES_JSON = {".json"}
EXTENSOES_SQLITE = {".db", ".sqlite", ".sqlite3"}
MAGICO_SQLITE = b"SQLite format 3\x00"

# Acima disso o restore é dividido em lotes e perde a atomicidade.
LIMITE_LOTE_BYTES = 700_000


class BackupError(RuntimeError):
    """Arquivo de backup inválido ou falha ao exportar/restaurar."""


@dataclass(slots=True)
class BackupData:
    """Conteúdo de um arquivo de backup."""

    categorias: list[Categoria] = field(default_factory=list)
    receitas: list[Receita] = field(default_factory=list)
    cardapio: MealPlannerState | None = None
    gerado_em: str = ""
    origem: str = ""
    versao: int = VERSAO_BACKUP

    def resumo(self) -> str:
        quando = formatar_data(self.gerado_em)
        linhas = [
            f"Gerado em: {quando}",
            f"Categorias: {len(self.categorias)}",
            f"Receitas: {len(self.receitas)}",
        ]
        if self.cardapio and self.cardapio.menu:
            linhas.append(f"Cardápio salvo: {self.cardapio.menu}")
        if self.origem:
            linhas.append(f"Origem: {self.origem}")
        return "\n".join(linhas)


# ── Nomes de arquivo ────────────────────────────────────────────────────────


def agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def formatar_data(iso: str) -> str:
    if not iso:
        return "desconhecido"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


def nome_sugerido(extensao: str, prefixo: str = "culinaria-backup") -> str:
    return f"{prefixo}-{datetime.now().strftime('%Y-%m-%d_%H%M%S')}{extensao}"


def caminho_padrao(extensao: str, prefixo: str = "culinaria-backup") -> Path:
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return config.BACKUP_DIR / nome_sugerido(extensao, prefixo)


# ── Coleta ──────────────────────────────────────────────────────────────────


def coletar(repo: AppRepository, store: MealPlannerStore | None = None) -> BackupData:
    """Lê o estado atual do Turso (sem cache) e o cardápio salvo em disco."""
    return BackupData(
        categorias=repo.get_all_categorias(force_refresh=True),
        receitas=repo.get_all_receitas(force_refresh=True),
        cardapio=(store or MealPlannerStore()).load(),
        gerado_em=agora_iso(),
        origem=config.TURSO_BASE_URL,
    )


# ── Exportação ──────────────────────────────────────────────────────────────


def exportar_json(dados: BackupData, destino: Path) -> Path:
    payload = {
        "app": APP,
        "versao_backup": dados.versao,
        "gerado_em": dados.gerado_em or agora_iso(),
        "origem": dados.origem,
        "totais": {"categorias": len(dados.categorias), "receitas": len(dados.receitas)},
        "categorias": [
            {"CodCat": c.cod_cat, "Cat": c.cat} for c in dados.categorias
        ],
        "receitas": [
            {
                "ID": r.id,
                "Cod": r.cod,
                "CodCat": r.cod_cat,
                "Titulo": r.titulo,
                "Receita": r.receita,
                "Link": r.link,
            }
            for r in dados.receitas
        ],
        "cardapio": _cardapio_para_json(dados.cardapio),
    }
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def exportar_sqlite(dados: BackupData, destino: Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()

    conexao = sqlite3.connect(destino)
    try:
        conexao.executescript(
            """
            CREATE TABLE categorias (
                CodCat INTEGER PRIMARY KEY,
                Cat    TEXT NOT NULL
            );
            CREATE TABLE receitas (
                ID      INTEGER PRIMARY KEY,
                Cod     INTEGER,
                CodCat  INTEGER,
                Titulo  TEXT,
                Receita TEXT,
                Link    TEXT
            );
            CREATE TABLE backup_meta (
                chave TEXT PRIMARY KEY,
                valor TEXT
            );
            """
        )
        conexao.executemany(
            "INSERT INTO categorias (CodCat, Cat) VALUES (?, ?)",
            [(c.cod_cat, c.cat) for c in dados.categorias],
        )
        conexao.executemany(
            "INSERT INTO receitas (ID, Cod, CodCat, Titulo, Receita, Link) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (r.id, r.cod, r.cod_cat, r.titulo, r.receita, r.link)
                for r in dados.receitas
            ],
        )
        conexao.executemany(
            "INSERT INTO backup_meta (chave, valor) VALUES (?, ?)",
            [
                ("app", APP),
                ("versao_backup", str(dados.versao)),
                ("gerado_em", dados.gerado_em or agora_iso()),
                ("origem", dados.origem),
                ("cardapio", json.dumps(_cardapio_para_json(dados.cardapio), ensure_ascii=False)),
            ],
        )
        conexao.commit()
    finally:
        conexao.close()
    return destino


def exportar(dados: BackupData, destino: Path) -> Path:
    """Escolhe o formato pela extensão do arquivo."""
    destino = Path(destino)
    sufixo = destino.suffix.lower()
    if sufixo in EXTENSOES_SQLITE:
        return exportar_sqlite(dados, destino)
    if sufixo in EXTENSOES_JSON:
        return exportar_json(dados, destino)
    raise BackupError(f"Extensão não suportada: {sufixo or '(sem extensão)'}")


# ── Leitura ─────────────────────────────────────────────────────────────────


def detectar_formato(origem: Path) -> str:
    origem = Path(origem)
    if not origem.is_file():
        raise BackupError(f"Arquivo não encontrado: {origem}")
    with origem.open("rb") as f:
        if f.read(16) == MAGICO_SQLITE:
            return "sqlite"
    sufixo = origem.suffix.lower()
    if sufixo in EXTENSOES_JSON:
        return "json"
    if sufixo in EXTENSOES_SQLITE:
        raise BackupError("O arquivo tem extensão de SQLite mas não é um banco válido.")
    return "json"  # tenta JSON como último recurso


def ler_backup(origem: Path) -> BackupData:
    formato = detectar_formato(origem)
    return _ler_sqlite(Path(origem)) if formato == "sqlite" else _ler_json(Path(origem))


def _ler_json(origem: Path) -> BackupData:
    try:
        payload = json.loads(origem.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise BackupError("O arquivo não é um backup de texto válido.") from exc
    except json.JSONDecodeError as exc:
        raise BackupError(f"JSON inválido (linha {exc.lineno}): {exc.msg}") from exc
    if not isinstance(payload, dict) or "receitas" not in payload:
        raise BackupError("Este JSON não parece ser um backup do Culinária.")

    return BackupData(
        categorias=[_categoria(c) for c in payload.get("categorias") or []],
        receitas=[_receita(r) for r in payload.get("receitas") or []],
        cardapio=_cardapio_de_json(payload.get("cardapio")),
        gerado_em=as_str(payload.get("gerado_em")),
        origem=as_str(payload.get("origem")),
        versao=as_int(payload.get("versao_backup"), VERSAO_BACKUP),
    )


def _ler_sqlite(origem: Path) -> BackupData:
    conexao = sqlite3.connect(f"file:{origem}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        tabelas = {
            row["name"]
            for row in conexao.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "receitas" not in tabelas:
            raise BackupError("Este banco não contém a tabela 'receitas'.")

        categorias = (
            [_categoria(dict(r)) for r in conexao.execute("SELECT CodCat, Cat FROM categorias")]
            if "categorias" in tabelas
            else []
        )
        receitas = [
            _receita(dict(r))
            for r in conexao.execute(
                "SELECT ID, Cod, CodCat, Titulo, Receita, Link FROM receitas"
            )
        ]
        meta: dict[str, str] = {}
        if "backup_meta" in tabelas:
            meta = {
                r["chave"]: r["valor"]
                for r in conexao.execute("SELECT chave, valor FROM backup_meta")
            }
    except sqlite3.DatabaseError as exc:
        raise BackupError(f"Não foi possível ler o banco: {exc}") from exc
    finally:
        conexao.close()

    cardapio = None
    if meta.get("cardapio"):
        try:
            cardapio = _cardapio_de_json(json.loads(meta["cardapio"]))
        except json.JSONDecodeError:
            cardapio = None

    return BackupData(
        categorias=categorias,
        receitas=receitas,
        cardapio=cardapio,
        gerado_em=meta.get("gerado_em", ""),
        origem=meta.get("origem", ""),
        versao=as_int(meta.get("versao_backup"), VERSAO_BACKUP),
    )


# ── Validação ───────────────────────────────────────────────────────────────


def validar(dados: BackupData) -> list[str]:
    """Avisos que não impedem a restauração, mas o usuário deve saber."""
    avisos: list[str] = []
    if dados.versao > VERSAO_BACKUP:
        avisos.append(
            f"O backup é da versão {dados.versao} e este app entende até a {VERSAO_BACKUP}."
        )
    if not dados.receitas:
        avisos.append("O backup não tem nenhuma receita.")
    if not dados.categorias:
        avisos.append("O backup não tem nenhuma categoria.")

    cods = [c.cod_cat for c in dados.categorias]
    if len(cods) != len(set(cods)):
        avisos.append("Há categorias com CodCat repetido; a última prevalece.")

    conhecidos = set(cods)
    orfas = sorted({r.cod_cat for r in dados.receitas if r.cod_cat not in conhecidos})
    if orfas:
        avisos.append(
            f"{len(orfas)} categoria(s) referenciada(s) por receitas não existem no backup: "
            f"{', '.join(map(str, orfas[:8]))}. Serão criadas automaticamente."
        )

    receita_cods = [r.cod for r in dados.receitas]
    if len(receita_cods) != len(set(receita_cods)):
        avisos.append("Há receitas com o mesmo Nº (Cod) — o app usa esse número para busca.")
    return avisos


def completar_categorias(dados: BackupData) -> BackupData:
    """Cria categorias-fantasma para CodCat citados por receitas mas ausentes."""
    conhecidos = {c.cod_cat for c in dados.categorias}
    faltando = sorted({r.cod_cat for r in dados.receitas if r.cod_cat not in conhecidos})
    if not faltando:
        return dados
    extras = [Categoria(id=cod, cod_cat=cod, cat=f"Categoria {cod}") for cod in faltando]
    dados.categorias = [*dados.categorias, *extras]
    return dados


# ── Restauração ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ResultadoRestauracao:
    categorias: int = 0
    receitas: int = 0
    atomico: bool = True
    backup_seguranca: Path | None = None

    def resumo(self) -> str:
        texto = f"{self.receitas} receita(s) e {self.categorias} categoria(s) restauradas."
        if self.backup_seguranca:
            texto += f"\nBackup de segurança: {self.backup_seguranca}"
        if not self.atomico:
            texto += "\n(Enviado em lotes por causa do tamanho.)"
        return texto


def substituir_tudo(
    repo: AppRepository,
    dados: BackupData,
    store: MealPlannerStore | None = None,
    fazer_backup_seguranca: bool = True,
    restaurar_cardapio: bool = True,
) -> ResultadoRestauracao:
    """Apaga receitas e categorias do Turso e grava o conteúdo do backup.

    Antes de apagar, exporta o estado atual para `BACKUP_DIR` (rede de segurança).
    """
    resultado = ResultadoRestauracao()

    if fazer_backup_seguranca:
        atual = coletar(repo, store)
        resultado.backup_seguranca = exportar_json(
            atual, caminho_padrao(".json", "antes-de-restaurar")
        )

    dados = completar_categorias(dados)

    comandos: list[tuple[str, Sequence[Any] | None]] = [
        ("DELETE FROM receitas", None),
        ("DELETE FROM categorias", None),
    ]
    for c in dados.categorias:
        comandos.append(("INSERT INTO categorias (CodCat, Cat) VALUES (?, ?)", [c.cod_cat, c.cat]))
    for r in dados.receitas:
        comandos.append(
            (
                "INSERT INTO receitas (Cod, CodCat, Titulo, Receita, Link) VALUES (?, ?, ?, ?, ?)",
                [r.cod, r.cod_cat, r.titulo, r.receita, r.link or ""],
            )
        )

    cabe_em_um_lote = repo.db.tamanho_estimado(comandos) <= LIMITE_LOTE_BYTES
    if cabe_em_um_lote:
        repo.db.batch(comandos, transacao=True)
    else:
        for lote in _dividir(comandos, LIMITE_LOTE_BYTES, repo.db.tamanho_estimado):
            repo.db.batch(lote, transacao=False)
    resultado.atomico = cabe_em_um_lote

    resultado.categorias = len(dados.categorias)
    resultado.receitas = len(dados.receitas)
    repo.invalidar_cache()

    if restaurar_cardapio and dados.cardapio is not None:
        (store or MealPlannerStore()).save(dados.cardapio)

    return resultado


def _dividir(comandos, limite: int, medir) -> list[list]:
    """Quebra os comandos em lotes, mantendo os DELETE no primeiro."""
    lotes: list[list] = []
    atual: list = []
    for comando in comandos:
        atual.append(comando)
        if medir(atual) >= limite:
            lotes.append(atual)
            atual = []
    if atual:
        lotes.append(atual)
    return lotes


# ── Conversores ─────────────────────────────────────────────────────────────


def _categoria(row: dict[str, Any]) -> Categoria:
    cod = as_int(row.get("CodCat", row.get("cod_cat")))
    return Categoria(id=cod, cod_cat=cod, cat=as_str(row.get("Cat", row.get("cat"))))


def _receita(row: dict[str, Any]) -> Receita:
    link = as_str(row.get("Link", row.get("link")))
    return Receita(
        id=as_int(row.get("ID", row.get("id"))),
        cod=as_int(row.get("Cod", row.get("cod"))),
        cod_cat=as_int(row.get("CodCat", row.get("cod_cat"))),
        titulo=as_str(row.get("Titulo", row.get("titulo"))),
        receita=as_str(row.get("Receita", row.get("receita"))),
        link=link or None,
    )


def _cardapio_para_json(estado: MealPlannerState | None) -> dict[str, Any]:
    if estado is None:
        return {"menu": None, "meals": {}}
    return {
        "menu": estado.menu,
        "meals": {
            dia: [{"title": m.title, "recipe": m.recipe, "link": m.link} for m in itens]
            for dia, itens in estado.meals.items()
        },
    }


def _cardapio_de_json(payload: Any) -> MealPlannerState | None:
    if not isinstance(payload, dict):
        return None
    meals: dict[str, list[PlannedMeal]] = {}
    for dia, itens in (payload.get("meals") or {}).items():
        lista = itens if isinstance(itens, list) else [itens]
        meals[dia] = [
            PlannedMeal(
                title=as_str(i.get("title")),
                recipe=as_str(i.get("recipe")),
                link=i.get("link"),
            )
            for i in lista
            if isinstance(i, dict)
        ]
    return MealPlannerState(menu=payload.get("menu"), meals=meals)

"""Cliente HTTP do Turso (equivalente a TursoClient + TursoApiService + TursoModels)."""
from __future__ import annotations

from typing import Any, Iterable, Sequence

import requests

from . import config


class TursoError(RuntimeError):
    """Erro devolvido pela API do Turso ou pela rede."""


class TursoClient:
    """Executa SQL via endpoint /v2/pipeline do Turso."""

    def __init__(
        self,
        base_url: str = config.TURSO_BASE_URL,
        auth_token: str = config.TURSO_AUTH_TOKEN,
        timeout: float = config.HTTP_TIMEOUT,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/v2/pipeline"
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }
        )

    # ── API pública ──────────────────────────────────────────────────────────

    def query(self, sql: str, args: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        """Executa um SELECT e devolve linhas como dicionários."""
        payload = {
            "requests": [
                {"type": "execute", "stmt": self._stmt(sql, args)},
                {"type": "close"},
            ]
        }
        body = self._post(payload)
        return self._rows(body)

    def execute(self, sql: str, args: Sequence[Any] | None = None) -> int:
        """Executa INSERT/UPDATE/DELETE e devolve o número de linhas afetadas."""
        payload = {
            "requests": [
                {"type": "execute", "stmt": self._stmt(sql, args)},
                {"type": "close"},
            ]
        }
        body = self._post(payload)
        for result in body.get("results", []):
            resp = result.get("response") or {}
            inner = resp.get("result") or {}
            if "affected_row_count" in inner:
                return int(inner["affected_row_count"])
        return 0

    def batch(
        self,
        comandos: Sequence[tuple[str, Sequence[Any] | None]],
        transacao: bool = False,
    ) -> int:
        """Executa vários comandos numa única requisição (mesma conexão).

        Com `transacao=True` envolve tudo em BEGIN/COMMIT — só é atômico porque
        o pipeline inteiro roda na mesma conexão do Turso.
        Devolve a soma das linhas afetadas.
        """
        if not comandos:
            return 0

        requests_: list[dict[str, Any]] = []
        if transacao:
            requests_.append({"type": "execute", "stmt": {"sql": "BEGIN"}})
        for sql, args in comandos:
            requests_.append({"type": "execute", "stmt": self._stmt(sql, args)})
        if transacao:
            requests_.append({"type": "execute", "stmt": {"sql": "COMMIT"}})
        requests_.append({"type": "close"})

        try:
            body = self._post({"requests": requests_})
        except TursoError:
            if transacao:
                # Melhor esforço para não deixar a conexão presa numa transação.
                try:
                    self._post(
                        {"requests": [{"type": "execute", "stmt": {"sql": "ROLLBACK"}},
                                      {"type": "close"}]}
                    )
                except TursoError:
                    pass
            raise

        total = 0
        for result in body.get("results", []):
            inner = (result.get("response") or {}).get("result") or {}
            total += int(inner.get("affected_row_count") or 0)
        return total

    @staticmethod
    def tamanho_estimado(comandos: Sequence[tuple[str, Sequence[Any] | None]]) -> int:
        """Bytes aproximados do payload — usado para decidir se cabe num lote só."""
        total = 0
        for sql, args in comandos:
            total += len(sql.encode("utf-8")) + 40
            for a in args or ():
                total += len(str(a).encode("utf-8")) + 40
        return total

    def close(self) -> None:
        self._session.close()

    # ── Internos ─────────────────────────────────────────────────────────────

    @staticmethod
    def _stmt(sql: str, args: Sequence[Any] | None) -> dict[str, Any]:
        stmt: dict[str, Any] = {"sql": sql}
        if args:
            stmt["args"] = [TursoClient._arg(a) for a in args]
        return stmt

    @staticmethod
    def _arg(value: Any) -> dict[str, Any]:
        if value is None:
            return {"type": "null", "value": None}
        if isinstance(value, bool):
            return {"type": "integer", "value": "1" if value else "0"}
        if isinstance(value, int):
            return {"type": "integer", "value": str(value)}
        if isinstance(value, float):
            return {"type": "float", "value": value}
        if isinstance(value, (bytes, bytearray)):
            import base64

            return {"type": "blob", "base64": base64.b64encode(value).decode()}
        return {"type": "text", "value": str(value)}

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._session.post(self._url, json=payload, timeout=self._timeout)
        except requests.Timeout as exc:
            raise TursoError("O banco demorou para responder. Tente novamente.") from exc
        except requests.ConnectionError as exc:
            raise TursoError("Sem acesso ao banco. Verifique sua conexão.") from exc

        if response.status_code in (401, 403):
            raise TursoError(
                "O banco recusou o acesso (erro %d). Confira TURSO_AUTH_TOKEN e "
                "TURSO_BASE_URL no arquivo .env da pasta python-app." % response.status_code
            )
        if response.status_code >= 400:
            raise TursoError(f"Erro {response.status_code} ao acessar o banco.")

        body = response.json()
        for result in body.get("results", []):
            if result.get("type") == "error" or result.get("error"):
                erro = result.get("error") or {}
                raise TursoError(erro.get("message", "Erro desconhecido no Turso."))
        return body

    @staticmethod
    def _rows(body: dict[str, Any]) -> list[dict[str, Any]]:
        linhas: list[dict[str, Any]] = []
        for result in body.get("results", []):
            resp = result.get("response") or {}
            if resp.get("type") != "execute":
                continue
            inner = resp.get("result") or {}
            cols = [c.get("name") for c in inner.get("cols", [])]
            for row in inner.get("rows", []):
                linhas.append(
                    {col: TursoClient._value(cell) for col, cell in zip(cols, row)}
                )
        return linhas

    @staticmethod
    def _value(cell: Any) -> Any:
        if not isinstance(cell, dict):
            return cell
        tipo, valor = cell.get("type"), cell.get("value")
        if tipo == "null":
            return None
        if tipo == "integer":
            try:
                return int(valor)
            except (TypeError, ValueError):
                return None
        if tipo == "float":
            try:
                return float(valor)
            except (TypeError, ValueError):
                return None
        return valor


def as_int(value: Any, default: int = 0) -> int:
    """Conversão tolerante como no parse do Kotlin."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def as_str(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


def first(items: Iterable[Any]) -> Any | None:
    return next(iter(items), None)

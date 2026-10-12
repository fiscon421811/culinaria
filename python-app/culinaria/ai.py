"""Cliente do serviço de IA (equivalente a RecipeAiService/RecipeAiClient)."""
from __future__ import annotations

import requests

from . import config
from .models import RecipeAiResult, VideoRecipeResult


class AiError(RuntimeError):
    """Falha ao acessar ou interpretar a resposta da IA."""


class RecipeAiClient:
    def __init__(
        self,
        base_url: str = config.MEAL_AI_BASE_URL,
        timeout: float = config.AI_TIMEOUT,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers["Content-Type"] = "application/json"

    # ── Endpoints ────────────────────────────────────────────────────────────

    def extract_recipe(self, url: str, contexto: str | None = None) -> RecipeAiResult:
        """POST /extract-recipe — lê uma receita de um link público."""
        payload = {"url": url}
        if contexto:
            payload["context"] = contexto
        return RecipeAiResult.from_json(self._post("extract-recipe", payload))

    def generate_seasonal_recipe(
        self,
        titulo: str,
        estacao: str,
        refeicao: str,
        dia: str,
        video_url: str | None = None,
    ) -> RecipeAiResult:
        """POST /generate-seasonal-recipe — gera a receita completa de uma sugestão."""
        payload = {"title": titulo, "season": estacao, "meal": refeicao, "day": dia}
        if video_url:
            payload["videoUrl"] = video_url
        resultado = RecipeAiResult.from_json(self._post("generate-seasonal-recipe", payload))
        if video_url and not resultado.video_url:
            resultado = RecipeAiResult(
                titulo=resultado.titulo,
                ingredientes=resultado.ingredientes,
                modo_preparo=resultado.modo_preparo,
                video_url=video_url,
            )
        return resultado

    def search_video_recipes(self, query: str) -> list[VideoRecipeResult]:
        """POST /search-video-recipes — busca vídeos públicos de receitas."""
        data = self._post("search-video-recipes", {"query": query})
        return [
            VideoRecipeResult(title=item.get("title", ""), url=item.get("url", ""))
            for item in (data.get("results") or [])
            if item.get("url")
        ]

    def health(self) -> bool:
        try:
            response = self._session.get(f"{self._base}/health", timeout=10)
            return response.ok
        except requests.RequestException:
            return False

    # ── Internos ─────────────────────────────────────────────────────────────

    def _post(self, path: str, payload: dict) -> dict:
        try:
            response = self._session.post(
                f"{self._base}/{path}", json=payload, timeout=self._timeout
            )
        except requests.Timeout as exc:
            raise AiError("A IA demorou para responder. Tente novamente.") from exc
        except requests.ConnectionError as exc:
            raise AiError("Sem acesso ao servidor de IA. Verifique sua conexão.") from exc
        except requests.RequestException as exc:
            raise AiError(f"Falha ao acessar a IA: {exc}") from exc

        if not response.ok:
            mensagem = "Não foi possível ler esse link público."
            try:
                corpo = response.json()
                mensagem = corpo.get("error") or mensagem
            except ValueError:
                pass
            raise AiError(mensagem)

        try:
            return response.json()
        except ValueError as exc:
            raise AiError("A IA devolveu uma resposta inválida.") from exc

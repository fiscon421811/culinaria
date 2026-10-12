"""Execução em background sem travar a UI (equivalente a viewModelScope + Dispatchers.IO)."""
from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _Sinais(QObject):
    ok = Signal(object)
    erro = Signal(str)
    fim = Signal()


class _Tarefa(QRunnable):
    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self._fn = fn
        self.sinais = _Sinais()

    @Slot()
    def run(self) -> None:  # pragma: no cover - executa em thread do pool
        try:
            resultado = self._fn()
        except Exception as exc:  # noqa: BLE001 - repassa a mensagem para a UI
            self.sinais.erro.emit(str(exc) or exc.__class__.__name__)
        else:
            self.sinais.ok.emit(resultado)
        finally:
            self.sinais.fim.emit()


_ativas: set[_Tarefa] = set()


def run_async(
    fn: Callable[[], Any],
    on_ok: Callable[[Any], None] | None = None,
    on_erro: Callable[[str], None] | None = None,
    on_fim: Callable[[], None] | None = None,
) -> None:
    """Roda `fn` no pool de threads e devolve o resultado na thread da UI."""
    tarefa = _Tarefa(fn)
    # O Qt destrói o QRunnable ao terminar; guardamos a referência até os sinais
    # em fila serem entregues na thread da UI.
    tarefa.setAutoDelete(False)
    _ativas.add(tarefa)

    if on_ok:
        tarefa.sinais.ok.connect(on_ok)
    if on_erro:
        tarefa.sinais.erro.connect(on_erro)
    if on_fim:
        tarefa.sinais.fim.connect(on_fim)
    tarefa.sinais.fim.connect(lambda t=tarefa: _ativas.discard(t))

    QThreadPool.globalInstance().start(tarefa)


def aguardar(timeout_ms: int = 30_000) -> bool:
    """Espera as tarefas em andamento — útil em testes."""
    return QThreadPool.globalInstance().waitForDone(timeout_ms)

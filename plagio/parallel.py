"""Versão paralela: processos comparam linhas da matriz de pares e registram
os matches numa área de memória compartilhada.

Processos (e não threads) porque a comparação é limitada por CPU e o GIL impediria o ganho.

Três granularidades de lock, para medir o custo de cada uma (ver ROW_STRATEGIES):
todas dão o mesmo resultado; o que muda é quanto tempo os processos passam esperando.
"""
import contextlib
import multiprocessing
from types import SimpleNamespace

from plagio.similarity import jaccard

MAX_MATCHES = 5_000_000

# Preenchido em cada processo filho por _init_worker; com "fork" os dados grandes
# (shingle_sets) são herdados por copy-on-write em vez de serializados para cada filho.
_worker = SimpleNamespace()


def find_similar_pairs(shingle_sets, threshold, processes=None, use_lock=True, strategy="record"):
    """`strategy` escolhe onde o lock é adquirido (ver ROW_STRATEGIES).
    `use_lock=False` existe só para demonstrar a condição de corrida; nunca use em produção."""
    if strategy not in ROW_STRATEGIES:
        raise ValueError(f"estratégia desconhecida: {strategy!r}; use uma de {sorted(ROW_STRATEGIES)}")

    ctx = multiprocessing.get_context("fork")
    count = ctx.Value("i", 0)
    slots = ctx.RawArray("i", 2 * MAX_MATCHES)
    init_args = (shingle_sets, threshold, count, slots, use_lock, strategy)

    with ctx.Pool(processes, _init_worker, init_args) as pool:
        # A linha 0 tem n-1 pares e a última tem 0: entregar uma linha por vez, da maior
        # para a menor, deixa os processos livres pegarem a próxima e equilibra a carga.
        pool.map(_run_row, range(len(shingle_sets)), chunksize=1)

    return {(slots[2 * k], slots[2 * k + 1]) for k in range(count.value)}


def _init_worker(shingle_sets, threshold, count, slots, use_lock, strategy):
    _worker.shingle_sets = shingle_sets
    _worker.threshold = threshold
    _worker.count = count
    _worker.slots = slots
    _worker.lock = count.get_lock() if use_lock else contextlib.nullcontext()
    _worker.compare_row = ROW_STRATEGIES[strategy]


def _run_row(i):
    _worker.compare_row(i)


def _similar_pairs_in_row(i):
    """Só compara; não toca em estado compartilhado. É a parte que deve rodar em paralelo."""
    shingle_sets, threshold = _worker.shingle_sets, _worker.threshold
    for j in range(i + 1, len(shingle_sets)):
        if jaccard(shingle_sets[i], shingle_sets[j]) >= threshold:
            yield i, j


def _append_match(i, j):
    """Seção crítica: ler o contador, gravar no slot e incrementar precisa ser atômico.
    Quem chama já deve estar segurando o lock. Cada acesso a count.value já é protegido
    individualmente; o que não é atômico é a sequência inteira."""
    slot = _worker.count.value
    if slot >= MAX_MATCHES:
        raise OverflowError(f"mais de {MAX_MATCHES} matches; aumente MAX_MATCHES")
    _worker.slots[2 * slot] = i
    _worker.slots[2 * slot + 1] = j
    _worker.count.value = slot + 1


def _row_record(i):
    """Lock só em volta de cada registro. Seção crítica mínima, mas um lock por match."""
    for pair in _similar_pairs_in_row(i):
        with _worker.lock:
            _append_match(*pair)


def _row_whole_loop(i):
    """Lock em volta da linha inteira, comparações incluídas. Correto, mas os processos
    se revezam para comparar: o trabalho paralelizável vira serial."""
    with _worker.lock:
        for pair in _similar_pairs_in_row(i):
            _append_match(*pair)


def _row_local_merge(i):
    """Compara sem lock, guarda os matches da linha localmente e pega o lock uma vez por linha."""
    pairs = list(_similar_pairs_in_row(i))
    with _worker.lock:
        for pair in pairs:
            _append_match(*pair)


ROW_STRATEGIES = {
    "record": _row_record,
    "whole_loop": _row_whole_loop,
    "local_merge": _row_local_merge,
}

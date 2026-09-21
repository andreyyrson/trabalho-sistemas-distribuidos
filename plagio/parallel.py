"""Versão paralela: processos comparam linhas da matriz de pares e registram
os matches numa área de memória compartilhada.

Processos (e não threads) porque a comparação é limitada por CPU e o GIL impediria o ganho.
"""
import contextlib
import multiprocessing
from types import SimpleNamespace

from plagio.similarity import jaccard

MAX_MATCHES = 1_000_000

# Preenchido em cada processo filho por _init_worker; com "fork" os dados grandes
# (shingle_sets) são herdados por copy-on-write em vez de serializados para cada filho.
_worker = SimpleNamespace()


def find_similar_pairs(shingle_sets, threshold, processes=None, use_lock=True):
    """`use_lock=False` existe só para demonstrar a condição de corrida; nunca use em produção."""
    ctx = multiprocessing.get_context("fork")
    count = ctx.Value("i", 0)
    slots = ctx.RawArray("i", 2 * MAX_MATCHES)
    init_args = (shingle_sets, threshold, count, slots, use_lock)

    with ctx.Pool(processes, _init_worker, init_args) as pool:
        # A linha 0 tem n-1 pares e a última tem 0: entregar uma linha por vez, da maior
        # para a menor, deixa os processos livres pegarem a próxima e equilibra a carga.
        pool.map(_compare_row, range(len(shingle_sets)), chunksize=1)

    return {(slots[2 * k], slots[2 * k + 1]) for k in range(count.value)}


def _init_worker(shingle_sets, threshold, count, slots, use_lock):
    _worker.shingle_sets = shingle_sets
    _worker.threshold = threshold
    _worker.count = count
    _worker.slots = slots
    _worker.lock = count.get_lock() if use_lock else contextlib.nullcontext()


def _compare_row(i):
    shingle_sets, threshold = _worker.shingle_sets, _worker.threshold
    for j in range(i + 1, len(shingle_sets)):
        if jaccard(shingle_sets[i], shingle_sets[j]) >= threshold:
            _record_match(i, j)


def _record_match(i, j):
    # Seção crítica: ler o contador, gravar no slot e incrementar precisa ser atômico.
    # Cada acesso a count.value já é protegido individualmente; o que não é atômico
    # é a sequência inteira, e é ela que o lock externo protege.
    with _worker.lock:
        slot = _worker.count.value
        if slot >= MAX_MATCHES:
            raise OverflowError(f"mais de {MAX_MATCHES} matches; aumente MAX_MATCHES")
        _worker.slots[2 * slot] = i
        _worker.slots[2 * slot + 1] = j
        _worker.count.value = slot + 1

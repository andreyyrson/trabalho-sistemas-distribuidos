"""Mede sequencial x paralelo na mesma máquina e com a mesma entrada, e compara o
speedup medido com o previsto pela lei de Amdahl.

Uso: python3 benchmark.py --docs 800 --repeats 3
"""
import argparse
import os
import statistics
import time

from plagio import parallel, sequential
from plagio.corpus import generate_corpus
from plagio.similarity import to_shingles

THRESHOLD = 0.5


def timed(fn):
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


def amdahl(parallel_fraction, workers):
    return 1 / ((1 - parallel_fraction) + parallel_fraction / workers)


def summarize(label, times):
    spread = statistics.stdev(times) if len(times) > 1 else 0.0
    print(f"{label}: {statistics.mean(times):.2f}s ± {spread:.2f}s  ({', '.join(f'{t:.2f}' for t in times)})")


def main():
    args = parse_args()
    docs, planted = generate_corpus(args.docs, seed=args.seed)

    # O cálculo dos shingles roda só no processo pai, então é parte serial em ambas as versões.
    shingle_sets, shingle_time = timed(lambda: [to_shingles(doc) for doc in docs])
    n_pairs = args.docs * (args.docs - 1) // 2
    print(f"docs={args.docs} pares={n_pairs} processos={args.processes} repetições={args.repeats}")
    print(f"shingles (serial, fora do laço de pares): {shingle_time:.2f}s")

    sequential_times, parallel_times = [], []
    for run in range(args.repeats):
        seq_result, seq_time = timed(lambda: sequential.find_similar_pairs(shingle_sets, THRESHOLD))
        par_result, par_time = timed(
            lambda: parallel.find_similar_pairs(shingle_sets, THRESHOLD, processes=args.processes)
        )
        if not (seq_result == par_result == planted):
            raise SystemExit(f"rodada {run}: resultados diferentes (seq={len(seq_result)}, par={len(par_result)}, gabarito={len(planted)})")
        sequential_times.append(seq_time)
        parallel_times.append(par_time)

    summarize("sequencial", sequential_times)
    summarize("paralelo  ", parallel_times)

    seq_mean, par_mean = statistics.mean(sequential_times), statistics.mean(parallel_times)
    # Fração paralelizável = parte do tempo sequencial gasta no laço de pares.
    parallel_fraction = seq_mean / (seq_mean + shingle_time)
    measured = (seq_mean + shingle_time) / (par_mean + shingle_time)
    predicted = amdahl(parallel_fraction, args.processes)
    print(f"p estimado: {parallel_fraction:.4f}")
    print(f"speedup medido:   {measured:.2f}x  (eficiência {measured / args.processes:.0%})")
    print(f"speedup Amdahl:   {predicted:.2f}x")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=int, default=400)
    parser.add_argument("--processes", type=int, default=os.cpu_count())
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    main()

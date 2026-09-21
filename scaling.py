"""Curva de speedup: mede a versão paralela com vários números de processos contra um
único tempo sequencial e imprime a tabela em Markdown, pronta para colar no relatório.

Uso: python3 scaling.py --docs 1000 --processes 1,2,4,8,12 --repeats 3
"""
import argparse
import statistics

from benchmark import THRESHOLD, amdahl, timed
from plagio import parallel, sequential
from plagio.corpus import generate_corpus
from plagio.similarity import to_shingles


def main():
    args = parse_args()
    docs, planted = generate_corpus(args.docs, seed=args.seed)
    shingle_sets, shingle_time = timed(lambda: [to_shingles(doc) for doc in docs])

    sequential_times = [
        measure(lambda: sequential.find_similar_pairs(shingle_sets, THRESHOLD), planted)
        for _ in range(args.repeats)
    ]
    sequential_mean = statistics.mean(sequential_times)
    sequential_total = sequential_mean + shingle_time
    parallel_fraction = sequential_mean / sequential_total

    print(f"docs={args.docs} repetições={args.repeats}")
    print(f"sequencial: {sequential_mean:.2f}s + shingles {shingle_time:.2f}s | p estimado: {parallel_fraction:.4f}\n")
    print("| Processos | Tempo paralelo (s) | Desvio (s) | Speedup | Eficiência | Amdahl |")
    print("|---|---|---|---|---|---|")

    for workers in args.processes:
        times = [
            measure(lambda: parallel.find_similar_pairs(shingle_sets, THRESHOLD, processes=workers), planted)
            for _ in range(args.repeats)
        ]
        mean = statistics.mean(times)
        spread = statistics.stdev(times) if len(times) > 1 else 0.0
        speedup = sequential_total / (mean + shingle_time)
        print(
            f"| {workers} | {mean:.2f} | {spread:.2f} | {speedup:.2f}x "
            f"| {speedup / workers:.0%} | {amdahl(parallel_fraction, workers):.2f}x |",
            flush=True,  # a tabela leva minutos; mostrar cada linha assim que ela fica pronta
        )


def measure(run, expected):
    result, elapsed = timed(run)
    if result != expected:
        raise SystemExit(f"resultado diferente do gabarito (obtido={len(result)}, esperado={len(expected)})")
    return elapsed


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=int, default=400)
    parser.add_argument("--processes", type=lambda s: [int(n) for n in s.split(",")], default="1,2,4,8")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    main()

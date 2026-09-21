"""Curva de speedup: mede a versão paralela, por estratégia de lock e número de processos,
contra um único tempo sequencial, e imprime a tabela em Markdown para colar no relatório.

Dois experimentos úteis:
  1. Limiar realista (0.5): os matches são raros, então "record" e "local_merge" quase não
     disputam o lock; "whole_loop" serializa tudo e o speedup fica perto de 1.
  2. Limiar 0 (todo par vira match): a disputa pelo lock explode e "record" (um lock por
     match) fica muito pior que "local_merge" (um lock por linha).

Uso: python3 scaling.py --docs 1000 --processes 1,2,4 --repeats 3
     python3 scaling.py --docs 800 --processes 4 --threshold 0
"""
import argparse
import statistics

from benchmark import THRESHOLD, amdahl, timed
from plagio import parallel, sequential
from plagio.corpus import generate_corpus
from plagio.similarity import to_shingles


def main():
    args = parse_args()
    docs, _ = generate_corpus(args.docs, seed=args.seed)
    shingle_sets, shingle_time = timed(lambda: [to_shingles(doc) for doc in docs])

    # O primeiro sequencial vira a referência: com limiar diferente de 0.5 não há gabarito plantado.
    print(f"docs={args.docs} limiar={args.threshold} repetições={args.repeats}", flush=True)
    expected, first_time = timed(lambda: sequential.find_similar_pairs(shingle_sets, args.threshold))
    print(f"sequencial rodada 1: {first_time:.2f}s (pares parecidos={len(expected)})", flush=True)
    sequential_times = [first_time]
    for run in range(2, args.repeats + 1):
        sequential_times.append(
            measure(lambda: sequential.find_similar_pairs(shingle_sets, args.threshold), expected)
        )
        print(f"sequencial rodada {run}: {sequential_times[-1]:.2f}s", flush=True)

    sequential_mean = statistics.mean(sequential_times)
    sequential_total = sequential_mean + shingle_time
    parallel_fraction = sequential_mean / sequential_total
    print(f"sequencial: {sequential_mean:.2f}s + shingles {shingle_time:.2f}s | p estimado: {parallel_fraction:.4f}\n")
    print("| Estratégia | Processos | Tempo paralelo (s) | Desvio (s) | Speedup | Eficiência | Amdahl |")
    print("|---|---|---|---|---|---|---|")

    for strategy in args.strategies:
        for workers in args.processes:
            times = [
                measure(
                    lambda: parallel.find_similar_pairs(
                        shingle_sets, args.threshold, processes=workers, strategy=strategy
                    ),
                    expected,
                )
                for _ in range(args.repeats)
            ]
            mean = statistics.mean(times)
            spread = statistics.stdev(times) if len(times) > 1 else 0.0
            speedup = sequential_total / (mean + shingle_time)
            print(
                f"| {strategy} | {workers} | {mean:.2f} | {spread:.2f} | {speedup:.2f}x "
                f"| {speedup / workers:.0%} | {amdahl(parallel_fraction, workers):.2f}x |",
                flush=True,  # a tabela leva minutos; mostrar cada linha assim que ela fica pronta
            )


def measure(run, expected):
    result, elapsed = timed(run)
    if result != expected:
        raise SystemExit(f"resultado diferente da referência (obtido={len(result)}, esperado={len(expected)})")
    return elapsed


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs", type=int, default=400)
    parser.add_argument("--processes", type=lambda s: [int(n) for n in s.split(",")], default="1,2,4,8")
    parser.add_argument(
        "--strategies",
        type=lambda s: s.split(","),
        default=",".join(parallel.ROW_STRATEGIES),
        help="lista separada por vírgula: " + ", ".join(parallel.ROW_STRATEGIES),
    )
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    main()

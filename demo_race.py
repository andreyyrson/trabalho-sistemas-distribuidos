"""Demonstração ao vivo da condição de corrida na seção crítica.

Com limiar 0 todo par de documentos é "similar" e vira um registro na área compartilhada,
o que maximiza a contenção no contador. Sem lock, processos leem o mesmo valor do contador
e sobrescrevem o slot um do outro, então pares somem do resultado. Com lock, nunca somem.

Uso: python3 demo_race.py --docs 120 --runs 5 --processes 4
"""
import argparse
import os

from plagio import parallel
from plagio.corpus import generate_corpus
from plagio.similarity import to_shingles


def main():
    args = parse_args()
    if (os.cpu_count() or 1) < 2:
        print("Aviso: com 1 núcleo a corrida quase não aparece; rode em uma máquina com 2 ou mais.")

    # Documentos curtos: o custo por par fica mínimo e o tempo todo vai para a disputa pelo contador.
    docs, _ = generate_corpus(args.docs, min_words=20, max_words=40)
    shingle_sets = [to_shingles(doc) for doc in docs]
    expected = args.docs * (args.docs - 1) // 2
    print(f"docs={args.docs} processos={args.processes} pares esperados={expected}\n")

    for use_lock in (False, True):
        label = "COM lock" if use_lock else "SEM lock"
        for run in range(1, args.runs + 1):
            found = len(parallel.find_similar_pairs(shingle_sets, 0.0, processes=args.processes, use_lock=use_lock))
            status = "ok" if found == expected else f"PERDEU {expected - found} pares"
            print(f"{label} rodada {run}: {found} pares ({status})")
        print()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=int, default=120)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--processes", type=int, default=os.cpu_count())
    return parser.parse_args()


if __name__ == "__main__":
    main()

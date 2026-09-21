"""Versão sequencial: baseline para verificar a paralela e medir o speedup."""
from plagio.similarity import jaccard


def find_similar_pairs(shingle_sets, threshold):
    n = len(shingle_sets)
    return {
        (i, j)
        for i in range(n)
        for j in range(i + 1, n)
        if jaccard(shingle_sets[i], shingle_sets[j]) >= threshold
    }

"""Similaridade de Jaccard entre documentos, calculada sobre shingles de palavras."""

SHINGLE_SIZE = 5


def to_shingles(words):
    # hash() em vez da tupla: conjuntos de ints ocupam menos memória e a interseção é mais rápida.
    return frozenset(
        hash(tuple(words[i:i + SHINGLE_SIZE])) for i in range(len(words) - SHINGLE_SIZE + 1)
    )


def jaccard(a, b):
    shared = len(a & b)
    return shared / (len(a) + len(b) - shared)

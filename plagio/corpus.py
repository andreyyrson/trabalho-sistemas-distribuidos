"""Corpus sintético com plágios plantados.

Gerar o corpus (em vez de baixar textos reais) dá um gabarito exato dos pares
plagiados, o que permite verificar automaticamente qualquer versão do algoritmo.
"""
import random

VOCAB_SIZE = 5000
# Trocar 5% das palavras mantém o Jaccard cópia-original em ~0.63 com shingles de 5 palavras;
# textos não relacionados ficam perto de 0, então um limiar de 0.5 separa os dois grupos.
EDIT_RATE = 0.05


def generate_corpus(n_docs, seed=42, plagiarism_rate=0.05, min_words=500, max_words=4000):
    """Retorna (documentos, pares_plantados). Cada documento é uma lista de palavras."""
    rng = random.Random(seed)
    vocab = [f"w{i}" for i in range(VOCAB_SIZE)]
    docs, originals_available, planted = [], [], set()
    for i in range(n_docs):
        if originals_available and rng.random() < plagiarism_rate:
            # Cada original é copiado no máximo uma vez: duas cópias do mesmo original
            # também se pareceriam entre si e criariam pares que o gabarito não conhece.
            source = originals_available.pop(rng.randrange(len(originals_available)))
            docs.append(_edit(docs[source], rng, vocab))
            planted.add((source, i))
        else:
            docs.append(rng.choices(vocab, k=rng.randint(min_words, max_words)))
            originals_available.append(i)
    return docs, planted


def _edit(words, rng, vocab):
    return [rng.choice(vocab) if rng.random() < EDIT_RATE else word for word in words]

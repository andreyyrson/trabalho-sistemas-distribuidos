import os
import unittest

from plagio import parallel, sequential
from plagio.corpus import generate_corpus
from plagio.similarity import to_shingles

THRESHOLD = 0.5


def build(n_docs, **corpus_kwargs):
    docs, planted = generate_corpus(n_docs, **corpus_kwargs)
    return [to_shingles(doc) for doc in docs], planted


class SequentialTest(unittest.TestCase):
    def test_finds_exactly_the_planted_pairs(self):
        shingle_sets, planted = build(60, plagiarism_rate=0.2, min_words=200, max_words=600)
        self.assertGreater(len(planted), 0)
        self.assertEqual(sequential.find_similar_pairs(shingle_sets, THRESHOLD), planted)


class ParallelTest(unittest.TestCase):
    def test_equals_sequential_across_repeated_runs(self):
        shingle_sets, _ = build(60, plagiarism_rate=0.2, min_words=200, max_words=600)
        expected = sequential.find_similar_pairs(shingle_sets, THRESHOLD)
        for _ in range(20):
            self.assertEqual(parallel.find_similar_pairs(shingle_sets, THRESHOLD, processes=4), expected)

    @unittest.skipIf((os.cpu_count() or 1) < 2, "a corrida precisa de pelo menos 2 núcleos")
    def test_without_lock_loses_matches(self):
        # Limiar 0 faz todo par ser registrado: a contenção no contador fica máxima e a corrida aparece.
        shingle_sets, _ = build(120, min_words=20, max_words=40)
        total_pairs = len(shingle_sets) * (len(shingle_sets) - 1) // 2
        found_counts = [
            len(parallel.find_similar_pairs(shingle_sets, 0.0, processes=4, use_lock=False))
            for _ in range(5)
        ]
        self.assertLess(min(found_counts), total_pairs)

    def test_every_strategy_equals_sequential(self):
        shingle_sets, _ = build(60, plagiarism_rate=0.2, min_words=200, max_words=600)
        expected = sequential.find_similar_pairs(shingle_sets, THRESHOLD)
        for strategy in parallel.ROW_STRATEGIES:
            with self.subTest(strategy=strategy):
                found = parallel.find_similar_pairs(shingle_sets, THRESHOLD, processes=4, strategy=strategy)
                self.assertEqual(found, expected)

    def test_every_strategy_keeps_every_match_under_max_contention(self):
        shingle_sets, _ = build(120, min_words=20, max_words=40)
        total_pairs = len(shingle_sets) * (len(shingle_sets) - 1) // 2
        for strategy in parallel.ROW_STRATEGIES:
            with self.subTest(strategy=strategy):
                found = parallel.find_similar_pairs(shingle_sets, 0.0, processes=4, strategy=strategy)
                self.assertEqual(len(found), total_pairs)

    def test_unknown_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            parallel.find_similar_pairs([], THRESHOLD, strategy="nao_existe")

    def test_with_lock_keeps_every_match_under_max_contention(self):
        shingle_sets, _ = build(120, min_words=20, max_words=40)
        total_pairs = len(shingle_sets) * (len(shingle_sets) - 1) // 2
        self.assertEqual(len(parallel.find_similar_pairs(shingle_sets, 0.0, processes=4)), total_pairs)


if __name__ == "__main__":
    unittest.main()

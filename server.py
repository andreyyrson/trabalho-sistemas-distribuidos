"""Serviço HTTP mínimo: executa a comparação e devolve os tempos em JSON.

Atende uma requisição por vez (HTTPServer, não ThreadingHTTPServer) de propósito: duas
execuções simultâneas disputariam os mesmos núcleos e invalidariam a medição, e criar
processos com fork a partir de um servidor com várias threads é frágil.

Uso: python3 server.py
     curl "http://<ip>:8000/run?docs=300&processes=2"
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from benchmark import THRESHOLD, timed
from plagio import parallel, sequential
from plagio.corpus import generate_corpus
from plagio.similarity import to_shingles

PORT = 8000
DEFAULT_DOCS = 300
# O endpoint não tem autenticação: o teto impede que um pedido ocupe a máquina por horas.
MAX_DOCS = 5000


def int_param(params, name, default, low, high):
    raw = params.get(name, [default])[0]
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} deve ser um inteiro") from None
    if not low <= value <= high:
        raise ValueError(f"{name} deve estar entre {low} e {high}")
    return value


def compare(n_docs, processes):
    docs, _ = generate_corpus(n_docs)
    shingle_sets = [to_shingles(doc) for doc in docs]
    sequential_result, sequential_time = timed(lambda: sequential.find_similar_pairs(shingle_sets, THRESHOLD))
    parallel_result, parallel_time = timed(
        lambda: parallel.find_similar_pairs(shingle_sets, THRESHOLD, processes=processes)
    )
    return {
        "docs": n_docs,
        "pairs": n_docs * (n_docs - 1) // 2,
        "processes": processes,
        "similar_pairs_found": len(parallel_result),
        "results_match": sequential_result == parallel_result,
        "sequential_seconds": round(sequential_time, 3),
        "parallel_seconds": round(parallel_time, 3),
        # Só o laço de pares; não inclui o cálculo dos shingles (que é serial).
        "speedup": round(sequential_time / parallel_time, 2),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            self._send(200, {"status": "ok", "cpus": os.cpu_count()})
        elif url.path == "/run":
            self._run(parse_qs(url.query))
        else:
            self._send(404, {"error": "use /health ou /run?docs=N&processes=P"})

    def _run(self, params):
        try:
            n_docs = int_param(params, "docs", DEFAULT_DOCS, 2, MAX_DOCS)
            processes = int_param(params, "processes", os.cpu_count(), 1, os.cpu_count())
        except ValueError as error:
            self._send(400, {"error": str(error)})
            return
        self._send(200, compare(n_docs, processes))

    def _send(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    print(f"Escutando na porta {PORT} (Ctrl+C para encerrar)")
    try:
        HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado")

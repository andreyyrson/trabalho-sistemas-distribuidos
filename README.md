# Detecção de plágio em paralelo

Projeto de Solução Distribuída, Etapa 1 (070080 Sistemas Distribuídos e Paralelos).

Dado um conjunto de documentos, encontra todos os pares parecidos entre si. A comparação de
todos os pares cresce com o quadrado do número de documentos, então o problema é caro e se
divide bem em partes independentes. Há uma versão sequencial e uma paralela do mesmo programa,
medidas na mesma máquina e com a mesma entrada.

## O problema

- **Entrada:** N documentos (listas de palavras). O corpus é gerado por semente em
  `plagio/corpus.py`, com plágios plantados. Isso dá um gabarito exato dos pares que devem
  aparecer e dispensa arquivos de entrada.
- **Comparação:** cada documento vira o conjunto de seus *shingles* (janelas de 5 palavras) e
  dois documentos são "parecidos" quando o índice de Jaccard entre os conjuntos passa do limiar
  (0,5).
- **Unidade de trabalho:** uma linha *i* da matriz de pares, isto é, o documento *i* contra todos
  os documentos *j > i*. As linhas são independentes entre si.
- **Verificação:** o resultado paralelo tem de ser igual ao sequencial e ao gabarito dos pares
  plantados.

## Estratégia de paralelização

- **Paralelismo de dados**, com `multiprocessing` e o método `fork` (só Linux).
- **Processos, não threads:** a comparação é limitada por processador (interseção de conjuntos).
  Em CPython o GIL impede que threads ganhem velocidade nesse tipo de trabalho.
- **Divisão dinâmica:** as linhas são entregues uma por vez, da mais pesada (documento 0, com
  N-1 pares) para a mais leve. Um processo que termina cedo pega a próxima linha, o que
  equilibra a carga.

## Sincronização

Os processos registram os pares encontrados numa memória compartilhada: um vetor de slots e um
contador. A seção crítica em `plagio/parallel.py` (`_record_match`) é a sequência **ler o
contador, gravar o par no slot, incrementar**. Ela é protegida por um **lock**
(`multiprocessing`). Cada acesso ao contador já é atômico sozinho; o que não é atômico é a
sequência inteira, e é ela que o lock protege.

Sem o lock, dois processos leem o mesmo valor do contador e um sobrescreve o registro do outro,
e pares somem do resultado. `demo_race.py` mostra isso ao vivo.

## Como rodar

Requer Python 3.12 e Linux, sem dependências externas.

```
python3 -m unittest discover -s tests -t . -v    # testes
python3 demo_race.py                             # corrida com e sem lock
python3 benchmark.py --docs 1000 --repeats 3     # sequencial x paralelo, com Amdahl
python3 scaling.py --docs 1000 --processes 1,2,4 --repeats 3   # curva por nº de processos
python3 server.py                                # serviço HTTP na porta 8000
```

O tempo cresce com o quadrado de `--docs`. Comece com `--docs 300` para calibrar.

Serviço:

```
curl "http://<ip>:8000/health"
curl "http://<ip>:8000/run?docs=300&processes=2"
```

## Estrutura

| Arquivo | Função |
|---|---|
| `plagio/corpus.py` | Gera o corpus com plágios plantados |
| `plagio/similarity.py` | Shingles e índice de Jaccard |
| `plagio/sequential.py` | Versão sequencial (linha de base) |
| `plagio/parallel.py` | Versão paralela, com a seção crítica |
| `benchmark.py` | Mede sequencial x paralelo e compara com a lei de Amdahl |
| `scaling.py` | Curva de speedup por número de processos |
| `demo_race.py` | Demonstra a condição de corrida sem lock |
| `server.py` | Serviço HTTP que executa a comparação |
| `tests/` | Testes de equivalência, corrida e serviço |

## Ambiente na nuvem

_A preencher com os dados reais da instância usada nas medições._

| Item | Valor |
|---|---|
| Região / zona | |
| Instância (família, tamanho, vCPUs) | |
| Porta administrativa (22) | Origem: IP da equipe /32 |
| Porta do serviço (8000) | Origem: |

## Resultados

_A preencher com as medições feitas na instância acima. Cada tempo é a média de 3 execuções, com
a mesma entrada nas duas versões._

| Processos | Tempo paralelo (s) | Speedup | Amdahl |
|---|---|---|---|
| | | | |

Tempo sequencial: _s_. Fração paralelizável estimada (p): _._

## Segurança

Este repositório não contém chaves, tokens nem credenciais. Os arquivos `*.pem` estão no
`.gitignore`.

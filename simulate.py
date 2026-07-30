#!/usr/bin/env python3
"""
sub2k-intent — simulate.py

Simula exatamente a lógica do command_matcher.ino em Python, pra validar
o matching e calibrar o threshold antes de gravar no Arduino de verdade.

Autor: Bruno Nunes da Silva (criador do DevSoft JARVIS AI)
Produto: https://devsoft-ai.webnode.page/
"""

import json
import sys
from generate_table import fnv1a, normalize_text, word_trigrams, DIM

CONFIDENCE_THRESHOLD = 40


def embed_int(text):
    acc = [0] * DIM
    for word in normalize_text(text):
        for ng in word_trigrams(word):
            h = fnv1a(ng)
            bucket = h % DIM
            sign = 1 if (h >> 31) & 1 else -1
            acc[bucket] += sign
    sum_sq = sum(x * x for x in acc)
    if sum_sq == 0:
        return [0] * DIM
    norm = 1
    while norm * norm < sum_sq:
        norm += 1
    out = []
    for x in acc:
        scaled = (x * 127) // norm
        scaled = max(-127, min(127, scaled))
        out.append(scaled)
    return out


def load_table(commands_path):
    with open(commands_path, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    names = {}
    for cmd in data["commands"]:
        names[cmd["id"]] = cmd["name"]
        for phrase in cmd["phrases"]:
            vec = embed_int(phrase)
            rows.append((cmd["id"], vec))
    return rows, names


def match(vec, rows, threshold):
    best_score = -10**9
    best_id = None
    for cid, ref in rows:
        score = sum(a * b for a, b in zip(vec, ref))
        if score > best_score:
            best_score = score
            best_id = cid
    normalized = best_score // 127
    if normalized < threshold:
        return None, normalized
    return best_id, normalized


# (frase, comando_esperado_ou_None_se_deve_rejeitar)
TEST_CASES = [
    ("liga a luz", "LUZ_LIGAR"),
    ("acende a luz da sala", "LUZ_LIGAR"),
    ("por favor acenda a luz", "LUZ_LIGAR"),
    ("pode ligar a luz pra mim", "LUZ_LIGAR"),
    ("desliga a luz", "LUZ_DESLIGAR"),
    ("apague a luz", "LUZ_DESLIGAR"),
    ("pode apagar a luz", "LUZ_DESLIGAR"),
    ("liga o ventilador", "VENTILADOR_LIGAR"),
    ("liga o vetilador", "VENTILADOR_LIGAR"),  # com erro de digitação
    ("desliga ventilador agora", "VENTILADOR_DESLIGAR"),
    ("qual o status do sistema", "STATUS"),
    ("como que ta o sistema", "STATUS"),
    ("oi tudo bem", None),
    ("vai chover hoje", None),
    ("qual seu nome", None),
    ("bom dia", None),
    ("obrigado", None),
]


def evaluate(rows, threshold, names):
    correct = 0
    wrong = []
    for phrase, expected in TEST_CASES:
        vec = embed_int(phrase)
        cid, score = match(vec, rows, threshold)
        got = names[cid] if cid is not None else None
        ok = (got == expected)
        correct += ok
        if not ok:
            wrong.append((phrase, expected, got, score))
    return correct, wrong


def main():
    rows, names = load_table("commands.json")

    print("=== Varredura de threshold ===")
    print(f"{'threshold':>9s} {'acertos':>8s} / {len(TEST_CASES)}")
    best_t, best_correct = None, -1
    for t in range(0, 128, 5):
        correct, _ = evaluate(rows, t, names)
        if correct > best_correct:
            best_correct, best_t = correct, t
        print(f"{t:9d} {correct:8d}")

    print(f"\nMelhor threshold encontrado: {best_t} ({best_correct}/{len(TEST_CASES)} acertos)\n")

    print(f"=== Detalhe com threshold={best_t} ===")
    print(f"{'frase':35s} {'score':>6s}  {'esperado':22s} {'obtido':22s}")
    print("-" * 90)
    for phrase, expected in TEST_CASES:
        vec = embed_int(phrase)
        cid, score = match(vec, rows, best_t)
        got = names[cid] if cid is not None else "(rejeitado)"
        exp = expected if expected else "(rejeitado)"
        flag = "  " if got == exp else " ❌"
        print(f"{phrase:35s} {score:6d}  {exp:22s} {got:22s}{flag}")


if __name__ == "__main__":
    main()

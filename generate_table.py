#!/usr/bin/env python3
"""
sub2k-intent — generate_table.py

Gera a tabela de referência (embeddings via hashing de trigramas de
caracteres, quantizados em int8) para casamento de intenção offline no
Arduino Uno (ATmega328P), usando menos de 2KB de RAM.

Autor: Bruno Nunes da Silva (criador do DevSoft JARVIS AI)

Uso:
    python3 generate_table.py commands.json > command_matcher/commands_table.h

O mesmo algoritmo de hashing (FNV-1a + trigramas com padding + assinatura
por bit) é reimplementado em C++ no sketch do Arduino, então os dois lados
PRECISAM ficar sincronizados. Se você mudar DIM ou a função de hash aqui,
replique no .ino também.
"""

import json
import sys
import re

DIM = 32 


def fnv1a(s: str) -> int:
    h = 2166136261
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def normalize_text(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9áàâãéêíóôõúç\s]", " ", text)
    return text.split()


def word_trigrams(word: str, n: int = 3) -> list[str]:
    padded = "#" + word + "#"
    if len(padded) < n:
        return [padded]
    return [padded[i:i + n] for i in range(len(padded) - n + 1)]


def embed(text: str, dim: int = DIM) -> list[float]:
    vec = [0.0] * dim
    for word in normalize_text(text):
        for ng in word_trigrams(word):
            h = fnv1a(ng)
            bucket = h % dim
            sign = 1.0 if (h >> 31) & 1 else -1.0
            vec[bucket] += sign
    norm = sum(x * x for x in vec) ** 0.5
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def quantize(vec: list[float]) -> list[int]:
    return [max(-127, min(127, round(x * 127))) for x in vec]


def main():
    if len(sys.argv) != 2:
        print("uso: generate_table.py commands.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)

    rows = []  
    for cmd in data["commands"]:
        for phrase in cmd["phrases"]:
            vec = embed(phrase)
            qvec = quantize(vec)
            rows.append((cmd["id"], cmd["name"], qvec, phrase))

    names = {cmd["id"]: cmd["name"] for cmd in data["commands"]}
    num_commands = len(names)

    print("// Arquivo gerado automaticamente por generate_table.py — não editar à mão.")
    print("// Projeto: sub2k-intent")
    print("// Autor: Bruno Nunes da Silva (criador do DevSoft JARVIS AI)")
    print(f"// DIM={DIM}  linhas={len(rows)}  comandos={num_commands}")
    print("#pragma once")
    print("#include <avr/pgmspace.h>")
    print()
    print(f"#define EMBED_DIM {DIM}")
    print(f"#define NUM_ROWS {len(rows)}")
    print(f"#define NUM_COMMANDS {num_commands}")
    print()

    print("// nome de cada comando (pra debug via Serial)")
    print(f"const char* const COMMAND_NAMES[NUM_COMMANDS] = {{")
    for cid in sorted(names):
        print(f'  "{names[cid]}",')
    print("};")
    print()

    print("// tabela de vetores de referência, ficam na flash (PROGMEM)")
    print(f"const int8_t REF_VECTORS[NUM_ROWS][EMBED_DIM] PROGMEM = {{")
    for cid, name, qvec, phrase in rows:
        vec_str = ", ".join(str(v) for v in qvec)
        print(f"  {{ {vec_str} }}, // [{name}] \"{phrase}\"")
    print("};")
    print()

    print("// a que comando cada linha da tabela pertence")
    print(f"const uint8_t REF_COMMAND_ID[NUM_ROWS] PROGMEM = {{")
    print("  " + ", ".join(str(cid) for cid, _, _, _ in rows) + ",")
    print("};")

    total_bytes = len(rows) * DIM + len(rows)
    print(f"\n// Total aproximado em flash: {total_bytes} bytes ({total_bytes/1024:.2f} KB)", file=sys.stderr)
    print(f"// Linhas geradas: {len(rows)} | Comandos: {num_commands} | Dim: {DIM}", file=sys.stderr)


if __name__ == "__main__":
    main()

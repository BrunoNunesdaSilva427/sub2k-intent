# sub2k-intent

**Correspondência semântica de comandos rodando 100% offline num Arduino Uno - em menos de 2KB de RAM, sem ponto flutuante.**

Nenhum LLM, nenhuma rede neural, nenhuma conexão com a nuvem. Um ATmega328P de 2005 reconhecendo variações de linguagem natural ("liga a luz" / "acenda a lâmpada" / "por favor ligue a luz") com aritmética inteira pura.

---

## Por que isso existe

Rodar um LLM de verdade num microcontrolador de 8 bits é fisicamente impossível - mesmo os experimentos mais extremos de "LLM em ESP32" precisam de megabytes de RAM/flash e ainda assim só geram texto solto, sem seguir instruções. Só que a maioria dos produtos de automação/IoT não precisa de um LLM: precisa **reconhecer a intenção por trás de um punhado de comandos conhecidos**, tolerando variações de como a pessoa fala.

Este projeto mostra que dá pra fazer isso com uma técnica muito mais antiga e muito mais barata - **feature hashing sobre trigramas de caracteres** - comprimida ao ponto de caber inteira na RAM mais escassa do ecossistema Arduino.

## Como funciona

1. **Offline (seu PC):** `generate_table.py` pega uma lista de comandos com várias frases de exemplo cada, gera um "embedding" de cada frase via *hashing trick* sobre trigramas de caracteres (não sobre palavras inteiras - isso é o que dá tolerância a typos e flexões verbais), quantiza pra `int8`, e exporta tudo como uma tabela `PROGMEM` em C.

2. **No Arduino:** o sketch recebe uma frase via Serial, calcula o mesmo tipo de embedding localmente (mesma função de hash, mesma lógica de trigramas - os dois lados precisam ficar sincronizados), e faz um produto escalar (`dot product`) contra cada linha da tabela, direto na flash, sem carregar nada extra pra RAM. O comando com maior score acima de um threshold calibrado é o vencedor.

Nenhum float em nenhum momento no Arduino. Tudo em `int8`/`int16`/`int32`.

## Números reais

| Métrica | Valor |
|---|---|
| Comandos cadastrados | 5 |
| Frases de exemplo (variações) | 47 |
| Dimensões do vetor | 32 |
| Tabela de referência em flash | **1.51 KB** |
| RAM usada em runtime | dezenas de bytes (buffers temporários) |
| Acurácia no conjunto de teste (17 frases, incluindo fora de domínio) | **15/17 (88%)** |

## Onde funciona bem e onde quebra

Testei deliberadamente casos difíceis, incluindo frases que **deveriam ser rejeitadas** (fora do vocabulário treinado):

```
liga a luz                              -> LUZ_LIGAR              ✅
acende a luz da sala                    -> LUZ_LIGAR              ✅
apague a luz                            -> LUZ_DESLIGAR           ✅ (flexão verbal, não cadastrada literalmente)
liga o vetilador  (com erro de digitação) -> VENTILADOR_LIGAR      ✅ (trigramas toleram o typo)
vai chover hoje                         -> rejeitado corretamente ✅
bom dia                                 -> rejeitado corretamente ✅
oi tudo bem                             -> STATUS (falso positivo) ❌
```

**Limitação honesta:** o hashing por trigramas generaliza bem pra typos e variações morfológicas, mas ocasionalmente gera falsos positivos em frases curtas e genéricas por colisão estatística de hash. Isso é um limite estrutural do método com vocabulário pequeno - não um bug. Mitigação possível: aumentar a dimensão do vetor, ou adicionar uma classe explícita de "não-comando" com frases de exemplo negativas.

## Estrutura do projeto

```
sub2k-intent/
├── commands.json              # comandos + frases de exemplo (edite aqui pra adicionar comandos)
├── generate_table.py          # gera a tabela em C a partir do commands.json
├── simulate.py                # valida o matching e calibra o threshold antes de gravar no hardware
└── command_matcher/
    ├── command_matcher.ino    # sketch principal (abra este no Arduino IDE)
    └── commands_table.h       # tabela gerada automaticamente - não edite à mão
```

## Como usar

**1. Adicione/edite comandos** em `commands.json` (quanto mais frases de exemplo por comando, mais robusto):

```json
{ "id": 5, "name": "PORTA_ABRIR", "phrases": ["abre a porta", "abra a porta", "destranca a porta"] }
```

**2. Regenere a tabela:**
```bash
python3 generate_table.py commands.json > command_matcher/commands_table.h
```

**3. (Opcional, mas recomendado) Valide e calibre o threshold antes de gravar:**
```bash
python3 simulate.py
```

**4. Abra `command_matcher/command_matcher.ino` no Arduino IDE**, grave no Uno, abra o Serial Monitor (9600 baud) e digite frases.

## Requisitos

- Arduino Uno (ATmega328P) - ou qualquer AVR compatível com folga de flash equivalente
- Python 3.10+ (só pra geração da tabela, roda no seu computador - não precisa de bibliotecas externas - recomendado Python 3.10.11)
- Arduino IDE

## Sobre este projeto

Este código foi desenvolvido como um estudo de engenharia de restrição extrema - parte de uma série de experimentos explorando até onde dá pra levar NLP offline em hardware ultra-limitado, aplicado ao ecossistema de automação/IoT do **DevSoft JARVIS AI**.

**Autor:** Bruno Nunes da Silva (criador do DevSoft JARVIS AI)<br>
**Conheça o DevSoft JARVIS AI:** https://devsoft-ai.webnode.page/<br>
**Canal no YouTube:** https://www.youtube.com/@devsoftai5538

## Licença

MIT - use, modifique e distribua livremente, mantendo os créditos de autoria.

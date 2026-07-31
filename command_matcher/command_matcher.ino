

#include <avr/pgmspace.h>
#include <string.h>
#include "commands_table.h"

#define SERIAL_BUF_SIZE 64
#define CONFIDENCE_THRESHOLD 60  
#define MIN_INPUT_LENGTH 6       
                                 
                                
                                 

char inputBuffer[SERIAL_BUF_SIZE];
uint8_t inputLen = 0;


uint32_t fnv1a(const char* word, uint8_t len) {
  uint32_t h = 2166136261UL;
  for (uint8_t i = 0; i < len; i++) {
    h ^= (uint8_t)word[i];
    h *= 16777619UL;
  }
  return h;
}


void hashTrigramsOfWord(const char* word, uint8_t wlen, int16_t* acc) {
  char padded[26];
  uint8_t plen = 0;
  padded[plen++] = '#';
  for (uint8_t i = 0; i < wlen && plen < sizeof(padded) - 2; i++) {
    padded[plen++] = word[i];
  }
  padded[plen++] = '#';

  const uint8_t N = 3;
  if (plen < N) {
    uint32_t h = fnv1a(padded, plen);
    uint8_t bucket = h % EMBED_DIM;
    acc[bucket] += ((h >> 31) & 1) ? 1 : -1;
    return;
  }

  for (uint8_t i = 0; i + N <= plen; i++) {
    uint32_t h = fnv1a(&padded[i], N);
    uint8_t bucket = h % EMBED_DIM;
    int8_t sign = ((h >> 31) & 1) ? 1 : -1;
    acc[bucket] += sign;
  }
}

bool isWordChar(char c) {
  if (c >= 'a' && c <= 'z') return true;
  if (c >= 'A' && c <= 'Z') return true;
  if (c >= '0' && c <= '9') return true;
  if ((uint8_t)c >= 0x80) return true;
  return false;
}

void embedText(const char* text, int8_t* outVec) {
  int16_t acc[EMBED_DIM];
  for (uint8_t i = 0; i < EMBED_DIM; i++) acc[i] = 0;

  char word[24];
  uint8_t wlen = 0;

  for (uint8_t i = 0; ; i++) {
    char c = text[i];
    bool isSep = !isWordChar(c);
    if (!isSep && wlen < sizeof(word) - 1) {
      if (c >= 'A' && c <= 'Z') c = c - 'A' + 'a';
      word[wlen++] = c;
    }
    if (isSep) {
      if (wlen > 0) {
        hashTrigramsOfWord(word, wlen, acc);
      }
      wlen = 0;
    }
    if (c == '\0') break;
  }

  int32_t sumSq = 0;
  for (uint8_t i = 0; i < EMBED_DIM; i++) sumSq += (int32_t)acc[i] * acc[i];

  if (sumSq == 0) {
    for (uint8_t i = 0; i < EMBED_DIM; i++) outVec[i] = 0;
    return;
  }


  int32_t norm = 1;
  while (norm * norm < sumSq) norm++;

  for (uint8_t i = 0; i < EMBED_DIM; i++) {
    int32_t scaled = ((int32_t)acc[i] * 127) / norm;
    if (scaled > 127) scaled = 127;
    if (scaled < -127) scaled = -127;
    outVec[i] = (int8_t)scaled;
  }
}

int32_t dotProductPGM(const int8_t* vec, uint16_t rowIdx) {
  int32_t sum = 0;
  for (uint8_t i = 0; i < EMBED_DIM; i++) {
    int8_t refVal = (int8_t)pgm_read_byte(&REF_VECTORS[rowIdx][i]);
    sum += (int32_t)vec[i] * refVal;
  }
  return sum;
}


int16_t matchCommand(const int8_t* vec, int32_t* outScore) {
  int32_t bestScore = -2147483647L;
  uint16_t bestRow = 0;

  for (uint16_t r = 0; r < NUM_ROWS; r++) {
    int32_t score = dotProductPGM(vec, r);
    if (score > bestScore) {
      bestScore = score;
      bestRow = r;
    }
  }

  *outScore = bestScore / 127; 

  if (*outScore < CONFIDENCE_THRESHOLD) return -1;
  return (int16_t)pgm_read_byte(&REF_COMMAND_ID[bestRow]);
}



void setup() {
  Serial.begin(9600);
  Serial.println(F("Command matcher pronto. Digite uma frase e Enter."));
  Serial.print(F("Comandos carregados: "));
  Serial.println(NUM_COMMANDS);
  Serial.print(F("Linhas na tabela: "));
  Serial.println(NUM_ROWS);
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputLen > 0) {
        inputBuffer[inputLen] = '\0';
        processInput(inputBuffer);
        inputLen = 0;
      }
    } else if (inputLen < SERIAL_BUF_SIZE - 1) {
      inputBuffer[inputLen++] = c;
    }
  }
}

void processInput(const char* text) {

  uint8_t textLen = strlen(text);
  if (textLen < MIN_INPUT_LENGTH) {
    Serial.print(F("> \""));
    Serial.print(text);
    Serial.println(F("\"  -> não reconhecido (frase muito curta)"));
    return;
  }

  int8_t vec[EMBED_DIM];
  embedText(text, vec);

  int32_t score;
  int16_t cmdId = matchCommand(vec, &score);

  Serial.print(F("> \""));
  Serial.print(text);
  Serial.print(F("\"  score="));
  Serial.print(score);

  if (cmdId < 0) {
    Serial.println(F("  -> não reconhecido"));
  } else {
    Serial.print(F("  -> "));
    Serial.println(COMMAND_NAMES[cmdId]);
  }
}

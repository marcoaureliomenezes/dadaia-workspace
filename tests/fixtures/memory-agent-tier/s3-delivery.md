---
slug: s3-delivery
title: Entrega S3 via Kafka Connect
category: product
tldr: Tres S3 Sink connectors gravam topicos mainnet-* como NDJSON particionado (Wallclock) em raw/mainnet-*; fluent-bit envia logs redigidos a raw/app_logs/.
summary: A entrega S3 é a fronteira única de integração do produto. O Kafka Connect roda três S3 Sink connectors que escrevem NDJSON particionado por Wallclock em `raw/mainnet-*`; fluent-bit envia logs com redação por valor a `raw/app_logs/`. Consumidores downstream leem exclusivamente `raw/*`.
tags:
  - s3
  - kafka-connect
  - ndjson
  - partitioning
  - boundary
agent_tier: self-pull
token_estimate: 650
last_updated: "2026-07-08"
release_origin: v0.1.1
---

# Entrega S3 via Kafka Connect

## Propósito

A entrega S3 é a **fronteira única de integração** do `sample-consumer` (ADR-001): tudo
que a lane de streaming produz no Kafka é materializado em objetos S3 sob `raw/*`, e os
consumidores downstream (sample-explorer, camadas analíticas) leem exclusivamente esses
prefixos. Kafka, Redis e o estado interno dos jobs nunca são contrato externo.

O worker Kafka Connect (imagem construída de `infra/kafka-connect/`) roda três S3 Sink
connectors — um por família de tópico (blocos, txs-data, txs-decoded) — registrados por
um one-shot `connector-init`. Os connectors resolvem credenciais AWS pela cadeia padrão
do SDK (auto-refresh contra o endpoint `aws_signing_helper serve`), não por variável de
ambiente estática.

O particionamento usa o extractor **Wallclock** (tempo de ingestão) nos três connectors:
a decisão corrige o bug histórico em que schemas carregando segundos caíam em
`year=1970`. A partição reflete o tempo de ingestão da camada raw; o tempo do evento
permanece no payload. O tópico de blocos tem tuning por-tópico (`flush.size=50` +
`rotate.schedule.interval.ms=300000`) para honrar a promessa de latência ≤ 10 min; os
tópicos de txs mantêm `flush.size=1000` / rotação de 1h.

## Fluxo de uso

1. Os jobs de streaming produzem Avro nos tópicos `mainnet-*` (ver [[streaming-pipeline]]).
2. O `connector-init` registra os três S3 Sink connectors no worker Connect.
3. Cada connector consome seu tópico, converte para NDJSON e escreve objetos sob
   `s3://<bucket>/raw/mainnet-<stream>/year=YYYY/month=MM/day=DD/...` com partição
   Wallclock (ano corrente, nunca `year=1970`).
4. Em paralelo, o `fluent-bit` coleta logs dos containers, aplica redação por VALOR de
   segredo (padrões `AKIA...`, `sk-...`, `ghp_...`, `eyJ...`, shape de token Telegram,
   com guarda não-hex para não redigir endereços/hashes Ethereum de 40 hex) e envia a
   `raw/app_logs/`.

## Trigger típico

Roda continuamente: cada flush/rotação de connector materializa um novo objeto NDJSON no
S3 conforme os tópicos acumulam registros.

## Diferencial

Concentrar a integração num único prefixo S3 desacopla lanes e consumidores — cada lado
evolui independentemente, com latência limitada ao flush do sink. O extractor Wallclock
elimina a corrupção de partição `year=1970`, e a redação por valor no fluent-bit trata a
causa raiz (o shape do segredo) em vez de grepar nomes de variável.

## Estado runtime tocado

- Lê: tópicos Kafka `mainnet-*`; logs de container (fluent-bit).
- Escreve: `s3://<bucket>/raw/mainnet-*` (dados), `s3://<bucket>/raw/app_logs/` (logs).
- Config: `infra/kafka-connect/connectors/s3-sink-*.json`,
  `infra/kafka-connect/Dockerfile`, `infra/fluent-bit/fluent-bit.conf`.

## Dependências

- Requer antes: [[streaming-pipeline]] produzindo nos tópicos; o endpoint
  `aws_signing_helper serve` da lane streaming (:9911) disponível para o SDK resolver
  credenciais.
- Aciona depois: consumidores downstream (fora deste repo) leem `raw/*`.

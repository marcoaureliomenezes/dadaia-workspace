---
name: game-audio-design
description: >
  MetaSounds UE5, Attenuation Shapes, Reverb Submix. Sound design para combate aéreo:
  turbinas, afterburner, Doppler shift, explosões, cockpit. Fontes públicas seguras:
  Freesound.org (CC0/CC-BY), ZapSplat free tier.
applyTo: "repos/redacted-slug/**"
---

# game-audio-design

Referência de áudio para jogos. Carregue ao implementar sistema sonoro.

---

## 1. MetaSounds — Estrutura Básica

```
MetaSound Source Asset
  ├── Inputs: Throttle (float 0..1), IsAfterburner (bool), Velocity (float)
  ├── Nodes:
  │     ├── Wave Player: turbine_idle.wav (loop)
  │     ├── Pitch Shift: +Throttle * 12 semitones
  │     ├── Volume Envelope: Throttle * 0.8
  │     └── [If IsAfterburner] Additive Layer: afterburner_roar.wav
  └── Output: Mono/Stereo mix
```

---

## 2. Attenuation — Aeronave em Combate

```ini
# Sound Attenuation Asset para aeronaves:
AttenuationShape: Sphere
AttenuationShapeExtents: 5000.0    # Raio de 50m em UE units (1 UU = 1 cm)
FalloffDistance: 15000.0           # Fade out até 200m
SpatializationAlgorithm: HRTF     # Áudio 3D com Head-Related Transfer Function
OcclusionEnabled: true
DopplerIntensity: 0.8              # Efeito Doppler moderado (não exagerado)
```

---

## 3. Specs de Som para redacted-slug-v2

| Som | Técnica | Característica |
|---|---|---|
| Turbina idle | Loop + pitch shift por throttle | Frequência: 800–2400 Hz |
| Afterburner | Layer aditiva + reverb hall | Burst de 150–300 Hz + harmônicos |
| Vento relativo | Noise filtrado por velocidade | Aumenta quadraticamente com speed |
| Explosão | ADSR: attack 2ms, decay 800ms | Layered: bass boom + crackle + debris |
| Cockpit ambience | Loop de baixa amplitude | Frequências < 200 Hz |
| Lock-on warning | Beep repetido + reverb cabin | 1200 Hz, 200ms on/off |

---

## 4. Fontes de Áudio Públicas

| Fonte | Licença | Como usar |
|---|---|---|
| freesound.org | CC0 / CC-BY (por arquivo) | Verificar licença individual antes de baixar |
| zapsplat.com (free tier) | ZapSplat License | Crédito em documentação interna |
| BBC Sound Effects Library | BBC RemArc License | Verificar se uso em jogo é permitido por categoria |

**Workflow:**
```
1. WebSearch freesound.org "jet engine turbine loop"
2. Filtrar: License = CC0 (sem atribuição)
3. Baixar → processar no Audacity (normalizar, loop seamless)
4. Importar no UE5 como Sound Wave asset
5. Registrar fonte e licença no design report
```

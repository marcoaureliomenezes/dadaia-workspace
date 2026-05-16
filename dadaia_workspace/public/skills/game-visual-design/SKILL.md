---
name: game-visual-design
description: >
  Art direction para jogos UE5: design bible, identidade visual, paleta, moodboard,
  post-process volume (bloom, DoF, tone mapping), sky atmosphere, fog volumétrico,
  time-of-day system e camera rigs cinematográficas.
applyTo: "repos/tauan-games/**"
---

# game-visual-design

Referência de art direction e visual design. Carregue ao definir estética do jogo
ou configurar sistemas visuais em UE5.

---

## 1. Design Bible — Formato

```markdown
# Design Bible: <nome do jogo>

## Conceito Visual
<1 parágrafo: o que o jogador deve sentir ao ver o jogo>

## Referências Visuais
- Ref 1: [URL no ArtStation ou artstation.com] — por quê
- Ref 2: [URL] — por quê

## Paleta de Cores
| Papel | Hex | Uso |
|---|---|---|
| Sky primary | #1a2b4c | Céu noturno de combate |
| Enemy accent | #ff3a1a | Aviões inimigos, alertas |
| Friendly | #3af0ff | Aeronave do player, HUD |
| Terrain | #4a5a3a | Terreno / vegetação |

## Estética
<Low-poly / fotorrealista / estilizado / híbrido + justificativa>

## Proibições
<O que NÃO deve aparecer no jogo — mantém consistência>
```

---

## 2. Post-Process Volume — Config de Combate Aéreo

```ini
# Configurações recomendadas para aero-fighters-v2:

Bloom:
  Intensity: 0.4          # Sutil, não ofusca o HUD
  Threshold: 1.0

Depth of Field:
  Method: CircleDOF
  FocalDistance: 5000.0   # Foco no range de combate
  FstopAperture: 32.0     # DOF suave, não distrator

Tone Mapping:
  ACES: enabled           # Cor cinematográfica, padrão UE5
  Gamma: 2.2

Chromatic Aberration:
  Intensity: 0.3          # Apenas ao tomar dano (via Material Parameter Collection)

Vignette:
  Intensity: 0.3          # Borda escura, foco central
```

---

## 3. Sky Atmosphere + Time-of-Day

```cpp
// Configurar ciclo dia/noite via timeline:
// Altitude do sol em graus: 90° = meio-dia, 0° = nascer/pôr, -90° = meia-noite

UPROPERTY(EditAnywhere, BlueprintReadWrite)
float TimeOfDay = 14.0f; // 14h = luz de tarde, boa para combate

void ATimeOfDayManager::UpdateSunPosition()
{
    const float SunAngle = (TimeOfDay / 24.0f) * 360.0f - 90.0f;
    SunLight->SetRelativeRotation(FRotator(SunAngle, 0.0f, 0.0f));
    // SkyAtmosphere atualiza automaticamente via DirectionalLight
}
```

---

## 4. Fog Volumétrico para Altitude

```ini
# Exponential Height Fog — simula camada de neblina em baixa altitude:
FogDensity: 0.02
FogHeightFalloff: 0.2    # Fog diminui rapidamente com altitude
FogStartDistance: 5000   # Começa a 5km de distância
Volumetric: enabled
VolumetricScatteringIntensity: 1.0
```

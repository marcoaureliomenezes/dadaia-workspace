---
name: game-flight-dynamics
description: >
  JSBSim FDM integrado com UE5: coeficientes aerodinâmicos, propulsão, trem de pouso,
  FCS, loop de simulação passo fixo, ground effect, stall, integração com Chaos Physics.
applyTo: "repos/redacted-slug/redacted-slug-v2/**"
---

# game-flight-dynamics

Referência para integração do JSBSim Flight Dynamics Model com Unreal Engine 5.

---

## 1. Conceitos Fundamentais

| Variável | Símbolo | Descrição |
|---|---|---|
| Thrust | T | Força propulsiva (N) |
| Drag | D | Resistência aerodinâmica |
| Lift | L | Sustentação |
| Angle of Attack | α (alpha) | Ângulo entre vetor velocidade e corda da asa |
| Sideslip | β (beta) | Ângulo lateral |
| Mach | M | Velocidade relativa ao som |

**Stall:** ocorre quando α excede o ângulo crítico (~15-18°). Lift cai abruptamente.

**Ground effect:** Lift aumenta ~10-20% quando aeronave está a menos de 1 envergadura do solo.

---

## 2. Arquitetura de Integração UE5 + JSBSim

```
UE5 Tick (variável)
  ↓
UFlightComponent::TickComponent()
  ↓
JSBSimInterface::Step(dt_fixed)  ← passo fixo (dt = 1/120s)
  ↓ acumula dt_remaining
JSBSimInterface::GetState()      ← posição, velocidade, atitude
  ↓
APawn::SetActorLocation/Rotation ← interpolado para UE5
```

### Por que passo fixo?

JSBSim é um integrador numérico. Frame rate variável do UE5 causa instabilidade
na simulação física. Usar passo fixo de 1/120s (8.33ms) com acúmulo de delta time.

```cpp
// UFlightComponent.cpp
void UFlightComponent::TickComponent(float DeltaTime, ...)
{
    AccumulatedDt += DeltaTime;
    const float FixedStep = 1.0f / 120.0f;

    while (AccumulatedDt >= FixedStep)
    {
        JSBSimInterface->Step(FixedStep);
        AccumulatedDt -= FixedStep;
    }

    // Interpolar posição entre passos
    const float Alpha = AccumulatedDt / FixedStep;
    UpdateActorTransform(Alpha);
}
```

---

## 3. Inputs de Controle

```cpp
// Normalizado [-1, 1] → JSBSim espera range específico por eixo
JSBSimInterface->SetControl("fcs/aileron-cmd-norm",  AileronInput);   // roll
JSBSimInterface->SetControl("fcs/elevator-cmd-norm", ElevatorInput);  // pitch
JSBSimInterface->SetControl("fcs/rudder-cmd-norm",   RudderInput);    // yaw
JSBSimInterface->SetControl("fcs/throttle-cmd-norm", ThrottleInput);  // 0..1
```

---

## 4. Trem de Pouso e Ground Effect

```cpp
// Detectar contato com solo via Chaos Physics, não via JSBSim collision
void UFlightComponent::CheckGroundContact()
{
    FHitResult Hit;
    const FVector Start = GetOwner()->GetActorLocation();
    const FVector End = Start - FVector(0, 0, 200.0f);

    if (GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_WorldStatic))
    {
        const float HeightAGL = Hit.Distance; // Height Above Ground Level
        JSBSimInterface->SetGroundHeight(Hit.ImpactPoint.Z);
        JSBSimInterface->SetProperty("position/h-agl-ft", HeightAGL * 0.0328084f); // cm→ft
    }
}
```

---

## 5. Referências Oficiais

- JSBSim Introduction: https://jsbsim-team.github.io/jsbsim/
- Aircraft FDM files: https://github.com/JSBSim-Team/jsbsim/tree/master/aircraft

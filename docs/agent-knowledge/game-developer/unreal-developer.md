---
name: game-unreal-developer
description: >
  UE5 profundo para lógica de jogo: C++ Actor/Component/GameMode/GameState/PlayerController/Pawn,
  Behavior Trees, EQS, Chaos Physics, delegates, collision channels. Inclui protocolo de
  pesquisa com whitelist de fontes confiáveis para forums, exemplos e bugs conhecidos.
applyTo: "repos/redacted-slug/redacted-slug-v2/**"
trusted_sources:
  - dev.epicgames.com
  - forums.unrealengine.com
  - github.com
  - stackoverflow.com
  - reddit.com/r/unrealengine
  - reddit.com/r/gamedev
  - jsbsim-team.github.io
---

# game-unreal-developer

Referência técnica de UE5 para o game-developer. Carregue ao implementar qualquer
mecânica de gameplay em redacted-slug-v2.

---

## 1. Arquitetura de Classes UE5

### Hierarquia obrigatória

```
UGameInstance          → persiste entre levels, estado global de sessão
  UGameMode            → regras do jogo (server-only), spawns, condições de vitória
  UGameState           → estado replicável visível a todos os players
    APlayerController  → input, câmera, HUD (não tem mesh)
      APawn/ACharacter → mesh, movimentação física no mundo
        UActorComponent → lógica modular (weapon, health, flight)
```

### Onde colocar cada sistema

| Sistema | Classe correta |
|---|---|
| Regras de round, score, spawn de inimigos | `AGameMode` |
| Vidas, pontuação sincronizada | `AGameState` |
| Input de voo, câmera | `APlayerController` |
| Mesh da aeronave, colisões | `APawn` |
| Sistema de armas, health, afterburner | `UActorComponent` |
| IA de inimigo | `AAIController` + `UBehaviorTree` |

---

## 2. C++ Patterns Obrigatórios

### UFUNCTION e UPROPERTY

```cpp
UCLASS()
class AEROFIGHTERS_API APlayerAircraft : public APawn
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight")
    float MaxThrust = 50000.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weapons")
    int32 MissileCount = 6;

    UFUNCTION(BlueprintCallable, Category = "Flight")
    void FireMissile();

    UFUNCTION(BlueprintImplementableEvent, Category = "VFX")
    void OnMissileFired();

private:
    UPROPERTY()
    TObjectPtr<UFlightComponent> FlightComp;
};
```

### Delegate para eventos desacoplados

```cpp
// No header do GameMode:
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnEnemyDestroyed, int32, Points);

UPROPERTY(BlueprintAssignable)
FOnEnemyDestroyed OnEnemyDestroyed;

// No enemy actor ao morrer:
if (AMyGameMode* GM = GetWorld()->GetAuthGameMode<AMyGameMode>())
{
    GM->OnEnemyDestroyed.Broadcast(PointValue);
}
```

---

## 3. Behavior Tree para IA de Inimigo

### Setup mínimo

```
UBehaviorTree (asset)
  └── Root
        └── Selector
              ├── Sequence [atacar se jogador visível]
              │     ├── BTTask_CheckLineOfSight
              │     └── BTTask_FireWeapon
              └── Sequence [patrulhar]
                    └── BTTask_MoveToPatrolPoint
```

```cpp
// No AIController:
UPROPERTY(EditDefaultsOnly, Category = "AI")
TObjectPtr<UBehaviorTree> EnemyBehaviorTree;

void AEnemyAIController::BeginPlay()
{
    Super::BeginPlay();
    if (EnemyBehaviorTree)
    {
        RunBehaviorTree(EnemyBehaviorTree);
    }
}
```

---

## 4. Collision Channels

```cpp
// Setup de canal customizado no ProjectSettings → Collision:
// Canal: "Projectile" (ECC_GameTraceChannel1)
// Canal: "Aircraft"   (ECC_GameTraceChannel2)

// No construtor do projétil:
CollisionComponent->SetCollisionProfileName("Projectile");

// Query de linha (hitbox):
FHitResult Hit;
FCollisionQueryParams Params;
Params.AddIgnoredActor(this);

bool bHit = GetWorld()->LineTraceSingleByChannel(
    Hit,
    StartLocation,
    EndLocation,
    ECC_GameTraceChannel1,  // Projectile channel
    Params
);
```

---

## 5. Protocolo de Pesquisa

Antes de implementar qualquer sistema novo:

```
1. WebSearch em dev.epicgames.com — documentação oficial da feature
2. WebSearch em forums.unrealengine.com — threads com a versão UE5 alvo
3. WebSearch em github.com — exemplos de código para o pattern
4. Registrar qualquer bug conhecido da versão antes de iniciar
```

Fontes permitidas: dev.epicgames.com, forums.unrealengine.com, github.com,
stackoverflow.com, reddit.com/r/unrealengine, reddit.com/r/gamedev, jsbsim-team.github.io

**Nunca pesquisar fora desta whitelist sem aprovação explícita do operador.**

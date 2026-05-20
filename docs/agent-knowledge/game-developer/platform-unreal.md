---
name: game-platform-unreal
description: >
  Plataforma Nível 4: Unreal Engine 5 para fotorrealismo e simulações físicas AAA.
  Cobre decisão Blueprint vs C++, arquitetura Actor/Component/GameMode, Visual Scripting
  com Blueprints, Nanite/Lumen e packaging de Shipping build. Use raramente — somente
  quando Unity não for suficiente e a justificativa for documentada.
applyTo: "repos/tauan-games/**"
---

# game-platform-unreal

Referência para Unreal Engine 5. Esta é a plataforma mais complexa e cara de operar.
**Somente use quando a limitação técnica real de Unity for documentada e aprovada.**

---

## Quando usar UE5 no lugar de Unity

| Justificativa válida | Justificativa inválida |
|---|---|
| Nanite + Lumen para cena fotorrealista | "Parece mais profissional" |
| Chaos Physics para destruição em larga escala | O jogo é indie ou 2D |
| Integração com Epic Games Store como requisito | Preferência pessoal pela interface |
| Simulação de ambiente com Niagara VFX em escala AAA | Unity consegue fazer o mesmo |

**Custo real:** UE5 tem build times de minutos, requer hardware robusto, ocupa >80GB em disco e tem curva de aprendizado significativamente maior que Unity.

---

## 1. Blueprint vs C++

| Critério | Blueprint | C++ |
|---|---|---|
| Prototipagem rápida | Excelente | Lento |
| Performance crítica | Limitado | Nativo |
| Lógica complexa | Ilegível em scale | Preferido |
| Equipe sem programadores | Viável | Inviável |

**Regra prática:** comece em Blueprint, migre para C++ somente quando o profiler mostrar gargalo real.

### Comunicação Blueprint → C++

```cpp
// C++ expõe função para Blueprint
UFUNCTION(BlueprintCallable, Category = "Combat")
void TakeDamage(float Amount);

// Propriedade editável no Blueprint
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Stats")
float MaxHealth = 100.f;

// Event implementado no Blueprint, declarado em C++
UFUNCTION(BlueprintImplementableEvent, Category = "Combat")
void OnDeath();
```

---

## 2. Arquitetura UE5

### Hierarquia fundamental

```
GameInstance    ← persiste durante toda a sessão (login, dados globais)
  GameMode      ← regras do jogo, controla o flow (um por mapa)
    GameState   ← estado compartilhado (score, tempo, time)
    PlayerController ← input, câmera, HUD
      Pawn / Character ← o personagem controlado
        Components: StaticMeshComponent, CollisionComponent, etc.
```

### Actor e Components (C++)

```cpp
// Declaração de Actor
UCLASS()
class APlayer : public ACharacter
{
    GENERATED_BODY()

public:
    APlayer();

protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaTime) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;

private:
    UPROPERTY(VisibleAnywhere) UStaticMeshComponent* WeaponMesh;
    UPROPERTY(EditAnywhere, Category = "Stats") float MoveSpeed = 600.f;

    void MoveForward(float Value);
    void MoveRight(float Value);
};
```

```cpp
// Implementação
APlayer::APlayer()
{
    PrimaryActorTick.bCanEverTick = true;
    WeaponMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WeaponMesh"));
    WeaponMesh->SetupAttachment(GetMesh(), TEXT("hand_r"));
}

void APlayer::BeginPlay()
{
    Super::BeginPlay();
    // Inicialização após spawn
}

void APlayer::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    // Lógica por frame — prefira Timers e Events para lógica esparsa
}
```

### Delegates (equivalente a eventos C# do Unity)

```cpp
// Declaração
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnHealthChanged, float, NewHealth);

UPROPERTY(BlueprintAssignable, Category = "Events")
FOnHealthChanged OnHealthChanged;

// Broadcast
OnHealthChanged.Broadcast(CurrentHealth);

// Subscribe (em C++)
Component->OnHealthChanged.AddDynamic(this, &AMyActor::HandleHealthChanged);
```

---

## 3. Visual Scripting com Blueprints

### Event Graph — estrutura básica

```
Event BeginPlay → [inicialização]
Event Tick      → [lógica por frame — evite ao máximo]
Event OnHit     → [resposta a colisão]
Custom Event    → [chamado por outros Blueprints ou C++]
```

### Boas práticas em Blueprint

- Use **Functions** para lógica reutilizável (não Events)
- Use **Macros** para padrões repetidos (não Collapsed Nodes)
- Use **Event Dispatchers** para comunicação entre Blueprints (não referências diretas)
- Use **Cast To** com moderação — prefira Interfaces para desacoplamento
- Blueprint com > 100 nós: considere migrar para C++

### Blueprint Interface (desacoplamento)

```
Interface: BPI_Interactable
  Function: Interact(Player: APlayerCharacter)

Implementado em: Door, Chest, NPC — sem referência direta entre eles
```

---

## 4. Recursos Exclusivos UE5

### Nanite (geometria virtual)

Renderiza malhas de alta polígonagem sem LOD manual. Ative por mesh:
`StaticMesh → Details → Nanite Settings → Enable Nanite`

Não use em: malhas animadas (Skeletal Mesh), vegetação com billboarding, objetos transparentes.

### Lumen (iluminação global dinâmica)

```
Project Settings → Rendering → Global Illumination: Lumen
Project Settings → Rendering → Reflections: Lumen
```

Custo alto em hardware. Para jogos indie, use Baked Lighting ou Screen Space GI.

### Niagara (sistema de partículas)

Substitui o antigo Cascade. Use para VFX: explosões, fumaça, energia, clima.
Sistema GPU-driven — suporta milhões de partículas.

---

## 5. Packaging e Distribuição

### Shipping Build (produção)

```
Platforms → [Target Platform] → Package Project
```

**Development vs Shipping:**
- Development: logs, console, profiler ativo — use para debug
- Shipping: otimizado, sem console, menor — use para release

### Configurações de packaging

```
Project Settings → Packaging:
  Build Configuration: Shipping
  Full Rebuild: On (para release final)
  Compress Content: On
  Blueprint Nativization: Inclusive (converte Blueprints para C++ no build)
```

### Plataformas

| Plataforma | Requisito |
|---|---|
| Windows | Nenhum adicional |
| macOS | Mac com XCode |
| Linux | Cross-compilation toolchain |
| PS5 / Xbox | Developer Kit + licença de plataforma |
| Android | Android SDK configurado |

### Epic Games Store

- Requer acordo de publisher com a Epic
- Integração via Epic Online Services SDK
- Para indie: distribua via itch.io (sem requisitos) + Steam (taxa única de $100)

### Steam (via Steamworks)

1. Criar conta de developer em partner.steamgames.com
2. Configurar AppID no Portal Steamworks
3. Integrar Steamworks SDK no projeto (plugin de terceiros ou manual)
4. Upload via SteamCMD ou Steamworks build system

---

## Documentação UE5

- UE5 Docs: https://docs.unrealengine.com/
- UE5 Dev Portal: https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-7-documentation

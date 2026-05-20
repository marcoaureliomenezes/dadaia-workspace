---
name: game-platform-unity
description: >
  Plataforma Nível 3: Unity 6 com C# para jogos 3D AAA e mobile de alta qualidade.
  Cobre lifecycle de MonoBehaviour, física (Rigidbody/Collider), arquitetura com
  ScriptableObjects e prefabs, sistema de eventos C#, build para WebGL/PC/mobile e
  integração com Steam. Use quando física realista, shaders avançados, VFX ou
  multiplayer robusto forem requisitos que Godot não consegue atender.
applyTo: "repos/tauan-games/**"
---

# game-platform-unity

Referência para desenvolvimento com Unity 6 e C#. Carregue esta skill quando o projeto
exigir capacidades que Godot não cobre: física AAA, shaders complexos, ou ecossistema
de assets da Unity Asset Store.

---

## Quando usar Unity no lugar de Godot

| Sinal | Razão |
|---|---|
| Física de destruição ou soft body | Unity PhysX + Obi, Godot não tem equivalente |
| Shaders PBR complexos com HDRP | Unity HDRP supera Godot em qualidade visual |
| Multiplayer com Netcode for GameObjects | Solução madura da Unity |
| Precisa de assets da Asset Store | Maior ecossistema de assets prontos |
| VFX com Visual Effect Graph | Godot não tem equivalente |

**Não migre** sem justificativa real. Unity tem curva de aprendizado maior, build times mais longos e licenciamento mais complexo que Godot.

---

## 1. Lifecycle de MonoBehaviour

Todo script de jogo estende `MonoBehaviour`. A ordem de execução importa.

```csharp
using UnityEngine;

public class Player : MonoBehaviour
{
    // Serializado no Inspector
    [SerializeField] private float speed = 5f;
    [SerializeField] private float jumpForce = 8f;

    // Componentes (sempre cache, nunca GetComponent() no Update)
    private Rigidbody _rb;
    private Animator  _anim;
    private bool      _isGrounded;

    // Awake: inicialização de componentes, antes do Start
    private void Awake()
    {
        _rb   = GetComponent<Rigidbody>();
        _anim = GetComponent<Animator>();
    }

    // Start: inicialização de lógica, após todos os Awake
    private void Start()
    {
        // Configuração inicial
    }

    // Update: input, timers, lógica não-física — roda 1x por frame
    private void Update()
    {
        HandleInput();
    }

    // FixedUpdate: física — roda em intervalo fixo (padrão 50Hz)
    private void FixedUpdate()
    {
        ApplyMovement();
    }

    // LateUpdate: câmera, IK — roda após todos os Update
    private void LateUpdate()
    {
        UpdateCamera();
    }

    private void OnDestroy()
    {
        // Limpar events, cancelar coroutines
    }
}
```

**Regra:** nunca chame `GetComponent<>()` dentro de `Update()` ou `FixedUpdate()` — cache em `Awake()`.

### Ordem de execução

```
Awake (todos) → Start (todos) → [por frame] Update → FixedUpdate → LateUpdate → Render
```

---

## 2. Física

### Rigidbody (objeto físico dinâmico)

```csharp
private Rigidbody _rb;

private void Awake() => _rb = GetComponent<Rigidbody>();

private void FixedUpdate()
{
    // Movimento com força (respeita física)
    _rb.AddForce(Vector3.forward * speed, ForceMode.Force);

    // Impulso instantâneo (pulo)
    if (_isGrounded && Input.GetKeyDown(KeyCode.Space))
        _rb.AddForce(Vector3.up * jumpForce, ForceMode.Impulse);

    // Velocidade direta (plataformer simples)
    _rb.linearVelocity = new Vector3(inputX * speed, _rb.linearVelocity.y, 0f);
}
```

### ForceMode

| ForceMode | Quando usar |
|---|---|
| `Force` | Força contínua (propulsão, vento) |
| `Impulse` | Impacto instantâneo (pulo, explosão) |
| `Acceleration` | Ignora massa — útil para personagens |
| `VelocityChange` | Muda velocidade diretamente, ignora massa |

### Colliders e Layers

```csharp
// Detectar colisão
private void OnCollisionEnter(Collision col)
{
    if (col.gameObject.CompareTag("Ground"))
        _isGrounded = true;
}

private void OnCollisionExit(Collision col)
{
    if (col.gameObject.CompareTag("Ground"))
        _isGrounded = false;
}

// Trigger (sem física, somente detecção)
private void OnTriggerEnter(Collider other)
{
    if (other.CompareTag("Collectible"))
    {
        score++;
        Destroy(other.gameObject);
    }
}
```

**Layers:** configure colisão entre layers em **Edit → Project Settings → Physics → Layer Collision Matrix**. Nunca use string de tag para lógica de colisão crítica — use `LayerMask`.

### Raycast

```csharp
// Checar se está no chão
private bool CheckGrounded()
{
    return Physics.Raycast(transform.position, Vector3.down, 1.1f, groundLayer);
}

// Raycast com informação de hit
if (Physics.Raycast(camera.position, camera.forward, out RaycastHit hit, 100f))
{
    Debug.Log($"Hit: {hit.collider.name} at {hit.point}");
}
```

---

## 3. Arquitetura

### ScriptableObject (dados desacoplados do código)

```csharp
// Definição
[CreateAssetMenu(fileName = "EnemyData", menuName = "Game/Enemy Data")]
public class EnemyData : ScriptableObject
{
    public float health;
    public float speed;
    public float damage;
    public Sprite sprite;
}

// Uso no script de inimigo
public class Enemy : MonoBehaviour
{
    [SerializeField] private EnemyData data;

    private float _currentHealth;

    private void Start() => _currentHealth = data.health;

    public void TakeDamage(float amount)
    {
        _currentHealth -= amount;
        if (_currentHealth <= 0) Die();
    }
}
```

ScriptableObjects permitem criar variantes de inimigos no Inspector sem duplicar código.

### Prefabs e Object Pooling

```csharp
public class ObjectPool<T> : MonoBehaviour where T : MonoBehaviour
{
    [SerializeField] private T prefab;
    [SerializeField] private int poolSize = 20;
    private Queue<T> _pool = new();

    private void Awake()
    {
        for (int i = 0; i < poolSize; i++)
        {
            var obj = Instantiate(prefab);
            obj.gameObject.SetActive(false);
            _pool.Enqueue(obj);
        }
    }

    public T Get()
    {
        if (_pool.Count == 0) return Instantiate(prefab); // fallback
        var obj = _pool.Dequeue();
        obj.gameObject.SetActive(true);
        return obj;
    }

    public void Return(T obj)
    {
        obj.gameObject.SetActive(false);
        _pool.Enqueue(obj);
    }
}
```

### Sistema de eventos C# (desacoplamento)

```csharp
// Em vez de referências diretas, use eventos estáticos
public static class GameEvents
{
    public static event Action<int> OnScoreChanged;
    public static event Action OnPlayerDied;
    public static event Action<float> OnHealthChanged;

    public static void RaiseScore(int score)     => OnScoreChanged?.Invoke(score);
    public static void RaisePlayerDied()          => OnPlayerDied?.Invoke();
    public static void RaiseHealthChanged(float h) => OnHealthChanged?.Invoke(h);
}

// Subscriber (UI, audio, etc.)
private void OnEnable()  => GameEvents.OnScoreChanged += UpdateScoreUI;
private void OnDisable() => GameEvents.OnScoreChanged -= UpdateScoreUI; // SEMPRE desregistrar
```

---

## 4. Build e Distribuição

### Build Settings

**File → Build Settings** → selecionar plataforma → **Switch Platform** → **Build**.

| Plataforma | Pré-requisitos |
|---|---|
| WebGL | Nenhum; funciona em qualquer browser moderno |
| Windows | Nenhum |
| macOS | Somente em Mac; exige signing para fora da App Store |
| Android | Android SDK + JDK (configurar em Preferences → External Tools) |
| iOS | Somente em Mac + Xcode |

### WebGL — itch.io

```
Build Settings → WebGL → Build
```

Gera pasta com `index.html` + `Build/` + `StreamingAssets/`. Zipar e fazer upload no itch.io como HTML5.

**Otimizações WebGL:**
```
Player Settings → WebGL:
  Compression Format: Gzip (melhor compatibilidade) ou Brotli (menor tamanho)
  Publishing Settings → Enable Exceptions: None (reduz tamanho)
```

### PC Standalone

```
Build Settings → Windows (ou macOS, Linux) → Build
```

Para Steam: instalar Steamworks SDK + plugin Facepunch.Steamworks ou SteamManager.

### Mobile — Android

```
Build Settings → Android → Build
```

Signing: **Player Settings → Android → Publishing Settings → Keystore Manager** — crie um keystore próprio; nunca perca o keystore.

---

## Documentação Unity

- Unity Manual (Unity 6): https://docs.unity3d.com/Manual/index.html
- Unity Docs unificados: https://docs.unity.com/en-us
- Scripting API C#: https://docs.unity3d.com/ScriptReference/
- Unity Learn (tutoriais): https://learn.unity.com/
- Unity Physics: https://docs.unity3d.com/Manual/PhysicsSection.html

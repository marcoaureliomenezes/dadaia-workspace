---
name: game-platform-godot
description: >
  Plataforma Nível 2: Godot Engine v4.x para jogos 2D e 3D indie. Cobre arquitetura de
  nodes e scenes, GDScript, física 2D (CharacterBody2D, RigidBody2D), sistema de signals,
  export para HTML5/desktop/mobile e integração com itch.io via Butler. Use quando o
  projeto exigir editor visual, exportação multiplataforma ou arquitetura de cena robusta.
applyTo: "repos/redacted-slug/**"
---

# game-platform-godot

Referência para desenvolvimento com Godot Engine v4.x. Carregue esta skill ao migrar um
jogo browser para Godot ou ao criar um novo jogo com editor visual.

---

## Quando usar Godot no lugar de Phaser/Three.js

| Sinal | Razão para migrar para Godot |
|---|---|
| Cenas complexas com muitos objetos interagindo | Editor visual acelera composição |
| Precisa exportar para Android ou iOS | Godot exporta nativamente |
| Física de plataformer com slopes e ramps | CharacterBody2D + `move_and_slide` |
| Animações de sprites com AnimationPlayer | Editor visual de animação |
| Jogo multiplataforma (PC + mobile + web) | Um projeto, múltiplos exports |

**Não migre** somente porque o jogo ficou grande. Phaser + boa arquitetura escala bem para jogos 2D.

---

## 1. Arquitetura: Node e Scene

Tudo no Godot é um **Node**. Cenas são árvores de nodes salvas em `.tscn`.

```
GameScene (Node2D)          ← cena raiz
  ├── Player (CharacterBody2D)
  │     ├── Sprite2D
  │     ├── CollisionShape2D
  │     └── Camera2D
  ├── TileMap
  ├── Enemies (Node2D)      ← container para grupo de inimigos
  │     ├── Slime (instância de Slime.tscn)
  │     └── Bat  (instância de Bat.tscn)
  └── UI (CanvasLayer)
        ├── HealthBar
        └── ScoreLabel
```

**Regra:** nodes filho dependem do pai, nunca ao contrário. Comunicação entre irmãos: via Signal.

### Scene instancing

```gdscript
# Instanciar uma cena via código
var BulletScene = preload("res://scenes/Bullet.tscn")

func fire():
    var bullet = BulletScene.instantiate()
    bullet.position = $Muzzle.global_position
    bullet.direction = Vector2.RIGHT.rotated(rotation)
    get_parent().add_child(bullet)
```

---

## 2. GDScript

### Estrutura de script

```gdscript
extends CharacterBody2D

# Constantes (nomeadas, nunca magic numbers)
const SPEED      = 200.0
const JUMP_FORCE = 450.0
const GRAVITY    = 800.0

# Variáveis
var health: int = 100
var is_on_floor_custom: bool = false

# Signals
signal player_died
signal health_changed(new_health: int)

func _ready() -> void:
    # Chamado quando o node entra na árvore
    pass

func _process(delta: float) -> void:
    # Lógica não-física: UI, input, timers
    pass

func _physics_process(delta: float) -> void:
    # Física: movimento, colisão — use este, não _process
    _handle_movement(delta)
    move_and_slide()

func _handle_movement(delta: float) -> void:
    if not is_on_floor():
        velocity.y += GRAVITY * delta

    var direction = Input.get_axis("move_left", "move_right")
    velocity.x = direction * SPEED

    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = -JUMP_FORCE

func take_damage(amount: int) -> void:
    health -= amount
    health_changed.emit(health)
    if health <= 0:
        player_died.emit()
        queue_free()
```

### Tipos e anotações

```gdscript
@export var speed: float = 200.0       # editável no Inspector
@onready var sprite = $Sprite2D        # referência após _ready
@onready var anim   = $AnimationPlayer

var pos: Vector2 = Vector2(100, 200)
var vel: Vector2 = Vector2.ZERO

# Arrays e dicionários
var enemies: Array[Node2D] = []
var stats: Dictionary = { "score": 0, "lives": 3 }
```

---

## 3. Física 2D

### CharacterBody2D (plataformer, personagem controlável)

```gdscript
extends CharacterBody2D

func _physics_process(delta: float) -> void:
    # Gravidade
    if not is_on_floor():
        velocity.y += GRAVITY * delta
        velocity.y = min(velocity.y, MAX_FALL_SPEED)

    # Movimento horizontal
    var dir = Input.get_axis("ui_left", "ui_right")
    if dir != 0:
        velocity.x = dir * SPEED
    else:
        velocity.x = move_toward(velocity.x, 0, FRICTION * delta)

    # Pulo
    if Input.is_action_just_pressed("ui_accept") and is_on_floor():
        velocity.y = -JUMP_FORCE

    # Aplicar movimento + resposta de colisão automática
    move_and_slide()
```

### RigidBody2D (física dinâmica — caixas, projéteis)

```gdscript
extends RigidBody2D

func _ready() -> void:
    # Impulso inicial
    apply_impulse(Vector2(200, -300))

func _on_body_entered(body: Node) -> void:
    if body.is_in_group("player"):
        body.take_damage(damage)
    queue_free()
```

### StaticBody2D (plataformas, chão)

```gdscript
# Geralmente sem script — apenas Node + CollisionShape2D
# Para plataformas móveis:
extends StaticBody2D

@export var move_speed: float = 100.0
var direction: int = 1

func _physics_process(delta: float) -> void:
    position.x += move_speed * direction * delta
    if position.x > RIGHT_LIMIT or position.x < LEFT_LIMIT:
        direction *= -1
```

---

## 4. Sistema de Signals

Signals são a forma canônica de comunicação entre nodes no Godot. Evite referências diretas entre nodes não relacionados.

```gdscript
# Emitir signal
signal enemy_killed(points: int)

func die() -> void:
    enemy_killed.emit(score_value)
    queue_free()

# Conectar signal no _ready
func _ready() -> void:
    $Enemy.enemy_killed.connect(_on_enemy_killed)

func _on_enemy_killed(points: int) -> void:
    score += points
    $UI/ScoreLabel.text = str(score)
```

### Autoload (Singleton) para estado global

```gdscript
# GameManager.gd — declarado como Autoload em Project Settings
extends Node

var score: int = 0
var lives: int = 3

signal score_changed
signal game_over

func add_score(points: int) -> void:
    score += points
    score_changed.emit()

func lose_life() -> void:
    lives -= 1
    if lives <= 0:
        game_over.emit()
```

---

## 5. Export de Projeto

### Configurar Export Templates

1. **Project → Export → Add...** → escolher plataforma
2. Para HTML5: instalar export templates via **Editor → Manage Export Templates**
3. Verificar que `index.html` gerado abre no browser sem servidor local (para testes simples)

### HTML5 (itch.io)

```
Project → Export → Web (Runnable) → Export Project
```

Gera pasta com `index.html` + `game.pck` + `game.wasm`. Zipar e fazer upload no itch.io.

### Desktop (Windows / Linux / macOS)

```
Project → Export → Windows Desktop → Export Project
```

Para macOS: exige assinatura via Xcode (em mac) ou notarização para distribuição fora do itch.io.

### Mobile (Android)

1. Instalar Android SDK + JDK
2. Configurar em **Editor Settings → Export → Android**
3. **Project → Export → Android → Export Project** → gera `.apk`

---

## Documentação Godot

- Docs v4.x: https://docs.godotengine.org/en/stable/index.html
- GDScript Basics: https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/gdscript_basics.html
- Física 2D: https://docs.godotengine.org/en/stable/tutorials/physics/physics_introduction.html
- CharacterBody2D: https://docs.godotengine.org/en/stable/classes/class_characterbody2d.html

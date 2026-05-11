---
name: game-physics-engine
description: >
  Motor de física para game development: game loop com delta time, máquina de estados,
  cinemática (Euler e Verlet), gravidade, atrito, impulso, colisão (AABB, Circle, SAT),
  spatial hashing, balística e sistemas de partículas. Referência técnica completa para
  implementar física frame-rate independent em qualquer plataforma.
applyTo: "repos/redacted-slug/**"
---

# game-physics-engine

Referência técnica de física para jogos. Carregue esta skill antes de implementar qualquer
mecânica de movimento, colisão ou projéteis.

---

## 1. Game Loop e Tempo

### requestAnimationFrame (browser)

```js
let lastTime = 0;

function gameLoop(timestamp) {
  const dt = Math.min((timestamp - lastTime) / 1000, 0.05); // cap em 50ms
  lastTime = timestamp;

  processInput();
  update(dt);
  render();

  requestAnimationFrame(gameLoop);
}
requestAnimationFrame(gameLoop);
```

**Cap obrigatório em dt:** sem cap, uma aba em background acumula dt gigante e explode o estado.
Use `Math.min(dt, 0.05)` — nunca simule mais de 50ms de uma vez.

### Separação de concerns (lei)

```
processInput()  → captura e normaliza input; nunca aplica movimento
update(dt)      → física, colisão, lógica; nunca renderiza
render()        → lê estado imutável e desenha; nunca modifica estado
```

Qualquer código que misture essas três fases cria bugs impossíveis de reproduzir.

### Máquina de estados do jogo

```js
const State = { MENU: 'MENU', PLAYING: 'PLAYING', PAUSED: 'PAUSED', GAME_OVER: 'GAME_OVER' };
let state = State.MENU;

function update(dt) {
  switch (state) {
    case State.MENU:    updateMenu(dt);   break;
    case State.PLAYING: updateGame(dt);   break;
    case State.PAUSED:  updatePaused(dt); break;
    case State.GAME_OVER: updateGameOver(dt); break;
  }
}

function setState(next) {
  state = next; // transição explícita — nunca implícita por flags booleanas
}
```

Nunca use `if (playing && !paused && !dead && started)` — isso é estado implícito e acumula bugs.

---

## 2. Física e Movimento

### Integração de Euler (padrão para a maioria dos jogos)

```js
// A cada frame
velocity.x += acceleration.x * dt;
velocity.y += acceleration.y * dt;
position.x += velocity.x * dt;
position.y += velocity.y * dt;
```

Simples e suficiente para a maioria dos jogos. Instável com dt variável grande — use cap.

### Integração de Verlet (mais estável para colisão)

```js
const newX = position.x * 2 - prevPosition.x + acceleration.x * dt * dt;
const newY = position.y * 2 - prevPosition.y + acceleration.y * dt * dt;
prevPosition = { ...position };
position = { x: newX, y: newY };
// Velocidade derivada: velocity = (position - prevPosition) / dt
```

Prefira Verlet quando objetos colidem com frequência e precisam de estabilidade.

### Constantes nomeadas (regra absoluta)

```js
// ERRADO — magic numbers
velocity.y += 0.5;
if (velocity.y > 12) velocity.y = 12;

// CORRETO — constantes nomeadas
const GRAVITY     = 800;  // px/s²
const MAX_FALL    = 600;  // px/s
const JUMP_FORCE  = 450;  // px/s
const MOVE_SPEED  = 200;  // px/s
const FRICTION    = 8;    // coeficiente

velocity.y = Math.min(velocity.y + GRAVITY * dt, MAX_FALL);
```

### Mecânicas fundamentais

```js
// Gravidade
velocity.y += GRAVITY * dt;

// Atrito (horizontal, no chão)
if (onGround) velocity.x *= Math.pow(1 - FRICTION * dt, 1);

// Impulso (pulo)
function jump() {
  if (onGround) {
    velocity.y = -JUMP_FORCE;
    onGround = false;
  }
}

// Aceleração por input
if (keys.left)  velocity.x -= ACCEL * dt;
if (keys.right) velocity.x += ACCEL * dt;
velocity.x = Math.max(-MAX_SPEED, Math.min(MAX_SPEED, velocity.x));
```

---

## 3. Colisão e Hitbox

### AABB (Axis-Aligned Bounding Box) — mais comum

```js
function aabbOverlap(a, b) {
  return a.x < b.x + b.w &&
         a.x + a.w > b.x &&
         a.y < b.y + b.h &&
         a.y + a.h > b.y;
}

// Resolução de colisão: empurrar o objeto para fora
function resolveAABB(moving, static_) {
  const overlapX = Math.min(moving.x + moving.w, static_.x + static_.w) - Math.max(moving.x, static_.x);
  const overlapY = Math.min(moving.y + moving.h, static_.y + static_.h) - Math.max(moving.y, static_.y);

  if (overlapX < overlapY) {
    // colisão lateral
    moving.x += moving.x < static_.x ? -overlapX : overlapX;
    moving.velocity.x = 0;
  } else {
    // colisão vertical
    moving.y += moving.y < static_.y ? -overlapY : overlapY;
    if (moving.y < static_.y) { moving.onGround = true; }
    moving.velocity.y = 0;
  }
}
```

### Circle vs Circle

```js
function circleOverlap(a, b) {
  const dx = a.x - b.x, dy = a.y - b.y;
  const distSq = dx * dx + dy * dy;
  const radSum = a.radius + b.radius;
  return distSq < radSum * radSum; // evita sqrt quando só precisa de bool
}

function circleDistance(a, b) {
  const dx = a.x - b.x, dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}
```

### SAT (Separating Axis Theorem) — polígonos convexos

Use somente quando AABB e Circle não forem suficientes (hitboxes irregulares).

```js
function satOverlap(polyA, polyB) {
  const axes = [...getNormals(polyA), ...getNormals(polyB)];
  for (const axis of axes) {
    const projA = project(polyA, axis);
    const projB = project(polyB, axis);
    if (projA.max < projB.min || projB.max < projA.min) return false; // separação encontrada
  }
  return true;
}

function getNormals(poly) {
  return poly.vertices.map((v, i) => {
    const next = poly.vertices[(i + 1) % poly.vertices.length];
    const edge = { x: next.x - v.x, y: next.y - v.y };
    return { x: -edge.y, y: edge.x }; // normal perpendicular
  });
}
```

### Spatial Hashing — performance com muitos objetos

```js
class SpatialHash {
  constructor(cellSize) {
    this.cellSize = cellSize;
    this.cells = new Map();
  }
  _key(x, y) { return `${Math.floor(x/this.cellSize)},${Math.floor(y/this.cellSize)}`; }
  insert(obj) {
    const key = this._key(obj.x, obj.y);
    if (!this.cells.has(key)) this.cells.set(key, []);
    this.cells.get(key).push(obj);
  }
  query(x, y, radius) {
    const results = [];
    const r = Math.ceil(radius / this.cellSize);
    const cx = Math.floor(x / this.cellSize);
    const cy = Math.floor(y / this.cellSize);
    for (let dx = -r; dx <= r; dx++)
      for (let dy = -r; dy <= r; dy++) {
        const key = `${cx+dx},${cy+dy}`;
        if (this.cells.has(key)) results.push(...this.cells.get(key));
      }
    return results;
  }
  clear() { this.cells.clear(); }
}
```

Reduz colisão de O(n²) para O(n). Use quando houver > 50 objetos colidindo.

---

## 4. Balística e Projéteis

### Trajetória linear

```js
class Projectile {
  constructor(x, y, angle, speed) {
    this.pos = { x, y };
    this.vel = { x: Math.cos(angle) * speed, y: Math.sin(angle) * speed };
    this.alive = true;
    this.damage = PROJECTILE_DAMAGE;
  }

  update(dt) {
    this.pos.x += this.vel.x * dt;
    this.pos.y += this.vel.y * dt;

    // Destroy fora dos limites — nunca deixar acumular
    if (this.pos.x < -50 || this.pos.x > WORLD_W + 50 ||
        this.pos.y < -50 || this.pos.y > WORLD_H + 50) {
      this.alive = false;
    }
  }
}
```

### Trajetória parabólica (com gravidade)

```js
update(dt) {
  this.vel.y += PROJECTILE_GRAVITY * dt; // gravidade própria do projétil
  this.pos.x += this.vel.x * dt;
  this.pos.y += this.vel.y * dt;
}
```

### Sistema de disparo com cooldown

```js
class Weapon {
  constructor() {
    this.cooldown = 0;
    this.projectiles = [];
  }

  update(dt) {
    this.cooldown = Math.max(0, this.cooldown - dt);
    // limpar projéteis mortos
    this.projectiles = this.projectiles.filter(p => p.alive);
    for (const p of this.projectiles) p.update(dt);
  }

  fire(x, y, angle) {
    if (this.cooldown > 0) return;
    this.projectiles.push(new Projectile(x, y, angle, BULLET_SPEED));
    this.cooldown = 1 / FIRE_RATE; // FIRE_RATE em shots/segundo
  }
}
```

---

## 5. Animações e Partículas

### Spritesheet frame-by-frame

```js
class Animator {
  constructor(frameCount, frameDuration) {
    this.frameCount    = frameCount;
    this.frameDuration = frameDuration; // segundos por frame
    this.currentFrame  = 0;
    this.timer         = 0;
  }

  update(dt) {
    this.timer += dt;
    if (this.timer >= this.frameDuration) {
      this.timer = 0;
      this.currentFrame = (this.currentFrame + 1) % this.frameCount;
    }
  }

  // sourceX para spritesheet horizontal
  get srcX() { return this.currentFrame * FRAME_WIDTH; }
}
```

### Easing functions

```js
const ease = {
  linear:   t => t,
  easeIn:   t => t * t,
  easeOut:  t => t * (2 - t),
  easeInOut: t => t < 0.5 ? 2*t*t : -1+(4-2*t)*t,
  elastic:  t => Math.pow(2,-10*t) * Math.sin((t-0.075)*(2*Math.PI)/0.3) + 1,
};
```

### Pool de partículas (sem garbage collection)

```js
class ParticleSystem {
  constructor(maxParticles = 200) {
    this.pool = Array.from({ length: maxParticles }, () => ({ alive: false }));
  }

  emit(x, y, count = 10) {
    let emitted = 0;
    for (const p of this.pool) {
      if (p.alive) continue;
      p.alive  = true;
      p.x = x; p.y = y;
      p.vx = (Math.random() - 0.5) * 300;
      p.vy = (Math.random() - 0.5) * 300 - 100;
      p.life = 1.0;
      p.decay = Math.random() * 1.5 + 0.5;
      p.r = Math.random() * 3 + 1;
      if (++emitted >= count) break;
    }
  }

  update(dt) {
    for (const p of this.pool) {
      if (!p.alive) continue;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += 200 * dt; // gravidade leve
      p.life -= p.decay * dt;
      if (p.life <= 0) p.alive = false;
    }
  }

  render(ctx) {
    for (const p of this.pool) {
      if (!p.alive) continue;
      ctx.globalAlpha = p.life;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
}
```

Reutilize objetos do pool — nunca crie `new Particle()` dentro do loop de update.

---
name: game-map-architect
description: >
  Arquitetura de mapas e câmera para jogos: tilemap, geração procedural, chunk loading,
  câmera que segue o jogador com lerp, scrolling e parallax multicamada, efeitos de câmera
  (shake, flash, zoom) e UI/HUD separada do espaço de mundo. Referência para qualquer
  jogo com mapa maior que a tela.
applyTo: "repos/redacted-slug/**"
---

# game-map-architect

Referência técnica para mapas, câmera e UI de jogo. Carregue esta skill ao implementar
qualquer mecânica de mundo maior que a tela, scrolling, parallax ou HUD.

---

## 1. Fundamentos de Mapa

### Tilemap

Um tilemap é uma grade de índices. Cada índice aponta para um tile em um tileset.

```js
const TILE_SIZE = 32; // px

const map = [
  [1, 1, 1, 1, 1, 1, 1],
  [1, 0, 0, 0, 0, 0, 1],
  [1, 0, 2, 0, 2, 0, 1],
  [1, 1, 1, 1, 1, 1, 1],
];

// Coordenadas de tile → coordenadas de mundo
function tileToWorld(col, row) {
  return { x: col * TILE_SIZE, y: row * TILE_SIZE };
}

// Renderizar somente tiles visíveis
function renderTilemap(ctx, camera) {
  const startCol = Math.floor(camera.x / TILE_SIZE);
  const startRow = Math.floor(camera.y / TILE_SIZE);
  const endCol   = Math.ceil((camera.x + SCREEN_W) / TILE_SIZE);
  const endRow   = Math.ceil((camera.y + SCREEN_H) / TILE_SIZE);

  for (let row = startRow; row < endRow; row++) {
    for (let col = startCol; col < endCol; col++) {
      const tileId = map[row]?.[col];
      if (!tileId) continue;
      const screenX = col * TILE_SIZE - camera.x;
      const screenY = row * TILE_SIZE - camera.y;
      drawTile(ctx, tileId, screenX, screenY);
    }
  }
}
```

**Renderize somente os tiles visíveis** — nunca itere sobre o mapa inteiro a cada frame.

### Geração Procedural com ruído

```js
// Simplex/Perlin noise para terreno suave
function generateTerrain(width, seed = 42) {
  const terrain = [];
  for (let x = 0; x < width; x++) {
    // noise retorna valor em [0, 1]
    const height = Math.floor(noise(x * 0.05 + seed) * 10 + 5);
    terrain.push(height);
  }
  return terrain;
}

// Geração de chunk: mundo infinito em pedaços
const CHUNK_SIZE = 16; // tiles por chunk

function getOrGenerateChunk(chunkX) {
  if (chunks.has(chunkX)) return chunks.get(chunkX);
  const chunk = generateChunk(chunkX);
  chunks.set(chunkX, chunk);
  return chunk;
}
```

**Seed determinística:** o mesmo seed sempre gera o mesmo mapa. Essencial para multiplayer e debug.

### Chunk Loading

```js
function updateChunks(playerX) {
  const currentChunk = Math.floor(playerX / (CHUNK_SIZE * TILE_SIZE));
  const loadRadius   = 2; // chunks ao redor do jogador

  for (let cx = currentChunk - loadRadius; cx <= currentChunk + loadRadius; cx++) {
    getOrGenerateChunk(cx);
  }

  // Descarregar chunks distantes
  for (const [cx] of chunks) {
    if (Math.abs(cx - currentChunk) > loadRadius + 1) {
      chunks.delete(cx);
    }
  }
}
```

---

## 2. Câmera

### Coordenadas: mundo vs. tela

```
Mundo:  posição absoluta de todos os objetos (pode ser enorme)
Tela:   o que o jogador vê agora = posição de mundo - câmera

screenX = worldX - camera.x
screenY = worldY - camera.y
```

**Nunca misture** coordenadas de mundo e tela na mesma variável. Nomeie explicitamente.

### Câmera rígida (segue imediatamente)

```js
const camera = { x: 0, y: 0 };

function updateCamera(player) {
  camera.x = player.x - SCREEN_W / 2;
  camera.y = player.y - SCREEN_H / 2;

  // Limites do mundo
  camera.x = Math.max(0, Math.min(camera.x, WORLD_W - SCREEN_W));
  camera.y = Math.max(0, Math.min(camera.y, WORLD_H - SCREEN_H));
}
```

### Câmera suave com lerp (preferida)

```js
const CAMERA_LERP = 5; // maior = mais ágil; 3–8 é o range agradável

function updateCamera(player, dt) {
  const targetX = player.x - SCREEN_W / 2;
  const targetY = player.y - SCREEN_H / 2;

  camera.x += (targetX - camera.x) * CAMERA_LERP * dt;
  camera.y += (targetY - camera.y) * CAMERA_LERP * dt;

  camera.x = Math.max(0, Math.min(camera.x, WORLD_W - SCREEN_W));
  camera.y = Math.max(0, Math.min(camera.y, WORLD_H - SCREEN_H));
}
```

### Câmera com dead zone (câmera só move se jogador sair da zona)

```js
const DEAD_ZONE = { w: SCREEN_W * 0.3, h: SCREEN_H * 0.3 };

function updateCamera(player) {
  const dzLeft   = camera.x + SCREEN_W / 2 - DEAD_ZONE.w / 2;
  const dzRight  = camera.x + SCREEN_W / 2 + DEAD_ZONE.w / 2;
  const dzTop    = camera.y + SCREEN_H / 2 - DEAD_ZONE.h / 2;
  const dzBottom = camera.y + SCREEN_H / 2 + DEAD_ZONE.h / 2;

  if (player.x < dzLeft)  camera.x -= dzLeft - player.x;
  if (player.x > dzRight) camera.x += player.x - dzRight;
  if (player.y < dzTop)   camera.y -= dzTop - player.y;
  if (player.y > dzBottom) camera.y += player.y - dzBottom;
}
```

---

## 3. Scrolling e Parallax

### Parallax multicamada

Cada camada se move a uma velocidade proporcional à sua profundidade.
Camadas mais "distantes" movem mais devagar — cria ilusão de profundidade.

```js
const layers = [
  { image: 'sky',     speed: 0.1 },  // fundo distante
  { image: 'mountains', speed: 0.3 },
  { image: 'trees',   speed: 0.6 },
  { image: 'ground',  speed: 1.0 },  // mesmo speed da câmera
];

function renderParallax(ctx, cameraX) {
  for (const layer of layers) {
    const offsetX = cameraX * layer.speed % SCREEN_W;
    // renderizar 2 cópias para scroll contínuo
    ctx.drawImage(assets[layer.image], -offsetX, 0);
    ctx.drawImage(assets[layer.image], SCREEN_W - offsetX, 0);
  }
}
```

### Scroll infinito (Phaser tileSprite)

```js
// Em Phaser, scroll infinito em 1 linha
this.bg = this.add.tileSprite(0, 0, SCREEN_W, SCREEN_H, 'background');
this.bg.setScrollFactor(0); // fixa no espaço de tela

// No update:
this.bg.tilePositionX += SCROLL_SPEED * dt * 60; // normalizar com dt
```

### Scroll manual (canvas puro)

```js
let bgScrollX = 0;

function update(dt) {
  bgScrollX += BG_SCROLL_SPEED * dt;
  if (bgScrollX >= BG_WIDTH) bgScrollX -= BG_WIDTH;
}

function render(ctx) {
  ctx.drawImage(bgImage, -bgScrollX, 0);
  if (bgScrollX > 0) ctx.drawImage(bgImage, BG_WIDTH - bgScrollX, 0);
}
```

---

## 4. Efeitos de Câmera

Todos os efeitos de câmera funcionam como **offsets** aplicados no momento de renderizar.
Nunca transforme a posição real dos objetos — modifique somente o que a câmera "vê".

### Camera Shake

```js
const shake = { duration: 0, intensity: 0, offsetX: 0, offsetY: 0 };

function startShake(duration, intensity) {
  shake.duration  = duration;
  shake.intensity = intensity;
}

function updateShake(dt) {
  if (shake.duration <= 0) {
    shake.offsetX = 0; shake.offsetY = 0;
    return;
  }
  shake.duration -= dt;
  const progress  = shake.duration > 0 ? shake.duration / SHAKE_MAX_DURATION : 0;
  shake.offsetX   = (Math.random() - 0.5) * 2 * shake.intensity * progress;
  shake.offsetY   = (Math.random() - 0.5) * 2 * shake.intensity * progress;
}

// Ao renderizar: adicionar shake.offsetX/Y à posição da câmera
function applyCamera(ctx) {
  ctx.setTransform(1, 0, 0, 1,
    -(camera.x + shake.offsetX),
    -(camera.y + shake.offsetY));
}
```

### Flash de tela

```js
const flash = { alpha: 0, color: '#fff', decay: 3 };

function startFlash(color = '#fff', alpha = 1) {
  flash.color = color;
  flash.alpha = alpha;
}

function renderFlash(ctx) {
  if (flash.alpha <= 0) return;
  ctx.globalAlpha = flash.alpha;
  ctx.fillStyle   = flash.color;
  ctx.fillRect(0, 0, SCREEN_W, SCREEN_H);
  ctx.globalAlpha = 1;
  flash.alpha = Math.max(0, flash.alpha - flash.decay * dt);
}
```

### Zoom

```js
let zoom = 1;
let targetZoom = 1;
const ZOOM_LERP = 4;

function setZoom(target) { targetZoom = target; }

function updateZoom(dt) {
  zoom += (targetZoom - zoom) * ZOOM_LERP * dt;
}

function applyCamera(ctx) {
  ctx.setTransform(
    zoom, 0, 0, zoom,
    SCREEN_W / 2 - camera.x * zoom,
    SCREEN_H / 2 - camera.y * zoom
  );
}
```

---

## 5. UI de Jogo / HUD

A UI vive no **espaço de tela**, não no espaço de mundo. Renderize sempre após resetar a transformação da câmera.

```js
function render(ctx) {
  // 1. Aplicar câmera
  applyCamera(ctx);

  // 2. Renderizar mundo (entidades, tiles, partículas)
  renderWorld(ctx);

  // 3. Resetar câmera antes da UI
  ctx.setTransform(1, 0, 0, 1, 0, 0);

  // 4. Renderizar HUD (score, vida, munição)
  renderHUD(ctx);
}
```

### HUD: elementos comuns

```js
function renderHUD(ctx) {
  // Score (canto superior direito)
  ctx.font = '24px monospace';
  ctx.fillStyle = '#fff';
  ctx.textAlign = 'right';
  ctx.fillText(`SCORE: ${score}`, SCREEN_W - 16, 32);

  // Vida (barras, canto superior esquerdo)
  for (let i = 0; i < MAX_HEALTH; i++) {
    ctx.fillStyle = i < currentHealth ? '#e33' : '#333';
    ctx.fillRect(16 + i * 28, 16, 24, 16);
  }

  // Munição
  ctx.textAlign = 'left';
  ctx.fillText(`${ammo} / ${maxAmmo}`, 16, SCREEN_H - 16);
}

// Minimapa
function renderMinimap(ctx) {
  const scale = 0.05; // mundo × 5% = minimapa
  const mmX = SCREEN_W - MINIMAP_W - 8;
  const mmY = 8;
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.fillRect(mmX, mmY, MINIMAP_W, MINIMAP_H);

  // Jogador no minimapa
  ctx.fillStyle = '#0f0';
  ctx.fillRect(
    mmX + player.x * scale,
    mmY + player.y * scale,
    4, 4
  );
}
```

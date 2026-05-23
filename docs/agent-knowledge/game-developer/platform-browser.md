---
name: game-platform-browser
description: >
  Plataforma Nível 1: jogos 2D e 3D no browser sem build step. Cobre Phaser.js v4 (2D),
  Three.js (3D procedural), Babylon.js (3D PBR), setup via CDN, estrutura de projeto,
  padrões de cena e física. Inclui todos os links de documentação oficial. Use quando
  implementar redacted-slug-trex (Phaser), redacted-slug (Three.js) ou qualquer jogo browser-first.
applyTo: "repos/redacted-slug/**"
---

# game-platform-browser

Referência para jogos 2D e 3D que rodam direto no browser. Carregue esta skill ao
trabalhar em `redacted-slug-trex` (Phaser.js) ou `redacted-slug` (Three.js).

---

## Quando usar

| Engine | Quando | Stack atual em redacted-slug |
|---|---|---|
| Phaser.js v4 | Jogos 2D com física, sprites, tilemaps | `redacted-slug-trex` |
| Three.js | 3D procedural, geometria programática, N64 aesthetic | `redacted-slug` |
| Babylon.js | 3D com PBR, raycasting, ferramentas de debug visuais | — |

**Regra do workspace:** sem build step — tudo via CDN. Abrir `index.html` direto no browser é o fluxo.

---

## Phaser.js v4

### Setup via CDN

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Meu Jogo</title>
</head>
<body>
<script src="https://cdn.jsdelivr.net/npm/phaser@4/dist/phaser.min.js"></script>
<script src="src/game.js"></script>
</body>
</html>
```

### Estrutura de jogo com cenas

```js
class MenuScene extends Phaser.Scene {
  constructor() { super({ key: 'MenuScene' }); }

  create() {
    this.add.text(400, 300, 'PRESS SPACE', { fontSize: '32px', fill: '#fff' })
        .setOrigin(0.5);
    this.input.keyboard.once('keydown-SPACE', () => {
      this.scene.start('GameScene');
    });
  }
}

class GameScene extends Phaser.Scene {
  constructor() { super({ key: 'GameScene' }); }

  preload() {
    // Assets gerados proceduralmente: não carregue arquivos externos
  }

  create() {
    // Física arcade
    this.physics.world.gravity.y = 800;

    // Jogador
    this.player = this.physics.add.sprite(100, 300, 'player');
    this.player.setCollideWorldBounds(true);

    // Plataformas
    this.platforms = this.physics.add.staticGroup();
    this.platforms.add(this.add.rectangle(400, 568, 800, 32, 0x666666));

    // Colisão declarativa
    this.physics.add.collider(this.player, this.platforms);

    // Input
    this.cursors = this.input.keyboard.createCursorKeys();
  }

  update(time, delta) {
    const dt = delta / 1000;

    if (this.cursors.left.isDown)  this.player.setVelocityX(-200);
    else if (this.cursors.right.isDown) this.player.setVelocityX(200);
    else this.player.setVelocityX(0);

    if (this.cursors.up.isDown && this.player.body.blocked.down) {
      this.player.setVelocityY(-500);
    }
  }
}

const config = {
  type: Phaser.AUTO,
  width: 800,
  height: 600,
  backgroundColor: '#1a1a2e',
  physics: { default: 'arcade', arcade: { gravity: { y: 0 }, debug: false } },
  scene: [MenuScene, GameScene],
};

new Phaser.Game(config);
```

### Física: Arcade vs Matter.js

| Arcade | Matter.js |
|---|---|
| AABB simples, muito rápido | Física de corpos rígidos completa |
| Ideal para plataformer, shoot 'em up | Ideal para puzzles com física real |
| `physics: { default: 'arcade' }` | `physics: { default: 'matter' }` |

### Scroll infinito com tileSprite

```js
// No create():
this.bg = this.add.tileSprite(400, 300, 800, 600, 'background');
this.bg.setScrollFactor(0); // não se move com câmera

// No update():
this.bg.tilePositionX += 2; // pixels por frame — normalize com delta
```

### Câmera que segue o jogador

```js
// No create():
this.cameras.main.startFollow(this.player, true, 0.1, 0.1); // lerp x, lerp y
this.cameras.main.setBounds(0, 0, WORLD_W, WORLD_H);
```

### Grupos e colisão declarativa

```js
// Grupo de inimigos
this.enemies = this.physics.add.group();
this.enemies.create(500, 200, 'enemy');

// Colisão: jogador vs inimigos
this.physics.add.overlap(this.player, this.enemies, this.onPlayerHit, null, this);

// Colisão estática: balas vs plataformas
this.physics.add.collider(this.bullets, this.platforms, (bullet) => {
  bullet.destroy();
});
```

### Geração procedural de sprites (sem assets externos)

```js
function createPlayerTexture(scene) {
  const g = scene.add.graphics();
  g.fillStyle(0x00aaff);
  g.fillRect(0, 0, 32, 48);
  g.fillStyle(0xffffff);
  g.fillCircle(16, 12, 10); // cabeça
  g.generateTexture('player', 32, 48);
  g.destroy();
}
```

### Documentação Phaser

- API Reference v4: https://docs.phaser.io/api-documentation/api-documentation
- Getting Started: https://docs.phaser.io/phaser/getting-started/making-your-first-phaser-game
- Arcade Physics: https://docs.phaser.io/phaser/concepts/physics/arcade
- Examples (5000+): https://phaser.io/examples
- MDN Physics Tutorial: https://developer.mozilla.org/en-US/docs/Games/Tutorials/2D_breakout_game_Phaser/Physics

---

## Three.js

### Setup via CDN com importmap

```html
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/"
  }
}
</script>
<script type="module" src="src/main.js"></script>
```

### Estrutura mínima

```js
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const scene  = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 5, 10);
camera.lookAt(0, 0, 0);

// Luz
scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const dirLight = new THREE.DirectionalLight(0xffffff, 1);
dirLight.position.set(5, 10, 5);
scene.add(dirLight);

// Objeto
const geo = new THREE.BoxGeometry(1, 1, 1);
const mat = new THREE.MeshLambertMaterial({ color: 0x00aaff });
const cube = new THREE.Mesh(geo, mat);
scene.add(cube);

// Loop
let prevTime = performance.now();
function animate() {
  requestAnimationFrame(animate);
  const now = performance.now();
  const dt  = Math.min((now - prevTime) / 1000, 0.05);
  prevTime  = now;

  cube.rotation.y += dt;
  renderer.render(scene, camera);
}
animate();
```

### N64 Low-Poly Aesthetic (redacted-slug)

```js
// Material flat shading — sem interpolação de normais
const mat = new THREE.MeshLambertMaterial({
  color: 0xff4400,
  flatShading: true,  // estética N64/PS1
});

// Geometria de avião procedural
function createPlane() {
  const geo = new THREE.BufferGeometry();
  const vertices = new Float32Array([
    0, 0, -2,   // nariz
   -1, 0,  1,   // asa esquerda
    1, 0,  1,   // asa direita
    0, 0.3, 0.5, // dorso
  ]);
  const indices = [0,1,3, 0,3,2, 1,2,3, 0,2,1];
  geo.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return new THREE.Mesh(geo, mat);
}

// Fog para profundidade estilizada
scene.fog = new THREE.Fog(0x001133, 50, 300);

// Renderização pixelada (look retro)
renderer.setPixelRatio(0.5); // metade da resolução nativa
```

### Câmera rig para shoot 'em up 3D

```js
// Câmera fixa acima, olhando para baixo e levemente à frente
camera.position.set(0, 15, 8);
camera.lookAt(0, 0, -5);

// Câmera que segue jogador (horizontal apenas)
function updateCamera(playerPos) {
  camera.position.x += (playerPos.x - camera.position.x) * 0.05;
}
```

### Documentação Three.js

- Docs: https://threejs.org/docs/
- Manual: https://threejs.org/manual/
- Examples: https://threejs.org/examples/

---

## Babylon.js

### Quando usar no lugar de Three.js

- Precisa de raycasting com resultado rico (picking)
- Precisa de materiais PBR realistas com environment maps
- Quer usar o Inspector (debugger visual em runtime)
- Precisa de câmera Arc Rotate, Follow Camera nativas

### Setup via CDN

```html
<script src="https://cdn.babylonjs.com/babylon.js"></script>
<script src="https://cdn.babylonjs.com/babylon.gui.min.js"></script>
```

### Estrutura mínima

```js
const canvas  = document.getElementById('canvas');
const engine  = new BABYLON.Engine(canvas, true);
const scene   = new BABYLON.Scene(engine);

// Câmera
const camera  = new BABYLON.ArcRotateCamera('cam', -Math.PI/2, Math.PI/3, 10,
                BABYLON.Vector3.Zero(), scene);
camera.attachControl(canvas, true);

// Luz
new BABYLON.HemisphericLight('light', new BABYLON.Vector3(0,1,0), scene);

// Mesh
BABYLON.MeshBuilder.CreateBox('box', { size: 1 }, scene);

engine.runRenderLoop(() => scene.render());
window.addEventListener('resize', () => engine.resize());
```

### Documentação Babylon.js

- Docs: https://doc.babylonjs.com/
- Playground (editor online): https://playground.babylonjs.com/

---

## Estrutura de arquivos recomendada (sem build step)

```
meu-jogo/
  index.html         ← entrada; carrega CDN + src/game.js
  src/
    game.js          ← config + instância do jogo/engine
    scenes/
      MenuScene.js
      GameScene.js
    entities/
      Player.js
      Enemy.js
      Projectile.js
    systems/
      PhysicsSystem.js
      InputSystem.js
    utils/
      constants.js   ← TODAS as constantes nomeadas aqui
      math.js
  tests/
    game.spec.js     ← Playwright
```

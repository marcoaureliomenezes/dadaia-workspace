---
name: game-packaging-distribution
description: >
  Empacotar e distribuir jogos para cada plataforma: Phaser/Three.js para GitHub Pages e
  itch.io, Godot para HTML5/desktop/mobile com Butler CLI, Unity para WebGL/PC/mobile/Steam,
  UE5 para Shipping build e lojas AAA. Inclui checklist universal de release e guia de
  versionamento. Use antes de qualquer publicação de jogo.
applyTo: "repos/redacted-slug/**"
---

# game-packaging-distribution

Referência completa para empacotar e distribuir jogos. Carregue esta skill antes de
preparar qualquer release, seja browser, desktop ou mobile.

---

## Nível 1 — Browser (Phaser.js / Three.js)

Jogos browser-first sem build step são os mais simples de distribuir.
O artefato é a própria pasta do projeto: `index.html` + `src/` + libs CDN.

### GitHub Pages (distribuição gratuita, sem servidor)

```bash
# Opção A: branch gh-pages manual
git checkout -b gh-pages
git push origin gh-pages
# Ativar em: repo Settings → Pages → Source: gh-pages branch

# Opção B: gh-pages CLI (automatizado)
npm install -g gh-pages
gh-pages -d .   # publica o diretório atual no branch gh-pages

# URL resultante: https://<user>.github.io/<repo>/
```

**Para redacted-slug:** cada jogo em subpasta → URL `github.io/redacted-slug/redacted-slug-trex/`

### itch.io — HTML5 Upload

1. Criar conta em itch.io → New Project → Kind: HTML
2. Zipar a pasta do jogo (incluindo `index.html` na raiz do zip)
3. Upload → marcar "This file is played in the browser"
4. Configurar viewport: largura e altura do canvas
5. Embed options: `Embed in page` (não `Click to launch`)

```bash
# Estrutura do zip para itch.io
meu-jogo.zip
  index.html       ← OBRIGATÓRIO na raiz
  src/
    game.js
  # NÃO incluir node_modules, .git, etc.
```

### Verificação antes do upload

```bash
# Testar localmente com servidor HTTP (nunca file://)
python3 -m http.server 8080
# Abrir: http://localhost:8080

# Verificar que não há imports com caminho absoluto quebrado
grep -r "file://" src/

# Verificar que o jogo funciona sem internet (CDN offline check)
# Testar com Network throttling "Offline" no DevTools
```

---

## Nível 2 — Godot

### Configurar Export Templates

```
Editor → Manage Export Templates → Download and Install
```

Obrigatório antes de qualquer export. Templates são versionados — use a mesma versão do editor.

### HTML5 (Web)

```
Project → Export → Add → Web (Runnable) → Export Project
```

Gera: `index.html`, `game.pck`, `game.wasm`, `game.js`, `game.audio.worklet.js`

```bash
# Zipar para itch.io
cd export/html5
zip -r ../meu-jogo-web.zip .

# Testar localmente (Godot 4 exige SharedArrayBuffer — use servidor com headers corretos)
python3 -m http.server 8080
# Ou usar Godot's built-in export preview
```

**Nota:** itch.io suporta Godot HTML5 nativamente com os headers corretos ativados na configuração do projeto.

### Desktop — Windows / Linux / macOS

```
Project → Export → Add → Windows Desktop → Export Project → .exe
Project → Export → Add → Linux/X11 → Export Project → binário
Project → Export → Add → macOS → Export Project → .app (em Mac)
```

### itch.io via Butler CLI (automatizado)

Butler é a CLI oficial do itch.io para uploads automatizados.

```bash
# Instalar Butler
curl -L -o butler.zip https://broth.itch.ovh/butler/linux-amd64/LATEST/archive/default
unzip butler.zip && chmod +x butler

# Autenticar (uma vez)
./butler login

# Upload (channel = plataforma)
./butler push meu-jogo-win.zip usuario/meu-jogo:windows
./butler push meu-jogo-linux.zip usuario/meu-jogo:linux
./butler push meu-jogo-html5.zip usuario/meu-jogo:html5

# Butler detecta diff entre uploads — somente envia o que mudou
```

### Mobile — Android

```bash
# Pré-requisitos
export ANDROID_HOME=~/Android/Sdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk

# Configurar em Godot: Editor Settings → Export → Android
# Assinar: Project → Export → Android → Keystore

# Exportar .apk
Project → Export → Android → Export Project
```

---

## Nível 3 — Unity

### WebGL para itch.io

```
File → Build Settings → WebGL → Switch Platform → Build

# Configurações recomendadas para itch.io:
Player Settings → Resolution: Full Screen (deferred), 960x540
Player Settings → WebGL → Compression Format: Gzip
Player Settings → WebGL → Enable Exceptions: None
```

```bash
# Zipar output
cd Build/WebGL
zip -r ../../meu-jogo-webgl.zip .

# Upload no itch.io → Kind: HTML → This file is played in the browser
# Ativar: SharedArrayBuffer support (opcional, para melhor performance)
```

### PC Standalone

```
File → Build Settings → Windows, Mac, Linux → Build
```

Para distribuição via itch.io: zipar o diretório do build inteiro (`.exe` + `_Data/`).

### Steam (Steamworks)

```bash
# 1. Criar conta: partner.steamgames.com (taxa única USD 100 por jogo)
# 2. Configurar AppID no Steamworks Portal
# 3. Integrar SDK (usar plugin Facepunch.Steamworks para Unity)

# Upload via SteamCMD
./steamcmd.exe
  +login <usuario>
  +run_app_build app_build_<appid>.vdf
  +quit

# app_build.vdf (VDF = Valve Data Format)
"AppBuild" {
  "AppID"    "1234567"
  "Desc"     "v1.0.0 release"
  "ContentRoot" ".\build\"
  "BuildOutput" ".\logs\"
  "Depots" {
    "1234568" { "FileMapping" { "LocalPath" "*" "DepotPath" "." "recursive" "1" } }
  }
}
```

### Mobile — Android (Unity)

```
File → Build Settings → Android → Switch Platform → Build and Run

# Signing: Player Settings → Android → Publishing Settings → Keystore Manager
# NUNCA perca o keystore — sem ele é impossível atualizar o app publicado
```

---

## Nível 4 — Unreal Engine 5

### Shipping Build

```
Platforms → [Target] → Package Project
Build Configuration: Shipping (nunca Development para release)
```

Diferença crítica:
- **Development:** logs, console UE, profiler — para debug
- **Shipping:** otimizado, sem console, sem símbolos de debug — para release

### Configurações de Packaging

```
Project Settings → Packaging:
  Full Rebuild: On (para release final; Off para iterações de dev)
  Compress Content: On (reduz tamanho do package)
  Blueprint Nativization: Inclusive (converte Blueprint para C++ no build)
  Create Compressed Cooked Packages: On
```

### Steam

```
# 1. Registrar na Steamworks (USD 100 por AppID)
# 2. Integrar Online Subsystem Steam
# Project Settings → Plugins → Online Subsystem Steam → Enable
# DefaultEngine.ini:
[OnlineSubsystem]
DefaultPlatformService=Steam

[OnlineSubsystemSteam]
bEnabled=true
SteamDevAppId=480  # usar AppID real em produção
```

### Epic Games Store

```
# Exige acordo de publisher com a Epic
# Integrar Epic Online Services SDK
# Via plugin: EOS (Epic Online Services) Plugin for Unreal Engine
```

---

## Checklist Universal de Release

Execute este checklist antes de qualquer publicação, independente da plataforma.

### Versão e metadados

- [ ] Versão incrementada (semver: MAJOR.MINOR.PATCH)
- [ ] CHANGELOG.md atualizado com o que mudou
- [ ] README.md com instruções de como jogar
- [ ] Screenshots (mínimo 3, formato recomendado: 16:9, 1280x720)
- [ ] Ícone do jogo (256x256 PNG sem fundo transparente)
- [ ] Nome do jogo consistente em todos os lugares

### Qualidade

- [ ] Jogo abre sem erros no console do browser (F12)
- [ ] Testado em Chrome, Firefox e Safari (para jogos browser)
- [ ] Framerate estável (use performance.now() ou Stats panel)
- [ ] Game Over e tela de menu funcionam corretamente
- [ ] Inputs respondem sem delay perceptível
- [ ] Sem memory leaks em sessão de 10+ minutos

### Conteúdo

- [ ] Nenhum placeholder ("TEST", "TODO", "DEBUG") visível
- [ ] Nenhum console.log() deixado no código (ou desabilitado)
- [ ] Nenhuma tecla de debug ativa (invencibilidade, skip de fase, etc.)
- [ ] Créditos presentes (autores, assets de terceiros, licenças)

### Build

- [ ] Build limpo a partir de zero (não incremental)
- [ ] Testado o artefato final (não o dev server)
- [ ] Tamanho do artefato verificado (jogos browser: < 50MB sem justificativa)

### Git

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## Versionamento de Jogos

Use semver adaptado para jogos:

| Componente | Quando incrementar |
|---|---|
| MAJOR (1.x.x) | Mudança de plataforma ou reformulação completa do jogo |
| MINOR (x.1.x) | Nova fase, novo personagem, nova mecânica |
| PATCH (x.x.1) | Bug fix, ajuste de balanceamento, correção de texto |

```bash
# Criar release no GitHub
gh release create v1.2.0 ./build/*.zip \
  --title "v1.2.0 — Nova fase: Floresta" \
  --notes "$(cat CHANGELOG.md | head -30)"
```

<!--
PROMOVIDO → `dadaia-workspace-brand-identity-v1` (2026-05-17):
  paleta + tokens CSS + logo rinoceronte SVG. Ver
  `specs/releases/dadaia-workspace-brand-identity-v1/SPEC.md` (Status: Em revisão).
PROMOVIDO → `agent-monitoring-v1` (2026-05-17):
  monitoramento de agentes via panel (4 abas, reader Python stdlib).
  Ver `specs/releases/agent-monitoring-v1/SPEC.md` (Status: Em revisão).
-->

We need to evolve our taua-games aero-fighters creating the aero-fighters V2.


Based on his web version, now the v2 bring more realism, different and more advance technologies and more fun.


The stack is more complex.


See the stack in:


Plano: Criar Mapa Fotorrealista de Inhaúma em Unreal Engine 5
Este plano detalha os passos para criar um novo projeto em Unreal Engine 5 e usar o plugin Cesium for Unreal para streamar um mapa 3D fotorrealista da região de Inhaúma, MG, usando os dados do Google Maps.

1. Preparação do Ambiente
Ação: Criar um novo projeto "Blank" em Unreal Engine 5, com a configuração "Blueprint" e qualidade "Maximum".
Justificativa: Um projeto limpo é o ideal para começar. A qualidade máxima garante que Lumen e outras features de renderização estejam ativas por padrão, o que é essencial para o realismo.
2. Instalação do Plugin Cesium for Unreal
Ação: Baixar e instalar o plugin gratuito "Cesium for Unreal" a partir da Epic Games Marketplace para o projeto recém-criado.
Justificativa: O Cesium é a tecnologia-chave que conecta a Unreal Engine aos dados geoespaciais 3D do mundo real, permitindo o streaming de mapas em tempo real.
3. Configuração do Mapa 3D (Cesium)
Ação:
No nível padrão, remover os objetos de exemplo (piso, paredes).
Adicionar o ator CesiumGeoreference ao nível. Este ator ancora o mundo virtual no mundo real.
Adicionar o ator Cesium World Terrain + Bing Maps Aerial Imagery a partir do painel Cesium. Isso servirá como uma camada base de baixa resolução para o globo terrestre.
Adicionar um novo ator Cesium3DTileset e nomeá-lo GooglePhotorealisticTiles.
Na configuração do GooglePhotorealisticTiles, na seção "Source", selecionar a opção From URL.
Ponto Crítico: Para acessar os dados do Google, você precisará criar uma chave de API na Google Maps Platform (com a API "Map Tiles" ativada). Vou precisar que você me forneça essa chave para inserir no campo URL do Tileset.
No ator CesiumGeoreference, definir a origem do mundo para as coordenadas de Inhaúma, MG: Latitude: -19.47, Longitude: -44.46, Height: 800 (metros).
No ator GooglePhotorealisticTiles, habilitar a opção Show Credits On Screen para cumprir os termos de serviço do Google.
Justificativa: Este é o processo padrão para configurar o Cesium para streamar os dados 3D fotorrealistas do Google. A georreferência é crucial para posicionar o mapa corretamente.
4. Configuração do Jogador e Iluminação
Ação:
Adicionar um Player Start ao nível e posicioná-lo a uma altitude segura acima do terreno (ex: 2000 metros acima da altura base).
Adicionar um CesiumSunSky ao nível para uma iluminação realista baseada em data e hora. Ele substituirá a iluminação padrão.
Justificativa: O CesiumSunSky proporciona uma iluminação georreferenciada que muda dinamicamente, aumentando drasticamente o realismo do cenário para um jogo de voo.


To plan it we will use thw folowing workflow:

product engineer receives the demand.

- Do a dadaia-grill to understand the demand and the vision of it.
- Spawn the following agents:
  - software-architect: Analyze how will be the architecture and implementation of the new game based on the stack.
  - game-designer: Help to design the game, the mechanics, the fun part of it.
  - game-developer: Help to implement the game, based on the design and the architecture defined.
  - game-tester: Help to test the game, giving feedback about the fun and the mechanics of it.
  - devops-engineer: Will plan the pipeline to distribute the game to the users.

The Stack is Unreal engine and Cesium. And others. See this plan gave by an specialist.


Plano: Criar Mapa Fotorrealista de Inhaúma em Unreal Engine 5
Este plano detalha os passos para criar um novo projeto em Unreal Engine 5 e usar o plugin Cesium for Unreal para streamar um mapa 3D fotorrealista da região de Inhaúma, MG, usando os dados do Google Maps.

1. Preparação do Ambiente
Ação: Criar um novo projeto "Blank" em Unreal Engine 5, com a configuração "Blueprint" e qualidade "Maximum".
Justificativa: Um projeto limpo é o ideal para começar. A qualidade máxima garante que Lumen e outras features de renderização estejam ativas por padrão, o que é essencial para o realismo.
2. Instalação do Plugin Cesium for Unreal
Ação: Baixar e instalar o plugin gratuito "Cesium for Unreal" a partir da Epic Games Marketplace para o projeto recém-criado.
Justificativa: O Cesium é a tecnologia-chave que conecta a Unreal Engine aos dados geoespaciais 3D do mundo real, permitindo o streaming de mapas em tempo real.
3. Configuração do Mapa 3D (Cesium)
Ação:
No nível padrão, remover os objetos de exemplo (piso, paredes).
Adicionar o ator CesiumGeoreference ao nível. Este ator ancora o mundo virtual no mundo real.
Adicionar o ator Cesium World Terrain + Bing Maps Aerial Imagery a partir do painel Cesium. Isso servirá como uma camada base de baixa resolução para o globo terrestre.
Adicionar um novo ator Cesium3DTileset e nomeá-lo GooglePhotorealisticTiles.
Na configuração do GooglePhotorealisticTiles, na seção "Source", selecionar a opção From URL.
Ponto Crítico: Para acessar os dados do Google, você precisará criar uma chave de API na Google Maps Platform (com a API "Map Tiles" ativada). Vou precisar que você me forneça essa chave para inserir no campo URL do Tileset.
No ator CesiumGeoreference, definir a origem do mundo para as coordenadas de Inhaúma, MG: Latitude: -19.47, Longitude: -44.46, Height: 800 (metros).
No ator GooglePhotorealisticTiles, habilitar a opção Show Credits On Screen para cumprir os termos de serviço do Google.
Justificativa: Este é o processo padrão para configurar o Cesium para streamar os dados 3D fotorrealistas do Google. A georreferência é crucial para posicionar o mapa corretamente.
4. Configuração do Jogador e Iluminação
Ação:
Adicionar um Player Start ao nível e posicioná-lo a uma altitude segura acima do terreno (ex: 2000 metros acima da altura base).
Adicionar um CesiumSunSky ao nível para uma iluminação realista baseada em data e hora. Ele substituirá a iluminação padrão.
Justificativa: O CesiumSunSky proporciona uma iluminação georreferenciada que muda dinamicamente, aumentando drasticamente o realismo do cenário para um jogo de voo.
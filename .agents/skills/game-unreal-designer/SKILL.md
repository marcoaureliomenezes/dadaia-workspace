---
name: game-unreal-designer
description: >
  UE5 profundo para design: World Partition, Landscape, PCG, Nanite, Lumen, Megascans/Fab.
  Protocolo de pesquisa e curadoria de mapas e assets de fontes públicas seguras
  (OSM, USGS, NASA EarthData, OpenTopography, Sketchfab CC, ArtStation).
applyTo: "repos/redacted-slug/redacted-slug-v2/**"
trusted_sources:
  - dev.epicgames.com
  - forums.unrealengine.com
  - openstreetmap.org
  - earthexplorer.usgs.gov
  - earthdata.nasa.gov
  - opentopography.org
  - sketchfab.com
  - fab.com
  - artstation.com
  - freesound.org
  - cesium.com/learn
  - sidefx.com/docs
  - gdal.org
  - qgis.org
---

# game-unreal-designer

Referência técnica de UE5 para o game-designer. Carregue ao implementar level design,
pipeline geoespacial ou configuração de iluminação em redacted-slug-v2.

---

## 1. World Partition + Sublevels

```
World Partition = streaming automático de cells do mundo
  └── Cada cell: 128m x 128m (padrão, ajustável)
        └── Ativa/desativa baseado em posição do player

Sublevels = agrupamento manual de actors em layers temáticos
  ├── SL_Terrain    → landscape + terrain meshes
  ├── SL_Buildings  → estruturas urbanas
  ├── SL_VFX        → effects, weather
  └── SL_Gameplay   → triggers, spawn points (gerenciado pelo game-developer)
```

**Regra:** game-designer gerencia SL_Terrain, SL_Buildings, SL_VFX.
SL_Gameplay é exclusivo do game-developer.

---

## 2. Nanite para Meshes Fotogramétricos

```python
# Python no UE5 Editor para configurar Nanite em batch:
import unreal

assets = unreal.EditorAssetLibrary.list_assets("/Game/Photogrammetry/", recursive=True)
for asset_path in assets:
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if isinstance(asset, unreal.StaticMesh):
        asset.set_editor_property("nanite_settings",
            unreal.MeshNaniteSettings(enabled=True, position_precision=1.0))
        unreal.EditorAssetLibrary.save_asset(asset_path)
```

---

## 3. Lumen — Configuração Recomendada

```ini
# DefaultEngine.ini
[/Script/Engine.RendererSettings]
r.Lumen.Reflections.Allow=1
r.Lumen.DiffuseIndirect.Allow=1
r.Lumen.HardwareRayTracing=1          # GPU RTX: melhor qualidade
r.Lumen.HardwareRayTracing=0          # Sem RTX: software fallback
r.Lumen.Scene.SurfaceCacheResolution=1.0
r.Shadow.Virtual.Enable=1             # Virtual Shadow Maps (obrigatório com Lumen)
```

**Sky Light:** sempre usar HDRI para base de iluminação realista. Avoid baked lightmaps.

---

## 4. PCG Framework — Vegetação e Scatter

```cpp
// PCGGraph para distribuição de árvores em terreno:
// 1. Surface Sampler → pontos no Landscape
// 2. Attribute Filter → slope < 30° (sem árvores em encostas íngremes)
// 3. Density Filter → baseado em altitude (altura = menos vegetação)
// 4. Static Mesh Spawner → sorteia de pool de N meshes de árvores
```

---

## 5. Protocolo de Pesquisa de Mapas

### Fontes permitidas e licenças

| Fonte | Dados | Licença | Atribuição |
|---|---|---|---|
| openstreetmap.org | Vias, edificações, infraestrutura | ODbL | Obrigatória |
| earthexplorer.usgs.gov | DEM, terrain, imagery | Domínio público (EUA) | Recomendada |
| earthdata.nasa.gov | Satellite imagery, SRTM | Domínio público | Recomendada |
| opentopography.org | LiDAR, point cloud | CC-BY / Open | Por dataset |
| sketchfab.com | 3D assets | CC (verificar por item) | Por item |
| fab.com | Megascans | Fab EULA | Incluída |

### Regra de segurança

**NUNCA usar Google Maps, Google Earth ou Street View para:**
- Reconstrução 3D
- Extração de dados geoespaciais
- Base de heightmap

Violação dessas diretrizes é proibida pela Google Geo Guidelines.

### Workflow de curadoria

```
1. Identificar área geográfica de interesse
2. WebSearch no USGS EarthExplorer → baixar DEM (GeoTIFF, WGS84)
3. WebSearch no OSM → exportar área como .osm ou via Overpass API
4. QGIS → reprojetar para CRS do projeto (UTM ou projeção local)
5. GDAL → gerar mosaico, recortar por AOI, exportar .tif
6. UE5 → importar heightmap via Landscape Import
7. Registrar fonte e licença no design report
```

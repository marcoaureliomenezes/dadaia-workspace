---
name: game-geospatial-pipeline
description: >
  Pipeline completo de dados geoespaciais para UE5: QGIS → GDAL/PDAL →
  RealityScan/Metashape → Cesium ion → Cesium for Unreal → UE5 Landscape.
  Estratégia de fidelidade em 3 escalas: regional, urbana e landmark.
applyTo: "repos/tauan-games/aero-fighters-v2/**"
---

# game-geospatial-pipeline

Pipeline de ponta a ponta para mapas realistas baseados em dados geoespaciais.

---

## 1. Estratégia de Fidelidade em 3 Escalas

| Escala | Método | Ferramenta | Fidelidade |
|---|---|---|---|
| Regional (>10km) | DEM heightfield + ortofoto | USGS/NASA → GDAL → UE5 Landscape | Macro relevo, vales, rios |
| Urbana (500m–10km) | 3D Tiles streamados | RealityScan → Cesium ion → Cesium for Unreal | Edificações, infraestrutura |
| Landmark (<500m) | Mesh local Nanite | RealityScan/Metashape → Nanite | Aeroporto, torre, base |

---

## 2. QGIS — Preparação e Validação

```bash
# Reprojetar DEM para UTM (necessário para importar no UE5):
# No QGIS Processing → Reproject Layer
# Source CRS: EPSG:4326 (WGS84)
# Target CRS: EPSG:32723 (UTM Zone 23S para Brasil)

# Inspecionar raster antes de exportar:
# Layer → Layer Properties → Information
# Verificar: CRS correto, nodata = -9999, unidade em metros
```

---

## 3. GDAL — Comandos Essenciais

```bash
# Reprojetar + recortar por bounding box:
gdalwarp -t_srs EPSG:32723 \
         -te xmin ymin xmax ymax \
         -r bilinear \
         input_dem.tif output_dem_utm.tif

# Normalizar para heightmap 16-bit PNG (UE5 usa R16):
gdal_translate -ot UInt16 -scale \
               output_dem_utm.tif heightmap_r16.png

# Verificar estatísticas:
gdalinfo -stats heightmap_r16.png
```

---

## 4. Cesium for Unreal — Setup

```
1. Instalar plugin Cesium for Unreal via Epic Games Marketplace
2. Criar conta Cesium ion (cesium.com/ion)
3. No UE5: Cesium panel → Sign In → conectar token
4. Add Cesium World Terrain (tile global de terreno)
5. Add Bing Maps Aerial imagery (ortofoto global)
6. Georeference Origin: definir lat/lon/alt do ponto central do mapa
```

```cpp
// Georreferenciamento no UE5:
ACesiumGeoreference* GeoRef = ACesiumGeoreference::GetDefaultGeoreference(GetWorld());
GeoRef->SetOriginLongitude(-46.6333);  // São Paulo como exemplo
GeoRef->SetOriginLatitude(-23.5505);
GeoRef->SetOriginHeight(800.0);        // Altitude em metros
```

---

## 5. Importar Heightmap no UE5 Landscape

```
1. Landscape tool → Import from File
2. Format: R16 (16-bit unsigned)
3. Scale Z: (max_altitude - min_altitude) * 100 / 512 cm
   Ex: (3000m - 0m) * 100 / 512 = 585.9 → usar 600
4. Após import: Landscape → Material → atribuir LandscapeMaterial com layers
```

---

## 6. Legal e Licenças

| Fonte | Licença | Obrigação |
|---|---|---|
| USGS EarthExplorer | Domínio público (dados federais EUA) | Atribuição recomendada |
| NASA EarthData / SRTM | Domínio público | Citar como "NASA SRTM data" |
| OpenStreetMap | ODbL | Atribuição obrigatória: "© OpenStreetMap contributors" |
| OpenTopography | CC-BY 4.0 (maioria) | Atribuição obrigatória por dataset |

**Proibições absolutas:**
- Não usar Google Maps, Google Earth ou Street View
- Não redistribuir dados com licença restritiva sem permissão
- Sempre registrar fonte e licença no design report

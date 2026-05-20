---
name: game-testing-ue5
description: >
  UE5 Functional Testing Framework, Gauntlet Automation, PIE screenshots, severity matrix
  e report HTML com evidências. Protocolo de pesquisa de bugs conhecidos antes de cada
  sessão de testes.
applyTo: "repos/tauan-games/aero-fighters-v2/**"
trusted_sources:
  - dev.epicgames.com
  - forums.unrealengine.com
  - issues.unrealengine.com
  - github.com
  - reddit.com/r/unrealengine
---

# game-testing-ue5

Referência para o game-tester. Carregue ao definir acceptance criteria ou executar
uma sessão de testes em aero-fighters-v2.

---

## 1. Protocolo Pré-Sessão (obrigatório)

Antes de qualquer sessão de testes:

```
1. WebSearch issues.unrealengine.com "UE5 <versão alvo> known issues"
2. WebSearch forums.unrealengine.com "<sistema testado> bug <versão>"
3. Registrar bugs conhecidos relevantes no report antes de testar
4. Isso evita reportar bugs da engine como bugs do jogo
```

---

## 2. UE5 Functional Testing Framework

### Setup básico

```cpp
// Criar FunctionalTest actor no level de teste:
// 1. Place Actor → FunctionalTest
// 2. Subclassificar em Blueprint ou C++

UCLASS()
class AFlight_Test_BasicControls : public AFunctionalTest
{
    GENERATED_BODY()

protected:
    virtual void PrepareTest() override
    {
        // Spawnar aeronave em posição conhecida
        FVector SpawnLoc(0, 0, 5000);  // 50m de altitude
        TestAircraft = GetWorld()->SpawnActor<APlayerAircraft>(SpawnLoc, FRotator::ZeroRotator);
    }

    virtual void StartTest() override
    {
        // Simular input de throttle completo por 5 segundos
        TestAircraft->SetThrottleInput(1.0f);
        SetTimer(5.0f);
    }

    void OnTimer()
    {
        // Verificar: velocidade deve ser > 200 knots após 5s com throttle máximo
        const float SpeedKnots = TestAircraft->GetAirspeed() * 0.000539957f;
        AssertTrue(SpeedKnots > 200.0f,
            FString::Printf(TEXT("Airspeed %f kts after 5s throttle"), SpeedKnots));
        FinishTest(EFunctionalTestResult::Succeeded, TEXT("Speed OK"));
    }
};
```

### Rodar via CLI

```bash
# Headless — sem abrir editor:
UnrealEditor-Cmd.exe "AeroFightersV2.uproject" \
  -ExecCmds="Automation RunTests Flight.BasicControls" \
  -Unattended -NullRHI -Log \
  -ReportOutputPath="TestResults/"
```

---

## 3. PIE Screenshot — Evidência Automatizada

```cpp
// No FunctionalTest, antes de AssertTrue:
void CaptureEvidence(const FString& TestName)
{
    const FString ScreenshotName = FString::Printf(
        TEXT("%s_%s"),
        *TestName,
        *FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"))
    );
    FScreenshotRequest::RequestScreenshot(ScreenshotName, false, false);
}
```

```bash
# Screenshots salvos em:
# <project>/Saved/Screenshots/WindowsEditor/
```

---

## 4. Formato do Quality Report

```html
<!-- Template obrigatório para quality report HTML -->
<!DOCTYPE html>
<html>
<head><title>Quality Report — {game} — {feature}</title></head>
<body>
<h1>Quality Report</h1>
<p><strong>Jogo:</strong> {game} | <strong>Feature:</strong> {feature}</p>
<p><strong>UE5 Version:</strong> {version} | <strong>Data:</strong> {date}</p>
<p><strong>Resultado:</strong> PASS / FAIL</p>

<h2>Sumário por Severity</h2>
<table>
  <tr><th>Severity</th><th>Total</th><th>Open</th></tr>
  <tr><td>Critical</td><td>{n}</td><td>{n}</td></tr>
  <tr><td>High</td><td>{n}</td><td>{n}</td></tr>
  <tr><td>Medium</td><td>{n}</td><td>{n}</td></tr>
  <tr><td>Low</td><td>{n}</td><td>{n}</td></tr>
</table>

<h2>Bugs Encontrados</h2>
<!-- Por cada bug: -->
<h3>BUG-{n}: {título} [{severity}] [{sub-domínio: lógica|design}]</h3>
<p><strong>Reproduced:</strong> {steps}</p>
<p><strong>Expected:</strong> {behavior}</p>
<p><strong>Actual:</strong> {behavior}</p>
<img src="{screenshot_path}" alt="Evidence screenshot"/>
<p><strong>Direcionar para:</strong> game-developer | game-designer</p>

<h2>Bugs Conhecidos da Engine (não contar como bugs do jogo)</h2>
<!-- Registrar bugs encontrados no protocolo pré-sessão -->
</body>
</html>
```

---

## 5. Severity Matrix

| Nível | Critério | Bloqueia deploy? |
|---|---|---|
| Critical | Crash, corrupção de dados, jogo inicia mas não fecha | Sim — sempre |
| High | Feature core quebrada sem workaround | Sim |
| Medium | Feature degradada, workaround disponível | Não (registrar como debt) |
| Low | Cosmético, não afeta gameplay | Não |

**Regra:** task só pode ser marcada `[x]` DONE se não houver bugs Critical ou High abertos.

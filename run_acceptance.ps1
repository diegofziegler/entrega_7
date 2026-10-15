param(
    [ValidateRange(1, 60)]
    [int]$HealthTimeoutMinutes = 10
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Stop-WithMessage {
    param([Parameter(Mandatory = $true)][string]$Message)
    throw $Message
}

function Invoke-RequiredCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host "`n> $Name $($Arguments -join ' ')" -ForegroundColor Cyan
    & $Name @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "El comando '$Name $($Arguments -join ' ')' terminó con código $LASTEXITCODE."
    }
}

function Read-DotEnv {
    param([Parameter(Mandatory = $true)][string]$Path)

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') {
            $value = $matches[2].Trim()
            if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            $values[$matches[1]] = $value
        }
    }
    return $values
}

function Test-RequiredConfiguration {
    $envPath = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
        Stop-WithMessage "No existe .env. Créalo con 'Copy-Item .env.example .env' y completa manualmente las API keys."
    }

    $values = Read-DotEnv -Path $envPath
    $provider = ([string]$values["LLM_PROVIDER"]).Trim().ToLowerInvariant()
    $providerKeyName = switch ($provider) {
        "gemini" { "GEMINI_API_KEY"; break }
        "groq"   { "GROQ_API_KEY"; break }
        "openai" { "OPENAI_API_KEY"; break }
        default  { Stop-WithMessage "LLM_PROVIDER debe ser gemini, groq u openai en .env." }
    }

    $requiredNames = @($providerKeyName, "OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_NAME")
    $missing = @($requiredNames | Where-Object { -not $values.ContainsKey($_) -or [string]::IsNullOrWhiteSpace([string]$values[$_]) })
    if ($missing.Count -gt 0) {
        Stop-WithMessage "Completa manualmente estos valores en .env: $($missing -join ', '). Las claves no se muestran ni se guardan en Git."
    }

    Write-Host "Configuración presente para LLM, embeddings OpenAI y Pinecone; no se mostrarán las claves." -ForegroundColor Green
    return $values
}

function Wait-ForReadyApi {
    param([Parameter(Mandatory = $true)][int]$TimeoutMinutes)

    $deadline = [DateTime]::UtcNow.AddMinutes($TimeoutMinutes)
    $lastProblem = "La API aún no respondió."
    Write-Host "`nEsperando health check listo en http://localhost:8000/health (máximo $TimeoutMinutes min)..." -ForegroundColor Cyan

    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 8
            if ($health.status -eq "ok" -and $health.rag_status -eq "active" -and $health.checkpointer -eq "redis") {
                Write-Host "API lista: status=$($health.status), rag_status=$($health.rag_status), checkpointer=$($health.checkpointer)." -ForegroundColor Green
                return
            }
            $lastProblem = "La API responde, pero aún no está lista: status=$($health.status), rag_status=$($health.rag_status), checkpointer=$($health.checkpointer)."
        }
        catch {
            $lastProblem = "Health check todavía no disponible: $($_.Exception.Message)"
        }
        Write-Host "$lastProblem Reintento en 5 segundos..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }

    Write-Host "`nÚltimos logs de la API:" -ForegroundColor Yellow
    & docker compose logs --tail 100 api
    Stop-WithMessage "Tiempo agotado esperando una API lista. $lastProblem Revisa .env, Pinecone y los logs anteriores. Los contenedores quedan activos para diagnóstico."
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Stop-WithMessage "No se encontró Docker. Instala/inicia Docker Desktop con Docker Compose."
    }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Stop-WithMessage "No se encontró uv. Instálalo antes de ejecutar este script."
    }

    $envConfig = Test-RequiredConfiguration

    $dockerInfo = & docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage "Docker no está iniciado o no está disponible. Inicia Docker Desktop y vuelve a ejecutar el script."
    }

    Invoke-RequiredCommand -Name "uv" -Arguments @("sync", "--frozen")
    Invoke-RequiredCommand -Name "docker" -Arguments @("compose", "up", "--build", "-d")
    Wait-ForReadyApi -TimeoutMinutes $HealthTimeoutMinutes

    $previousRedisUrl = $env:TEST_REDIS_URL
    $previousPhoenixEndpoint = $env:PHOENIX_COLLECTOR_ENDPOINT
    $previousPhoenixProject = $env:PHOENIX_PROJECT_NAME
    try {
        $env:TEST_REDIS_URL = "redis://localhost:6379"
        if (-not [string]::IsNullOrWhiteSpace([string]$envConfig["PHOENIX_COLLECTOR_ENDPOINT"])) {
            $env:PHOENIX_COLLECTOR_ENDPOINT = [string]$envConfig["PHOENIX_COLLECTOR_ENDPOINT"]
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$envConfig["PHOENIX_PROJECT_NAME"])) {
            $env:PHOENIX_PROJECT_NAME = [string]$envConfig["PHOENIX_PROJECT_NAME"]
        }
        Invoke-RequiredCommand -Name "uv" -Arguments @("run", "pytest", "-q")
        Invoke-RequiredCommand -Name "uv" -Arguments @("run", "python", "tests/test_5_preguntas.py")
    }
    finally {
        if ($null -eq $previousRedisUrl) {
            Remove-Item Env:TEST_REDIS_URL -ErrorAction SilentlyContinue
        }
        else {
            $env:TEST_REDIS_URL = $previousRedisUrl
        }
        if ($null -eq $previousPhoenixEndpoint) {
            Remove-Item Env:PHOENIX_COLLECTOR_ENDPOINT -ErrorAction SilentlyContinue
        }
        else {
            $env:PHOENIX_COLLECTOR_ENDPOINT = $previousPhoenixEndpoint
        }
        if ($null -eq $previousPhoenixProject) {
            Remove-Item Env:PHOENIX_PROJECT_NAME -ErrorAction SilentlyContinue
        }
        else {
            $env:PHOENIX_PROJECT_NAME = $previousPhoenixProject
        }
    }

    Write-Host "`nEjecución completa. API, Redis y Phoenix siguen activos para revisar http://localhost:6006." -ForegroundColor Green
    Write-Host "Trazas: trazas/spans.json | Log del test: tests/test_5_preguntas.log"
    Write-Host "Para detener el ambiente sin borrar el volumen de Redis: docker compose down"
}
catch {
    Write-Host "`nFALLO: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Los contenedores no se detuvieron; revisa el error y los logs con 'docker compose logs -f api'." -ForegroundColor Yellow
    exit 1
}

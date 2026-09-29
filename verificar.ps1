<#
.SYNOPSIS
    Ejecuta la misma verificacion que la integracion continua, en local.

.DESCRIPTION
    Los cuatro pasos, en el mismo orden y con los mismos comandos. Correrlo
    antes de subir evita el ciclo de "subir, esperar, ver el fallo, corregir".
#>
$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "  SGE-API - verificacion local" -ForegroundColor Cyan
Write-Host "  --------------------------------" -ForegroundColor DarkGray

$pasos = @(
    @{ nombre = 'Estilo (ruff)';      comando = { ruff check . } },
    @{ nombre = 'Tipado (mypy)';      comando = { mypy --strict app/ } },
    @{ nombre = 'Seguridad (bandit)'; comando = { bandit -r app/ -ll } },
    @{ nombre = 'Pruebas (pytest)';   comando = { pytest --cov=app --cov-report=term-missing } }
)

$fallos = 0
foreach ($paso in $pasos) {
    Write-Host ""
    Write-Host "  > $($paso.nombre)" -ForegroundColor Yellow
    try {
        & $paso.comando
        Write-Host "    OK" -ForegroundColor Green
    } catch {
        Write-Host "    FALLA: $_" -ForegroundColor Red
        $fallos++
    }
}

Write-Host ""
if ($fallos -eq 0) {
    Write-Host "  Los cuatro pasos pasan." -ForegroundColor Green
    exit 0
}
Write-Host "  $fallos paso(s) con hallazgos." -ForegroundColor Red
exit 1

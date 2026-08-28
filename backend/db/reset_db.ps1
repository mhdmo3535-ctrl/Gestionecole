# Recrée la base "gestionecole" à partir de zéro (schema + seed).
# Usage :  .\db\reset_db.ps1
# Nécessite psql (PostgreSQL 18) dans le PATH ou à l'emplacement par défaut.

$ErrorActionPreference = "Stop"

$psql = (Get-Command psql -ErrorAction SilentlyContinue).Source
if (-not $psql) {
    $psql = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $psql) { throw "psql.exe introuvable. Ajoute PostgreSQL\bin au PATH." }

$dbName = "gestionecole"
$pgUser = if ($env:PGUSER) { $env:PGUSER } else { "postgres" }
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Suppression et recréation de la base '$dbName'..." -ForegroundColor Cyan
& $psql -U $pgUser -h localhost -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $dbName;"
& $psql -U $pgUser -h localhost -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $dbName;"

Write-Host "Application du schéma..." -ForegroundColor Cyan
& $psql -U $pgUser -h localhost -d $dbName -v ON_ERROR_STOP=1 -f "$here\schema.sql"

Write-Host "Chargement des données de départ..." -ForegroundColor Cyan
& $psql -U $pgUser -h localhost -d $dbName -v ON_ERROR_STOP=1 -f "$here\seed.sql"

Write-Host "Chargement des matières et coefficients..." -ForegroundColor Cyan
& $psql -U $pgUser -h localhost -d $dbName -v ON_ERROR_STOP=1 -f "$here\seed_coefficients.sql"

Write-Host "Base '$dbName' prête." -ForegroundColor Green

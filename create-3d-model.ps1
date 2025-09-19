param(
    [Parameter(Mandatory = $true)]
    [string]$InputDir
)

$InputDir = (Resolve-Path $InputDir).Path
$outputDir = Join-Path $InputDir "models"
$projectName = Split-Path $InputDir -Leaf
$modelFile = Join-Path $outputDir "$projectName.glb"
$projectFile = Join-Path $outputDir "$projectName.rsproj"

# Create output directory
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

# RealityScan command
$rsArgs = @(
    "-headless",
    "-addFolder", $InputDir,
    "-align",
    "-setReconstructionRegionAuto", 
    "-calculateHighModel",
    "-calculateTexture",
    "-exportModel", "`"Model 1`"", $modelFile,
    "-save", $projectFile,
    "-quit"
)

Write-Host "Generating 3D model for directory: $inputDir"
Start-Process -FilePath "C:\Program Files\Epic Games\RealityScan_2.0\RealityScan.exe" -ArgumentList $rsArgs -NoNewWindow -Wait
Write-Host "3D model exported: ${modelFile}"

param(
  [Parameter(Mandatory = $true)][string]$InputDir,
  [int]$Throttle = 0,
  [int]$ThreadsPerProc = 0
)

$InputDir = (Resolve-Path $InputDir).Path

$jpgs = Get-ChildItem -Path $InputDir -Filter *.jpg -File -Recurse
if (-not $jpgs) { Write-Host "No .jpg files in $InputDir"; exit 0 }

$logical = [Environment]::ProcessorCount

if ($ThreadsPerProc -le 0) {
  if     ($logical -ge 32) { $ThreadsPerProc = 4 }
  elseif ($logical -ge 16) { $ThreadsPerProc = 3 }
  elseif ($logical -ge 8)  { $ThreadsPerProc = 2 }
  else                     { $ThreadsPerProc = 1 }
}

if ($Throttle -le 0) {
  $Throttle = [Math]::Max(1, [Math]::Floor($logical / $ThreadsPerProc))
}

$jpgs | ForEach-Object -Parallel {
    $base    = [IO.Path]::GetFileNameWithoutExtension($_.Name)
    $outPath = Join-Path $_.DirectoryName ($base + ".mask.png")

    if (Test-Path $outPath) {
        Write-Host "Skipping $($_.FullName) (mask exists)"
        return
    }

    $args = @()
    if ($using:ThreadsPerProc -gt 0) { $args += @("-limit","thread",$using:ThreadsPerProc) }
    $args += @(
      $_.FullName,
      "-colorspace","Gray",
      "-blur","0x1",
      "-auto-level",
      "-threshold","4%",
      "-define","connected-components:keep-top=2",
      "-connected-components","8",
      "-type","bilevel",
      $outPath
    )

    Write-Host "Processing $($_.FullName)"
    & magick @args | Out-Null
    Write-Host "Mask written to $outPath"
} -ThrottleLimit $Throttle

param([string]$Deck = 'candidate.pptx')
$ErrorActionPreference = 'Stop'
$existingPowerPoint = @(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$deckPath = if ([IO.Path]::IsPathRooted($Deck)) { $Deck } else { Join-Path $PSScriptRoot $Deck }
$previewPath = Join-Path $PSScriptRoot 'preview.png'
$presentation = $null
$powerPoint = New-Object -ComObject PowerPoint.Application
try {
    $presentation = $powerPoint.Presentations.Open($deckPath, -1, 0, 0)
    $slide = $presentation.Slides.Item(1)
    $slide.Export($previewPath, 'PNG', 1600, 900)
    Write-Output "PowerPoint rendered $($presentation.Slides.Count) slide, $($slide.Shapes.Count) shapes"
} finally {
    if ($null -ne $presentation) { $presentation.Close() }
    if (-not $existingPowerPoint) { $powerPoint.Quit() }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint)
}

$ErrorActionPreference = 'Stop'
$existingPowerPoint = @(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$deckPath = 'C:\Users\hiond\class\design-agentic-ai\temp\chunking_design_best_practices.pptx'
$previewPath = 'C:\Users\hiond\class\design-agentic-ai\temp\.chunking-build\powerpoint'
New-Item -ItemType Directory -Force -Path $previewPath | Out-Null
$presentation = $null
$powerPoint = New-Object -ComObject PowerPoint.Application
try {
    $presentation = $powerPoint.Presentations.Open($deckPath, -1, 0, 0)
    for ($slideIndex = 1; $slideIndex -le $presentation.Slides.Count; $slideIndex++) {
        $slide = $presentation.Slides.Item($slideIndex)
        $slide.Export((Join-Path $previewPath "slide-$slideIndex.png"), 'PNG', 1600, 900)
        Write-Output "PowerPoint rendered slide $slideIndex, shapes $($slide.Shapes.Count)"
    }
} finally {
    if ($null -ne $presentation) { $presentation.Close() }
    if (-not $existingPowerPoint) { $powerPoint.Quit() }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint)
}

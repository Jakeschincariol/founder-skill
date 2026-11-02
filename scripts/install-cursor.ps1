# Copies skills/founder-* into the user Cursor skills folder.
# Does not write into ~/.cursor/skills-cursor or into the open project.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$destRoot = Join-Path $env:USERPROFILE ".cursor\skills"
if ($destRoot -match "skills-cursor") {
    throw "Refusing to install into skills-cursor."
}
New-Item -ItemType Directory -Force -Path $destRoot | Out-Null
$skills = Get-ChildItem (Join-Path $root "skills") -Directory | Where-Object { $_.Name -like "founder-*" }
if (-not $skills) {
    throw "No founder-* skill folders under $root\skills"
}
foreach ($skill in $skills) {
    $dest = Join-Path $destRoot $skill.Name
    if (Test-Path $dest) {
        Remove-Item -Recurse -Force $dest
    }
    Copy-Item -Recurse $skill.FullName $dest
    Write-Output "installed $($skill.Name)"
}
Write-Output "Reload Cursor, then type /founder-board"

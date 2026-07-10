param(
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"

$appName = "Dubbing Manager"
$extension = ".dub"
$progId = "DubbingManager.Project"
$exePath = Join-Path $PSScriptRoot "Dubbing Manager.exe"
$classesRoot = "HKCU:\Software\Classes"
$extensionKey = Join-Path $classesRoot $extension
$progIdKey = Join-Path $classesRoot $progId

if ($Unregister) {
    Remove-Item -Path $extensionKey -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $progIdKey -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Removed $extension file association for $appName."
    exit 0
}

if (!(Test-Path $exePath)) {
    throw "Could not find '$exePath'. Run this script from the Dubbing Manager application folder."
}

New-Item -Path $extensionKey -Force | Out-Null
Set-ItemProperty -Path $extensionKey -Name "(default)" -Value $progId

New-Item -Path $progIdKey -Force | Out-Null
Set-ItemProperty -Path $progIdKey -Name "(default)" -Value "$appName Project"

$defaultIconKey = Join-Path $progIdKey "DefaultIcon"
New-Item -Path $defaultIconKey -Force | Out-Null
Set-ItemProperty -Path $defaultIconKey -Name "(default)" -Value "`"$exePath`",0"

$commandKey = Join-Path $progIdKey "shell\open\command"
New-Item -Path $commandKey -Force | Out-Null
Set-ItemProperty -Path $commandKey -Name "(default)" -Value "`"$exePath`" `"%1`""

Write-Host "Registered $extension files to open with $exePath."

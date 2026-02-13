# GUI launcher for uploader.ps1
# Shows a file picker to choose a JSON config, then runs uploader.ps1 in a new PowerShell window.

Add-Type -AssemblyName System.Windows.Forms

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ofd = New-Object System.Windows.Forms.OpenFileDialog
$ofd.InitialDirectory = $scriptDir
$ofd.Filter = "JSON files (*.json)|*.json"
$ofd.Title = "Select configuration JSON for uploader"
$ofd.CheckFileExists = $true

$result = $ofd.ShowDialog()
if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
    Write-Host "No file selected. Exiting."
    exit 0
}

$configFile = $ofd.FileName
$uploader = Join-Path $scriptDir 'uploader.ps1'

if (-not (Test-Path $uploader)) {
    [System.Windows.Forms.MessageBox]::Show("uploader.ps1 not found in script directory.`n$uploader","Error", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
    exit 1
}

# Launch uploader.ps1 in a new PowerShell window so output is visible and stays open.
$escapedUploader = $uploader -replace '"', '""'
$escapedConfig = $configFile -replace '"', '""'
$argList = "-NoProfile -ExecutionPolicy Bypass -File `"$escapedUploader`" `"$escapedConfig`""
Start-Process -FilePath powershell -ArgumentList $argList -WorkingDirectory $scriptDir -NoNewWindow:$false -WindowStyle Normal -Wait

exit $LASTEXITCODE

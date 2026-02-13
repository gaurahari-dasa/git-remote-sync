Param(
    [string]$ConfigFile
)

$UPLOAD_PACKAGE_DIR = "upload-package"
$UPLOAD_SPEC_FILE = "upload-spec.json"

function Exit-WithMessage([string]$msg, [int]$code=1){
    Write-Host $msg
    exit $code
}

# Verify upload package exists
if (-not (Test-Path $UPLOAD_PACKAGE_DIR -PathType Container)) {
    Exit-WithMessage "Upload package directory '$UPLOAD_PACKAGE_DIR' not found. Please run packer.py first to create an upload package." 1
}

$specPath = Join-Path $UPLOAD_PACKAGE_DIR $UPLOAD_SPEC_FILE
if (-not (Test-Path $specPath)) {
    Exit-WithMessage "Upload specification file '$UPLOAD_SPEC_FILE' not found in '$UPLOAD_PACKAGE_DIR'." 1
}

# Read upload spec to get config file path
$specRaw = Get-Content -Raw -Path $specPath
try {
    $upload_spec = $specRaw | ConvertFrom-Json
} catch {
    Exit-WithMessage "Failed to parse upload specification JSON: $_" 1
}

# Get config file path from upload spec
$ConfigFile = $upload_spec.config_file
if (-not $ConfigFile) {
    Exit-WithMessage "Config file path not found in upload specification." 1
}

if (-not (Test-Path $ConfigFile)) {
    Exit-WithMessage "Configuration file '$ConfigFile' not found." 1
}

# Read configuration
$configRaw = Get-Content -Raw -Path $ConfigFile
try {
    $config = $configRaw | ConvertFrom-Json
} catch {
    Exit-WithMessage "Failed to parse JSON configuration file: $_" 1
}

$ftp = $config.ftp
$ftp_host = $ftp.host
$ftp_user = $ftp.username
$ftp_pass = $ftp.password
$ftp_target_dir = $ftp.target_dir

if (-not ($ftp_host -and $ftp_user -and $ftp_pass -and $ftp_target_dir)) {
    Exit-WithMessage "Missing FTP configuration parameters in JSON file." 1
}

$package_hash = $upload_spec.package_hash
$files_mapping = $upload_spec.files

if ($package_hash) { Write-Host "Package hash: $package_hash`n" }

Write-Host "Files to upload:"
$keys = @()
if ($files_mapping) {
    foreach ($kv in $files_mapping.PSObject.Properties) {
        $keys += $kv.Name
        Write-Host " - $($kv.Name) -> $($kv.Value)"
    }
} else {
    Write-Host "No files to upload."
    exit 0
}

$confirm = Read-Host "`nDo you want to proceed with uploading $($keys.Count) files? (yes/no)"
if ($confirm.Trim().ToLower() -ne 'yes') {
    Write-Host "Operation cancelled by user."
    exit 0
}

$creds = New-Object System.Net.NetworkCredential($ftp_user, $ftp_pass)
$baseHost = $ftp_host.Trim()
# Ensure no protocol prefix in host
if ($baseHost.StartsWith('ftp://')) { $baseHost = $baseHost.Substring(6) }

# Normalize target directory (remove leading/trailing slashes)
$cfgTarget = $ftp_target_dir -replace "\\","/"
$cfgTarget = $cfgTarget.Trim('/')

$uploadedCount = 0

# Load FTP client assembly
[System.Reflection.Assembly]::LoadWithPartialName("System.Net.FtpClient") | Out-Null

foreach ($kv in $files_mapping.PSObject.Properties) {
    $numbered_file = $kv.Name
    $target_path = $kv.Value -replace "\\","/"

    $local_file_path = Join-Path $UPLOAD_PACKAGE_DIR $numbered_file
    if (-not (Test-Path $local_file_path -PathType Leaf)) {
        Write-Host "Warning: File not found in package: $numbered_file, skipping."
        continue
    }

    $target_dir = Split-Path -Path $target_path -Parent
    $target_filename = Split-Path -Path $target_path -Leaf
    
    # Normalize target_dir to use forward slashes for FTP
    if ($target_dir) {
        $target_dir = $target_dir -replace "\\","/"
    }

    # Compute full remote directory relative to host: cfgTarget + target_dir
    if ($target_dir) {
        if ($cfgTarget) { $fullRemoteDir = "$cfgTarget/$target_dir" } else { $fullRemoteDir = $target_dir }
    } else {
        $fullRemoteDir = $cfgTarget
    }
    $fullRemoteDir = $fullRemoteDir.Trim('/')

    try {
        Write-Host "Uploading: $numbered_file -> $target_path"
        
        # Try using FtpClient if available
        $ftpAvailable = $false
        try {
            $ftp = New-Object System.Net.FtpClient.FtpClient
            $ftp.Host = $baseHost
            $ftp.Credentials = New-Object System.Net.NetworkCredential($ftp_user, $ftp_pass)
            $ftp.DataConnectionType = [System.Net.FtpClient.FtpDataConnectionType]::AutoPassive
            $ftp.Connect()
            
            # Create directories if needed
            if ($fullRemoteDir) {
                $ftp.CreateDirectory($fullRemoteDir, $true)
            }
            
            # Upload file
            $fileStream = [System.IO.File]::OpenRead($local_file_path)
            $remotePath = if ($fullRemoteDir) { "$fullRemoteDir/$target_filename" } else { $target_filename }
            $ftp.UploadStream($fileStream, $remotePath)
            $fileStream.Close()
            
            $ftp.Disconnect()
            $ftpAvailable = $true
        } catch {
            # FtpClient assembly not available, fall back to WebClient
            $ftpAvailable = $false
        }
        
        if (-not $ftpAvailable) {
            # Fallback to WebClient
            # Build upload URI with URL encoding for special characters
            $encodedFilename = [Uri]::EscapeDataString($target_filename)
            if ($fullRemoteDir) { $uploadUri = "ftp://$baseHost/$fullRemoteDir/$encodedFilename" }
            else { $uploadUri = "ftp://$baseHost/$encodedFilename" }
            
            $wc = New-Object System.Net.WebClient
            $wc.Credentials = New-Object System.Net.NetworkCredential($ftp_user, $ftp_pass)
            $wc.UploadFile($uploadUri, $local_file_path) | Out-Null
        }

        Write-Host "Uploaded: $numbered_file -> $target_path"
        $uploadedCount++
    } catch {
        $err = $_
        $msg = $err.Exception.Message
        Write-Host ("Error uploading {0}: {1}" -f $numbered_file, $msg)
    }
}

Write-Host "`nUpload complete. Files uploaded: $uploadedCount"

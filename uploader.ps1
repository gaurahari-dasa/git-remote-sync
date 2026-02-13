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

function Ensure-FtpDirectoryExists([string]$ftpHost, [string]$path, [System.Net.NetworkCredential]$creds) {
    if (-not $path) { return }
    $segments = $path.Split('/') | Where-Object { $_ -ne '' }
    $current = ''
    foreach ($seg in $segments) {
        if ($current -eq '') { $current = $seg } else { $current = "$current/$seg" }
        $uri = "ftp://$ftpHost/$current"
        try {
            $req = [System.Net.FtpWebRequest]::Create($uri)
            $req.Method = [System.Net.WebRequestMethods+Ftp]::MakeDirectory
            $req.Credentials = $creds
            $req.UseBinary = $true
            $req.KeepAlive = $false
            $resp = $req.GetResponse()
            $resp.Close()
        } catch {
            # Directory may already exist or server may not allow explicit mkd; ignore errors
        }
    }
}

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

    # Compute full remote directory relative to host: cfgTarget + target_dir
    if ($target_dir) {
        if ($cfgTarget) { $fullRemoteDir = "$cfgTarget/$target_dir" } else { $fullRemoteDir = $target_dir }
    } else {
        $fullRemoteDir = $cfgTarget
    }
    $fullRemoteDir = $fullRemoteDir.Trim('/')

    try {
        # Ensure remote directories exist
        Ensure-FtpDirectoryExists -host $baseHost -path $fullRemoteDir -creds $creds

        # Build upload URI
        if ($fullRemoteDir) { $uploadUri = "ftp://$baseHost/$fullRemoteDir/$target_filename" }
        else { $uploadUri = "ftp://$baseHost/$target_filename" }

        $wc = New-Object System.Net.WebClient
        $wc.Credentials = $creds
        $wc.UploadFile($uploadUri, $local_file_path) | Out-Null

        Write-Host "Uploaded: $numbered_file -> $target_path"
        $uploadedCount++
    } catch {
        $err = $_
        $msg = $err.Exception.Message
        Write-Host ("Error uploading {0}: {1}" -f $numbered_file, $msg)
    }
}

Write-Host "`nUpload complete. Files uploaded: $uploadedCount"

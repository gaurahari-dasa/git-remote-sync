import os
import sys
import json
import zipfile
import shutil
from datetime import datetime

# -------------------- Create Deployment ZIP --------------------
def create_deployment_zip(upload_package_dir, uploader_script, launcher_script, spec_file):
    """
    Create a zip file containing the launcher script, uploader script, upload package, and config file.
    
    Parameters:
    upload_package_dir: Directory containing numbered files and upload-spec.json
    uploader_script: Path to the uploader PowerShell script (uploader.ps1)
    launcher_script: Path to the launcher batch script (upload-launcher.bat)
    spec_file: Name of the upload specification file (upload-spec.json)
    """
    
    # Load upload specification to get config file path
    spec_filepath = os.path.join(upload_package_dir, spec_file)
    if not os.path.isfile(spec_filepath):
        raise Exception(f"Upload specification file not found: {spec_filepath}")
    
    with open(spec_filepath, "r") as f:
        upload_spec = json.load(f)
    
    # Get config file path from spec
    config_file = upload_spec.get("config_file")
    if not config_file:
        raise Exception("Config file path not found in upload specification.")
    
    if not os.path.isfile(config_file):
        raise Exception(f"Configuration file not found: {config_file}")
    
    # Get package hash for naming
    package_hash = upload_spec.get("package_hash", "unknown")
    short_hash = package_hash[:8] if package_hash else "unknown"
    
    # Create zip filename with timestamp and hash
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"deployment-{timestamp}-{short_hash}.zip"
    
    print(f"Creating deployment package: {zip_filename}")
    print(f"Config file: {config_file}")
    print(f"Launcher script: {launcher_script}")
    print(f"Uploader script: {uploader_script}")
    print(f"Upload package: {upload_package_dir}")
    
    # Create zip file
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        
        # Add launcher script to root of zip
        if os.path.isfile(launcher_script):
            zipf.write(launcher_script, arcname=os.path.basename(launcher_script))
            print(f"  Added: {os.path.basename(launcher_script)}")
        else:
            raise Exception(f"Launcher script not found: {launcher_script}")
        
        # Add uploader script to root of zip
        if os.path.isfile(uploader_script):
            zipf.write(uploader_script, arcname=os.path.basename(uploader_script))
            print(f"  Added: {os.path.basename(uploader_script)}")
        else:
            raise Exception(f"Uploader script not found: {uploader_script}")
        
        # Add config file to root of zip
        config_basename = os.path.basename(config_file)
        zipf.write(config_file, arcname=config_basename)
        print(f"  Added: {config_basename}")
        
        # Add entire upload package directory
        for root, dirs, files in os.walk(upload_package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate relative path for zip archive
                arcname = os.path.relpath(file_path, os.path.dirname(upload_package_dir))
                zipf.write(file_path, arcname=arcname)
                print(f"  Added: {arcname}")
    
    print(f"\nDeployment package created successfully: {zip_filename}")
    print(f"Package hash: {package_hash}")
    print(f"Total size: {os.path.getsize(zip_filename)} bytes")
    
    return zip_filename


# -------------------- Main Execution --------------------
def main():
    UPLOAD_PACKAGE_DIR = "upload-package"
    LAUNCHER_SCRIPT = "upload-launcher.bat"
    UPLOADER_SCRIPT = "uploader.ps1"
    UPLOAD_SPEC_FILE = "upload-spec.json"
    
    # Verify upload package exists
    if not os.path.isdir(UPLOAD_PACKAGE_DIR):
        print(f"Error: Upload package directory '{UPLOAD_PACKAGE_DIR}' not found.")
        print("Please run packer.py first to create an upload package.")
        sys.exit(1)
    
    spec_filepath = os.path.join(UPLOAD_PACKAGE_DIR, UPLOAD_SPEC_FILE)
    if not os.path.isfile(spec_filepath):
        print(f"Error: Upload specification file '{UPLOAD_SPEC_FILE}' not found in '{UPLOAD_PACKAGE_DIR}'.")
        sys.exit(1)
    
    # Verify launcher script exists
    if not os.path.isfile(LAUNCHER_SCRIPT):
        print(f"Error: Launcher script '{LAUNCHER_SCRIPT}' not found.")
        sys.exit(1)
    
    # Verify uploader script exists
    if not os.path.isfile(UPLOADER_SCRIPT):
        print(f"Error: Uploader script '{UPLOADER_SCRIPT}' not found.")
        sys.exit(1)
    
    try:
        create_deployment_zip(UPLOAD_PACKAGE_DIR, UPLOADER_SCRIPT, LAUNCHER_SCRIPT, UPLOAD_SPEC_FILE)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

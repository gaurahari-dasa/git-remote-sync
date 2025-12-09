import os
import sys
import json
from ftplib import FTP

# Upload package directory and specification file
UPLOAD_PACKAGE_DIR = "upload-package"
UPLOAD_SPEC_FILE = "upload-spec.json"

# -------------------- FTP Upload --------------------
def upload_via_ftp(package_dir, spec_file, ftp_host, ftp_user, ftp_pass, ftp_target_dir):
    """
    Upload files from package using specification mapping via FTP.
    
    Parameters:
    package_dir: Directory containing numbered files
    spec_file: JSON file with mapping of numbered files to target paths
    ftp_host: FTP server hostname/IP
    ftp_user: FTP username
    ftp_pass: FTP password
    ftp_target_dir: Target directory on FTP server
    """
    # Load upload specification
    spec_filepath = os.path.join(package_dir, spec_file)
    if not os.path.isfile(spec_filepath):
        raise Exception(f"Upload specification file not found: {spec_filepath}")
    
    with open(spec_filepath, "r") as f:
        upload_spec = json.load(f)
    
    if not upload_spec:
        print("No files to upload.")
        return
    
    # Connect to FTP
    ftp = FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)
    ftp.cwd(ftp_target_dir)
    
    uploaded_count = 0
    
    try:
        for numbered_file, target_path in upload_spec.items():
            try:
                # Get full path to numbered file
                local_file_path = os.path.join(package_dir, numbered_file)
                
                if not os.path.isfile(local_file_path):
                    print(f"Warning: File not found in package: {numbered_file}, skipping.")
                    continue
                
                # Split target path into directory and filename
                target_dir = os.path.dirname(target_path)
                target_filename = os.path.basename(target_path)
                
                # Navigate to or create target directory
                if target_dir:
                    # Convert Windows-style paths to forward slashes for FTP
                    ftp_target_dir_normalized = target_dir.replace(os.sep, "/")
                    
                    # Create directories if needed
                    for dir_part in ftp_target_dir_normalized.split("/"):
                        if dir_part:
                            try:
                                ftp.mkd(dir_part)
                            except:
                                # Directory might already exist
                                pass
                            ftp.cwd(dir_part)
                
                # Upload file
                with open(local_file_path, "rb") as f:
                    ftp.storbinary(f"STOR {target_filename}", f)
                
                print(f"Uploaded: {numbered_file} -> {target_path}")
                uploaded_count += 1
                
                # Return to target directory
                ftp.cwd(ftp_target_dir)
                
            except Exception as e:
                print(f"Error uploading {numbered_file}: {e}")
    
    finally:
        ftp.quit()
    
    print(f"\nUpload complete. Files uploaded: {uploaded_count}")


# -------------------- Main Execution --------------------
def main():
    # Load configuration
    config_file = input("config file: ")
    
    if not os.path.isfile(config_file):
        print(f"Configuration file '{config_file}' not found.")
        sys.exit(1)
    
    with open(config_file, "r") as f:
        config = json.load(f)
    
    # Get FTP configuration
    ftp_config = config.get("ftp", {})
    ftp_host = ftp_config.get("host")
    ftp_user = ftp_config.get("username")
    ftp_pass = ftp_config.get("password")
    ftp_target_dir = ftp_config.get("target_dir")
    
    if not all([ftp_host, ftp_user, ftp_pass, ftp_target_dir]):
        print("Missing FTP configuration parameters in JSON file.")
        sys.exit(1)
    
    # Check if upload package exists
    if not os.path.isdir(UPLOAD_PACKAGE_DIR):
        print(f"Upload package directory '{UPLOAD_PACKAGE_DIR}' not found.")
        print("Please run packer.py first to create an upload package.")
        sys.exit(1)
    
    spec_filepath = os.path.join(UPLOAD_PACKAGE_DIR, UPLOAD_SPEC_FILE)
    if not os.path.isfile(spec_filepath):
        print(f"Upload specification file '{UPLOAD_SPEC_FILE}' not found in '{UPLOAD_PACKAGE_DIR}'.")
        sys.exit(1)
    
    # Display package contents
    with open(spec_filepath, "r") as f:
        upload_spec = json.load(f)
    
    print("Files to upload:")
    for numbered_file, target_path in upload_spec.items():
        print(f" - {numbered_file} -> {target_path}")
    
    # Confirm before uploading
    confirm = (
        input(f"\nDo you want to proceed with uploading {len(upload_spec)} files? (yes/no): ")
        .strip()
        .lower()
    )
    if confirm != "yes":
        print("Operation cancelled by user.")
        sys.exit(0)
    
    try:
        # Upload files via FTP
        upload_via_ftp(UPLOAD_PACKAGE_DIR, UPLOAD_SPEC_FILE, ftp_host, ftp_user, ftp_pass, ftp_target_dir)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

import os
import sys
import json
import subprocess
import shutil
from datetime import datetime
import stat

# Archive output directory
ARCHIVE_OUTPUT_DIR = "folder-archives"

# Temporary checkout directory (relative to current working directory)
TEMP_CHECKOUT_DIR = "_checkout_temp"


# -------------------- Initialize Temporary Checkout --------------------
def init_temp_checkout(original_repo_path: str, temp_checkout_path: str, commit_hash: str):
    """
    Initialize a temporary Git repository and check out a specific commit.
    Uses git clone with sparse checkout or full clone depending on requirements.
    
    Parameters:
    original_repo_path: Path to the original Git repository
    temp_checkout_path: Path where temporary checkout will be created
    commit_hash: Git commit hash or alias to check out
    
    Returns:
    bool: True if successful, False otherwise
    """
    try:
        # Clean up if temp directory already exists
        if os.path.exists(temp_checkout_path):
            safe_rmtree(temp_checkout_path)

        # Initialize git repo from original repo (don't pre-create target dir;
        # let `git clone` create it). Use --no-hardlinks to avoid hardlinking
        # objects when cloning from a local repository which can cause
        # permission/cleanup issues on Windows.
        print(f"Initializing temporary checkout at: {temp_checkout_path}")
        
        # Clone from the original repository to the temporary location
        result = subprocess.run(
            ["git", "clone", "--no-hardlinks", original_repo_path, temp_checkout_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"Error cloning repository: {result.stderr}")
            return False
        
        # Checkout the specific commit in the temporary location
        print(f"Checking out commit: {commit_hash}")
        result = subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=temp_checkout_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"Error checking out commit {commit_hash}: {result.stderr}")
            return False
        
        print(f"Successfully checked out commit in temporary location")
        return True
    except Exception as e:
        print(f"Exception during temporary checkout initialization: {e}")
        return False


# -------------------- Copy Folder from Source --------------------
def copy_folder(source_path: str, dest_path: str):
    """
    Copy a folder from source to destination, including all subfolders and files recursively.
    
    Parameters:
    source_path: Source folder path
    dest_path: Destination folder path
    
    Returns:
    bool: True if successful, False otherwise
    """
    try:
        if not os.path.isdir(source_path):
            return False
        
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        
        # shutil.copytree recursively copies all subdirectories and files
        shutil.copytree(source_path, dest_path, dirs_exist_ok=False)
        folder_name = os.path.basename(source_path)
        print(f"Copied folder (recursive): {folder_name}")
        return True
    except Exception as e:
        print(f"Error copying folder: {e}")
        return False


# -------------------- Merge Missing Entries --------------------
def merge_missing_from_original(original_path: str, dest_path: str):
    """
    After copying a folder from the checked-out clone, merge any files or
    subfolders that exist in the original repo but were not present in the
    checked-out commit (e.g. untracked build/ folders).

    This will copy only entries that are missing in dest_path; it will not
    overwrite existing files in dest_path.
    """
    try:
        if not os.path.isdir(original_path):
            return

        for entry in os.listdir(original_path):
            src_entry = os.path.join(original_path, entry)
            dst_entry = os.path.join(dest_path, entry)

            # If entry already exists in destination, skip
            if os.path.exists(dst_entry):
                continue

            # Copy directories recursively, files with metadata
            if os.path.isdir(src_entry):
                try:
                    shutil.copytree(src_entry, dst_entry)
                    print(f"Merged missing directory: {entry}")
                except Exception as e:
                    print(f"Warning: failed to copy directory '{entry}': {e}")
            else:
                try:
                    shutil.copy2(src_entry, dst_entry)
                    print(f"Merged missing file: {entry}")
                except Exception as e:
                    print(f"Warning: failed to copy file '{entry}': {e}")
    except Exception as e:
        print(f"Warning: error while merging from original: {e}")


# -------------------- Cleanup Temporary Checkout --------------------
def cleanup_temp_checkout(temp_checkout_path: str):
    """
    Remove the temporary checkout directory.
    
    Parameters:
    temp_checkout_path: Path to the temporary checkout directory
    """
    try:
        if os.path.exists(temp_checkout_path):
            safe_rmtree(temp_checkout_path)
            print(f"Cleaned up temporary checkout directory")
    except Exception as e:
        print(f"Warning: Failed to cleanup temporary directory: {e}")


def safe_rmtree(path):
    """Remove a path like shutil.rmtree but try to fix permission errors on Windows.

    Attempts to make files writable before retrying removal.
    """
    def _onerror(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
        except Exception:
            try:
                os.chmod(p, 0o700)
            except Exception:
                pass
        try:
            func(p)
        except Exception:
            # last resort: if it's a file try unlink
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            except Exception:
                pass

    shutil.rmtree(path, onerror=_onerror)


# -------------------- Get Git Commit Hash --------------------
def get_git_commit_hash(repo_path: str, alias="HEAD"):
    """
    Returns the SHA-1 hash of the specified Git commit alias.
    
    Parameters:
    repo_path: Path to the Git repository (can be original or temporary)
    alias (str): A Git commit reference like 'HEAD', 'HEAD~1', 'HEAD^', etc.
    
    Returns:
    str: SHA-1 hash of the specified commit.
    """
    try:
        commit_hash = (
            subprocess.check_output(["git", "rev-parse", alias], cwd=repo_path)
            .decode("utf-8")
            .strip()
        )
        return commit_hash
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving commit hash for alias '{alias}':", e)
        return None


# -------------------- Create Folder Archive --------------------
def create_folder_archive(folder_path: str, archive_name: str):
    """
    Create a zip archive of a folder.
    
    Parameters:
    folder_path: Path to the folder to archive
    archive_name: Path where the archive should be created
    
    Returns:
    bool: True if successful, False otherwise
    """
    try:
        if not os.path.isdir(folder_path):
            print(f"Warning: Folder not found: {folder_path}")
            return False
        
        # Create zip archive
        shutil.make_archive(
            archive_name.replace(".zip", ""),  # Remove .zip extension for shutil
            "zip",
            os.path.dirname(folder_path),
            os.path.basename(folder_path)
        )
        
        if os.path.isfile(archive_name):
            file_size = os.path.getsize(archive_name)
            print(f"✓ Archived: {os.path.basename(folder_path)} -> {archive_name} ({file_size} bytes)")
            return True
        else:
            print(f"✗ Failed to create archive: {archive_name}")
            return False
    except Exception as e:
        print(f"Error archiving folder {folder_path}: {e}")
        return False


# -------------------- Main Execution --------------------
def main():
    # Get config file from command line argument
    if len(sys.argv) < 2:
        print("Usage: python folder-packer.py <config_file>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    if not os.path.isfile(config_file):
        print(f"Configuration file '{config_file}' not found.")
        sys.exit(1)
    
    with open(config_file, "r") as f:
        config = json.load(f)
    
    repo_path = config["repo"]["path"]
    
    # Normalize path separators
    repo_path = repo_path.replace("/", os.sep)
    
    if not os.path.isdir(repo_path):
        print(f"Repository path not found: {repo_path}")
        sys.exit(1)
    
    # Check if arch_folders property exists in config
    arch_folders = config.get("arch_folders", None)
    
    if arch_folders is None:
        print("Error: 'arch_folders' property not defined in configuration file.")
        print("Nothing to do.")
        sys.exit(0)
    
    if not arch_folders:
        print("Error: 'arch_folders' list is empty in configuration file.")
        print("Nothing to do.")
        sys.exit(0)
    
    # Get commit hash from user
    commit_hash = input("commit hash to archive (HEAD): ").strip()
    commit_hash = commit_hash if len(commit_hash) else 'HEAD'
    
    # First, resolve the commit hash in the original repo
    full_commit_hash = get_git_commit_hash(repo_path, commit_hash)
    if not full_commit_hash:
        print("Error: Could not resolve commit hash.")
        sys.exit(1)
    
    print(f"\nPreparing to archive folders from commit: {full_commit_hash}")
    print(f"Folders to archive: {', '.join(arch_folders)}")
    
    # Confirm before proceeding
    confirm = (
        input("\nDo you want to proceed with archiving these folders? (yes/no): ")
        .strip()
        .lower()
    )
    if confirm != "yes":
        print("Operation cancelled by user.")
        sys.exit(0)
    
    # Create temporary checkout
    temp_checkout_path = os.path.join(os.getcwd(), TEMP_CHECKOUT_DIR)
    print(f"\nInitializing temporary checkout at: {temp_checkout_path}")
    
    if not init_temp_checkout(repo_path, temp_checkout_path, commit_hash):
        print("Error: Failed to initialize temporary checkout.")
        cleanup_temp_checkout(temp_checkout_path)
        sys.exit(1)
    
    # Create output directory for archives
    if os.path.exists(ARCHIVE_OUTPUT_DIR):
        shutil.rmtree(ARCHIVE_OUTPUT_DIR)
    os.makedirs(ARCHIVE_OUTPUT_DIR, exist_ok=True)
    
    # Prepare temporary directory for collecting folders to archive
    temp_archive_dir = os.path.join(temp_checkout_path, ".archive_work")
    if os.path.exists(temp_archive_dir):
        shutil.rmtree(temp_archive_dir)
    os.makedirs(temp_archive_dir, exist_ok=True)
    
    # Collect all folders to be archived
    collected_folders = 0
    for folder_name in arch_folders:
        # First check if folder exists in the checked-out commit
        folder_in_checkout = os.path.join(temp_checkout_path, folder_name)
        
        if os.path.isdir(folder_in_checkout):
            # Folder exists in the checked-out commit, copy from there
            work_folder = os.path.join(temp_archive_dir, folder_name)
            if copy_folder(folder_in_checkout, work_folder):
                # Merge any untracked or additional files/folders present in the
                # original repo's working directory but not present in the
                # checked-out commit (e.g. generated 'build' folders).
                folder_in_original = os.path.join(repo_path, folder_name)
                merge_missing_from_original(folder_in_original, work_folder)
                collected_folders += 1
        else:
            # Folder doesn't exist in checked-out commit, try to copy from original repo
            folder_in_original = os.path.join(repo_path, folder_name)
            
            if os.path.isdir(folder_in_original):
                print(f"Note: '{folder_name}' not in checked-out commit, copying from original repo...")
                work_folder = os.path.join(temp_archive_dir, folder_name)
                if copy_folder(folder_in_original, work_folder):
                    collected_folders += 1
            else:
                print(f"✗ Folder not found in commit or original repo: {folder_name}")
    
    # Create single archive containing all collected folders
    if collected_folders > 0:
        # Use short commit hash (first 8 characters) in archive name
        short_hash = full_commit_hash[:8]
        archive_name = os.path.join(ARCHIVE_OUTPUT_DIR, f"archive_{short_hash}.zip")
        print(f"\nCreating combined archive with {collected_folders} folders...")
        
        if create_folder_archive(temp_archive_dir, archive_name):
            print(f"✓ Combined archive created successfully: {archive_name}")
        else:
            print("Error: Failed to create combined archive.")
            cleanup_temp_checkout(temp_checkout_path)
            sys.exit(1)
    else:
        print("Error: No folders were collected for archiving.")
        cleanup_temp_checkout(temp_checkout_path)
        sys.exit(1)
    
    # Cleanup temporary directory
    cleanup_temp_checkout(temp_checkout_path)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Archived {collected_folders}/{len(arch_folders)} folders")
    print(f"Archive saved to: {archive_name}")
    print(f"Commit: {full_commit_hash}")
    print(f"{'='*50}")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

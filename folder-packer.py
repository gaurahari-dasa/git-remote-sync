import os
import sys
import json
import subprocess
import shutil
from builder import build
from repo_manager import setup_repo

# Archive output directory
ARCHIVE_OUTPUT_DIR = "folder-archives"


# -------------------- Copy Item (File or Folder) --------------------
def copy_item(source_path: str, dest_path: str):
    """
    Copy an item (file or folder) from source to destination.
    For folders, recursively copies all subfolders and files.
    For files, copies with metadata preservation.
    
    Parameters:
    source_path: Source file or folder path
    dest_path: Destination file or folder path
    
    Returns:
    bool: True if successful, False otherwise
    """
    try:
        if not os.path.exists(source_path):
            return False
        
        if os.path.exists(dest_path):
            if os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
            else:
                os.remove(dest_path)
        
        # Handle directories
        if os.path.isdir(source_path):
            shutil.copytree(source_path, dest_path, dirs_exist_ok=False)
            item_name = os.path.basename(source_path)
            print(f"Copied directory (recursive): {item_name}")
            return True
        # Handle files
        else:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(source_path, dest_path)
            item_name = os.path.basename(source_path)
            print(f"Copied file: {item_name}")
            return True
    except Exception as e:
        print(f"Error copying item: {e}")
        return False


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
    
    # Set up the repository
    repo_path = setup_repo(config)
    
    if not repo_path:
        print("Failed to set up repository.")
        sys.exit(1)
    
    # Check if include_items property exists in config
    include_items = config.get("include_items", None)
    if include_items is None:
        print("Error: 'include_items' property not defined in configuration file.")
        print("Nothing to do.")
        sys.exit(0)
    if not isinstance(include_items, list):
        print("Error: 'include_items' must be a list in configuration file.")
        sys.exit(0)

    # Run build commands if specified
    if "build" in config:
        print("Running build commands...")
        if not build(config, repo_path):
            print("Build failed.")
            sys.exit(1)
        print("Build completed.")

    # Use HEAD as the commit to archive
    commit_hash = 'HEAD'

    # First, resolve the commit hash in the original repo
    full_commit_hash = get_git_commit_hash(repo_path, commit_hash)
    if not full_commit_hash:
        print("Error: Could not resolve commit hash.")
        sys.exit(1)

    # Get the package_hash from config
    package_hash = config["repo"].get("package_hash", None)
    if not package_hash:
        print("Error: 'package_hash' not found in config.")
        sys.exit(1)

    # Find changed files between package_hash and commit_hash
    try:
        result = subprocess.run([
            "git", "diff", "--name-only", package_hash, full_commit_hash
        ], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error running git diff: {result.stderr}")
            sys.exit(1)
        changed_files = result.stdout.strip().splitlines()
    except Exception as e:
        print(f"Error running git diff: {e}")
        sys.exit(1)

    # Extract top-level folders from changed files
    top_level_folders = set()
    for f in changed_files:
        parts = f.replace("\\", "/").split("/")
        if len(parts) > 1:
            top_level_folders.add(parts[0])
        elif len(parts) == 1 and os.path.dirname(f) == '':
            # file at repo root, skip
            continue

    # Merge unique top-level folders into include_items
    include_items_set = set(include_items)
    include_items_set.update(top_level_folders)
    include_items = list(include_items_set)

    # Read exclude_folders from config (optional)
    exclude_folders = config.get("exclude_folders", [])
    if not isinstance(exclude_folders, list):
        print("Warning: 'exclude_folders' must be a list in configuration file. Ignoring.")
        exclude_folders = []

    # Filter out excluded folders from include_items
    exclude_folders_set = set(exclude_folders)
    final_items = [item for item in include_items if item not in exclude_folders_set]
    excluded_items = [item for item in include_items if item in exclude_folders_set]

    print(f"\nPreparing to archive items from commit: {full_commit_hash}")
    if excluded_items:
        print(f"Excluded folders: {', '.join(excluded_items)}")
    if final_items:
        print(f"Items to archive: {', '.join(final_items)}")
    else:
        print("No items to archive after filtering.")
        sys.exit(0)

    include_items = final_items

    # Confirm before proceeding
    confirm = (
        input("\nDo you want to proceed with archiving these items? (yes/no): ")
        .strip()
        .lower()
    )
    if confirm != "yes":
        print("Operation cancelled by user.")
        sys.exit(0)
    
    # Use the repository path directly (already at HEAD from setup_repo)
    
    # Create output directory for archives
    if os.path.exists(ARCHIVE_OUTPUT_DIR):
        shutil.rmtree(ARCHIVE_OUTPUT_DIR)
    os.makedirs(ARCHIVE_OUTPUT_DIR, exist_ok=True)
    
    # Prepare temporary directory for collecting folders to archive
    temp_archive_dir = os.path.join(repo_path, ".archive_work")
    if os.path.exists(temp_archive_dir):
        shutil.rmtree(temp_archive_dir)
    os.makedirs(temp_archive_dir, exist_ok=True)
    
    # Collect all items (files or folders) to be archived
    collected_items = 0
    for item_name in include_items:
        # Check if item exists in the repository
        item_in_repo = os.path.join(repo_path, item_name)
        
        if os.path.exists(item_in_repo):
            # Item exists, copy from there
            work_item = os.path.join(temp_archive_dir, item_name)
            if copy_item(item_in_repo, work_item):
                collected_items += 1
        else:
            print(f"✗ Item not found: {item_name}")
    
    # Create single archive containing all collected items
    if collected_items > 0:
        # Use short commit hash (first 8 characters) in archive name
        short_hash = full_commit_hash[:8]
        archive_name = os.path.join(ARCHIVE_OUTPUT_DIR, f"archive_{short_hash}.zip")
        print(f"\nCreating combined archive with {collected_items} items...")
        
        if create_folder_archive(temp_archive_dir, archive_name):
            print(f"✓ Combined archive created successfully: {archive_name}")
            # Update package_hash in config file to the archived commit
            try:
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                config_data["repo"]["package_hash"] = full_commit_hash
                with open(config_file, "w") as f:
                    json.dump(config_data, f, indent=2)
                print(f"Updated package_hash in config to {full_commit_hash}")
            except Exception as e:
                print(f"Warning: Failed to update package_hash in config: {e}")
        else:
            print("Error: Failed to create combined archive.")
            sys.exit(1)
    else:
        print("Error: No folders were collected for archiving.")
        sys.exit(1)
    
    # Clean up temporary archive directory
    if os.path.exists(temp_archive_dir):
        shutil.rmtree(temp_archive_dir)
        print("Cleaned up temporary archive directory.")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Archived {collected_items}/{len(include_items)} items")
    print(f"Archive saved to: {archive_name}")
    print(f"Commit: {full_commit_hash}")
    print(f"{'='*50}")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

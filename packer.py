import os
import sys
import json
import subprocess
import shutil

# Upload package directory
UPLOAD_PACKAGE_DIR = "upload-package"
UPLOAD_SPEC_FILE = "upload-spec.json"

# -------------------- Get Changed Files --------------------
def get_changed_files(repo_path, commit1, commit2):
    """
    Get list of changed files between two commits using git diff.
    
    Parameters:
    repo_path: Path to the Git repository
    commit1: Earlier commit hash
    commit2: Present commit hash
    
    Returns:
    List of file paths relative to repo root
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", commit1, commit2],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise Exception(f"Git error: {result.stderr}")
    return result.stdout.strip().splitlines()


# -------------------- Get File from Git --------------------
def get_file_from_git(repo_path, commit_hash, file_path):
    """
    Retrieve file content from Git at specified commit.
    
    Parameters:
    repo_path: Path to the Git repository
    commit_hash: Git commit hash to retrieve from
    file_path: File path relative to repo root
    
    Returns:
    File content as bytes, or None if file cannot be retrieved
    """
    result = subprocess.run(
        ["git", "show", f"{commit_hash}:{file_path}"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    if result.returncode != 0:
        return None
    
    return result.stdout


# -------------------- Get Git Commit Hash --------------------
def get_git_commit_hash(repo_path: str, alias="HEAD"):
    """
    Returns the SHA-1 hash of the specified Git commit alias.
    
    Parameters:
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


# -------------------- Create Upload Package --------------------
def create_upload_package(file_list, repo_path, commit_hash, package_dir):
    """
    Create upload package with numbered files and mapping specification.
    
    Parameters:
    file_list: List of file paths to include
    repo_path: Path to the Git repository
    commit_hash: Git commit hash to retrieve files from
    package_dir: Directory to create upload package in
    
    Returns:
    Tuple of (upload_spec dict, full commit hash)
    """
    # Clean up and recreate package directory
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    os.makedirs(package_dir, exist_ok=True)
    
    # Resolve commit hash to full SHA-1
    full_commit_hash = get_git_commit_hash(repo_path, commit_hash)
    if not full_commit_hash:
        raise Exception(f"Could not resolve commit hash: {commit_hash}")
    
    # Create upload specification with new structure
    upload_spec = {
        "package_hash": full_commit_hash,
        "files": {}
    }
    file_counter = 1
    
    for file_path in file_list:
        # Get file content from Git
        file_content = get_file_from_git(repo_path, commit_hash, file_path)
        
        if file_content is None:
            print(f"Warning: Could not retrieve {file_path} from Git, skipping.")
            continue
        
        # Create numbered file
        numbered_filename = str(file_counter)
        numbered_filepath = os.path.join(package_dir, numbered_filename)
        
        # Write file content to numbered file
        with open(numbered_filepath, "wb") as f:
            f.write(file_content)
        
        # Add to files mapping
        upload_spec["files"][numbered_filename] = file_path
        
        print(f"Packaged: {file_path} -> {numbered_filename}")
        file_counter += 1
    
    # Write upload specification file
    spec_filepath = os.path.join(package_dir, UPLOAD_SPEC_FILE)
    with open(spec_filepath, "w") as f:
        json.dump(upload_spec, f, indent=4)
    
    print(f"\nUpload package created in '{package_dir}'")
    print(f"Specification file: {UPLOAD_SPEC_FILE}")
    print(f"Package hash: {full_commit_hash}")
    print(f"Total files packaged: {len(upload_spec['files'])}")
    
    return upload_spec, full_commit_hash


# -------------------- Main Execution --------------------
def main():
    # Load configuration
    config_file = input("config file: ")
    
    if not os.path.isfile(config_file):
        print(f"Configuration file '{config_file}' not found.")
        sys.exit(1)
    
    with open(config_file, "r") as f:
        config = json.load(f)
    
    repo_path = config["repo"]["path"]
    package_hash = config["repo"].get("package_hash", "")
    
    if not repo_path:
        print("Missing 'repo.path' in configuration file.")
        sys.exit(1)
    
    # Get commit hashes from user
    commit1 = input(f"earlier hash{f' ({package_hash})' if package_hash else ''}: ").strip()
    commit1 = commit1 if len(commit1) else package_hash
    commit2 = input("present hash (HEAD): ").strip()
    commit2 = commit2 if len(commit2) else 'HEAD'
    
    if not commit1:
        print("Error: earlier hash is required.")
        sys.exit(1)
    
    try:
        # Get changed files
        changed_files = get_changed_files(repo_path, commit1, commit2)
        
        if not changed_files:
            print("No changed files found between the specified commits.")
            sys.exit(0)
        
        print("Changed files:")
        for file in changed_files:
            print(f" - {file}")
        
        # Confirm before creating package
        confirm = (
            input("\nDo you want to proceed with creating the upload package? (yes/no): ")
            .strip()
            .lower()
        )
        if confirm != "yes":
            print("Operation cancelled by user.")
            sys.exit(0)
        
        # Create upload package
        upload_spec, full_commit_hash = create_upload_package(changed_files, repo_path, commit2, UPLOAD_PACKAGE_DIR)
        
        # Update package_hash in config file
        config["repo"]["package_hash"] = full_commit_hash
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
        
        print(f"\nConfiguration updated with package_hash: {full_commit_hash}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

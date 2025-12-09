import os
import sys
import json
import subprocess

# -------------------- Display Menu --------------------
def show_menu():
    """Display operation menu and get user choice."""
    print("\n=== git-remote-sync ===")
    print("1. Run Packer (create upload package)")
    print("2. Run Uploader (upload from package)")
    print("3. Run Full Pipeline (pack and upload)")
    print("4. Exit")
    
    choice = input("\nSelect operation (1-4): ").strip()
    return choice


# -------------------- Load Configuration from JSON --------------------
def load_config(config_file):
    """Load and validate configuration from JSON file."""
    if not os.path.isfile(config_file):
        print(f"Configuration file '{config_file}' not found.")
        sys.exit(1)
    
    with open(config_file, "r") as f:
        config = json.load(f)
    
    return config


# -------------------- Get Changed Files --------------------
def get_changed_files(repo_path, commit1, commit2):
    """Get list of changed files between two commits."""
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


# -------------------- Run Packer --------------------
def run_packer(config_file):
    """Run packer.py to create upload package."""
    script_path = os.path.join(os.path.dirname(__file__), "packer.py")
    if not os.path.isfile(script_path):
        print("Error: packer.py not found in the same directory.")
        return False
    
    # Run packer script
    result = subprocess.run([sys.executable, script_path], cwd=os.getcwd())
    return result.returncode == 0


# -------------------- Run Uploader --------------------
def run_uploader(config_file):
    """Run uploader.py to upload from package."""
    script_path = os.path.join(os.path.dirname(__file__), "uploader.py")
    if not os.path.isfile(script_path):
        print("Error: uploader.py not found in the same directory.")
        return False
    
    # Run uploader script
    result = subprocess.run([sys.executable, script_path], cwd=os.getcwd())
    return result.returncode == 0


# -------------------- Run Full Pipeline --------------------
def run_full_pipeline(config_file):
    """Run complete pipeline: pack then upload."""
    config = load_config(config_file)
    repo_path = config["repo"]["path"]
    earlier_hash = config["repo"]["earlier_hash"]
    
    ftp_config = config.get("ftp", {})
    ftp_host = ftp_config.get("host")
    ftp_user = ftp_config.get("username")
    ftp_pass = ftp_config.get("password")
    ftp_target_dir = ftp_config.get("target_dir")
    
    if not all([repo_path, ftp_host, ftp_user, ftp_pass, ftp_target_dir]):
        print("Missing configuration parameters in JSON file.")
        return False
    
    try:
        # Get commit hashes from user
        commit1 = input(f"earlier hash{f' ({earlier_hash})' if earlier_hash else ''}: ").strip()
        commit1 = commit1 if len(commit1) else earlier_hash
        commit2 = input("present hash (HEAD): ").strip()
        commit2 = commit2 if len(commit2) else 'HEAD'
        
        if not commit1:
            print("Error: earlier hash is required.")
            return False
        
        # Get changed files
        changed_files = get_changed_files(repo_path, commit1, commit2)
        if not changed_files:
            print("No changed files found between the specified commits.")
            return True
        
        print("Changed files:")
        for file in changed_files:
            print(f" - {file}")
        
        confirm = (
            input("\nDo you want to proceed with packing and uploading? (yes/no): ")
            .strip()
            .lower()
        )
        if confirm != "yes":
            print("Operation cancelled by user.")
            return True
        
        # Create upload package
        from packer import create_upload_package
        create_upload_package(changed_files, repo_path, commit2, "upload-package")
        
        # Upload files
        from uploader import upload_via_ftp
        upload_via_ftp("upload-package", "upload-spec.json", ftp_host, ftp_user, ftp_pass, ftp_target_dir)
        
        # Update config with new earlier_hash
        config["repo"]["earlier_hash"] = get_git_commit_hash(repo_path, commit2)
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
        
        print("Pipeline completed successfully.")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False


# -------------------- Main Execution --------------------
def main():
    config_file = input("config file: ")
    
    while True:
        choice = show_menu()
        
        if choice == "1":
            print("\n--- Running Packer ---")
            if run_packer(config_file):
                print("Packer completed successfully.")
            else:
                print("Packer failed or was cancelled.")
        
        elif choice == "2":
            print("\n--- Running Uploader ---")
            if run_uploader(config_file):
                print("Uploader completed successfully.")
            else:
                print("Uploader failed or was cancelled.")
        
        elif choice == "3":
            print("\n--- Running Full Pipeline ---")
            if run_full_pipeline(config_file):
                print("Full pipeline completed successfully.")
            else:
                print("Full pipeline failed or was cancelled.")
        
        elif choice == "4":
            print("Exiting...")
            sys.exit(0)
        
        else:
            print("Invalid choice. Please select 1-4.")


if __name__ == "__main__":
    main()

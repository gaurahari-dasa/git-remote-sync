import os
import sys
import json
import subprocess
import shutil
from ftplib import FTP

# ------------------ Load Configuration from JSON ------------------
config_file = input("config file: ")

if not os.path.isfile(config_file):
    print(f"Configuration file '{config_file}' not found.")
    sys.exit(1)

with open(config_file, "r") as f:
    config = json.load(f)

repo_path = config["repo"]["path"]
earlier_hash = config["repo"]["earlier_hash"]

ftp_config = config.get("ftp", {})
ftp_host = ftp_config.get("host")
ftp_user = ftp_config.get("username")
ftp_pass = ftp_config.get("password")
ftp_target_dir = ftp_config.get("target_dir")

if not all([repo_path, ftp_host, ftp_user, ftp_pass, ftp_target_dir]):
    print("Missing configuration parameters in JSON file.")
    sys.exit(1)

# Temporary folder to store files before FTP upload
temp_upload_dir = "ftp_upload"

# ------------------ Get Changed Files ------------------
def get_changed_files(repo_path, commit1, commit2):
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


# ------------------ Copy Files ------------------
def copy_files(file_list, repo_path, temp_upload_dir):
    if os.path.exists(temp_upload_dir):
        shutil.rmtree(temp_upload_dir)
    for file in file_list:
        src = os.path.join(repo_path, file)
        dst = os.path.join(temp_upload_dir, file)
        if os.path.isfile(src):
            print(f"Copying: {file}")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


# ------------------ FTP Upload ------------------
def upload_via_ftp(temp_upload_dir, ftp_host, ftp_user, ftp_pass, ftp_target_dir):
    ftp = FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)
    ftp.cwd(ftp_target_dir)

    for root, _, files in os.walk(temp_upload_dir):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, temp_upload_dir)
            remote_dirs = os.path.dirname(relative_path).split(os.sep)

            # Create remote directories if needed
            for dir in remote_dirs:
                if dir and dir not in ftp.nlst():
                    try:
                        ftp.mkd(dir)
                    except:
                        pass
                ftp.cwd(dir)

            # Upload file
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR " + file, f)

            # Return to target directory
            ftp.cwd(ftp_target_dir)

    ftp.quit()


# ----------- Git SHA1 commit hash of HEAD ------------
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


commit1 = input(f"earlier hash{f' ({earlier_hash})' if earlier_hash else ''}: ").strip()
commit1 = commit1 if len(commit1) else earlier_hash
commit2 = input("present hash (HEAD): ").strip()
commit2 = commit2 if len(commit2) else 'HEAD'

# ------------------ Main Execution ------------------
try:
    changed_files = get_changed_files(repo_path, commit1, commit2)
    if not changed_files:
        print("No changed files found between the specified commits.")
        sys.exit(0)

    print("Changed files:")
    for file in changed_files:
        print(f" - {file}")

    confirm = (
        input("Do you want to proceed with copying and FTP upload? (yes/no): ")
        .strip()
        .lower()
    )
    if confirm != "yes":
        print("Operation cancelled by user.")
        sys.exit(0)

    copy_files(changed_files, repo_path, temp_upload_dir)
    upload_via_ftp(temp_upload_dir, ftp_host, ftp_user, ftp_pass, ftp_target_dir)
    print("Files uploaded successfully via FTP.")
    config["repo"]["earlier_hash"] = get_git_commit_hash(repo_path, commit2)
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)
except Exception as e:
    print(f"Error: {e}")

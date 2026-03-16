import os
import subprocess
import re


def setup_repo(config):
    """
    Set up a cloned Git repository, checking out the release branch and pulling latest changes.
    
    Parameters:
    config: Configuration dictionary containing repo.uri and repo.release_branch
    
    Returns:
    str: Path to the local repository
    """
    uri = config["repo"]["uri"]
    release_branch = config["repo"].get("release_branch", "main")
    
    # Determine if URI is remote or local
    if uri.startswith(("http://", "https://", "git@", "ssh://")):
        # Remote repository - extract repo name for local directory
        repo_name = re.sub(r'\.git$', '', uri.split('/')[-1])
        local_path = os.path.join(os.getcwd(), repo_name)
        
        if not os.path.exists(local_path):
            print(f"Cloning repository from {uri} to {local_path}")
            result = subprocess.run(
                ["git", "clone", uri, local_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"Failed to clone repository: {result.stderr}")
        else:
            print(f"Repository already exists at {local_path}")
    else:
        # Local repository path
        local_path = uri
        if not os.path.exists(local_path):
            raise Exception(f"Local repository path does not exist: {local_path}")
        print(f"Using local repository at {local_path}")
    
    # Checkout to release branch
    print(f"Checking out to release branch: {release_branch}")
    result = subprocess.run(
        ["git", "checkout", release_branch],
        cwd=local_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Failed to checkout to {release_branch}: {result.stderr}")
    
    # Pull latest changes
    print("Pulling latest changes...")
    result = subprocess.run(
        ["git", "pull"],
        cwd=local_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Failed to pull changes: {result.stderr}")
    
    print(f"Repository setup complete at {local_path}")
    return local_path


if __name__ == "__main__":
    # Example usage
    import json
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python repo_manager.py <config_file>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    with open(config_file, "r") as f:
        config = json.load(f)
    
    try:
        repo_path = setup_repo(config)
        print(f"Repository is ready at: {repo_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
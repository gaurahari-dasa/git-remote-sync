import subprocess


def build(config: dict, temp_checkout_path: str):
    """
    Run the build command in the temporary checkout directory.

    Parameters:
    config: Configuration dictionary
    temp_checkout_path: Path to the temporary checkout directory

    Returns:
    bool: True if build succeeds or no build command, False otherwise
    """
    build_spec = config.get("build", {})
    if not isinstance(build_spec, dict):
        print("Invalid build configuration; expected object. Skipping build step.")
        return True

    # Support both `commands` list and legacy single `command` string.
    commands = []
    if "commands" in build_spec and isinstance(build_spec["commands"], list):
        commands = build_spec["commands"]
    elif "command" in build_spec and isinstance(build_spec["command"], str):
        commands = [build_spec["command"]]

    if not commands:
        print("No build command specified, skipping build step.")
        return True

    for idx, cmd in enumerate(commands, start=1):
        print(f"Running build command [{idx}/{len(commands)}]: {cmd}")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=temp_checkout_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                print(f"Build command failed with return code {result.returncode}")
                print(f"Command stdout: {result.stdout}")
                print(f"Command stderr: {result.stderr}")
                return False
        except Exception as e:
            print(f"Exception during build command: {e}")
            return False

    print("Build completed successfully.")
    return True
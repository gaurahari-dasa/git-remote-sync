# Copilot Instructions for git-remote-sync

## Project Overview
**git-remote-sync** is a deployment automation tool that synchronizes code changes from a Git repository to a remote FTP server. It uses Git diff to identify changed files between commits, stages them locally, then uploads only those deltas to production/staging environments.

**Core workflow:** Config → Identify changes → User confirmation → Copy → FTP upload → Update config

## Key Architecture

### Configuration-Driven Design
- All settings stored in JSON files (`cpp-website-uat.json`, `prod.json`)
- Required fields: `repo.path`, `repo.earlier_hash`, `ftp.{host,username,password,target_dir}`
- The `earlier_hash` acts as the baseline and gets updated after successful uploads (auto-persisted to config)

### Three-Stage Execution Pipeline
1. **Get Changed Files** - `get_changed_files()` uses `git diff --name-only <commit1> <commit2>`
2. **Local Staging** - `copy_files()` recreates directory structure in `ftp_upload/` temp dir
3. **FTP Upload** - `upload_via_ftp()` creates remote directories and uploads only changed files

### User Interaction Pattern
- Script prompts for config file path, commit hashes (with defaults), and confirmation
- Earlier hash defaults from config if provided; present hash defaults to `HEAD`
- No CLI args — all input via interactive prompts

## Developer Workflows

### Running a Deployment
```bash
python git_remote_sync.py
# Follow prompts: config file → earlier hash → present hash → confirm (yes/no)
```

### Testing a Diff Without Upload
- Stop after "Do you want to proceed?" prompt
- Inspect `ftp_upload/` directory to verify correct files staged
- Inspect git diff manually: `git diff --name-only <hash1> <hash2>`

### Resetting Earlier Hash (if deployment fails/reverts)
- Manually edit JSON config, adjust `earlier_hash` to desired commit
- Re-run script with corrected baseline

## Critical Patterns & Conventions

### FTP Directory Navigation
- Script changes directory with `ftp.cwd()` during upload, returns to target dir after each file
- Remote dir structure created on-demand: missing directories are created with `ftp.mkd()`
- Exception suppression on mkdir allows retry without errors

### Error Handling Philosophy
- Subprocess errors propagate: `git diff` failures raise exceptions and halt
- FTP connection errors (login, network) will crash script—no retry logic
- File copy errors (missing source, permission) silently skip individual files

### Relative Paths
- Git diff returns paths relative to repo root
- `os.path.relpath()` converts to local paths for staging
- `ftp_upload/` directory mirrors source repo structure exactly

## Important Implementation Details

### The `earlier_hash` Update Pattern
```python
config["repo"]["earlier_hash"] = get_git_commit_hash(repo_path, commit2)
```
- Only happens AFTER successful FTP upload (in try block, before except)
- Enables "incremental deploys" — next run automatically compares from last deployed commit
- If upload fails, config is NOT updated (good for resume logic)

### Temp Directory Cleanup
```python
if os.path.exists(temp_upload_dir):
    shutil.rmtree(temp_upload_dir)
```
- Full cleanup before each staging run — ensures no stale files from previous failed uploads

## Common Modifications

- **Add pre-upload validation**: Insert checks before `upload_via_ftp()` call
- **Support multiple config environments**: Load config file path from environment variable instead of prompt
- **Add rollback**: Capture uploaded file list and implement reverse FTP delete
- **Extend FTP to S3/cloud**: Replace `upload_via_ftp()` function; keep config/diff logic unchanged

## Code File References
- `git_remote_sync.py` - Single monolithic script (148 lines); no separate modules
- Config examples: `cpp-website-uat.json`, `prod.json`
- Staging temp dir: `ftp_upload/` (git-ignored)

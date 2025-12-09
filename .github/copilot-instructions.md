# Copilot Instructions for git-remote-sync

## Project Overview
**git-remote-sync** is a deployment automation tool that synchronizes code changes from a Git repository to a remote FTP server. It uses Git diff to identify changed files between commits, creates numbered upload packages, then uploads them to production/staging environments via FTP.

**Core workflow:** Git diff → Package creation (numbered files + mapping) → User confirmation → FTP upload → Update config

## Key Architecture

### Modular Three-Script Design
1. **git_remote_sync.py** - Main CLI controller with menu-driven interface
2. **packer.py** - Creates upload packages (numbered files + JSON spec)
3. **uploader.py** - Uploads packaged files via FTP using spec mapping

### Configuration-Driven Design
- All settings in JSON files (`cpp-website-uat.json`, `prod.json`)
- Required fields: `repo.path`, `ftp.{host,username,password,target_dir}`
- The `package_hash` tracks the last commit that was packaged and uploaded
- `package_hash` updates immediately after successful package creation
- `package_hash` is also stored in `upload-spec.json` for reference

### Upload Package Structure
```
upload-package/
  1                    # Numbered file (file content)
  2                    # Numbered file (file content)
  3                    # Numbered file (file content)
  upload-spec.json     # {
                       #   "__package_hash__": "abc123def456...",
                       #   "1": "path/to/file1.js",
                       #   "2": "path/to/file2.css",
                       #   "3": "path/to/file3.html"
                       # }
```

## Developer Workflows

### Running via Menu System
```bash
python git_remote_sync.py
# Select: 1=Packer, 2=Uploader, 3=Full Pipeline, 4=Exit
```

### Separate Packer and Uploader Execution
```bash
# Create package at one time
python packer.py
# config file: cpp-website-uat.json
# earlier hash: <accepts default or input>
# present hash: <accepts default or input>
# Inspect upload-package/ directory
# Upload at different time
python uploader.py
# config file: cpp-website-uat.json
```

### Full Pipeline (Pack + Upload in one run)
- Select option 3 from main menu or run directly via scripts
- Handles commit hash validation and config updates automatically

### Inspecting Package Before Upload
- Check `upload-package/upload-spec.json` to verify file mappings
- Review numbered files to validate content was captured correctly
- Upload specification is human-readable JSON for debugging

## Critical Patterns & Conventions

### Packer (packer.py)
- Retrieves file content directly from Git using `git show <commit>:<filepath>`
- Creates numbered files sequentially (1, 2, 3, ...) for portability
- Generates `upload-spec.json` mapping numbered files to target paths
- Handles deleted/missing files gracefully with warnings
- Cleans up previous packages before creating new ones

### Uploader (uploader.py)
- Reads `upload-spec.json` to find target paths for each numbered file
- Normalizes Windows paths to FTP-compatible forward slashes
- Creates remote directories on-demand with `ftp.mkd()`
- Exception suppression on mkdir (directory may already exist)
- Returns to target directory after each file upload

### Git Integration
- `get_changed_files()` uses `git diff --name-only <commit1> <commit2>`
- `get_git_commit_hash()` resolves aliases like 'HEAD' to full SHA-1
- Full pipeline updates `earlier_hash` AFTER successful upload

## Important Implementation Details

### The `package_hash` Update Pattern
```python
config["repo"]["package_hash"] = full_commit_hash
```
- Updates **immediately after successful package creation** (not after upload)
- Enables incremental deploys — next packer run defaults to comparing from last packaged commit
- Stored in `upload-spec.json` as `__package_hash__` metadata for audit trail
- If packing fails, config remains unchanged (supports retry)

### Numbered File Advantages
- Portable across systems (no special character issues)
- Compact package structure regardless of path depth
- Clear file counting for validation
- Independent of source file extensions

### Path Mapping in upload-spec.json
- Includes `__package_hash__` metadata entry for audit trail
- All other paths are relative to FTP target directory
- Windows path separators converted to `/` for FTP compatibility
- Format: `{"__package_hash__": "abc123...", "1": "resources/js/app.js", "2": "css/styles.css", ...}`

## Common Modifications

- **Add file filtering**: Modify `get_changed_files()` to exclude patterns (tests, config, docs)
- **Package versioning**: Add timestamp or commit hash to `upload-package/` naming
- **Pre-upload validation**: Insert integrity checks in uploader before FTP operations
- **Selective upload**: Only upload files matching specific patterns from `upload-spec.json`
- **Support S3/cloud**: Create new upload backend matching `upload_via_ftp()` signature
- **Deployment logging**: Track uploaded files to separate log file per deployment

## Code File References
- `git_remote_sync.py` - Main controller (~180 lines); menu + pipeline orchestration
- `packer.py` - Package creation (~177 lines); Git integration + file numbering
- `uploader.py` - FTP upload (~153 lines); specification mapping + remote directory handling
- Config examples: `cpp-website-uat.json`, `prod.json`
- Package dir: `upload-package/` (contains numbered files + spec JSON)

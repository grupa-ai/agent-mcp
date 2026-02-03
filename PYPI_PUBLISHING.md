# PyPI Publishing Guide for agent-mcp

This guide explains how to publish updates to the `agent-mcp` package on PyPI.

## Current Status

- **Package Name**: `agent-mcp`
- **PyPI URL**: https://pypi.org/project/agent-mcp/
- **Current Version**: 0.1.6 (updated)

## Prerequisites

1. **PyPI Account**: You need an account on [PyPI](https://pypi.org) and [TestPyPI](https://test.pypi.org) (optional, for testing)
2. **API Token**: Create an API token at https://pypi.org/manage/account/token/
3. **Build Tools**: Install required tools:
   ```bash
   pip install --upgrade build twine setuptools wheel
   ```

## Quick Start

### Option 1: Use the Automated Script (Recommended)

**Python Script:**
```bash
python3 publish_to_pypi.py
```

**Bash Script:**
```bash
./publish_to_pypi.sh
```

Both scripts will:
- Check current version
- Optionally update version
- Install/upgrade build tools
- Clean previous builds
- Build the package
- Upload to PyPI (with confirmation)

### Option 2: Manual Process

1. **Update Version** (if needed):
   - Update version in `setup.py`
   - Update version in `pyproject.toml`
   - Update version in `agent_mcp/__init__.py`

2. **Clean Previous Builds**:
   ```bash
   rm -rf build/ dist/ *.egg-info/
   ```

3. **Build the Package**:
   ```bash
   python3 -m build
   ```
   This creates both a source distribution (`.tar.gz`) and a wheel (`.whl`) in the `dist/` directory.

4. **Check the Build**:
   ```bash
   ls -lh dist/
   ```
   You should see:
   - `agent_mcp-0.1.6-py3-none-any.whl`
   - `agent_mcp-0.1.6.tar.gz`

5. **Upload to PyPI**:
   ```bash
   twine upload dist/*
   ```
   You'll be prompted for:
   - Username: `__token__`
   - Password: Your PyPI API token

6. **Verify Upload**:
   Visit https://pypi.org/project/agent-mcp/ to see your new version.

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 0.1.6)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Testing Before Publishing

### Test on TestPyPI First (Recommended)

1. Upload to TestPyPI:
   ```bash
   twine upload --repository testpypi dist/*
   ```

2. Test installation:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ agent-mcp
   ```

3. If successful, upload to production PyPI:
   ```bash
   twine upload dist/*
   ```

### Local Testing

Test the build locally:
```bash
pip install dist/agent_mcp-0.1.6-py3-none-any.whl
# or
pip install dist/agent_mcp-0.1.6.tar.gz
```

## Files That Need Version Updates

When updating the version, make sure to update it in:

1. `setup.py` - Line with `version="X.X.X"`
2. `pyproject.toml` - Line with `version = "X.X.X"`
3. `agent_mcp/__init__.py` - Line with `__version__ = "X.X.X"`

## Troubleshooting

### "Package already exists" Error

This means the version already exists on PyPI. You need to:
- Increment the version number
- Update all version files
- Rebuild and upload

### "Invalid credentials" Error

- Make sure you're using `__token__` as the username
- Use your PyPI API token (not your password)
- Check that the token has upload permissions

### Build Errors

- Ensure all dependencies are listed in `pyproject.toml`
- Check that `MANIFEST.in` includes all necessary files
- Verify `setup.py` is correctly configured

## Security Best Practices

1. **Use API Tokens**: Never use your PyPI password directly
2. **Token Scope**: Create tokens with only the necessary permissions
3. **Don't Commit Tokens**: Never commit API tokens to git
4. **Use `.pypirc`** (optional): Store credentials securely:
   ```ini
   [pypi]
   username = __token__
   password = pypi-YourTokenHere
   ```
   Place in `~/.pypirc` with proper permissions (chmod 600)

## Post-Publishing Checklist

- [ ] Verify package appears on PyPI
- [ ] Test installation: `pip install agent-mcp==0.1.6`
- [ ] Update release notes/changelog (if applicable)
- [ ] Tag the release in git: `git tag v0.1.6`
- [ ] Push tags: `git push --tags`

## Additional Resources

- [PyPI Documentation](https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Python Packaging Guide](https://packaging.python.org/)

## Notes

- The package uses both `setup.py` and `pyproject.toml` for compatibility
- Build artifacts are excluded from the package via `MANIFEST.in`
- The package requires Python 3.11+

# Agents

This file describes the AI agents participating in the development of this project and the established development workflow.

## Antigravity (Google DeepMind)
The primary coding assistant for this project. Responsible for architecture, unification, and implementation of the simulator.

### Development Workflow & Release Protocol

The agent is responsible for maintaining the stability and consistency of the simulator. All changes intended for a new version must follow this protocol:

#### 1. Feature Development & Synchronization
- Implement features or fixes following the modular architecture.
- Geographical coordinates in common code and documentation MUST remain anonymized (using 50.0N, 20.0E as placeholders).
- Ensure version consistency across all locations:
  - `pyproject.toml` (project version)
  - `src/caux_simulator/__init__.py` (`__version__` string)
  - `STATUS.md` (header version)
  - `CHANGELOG.md` (add entry for the new version)

#### 2. Verification
- All tests MUST pass before a release. The project uses `pytest`.
- Run unit tests: `pytest tests/unit`
- Run protocol tests: `PYTHONPATH=src pytest tests/protocol`
- Run integration tests: `pytest tests/integration`
- All protocol handlers (like WiFi sync `0x30`, `0x31`) should have corresponding tests.

#### 3. Release Script
- Use the provided `scripts/release.sh` to automate the local release process.
- The script:
  1. Validates documentation consistency.
  2. Runs the full test suite.
  3. Builds the distribution packages (`.tar.gz`, `.whl`) in an isolated environment.
  4. Performs `twine check` on the build.
  5. Automatically creates a Git tag (e.g., `v0.2.31`) on the current commit.

#### 4. Git Integrity
- A release commit MUST include:
  1. All final code changes.
  2. Updated `CHANGELOG.md` and `STATUS.md`.
  3. Synchronized version numbers.
- The Git tag MUST point exactly to the commit containing all these elements. NEVER tag a commit that is missing any part of the release data.

#### 5. CI/CD & Publishing
- The project uses GitHub Actions (`.github/workflows/publish.yml`).
- Pushing a version tag (`v*`) triggers the automated workflow.
- The workflow runs the full test suite on multiple Python versions (3.11, 3.12, 3.13) before publishing.
- Initially, publishing is directed to **TestPyPI**. To switch to production PyPI, modify the `publish.yml` workflow.

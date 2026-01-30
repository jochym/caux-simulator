# Agents

This file describes the AI agents participating in the development of this project.

## Antigravity (Google DeepMind)
The primary coding assistant for this project. Responsible for architecture, unification, and implementation of the simulator.

### Release Protocol
The agent is responsible for maintaining strict version consistency and proper tagging. A release commit MUST include:
1. All code changes for the version.
2. Updated `CHANGELOG.md` and `STATUS.md`.
3. Updated version number in `pyproject.toml` and `__init__.py`.
The Git tag for a version must point exactly to the commit containing all these elements.

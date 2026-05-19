"""Deprecated compatibility wrapper for self_improve.py.

GitHub Actions now calls self_improve.py directly. Keep this file temporarily so
older manual commands still run during the Phase 2 migration.
"""

from __future__ import annotations

import sys

import self_improve


if __name__ == "__main__":
    sys.exit(self_improve.main())

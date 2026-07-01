"""Ensure `import tools` works from tests without requiring a pip install."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

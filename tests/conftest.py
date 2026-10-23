"""Make the skill's scripts importable from tests without installing anything."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "linkedin-job" / "scripts"
sys.path.insert(0, str(SCRIPTS))

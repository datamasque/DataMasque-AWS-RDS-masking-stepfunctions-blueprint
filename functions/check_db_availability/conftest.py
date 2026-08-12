import os
import sys

# Ensure this Lambda's app.py is importable as `app` and not shadowed by a
# same-named module from a sibling function directory when pytest collects the
# whole tree from the repo root.
_here = os.path.dirname(__file__)
if _here not in sys.path:
    sys.path.insert(0, _here)
sys.modules.pop("app", None)

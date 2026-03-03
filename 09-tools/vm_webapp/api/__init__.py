# Re-export router from api.py file for backwards compatibility
# We use importlib to avoid circular imports since this package shadows the api.py file
import importlib.util
import sys
from pathlib import Path

# Load the api.py file directly as a module
spec = importlib.util.spec_from_file_location(
    "_api_module", 
    Path(__file__).parent.parent / "api.py"
)
_api_module = importlib.util.module_from_spec(spec)
sys.modules["_api_module"] = _api_module
spec.loader.exec_module(_api_module)

router = _api_module.router

__all__ = ["router"]

"""heuresis: a cost-ordered, time-aware, verified-and-abstaining retrieval engine."""
from .engine import Engine
from .model import Answer, AsOf, Scope
from .surface.config import load_config

__version__ = "0.1.0"

__all__ = ["Engine", "AsOf", "Scope", "Answer", "load_config", "__version__"]

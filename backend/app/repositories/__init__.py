"""Repository layer for database access."""

from app.repositories.analysis import AnalysisRepository
from app.repositories.stock import StockRepository

__all__ = ["StockRepository", "AnalysisRepository"]

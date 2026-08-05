"""Stock repository — Supabase queries for the stocks table."""

from supabase import Client

from app.db.client import get_supabase
from app.models.stock import Stock


class StockRepository:
    """Data access for the stocks table."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or get_supabase()

    def list_stocks(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Stock], int]:
        """List stocks with optional search and pagination.

        Returns ``(rows, total)`` where ``total`` is the total count
        of rows matching the filter, ignoring pagination.
        """
        start = (page - 1) * page_size
        end = start + page_size - 1

        builder = self._client.table("stocks").select("*", count="exact")

        if query:
            escaped = query.replace("%", "")
            pattern = f"%{escaped}%"
            builder = builder.or_(f"ticker.ilike.{pattern},company_name.ilike.{pattern}")

        try:
            count_builder = self._client.table("stocks").select("*", count="exact")
            if query:
                escaped = query.replace("%", "")
                pattern = f"%{escaped}%"
                count_builder = count_builder.or_(
                    f"ticker.ilike.{pattern},company_name.ilike.{pattern}"
                )
            count_response = count_builder.execute()
            total = count_response.count or 0
        except Exception:
            total = 0

        try:
            response = builder.range(start, end).execute()
        except Exception:
            return [], total

        rows = response.data or []
        return [Stock.model_validate(row) for row in rows], total

    def get_stock(self, ticker: str) -> Stock | None:
        """Fetch a single stock by ticker, or ``None`` if not found."""
        try:
            response = (
                self._client.table("stocks")
                .select("*")
                .eq("ticker", ticker.upper())
                .single()
                .execute()
            )
        except Exception:
            return None

        row = response.data
        if not row:
            return None
        return Stock.model_validate(row)

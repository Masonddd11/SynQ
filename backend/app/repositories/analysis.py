"""Analysis repository — Supabase queries for the analyses table."""

from postgrest.types import CountMethod
from supabase import Client, create_client

from app.config import settings
from app.db.client import get_supabase
from app.models.analysis import Analysis, AnalysisStatus


class AnalysisRepository:
    """Data access for the analyses table.

    Uses the service-role key client when available so server-side jobs can
    read and write any user's analyses.
    """

    def __init__(self, client: Client | None = None) -> None:
        if client is not None:
            self._client = client
        elif settings.supabase_service_key:
            self._client = create_client(settings.supabase_url, settings.supabase_service_key)
        else:
            self._client = get_supabase()

    def list_analyses(
        self,
        user_id: str,
        ticker: str | None = None,
        status: AnalysisStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Analysis], int]:
        """List analyses for a user, optionally filtered and paginated.

        Returns ``(rows, total)`` where ``total`` is the total count of
        matching rows, ignoring pagination.
        """
        start = (page - 1) * page_size
        end = start + page_size - 1

        builder = self._client.table("analyses").select("*", count=CountMethod.exact)
        builder = builder.eq("user_id", user_id)
        if ticker:
            builder = builder.eq("ticker", ticker)
        if status:
            builder = builder.eq("status", status.value)

        try:
            count_builder = self._client.table("analyses").select("*", count=CountMethod.exact)
            count_builder = count_builder.eq("user_id", user_id)
            if ticker:
                count_builder = count_builder.eq("ticker", ticker)
            if status:
                count_builder = count_builder.eq("status", status.value)
            count_response = count_builder.execute()
            total = count_response.count or 0
        except Exception:
            total = 0

        try:
            response = builder.order("created_at", desc=True).range(start, end).execute()
        except Exception:
            return [], total

        rows = response.data or []
        return [Analysis.model_validate(row) for row in rows], total

    def get_analysis(self, user_id: str, analysis_id: str) -> Analysis | None:
        """Fetch a single analysis owned by the user, or ``None``."""
        try:
            response = (
                self._client.table("analyses")
                .select("*")
                .eq("id", analysis_id)
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
        except Exception:
            return None

        if response is None or not response.data:
            return None
        return Analysis.model_validate(response.data)

    def get_latest_analysis(self, user_id: str, ticker: str) -> Analysis | None:
        """Fetch the most recently completed analysis for a ticker, or ``None``."""
        try:
            response = (
                self._client.table("analyses")
                .select("*")
                .eq("user_id", user_id)
                .eq("ticker", ticker)
                .eq("status", AnalysisStatus.COMPLETED.value)
                .order("completed_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception:
            return None

        row = response.data[0] if response.data else None
        if not row:
            return None
        return Analysis.model_validate(row)

    def create_analysis(self, user_id: str, ticker: str) -> Analysis:
        """Insert a pending analysis and return it.

        Raises on database errors; callers translate into API errors.
        """
        response = (
            self._client.table("analyses")
            .insert(
                {
                    "user_id": user_id,
                    "ticker": ticker,
                    "status": AnalysisStatus.PENDING.value,
                }
            )
            .execute()
        )
        row = response.data[0]
        return Analysis.model_validate(row)

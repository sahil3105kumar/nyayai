"""
the ONLY way rules code should touch Qdrant. rules/citation_checker.py
calls corpus.search, never the Qdrant client directly - that's what keeps
citation checking, future semantic retrieval, and future repeal mapping
all working off the same collection without rules code needing to know
Qdrant's API.

exact-field filter, no vector similarity, no model loading - citation
checking works even when the ML token-classification model isn't loaded.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from corpus.uploader import COLLECTION_NAME, get_client


def lookup_section(number: str, act: str, client: QdrantClient | None = None) -> dict | None:
    """exact citation lookup: does this section/article exist, and is it active?"""
    client = client or get_client()

    result = client.query_points(
        collection_name=COLLECTION_NAME,
        query_filter=Filter(
            must=[
                FieldCondition(key="number", match=MatchValue(value=number)),
                FieldCondition(key="act", match=MatchValue(value=act)),
            ]
        ),
        limit=1,
        with_payload=True,
    )

    if not result.points:
        return None

    return result.points[0].payload
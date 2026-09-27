"""Recipe URL import worker tests with mocked Gemini extract (issue #8)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.database import AsyncSessionLocal
from app.db_models.models import RecipeUrlImport
from app.pydantic_models.recipes import RecipeExtract
from app.scripts.extract import PageFetchResult
from app.recipe_import_worker import process_job


async def _reload_job(job_id: int) -> RecipeUrlImport:
    async with AsyncSessionLocal() as session:
        row = await session.get(RecipeUrlImport, job_id)
        assert row is not None
        return row


async def _insert_running_job(url_suffix: str) -> int:
    async with AsyncSessionLocal() as session:
        job = RecipeUrlImport(
            url=f"https://example.com/{url_suffix}",
            normalized_url=f"https://example.com/{url_suffix}",
            status="running",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_job_marks_ready() -> None:
    tag = uuid.uuid4().hex
    job_id = await _insert_running_job(f"recipe-{tag}")

    fake = RecipeExtract(name="Test", dish_name=f"Dish {tag}", components=[])

    with patch(
        "app.recipe_import_worker.extractor.fetch_page_for_import",
        new_callable=AsyncMock,
        return_value=PageFetchResult("Homemade caramel\n" + ("sugar " * 80), []),
    ), patch(
        "app.recipe_import_worker.extractor.extract_from_cached_page",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        await process_job(job_id)

    row = await _reload_job(job_id)
    assert row.status == "ready"
    assert row.extract is not None
    assert row.extract.get("dish_name") == f"Dish {tag}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_job_marks_failed() -> None:
    tag = uuid.uuid4().hex
    job_id = await _insert_running_job(f"fail-{tag}")

    with patch(
        "app.recipe_import_worker.extractor.fetch_page_for_import",
        new_callable=AsyncMock,
        side_effect=RuntimeError("gemini down"),
    ):
        await process_job(job_id)

    row = await _reload_job(job_id)
    assert row.status == "failed"
    assert "gemini down" in (row.error or "")

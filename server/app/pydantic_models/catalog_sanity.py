from datetime import datetime

from pydantic import BaseModel


class CatalogSanityRunCreate(BaseModel):
    use_laya: bool = False


class CatalogSanityDropItem(BaseModel):
    food_id: int
    layer: str
    reason: str
    name_en: str
    name_fr: str
    group_en: str


class CatalogSanityRunItem(BaseModel):
    id: int
    status: str
    use_laya: bool
    total_foods: int | None
    pipeline_layer: str | None
    layer_current: int | None
    layer_total: int | None
    drops_count: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    progress_label: str | None = None


class CatalogSanityRunDetail(CatalogSanityRunItem):
    result_drops: list[CatalogSanityDropItem] | None = None

"""Flat Pydantic models for MCP tool JSON Schema (Gemini-compatible)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.pydantic_models import recipes as models


class McpIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Ingredient name")
    quantity: str = Field(description="Amount as a string, e.g. 2 or 1/2")
    unit: str = Field(description="Unit, e.g. g, ml, tbsp, cup")


class McpInstruction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1, description="Step number starting at 1")
    text: str = Field(description="Instruction text")


class McpComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Component name, e.g. Sauce or Main")
    ingredients: list[McpIngredient] = Field(min_length=1)
    instructions: list[McpInstruction] = Field(min_length=1)


def to_api_components(parts: list[McpComponent]) -> list[models.Component]:
    return [
        models.Component(
            name=p.name,
            ingredients=[
                models.Ingredient(name=i.name, quantity=i.quantity, unit=i.unit)
                for i in p.ingredients
            ],
            instructions=[
                models.Instruction(step=s.step, text=s.text) for s in p.instructions
            ],
        )
        for p in parts
    ]

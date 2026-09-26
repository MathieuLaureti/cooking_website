from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from app.database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)


class OAuthClient(Base):
    __tablename__ = "oauth_client"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    client_secret_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    redirect_uris: Mapped[List[str]] = mapped_column(
        JSONB, insert_default=[], server_default="[]"
    )
    token_endpoint_auth_method: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="client_secret_post"
    )


class Dish(Base):
    __tablename__ = "dish"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255),unique=True)
    recipes: Mapped[List["Recipe"]] = relationship(back_populates="dish",cascade="all, delete-orphan")

class Recipe(Base):
    __tablename__ = "recipe"

    id: Mapped[int] = mapped_column(primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dish.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))

    dish: Mapped["Dish"] = relationship(back_populates="recipes")
    components: Mapped[List["RecipeComponent"]] = relationship(back_populates="recipe",cascade="all, delete-orphan")

class RecipeComponent(Base):
    __tablename__ = "recipe_component"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    recipe: Mapped["Recipe"] = relationship(back_populates="components")
    ingredients: Mapped[List["Ingredient"]] = relationship(back_populates="component",cascade="all, delete-orphan")
    instructions: Mapped[List["Instruction"]] = relationship(back_populates="component",cascade="all, delete-orphan")

class Ingredient(Base):
    __tablename__ = "ingredient"

    id: Mapped[int] = mapped_column(primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("recipe_component.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[str] = mapped_column(String(50), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    component: Mapped["RecipeComponent"] = relationship(back_populates="ingredients")

class Instruction(Base):
    __tablename__ = "instruction"

    id: Mapped[int] = mapped_column(primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("recipe_component.id"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    component: Mapped["RecipeComponent"] = relationship(back_populates="instructions")
    
class MatchChecker(Base):
    __tablename__ = "match_checker"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, index=True)
    avoid: Mapped[List[str]] = mapped_column(
        ARRAY(Text), 
        insert_default=[], 
        server_default="{}"
    )
    affinities: Mapped[List[str]] = mapped_column(
        ARRAY(Text), 
        insert_default=[], 
        server_default="{}"
    )
    matches: Mapped[List[Tuple[str, int]]] = mapped_column(
        JSONB, 
        insert_default=[], 
        server_default="[]"
    )


class CatalogFood(Base):
    __tablename__ = "catalog_food"
    __table_args__ = (UniqueConstraint("source", "external_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    external_code: Mapped[str] = mapped_column(String(16), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_fr: Mapped[str] = mapped_column(String(255), nullable=False)
    group_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    group_en: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    group_fr: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    nutrients: Mapped[List["CatalogFoodNutrient"]] = relationship(
        back_populates="food", cascade="all, delete-orphan"
    )
    aliases: Mapped[List["CatalogAlias"]] = relationship(
        back_populates="food", cascade="all, delete-orphan"
    )


class CatalogNutrient(Base):
    __tablename__ = "catalog_nutrient"
    __table_args__ = (UniqueConstraint("source", "external_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    external_code: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_fr: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    decimals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tagname: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    foods: Mapped[List["CatalogFoodNutrient"]] = relationship(back_populates="nutrient")


class CatalogFoodNutrient(Base):
    __tablename__ = "catalog_food_nutrient"

    food_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_food.id", ondelete="CASCADE"), primary_key=True
    )
    nutrient_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_nutrient.id", ondelete="CASCADE"), primary_key=True
    )
    amount_per_100g: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)

    food: Mapped["CatalogFood"] = relationship(back_populates="nutrients")
    nutrient: Mapped["CatalogNutrient"] = relationship(back_populates="foods")


class CatalogAlias(Base):
    __tablename__ = "catalog_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    food_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_food.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    locale: Mapped[str] = mapped_column(String(2), nullable=False)

    food: Mapped["CatalogFood"] = relationship(back_populates="aliases")


class CatalogAliasReview(Base):
    __tablename__ = "catalog_alias_review"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    candidates: Mapped[list] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    food_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("catalog_food.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecipeUrlImport(Base):
    __tablename__ = "recipe_url_import"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="queued")
    extract: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recipe_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recipe.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
from typing import List, Optional, Tuple
from sqlalchemy import ForeignKey, String, Text, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from app.database import Base

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
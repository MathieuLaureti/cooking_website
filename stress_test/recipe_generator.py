import random
from faker import Faker
import uuid
import requests
from recipes import (
    DishBase,
    RecipeCreate,
    Component,
    Ingredient,
    Instruction,
)
import argparse
import os

fake = Faker()

BASE_URL = "http://127.0.0.1:6666/recipes"


def post_dish(dish: DishBase):
    response = requests.post(f"{BASE_URL}/dish", json=dish.model_dump())
    response.raise_for_status()
    return response.json()


def post_recipe(recipe: RecipeCreate, dish_id: int):
    response = requests.post(f"{BASE_URL}/recipe/{dish_id}", json=recipe.model_dump())
    response.raise_for_status()
    return response.json()


def create_test_data(DISH_COUNT: int, RECIPE_COUNT: int):
    for _ in range(DISH_COUNT):
        post_dish(create_test_dish())
    for _ in range(RECIPE_COUNT):
        dish_id = random.randint(1, DISH_COUNT)
        post_recipe(create_test_recipe(DISH_COUNT), dish_id)


def create_test_dish() -> DishBase:
    return DishBase(name=f"dish {uuid.uuid4()}")


def create_test_recipe(dish_count: int) -> RecipeCreate:
    num_components = random.randint(1, 5)

    components = []
    for _ in range(num_components):
        components.append(
            Component(
                name=fake.word().capitalize(),
                instructions=[
                    Instruction(step=i, text=fake.sentence(nb_words=12))
                    for i in range(1, random.randint(3, 10))
                ],
                ingredients=[
                    Ingredient(
                        name=fake.word(),
                        quantity=str(random.randint(1, 500)),
                        unit=random.choice(["g", "ml", "tbsp", "units"]),
                    )
                    for _ in range(random.randint(2, 12))
                ],
            )
        )

    return RecipeCreate(
        dish_id=random.randint(1, dish_count),
        name=f"{fake.color_name()} {fake.job()} Recipe {uuid.uuid4()}",
        components=components,
    )


def main():
    default_dishes = int(os.getenv("DISH_COUNT", 3))
    default_recipes = int(os.getenv("RECIPE_COUNT", 10))

    parser = argparse.ArgumentParser(description="Seed the recipe database.")
    parser.add_argument(
        "--dishes", type=int, default=default_dishes, help="Number of dishes to create"
    )
    parser.add_argument(
        "--recipes",
        type=int,
        default=default_recipes,
        help="Number of recipes to create",
    )

    args = parser.parse_args()

    print(f"Starting seed: {args.dishes} dishes, {args.recipes} recipes.")
    create_test_data(args.dishes, args.recipes)


if __name__ == "__main__":
    main()

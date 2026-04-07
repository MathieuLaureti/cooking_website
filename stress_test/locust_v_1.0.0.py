import random
import os
from locust import HttpUser, task, between


class RecipeUser(HttpUser):
    wait_time = between(0.1, 0.5)

    # Get counts from environment variables
    dish_count = int(os.getenv("DISH_COUNT", 10))
    recipe_count = int(os.getenv("RECIPE_COUNT", 50))

    @task(1)
    def get_dishes(self):
        self.client.get("/recipes/dishes")

    @task(2)
    def get_dish_recipes(self):
        dish_id = random.randint(1, self.dish_count)
        self.client.get(f"/recipes/recipes/{dish_id}")

    @task(2)
    def get_single_recipe(self):
        recipe_id = random.randint(1, self.recipe_count)
        self.client.get(f"/recipes/recipe/{recipe_id}")

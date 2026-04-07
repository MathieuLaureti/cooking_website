import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 100 },   // Warm up
    { duration: '2m', target: 500 },   // Initial pressure
    { duration: '3m', target: 2000 },  // High load (Axum territory) (Python Breaking Territory)
    { duration: '4m', target: 10000 }, // Rust Breaking terriory
    { duration: '10m', target: 50000 }, // Force Breaking
  ],
  thresholds: {
    // ABORT the test if the error rate exceeds 10%
    http_req_failed: [{ threshold: 'rate<0.1', abortOnFail: true }],
    // ABORT the test if 95% of requests take more than 1500ms
    http_req_duration: [{ threshold: 'p(95)<1500', abortOnFail: true }],
  },
};

export default function () {
  const host = __ENV.HOST || 'http://localhost:6666';
  const dishCount = parseInt(__ENV.DISH_COUNT) || 100;
  const recipeCount = parseInt(__ENV.RECIPE_COUNT) || 500;

  // Weighted task simulation (similar to your Locust setup)
  const rand = Math.random();

  if (rand < 0.2) {
    // 20% - List dishes
    let res = http.get(`${host}/recipes/dishes`);
    check(res, { 'status is 200': (r) => r.status === 200 });
  } else if (rand < 0.6) {
    // 40% - Get dish recipes
    let dishId = Math.floor(Math.random() * dishCount) + 1;
    let res = http.get(`${host}/recipes/recipes/${dishId}`);
    check(res, { 'status is 200': (r) => r.status === 200 });
  } else {
    // 40% - Get single recipe
    let recipeId = Math.floor(Math.random() * recipeCount) + 1;
    let res = http.get(`${host}/recipes/recipe/${recipeId}`);
    check(res, { 'status is 200': (r) => r.status === 200 });
  }

  // Realistic user "think time"
  sleep(Math.random() * 0.4 + 0.1);
}

import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 100 },   // Warm up
    { duration: '1m', target: 500 },   // Initial pressure
    { duration: '2m', target: 10000 }, // Rust Breaking terriory
    { duration: '5m', target: 50000 }, // Force Breaking
  ],
  thresholds: {
    // Abort if the error rate in the CURRENT sample window exceeds 10%
    'http_req_failed': [{
      threshold: 'rate < 0.005',
      abortOnFail: true,
      delayAbortEval: '0s'
    }],
    // Abort if the 95th percentile of the LAST 10 seconds exceeds 1500ms
    'http_req_duration{expected_response:true}': [{
      threshold: 'p(95) < 1500',
      abortOnFail: true
    }],
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

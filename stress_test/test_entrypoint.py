import os
import time
import json
import subprocess
from datetime import datetime, timedelta

from recipe_generator import create_test_data
import docker
import threading


def collect_metrics_during_test(stop_event, folder_path, targets):
    client = docker.from_env()

    # Open file in append mode immediately
    with open(f"{folder_path}/raw_docker_metrics.jsonl", "a") as f:
        while not stop_event.is_set():
            current_sample = {"timestamp": time.time(), "containers": {}}
            for name in targets:
                try:
                    stats = client.containers.get(name).stats(stream=False)
                    current_sample["containers"][name] = stats
                except Exception:
                    continue

            # Write one line per second and flush to disk
            f.write(json.dumps(current_sample) + "\n")
            f.flush()

            time.sleep(1)


def run_stress_test(test_name, container_name, tool_command, iteration):
    folder_path = f"./test_results/{test_name}/{iteration}/{container_name}"
    os.makedirs(folder_path, exist_ok=True)
    print(f"Starting test: {test_name}")
    start = time.perf_counter()
    # List of all containers you want to monitor simultaneously
    target_containers = [
        "cw_fastapi_baseline",
        "cw_axum_test",
        "cw_custom_test",
        "cw_db_test",
        "cw_redis_test",
    ]
    print("test")

    # Start the background collector thread
    stop_event = threading.Event()
    collector_thread = threading.Thread(
        target=collect_metrics_during_test,
        args=(stop_event, folder_path, target_containers),
    )
    print("test")
    collector_thread.start()
    print("test")
    # Run the actual stress test tool (Locust/k6/etc)
    process = subprocess.run(tool_command, shell=True, capture_output=False)
    print("test")
    # Stop the collector as soon as the test finishes
    stop_event.set()
    collector_thread.join()
    print("test")
    end = time.perf_counter()
    duration_seconds = end - start
    threshold = [
        [60, 100],
        [180, 500],
        [360, 2000],
        [600, 10000],
        [1200, 50000],
        [1800, 200000],
    ]

    if int(duration_seconds) > 2400:
        user_count = "time too long"
        rps = user_count
    elif int(duration_seconds) <= 60:
        user_count = "time too short"
        rps = user_count
    else:
        user_count = next(
            threshold[i - 1][1]
            + (threshold[i][1] - threshold[i - 1][1])
            * (int(duration_seconds) - threshold[i - 1][0])
            / (threshold[i][0] - threshold[i - 1][0])
            for i, t in enumerate(threshold)
            if t[0] >= int(duration_seconds)
        )
        rps = round(float(user_count) * float(1 / (3 / 10)))
    print(f"Execution time: {duration_seconds:.8f} seconds")
    print(f"Estimated user limit reached : {user_count} VU")
    print("User Average Request per seconds 0.1 to 0.5 ~ 0.3 ")
    print(f"Estimated RPS reached : {rps}")

    # Save tool logs
    with open(f"{folder_path}/tool_output.txt", "w") as f:
        f.write(f"STDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}")

    print(f"Data captured and saved to {folder_path}/raw_docker_metrics.json\n")


def hey_full_test(iteration, services):
    test_name = "hey_200000_100"
    command = "hey -n 200000 -c 100 -o csv"
    for service in services:
        target_url = f"http://localhost:{service['port']}/health"
        json_path = (
            f"test_results/{test_name}/{iteration}/{service['name']}/test_details.csv"
        )

        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        full_cmd = f"{command} {target_url} > {json_path}"

        run_stress_test(
            test_name=test_name,
            container_name=service["name"],
            tool_command=full_cmd,
            iteration=iteration,
        )


def hey_full_stress_test(iteration, services):
    test_name = "hey_2m_1k"
    command = "hey -n 2000000 -c 1000 -o csv"
    for service in services:
        target_url = f"http://localhost:{service['port']}/health"
        json_path = (
            f"test_results/{test_name}/{iteration}/{service['name']}/test_details.csv"
        )
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        full_cmd = f"{command} {target_url} > {json_path}"

        run_stress_test(
            test_name=test_name,
            container_name=service["name"],
            tool_command=full_cmd,
            iteration=iteration,
        )


def locust_full_test(iteration, services, dish_count, recipe_count):
    test_name = "locust_v_1_0_0"
    # Configuration for the stress test
    test_file = "locust_v_1.0.0.py"
    users = 100
    spawn_rate = 20
    run_time = "30s"
    for service in services:
        json_path = (
            f"test_results/{test_name}/{iteration}/{service['name']}/test_details.json"
        )
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        locust_cmd = (
            f"DISH_COUNT={dish_count} RECIPE_COUNT={recipe_count} "
            f"locust -f {test_file} --headless "
            f"-u {users} -r {spawn_rate} -t {run_time} "
            f"--host http://localhost:{service['port']} "
            f"--json > {json_path}"  # Redirects the JSON summary to your file
        )
        run_stress_test(
            test_name=test_name,
            container_name=service["name"],
            tool_command=locust_cmd,
            iteration=iteration,
        )


def k6_full_test(iteration, services, dish_count, recipe_count):
    test_name = "k6_break_test"

    for service in services:
        k6_cmd = (
            f"k6 run "
            f"--summary-export=test_results/{test_name}/{iteration}/{service['name']}/test_details.json "
            f"--env HOST=http://localhost:{service['port']} "
            f"--env DISH_COUNT={dish_count} "
            f"--env RECIPE_COUNT={recipe_count} "
            f"k6_stress_test.js"
        )

        print(f"--- Running Break Test on {service['name']} ---")
        run_stress_test(
            test_name=test_name,
            container_name=service["name"],
            tool_command=k6_cmd,
            iteration=iteration,
        )
        time.sleep(60)


if __name__ == "__main__":
    iteration = "2"
    services = [
        {"name": "axum", "port": 6668},
        {"name": "fastapi", "port": 6666},
        # {"name": "custom", "port": 6669},
    ]
    dish_count = 100
    recipe_count = 500
    create_test_data(DISH_COUNT=dish_count, RECIPE_COUNT=recipe_count)
    # hey_full_stress_test(iteration, services)
    # hey_full_test(iteration, services)
    k6_full_test(iteration, services, dish_count, recipe_count)
    locust_full_test(iteration, services, dish_count, recipe_count)
    iteration = "3"
    dish_count = 1000
    recipe_count = 14500
    create_test_data(DISH_COUNT=dish_count, RECIPE_COUNT=recipe_count)
    k6_full_test(iteration, services, dish_count, recipe_count)
    locust_full_test(iteration, services, dish_count, recipe_count)

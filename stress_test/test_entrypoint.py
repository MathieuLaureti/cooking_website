import os
import time
import json
import subprocess
from datetime import datetime, timedelta

from recipe_generator import create_test_data
import docker
import threading


def collect_metrics_during_test(stop_event, folder_path, targets):
    """Threaded worker to capture raw Docker stats every second."""
    client = docker.from_env()
    samples = []

    while not stop_event.is_set():
        current_sample = {"timestamp": time.time(), "containers": {}}
        for name in targets:
            try:
                # Get the full, raw stats dictionary directly from Docker
                stats = client.containers.get(name).stats(stream=False)
                current_sample["containers"][name] = stats
            except Exception:
                continue
        samples.append(current_sample)
        time.sleep(1)  # 1-second resolution

    with open(f"{folder_path}/raw_docker_metrics.json", "w") as f:
        json.dump(samples, f, indent=2)


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
    ]

    # Start the background collector thread
    stop_event = threading.Event()
    collector_thread = threading.Thread(
        target=collect_metrics_during_test,
        args=(stop_event, folder_path, target_containers),
    )

    collector_thread.start()

    # Run the actual stress test tool (Locust/k6/etc)
    process = subprocess.run(tool_command, shell=True, capture_output=True, text=True)

    # Stop the collector as soon as the test finishes
    stop_event.set()
    collector_thread.join()
    end = time.perf_counter()
    print(f"Execution time: {end - start:.8f} seconds")
    # Save tool logs
    with open(f"{folder_path}/tool_output.txt", "w") as f:
        f.write(f"STDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}")

    print(f"Data captured and saved to {folder_path}/raw_docker_metrics.json\n")


def hey_full_test(iteration):
    test_name = "hey_200000_100"
    command = "hey -n 200000 -c 100 -o csv"
    services = [
        {"name": "fastapi", "port": 6666},
        {"name": "axum", "port": 6668},
        {"name": "custom", "port": 6669},
    ]

    for service in services:
        target_url = f"http://localhost:{service['port']}/health"
        # We redirect stdout to a json file in the tool_command string
        json_path = (
            f"test_results/{test_name}/{iteration}/{service['name']}/test_details.csv"
        )

        # Ensure the directory exists before hey runs
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        full_cmd = f"{command} {target_url} > {json_path}"

        run_stress_test(
            test_name=test_name,
            container_name=service["name"],
            tool_command=full_cmd,
            iteration=iteration,
        )


def hey_full_stress_test(iteration):
    test_name = "hey_10m_1k"
    command = "hey -n 10000000 -c 1000 -o csv"
    services = [
        {"name": "axum", "port": 6668},
        {"name": "custom", "port": 6669},
    ]

    for service in services:
        target_url = f"http://localhost:{service['port']}/health"
        # We redirect stdout to a json file in the tool_command string
        json_path = (
            f"test_results/{test_name}/{iteration}/{service['name']}/test_details.csv"
        )

        # Ensure the directory exists before hey runs
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        full_cmd = f"{command} {target_url} > {json_path}"

        run_stress_test(
            test_name=test_name,
            container_name=service["name"],
            tool_command=full_cmd,
            iteration=iteration,
        )


def locust_full_test(iteration):
    test_name = "locust_v_1_0_0"
    # Configuration for the stress test
    test_file = "locust_v_1.0.0.py"
    dish_count = 100
    recipe_count = 500
    create_test_data(DISH_COUNT=dish_count, RECIPE_COUNT=recipe_count)
    users = 100
    spawn_rate = 20
    run_time = "30s"

    services = [
        {"name": "fastapi", "port": 6666},
        {"name": "axum", "port": 6668},
        {"name": "custom", "port": 6669},
    ]
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


def k6_full_test(iteration):
    test_name = "k6_break_test"
    dish_count = 100
    recipe_count = 500

    services = [
        {"name": "cw_fastapi_baseline", "port": 6666},
        {"name": "cw_custom_test", "port": 6669},
        {"name": "cw_axum_test", "port": 6668},
    ]

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


if __name__ == "__main__":
    iteration = "1"
    hey_full_stress_test(iteration)
    locust_full_test(iteration)
    hey_full_test(iteration)
    k6_full_test(iteration)

"""
Test the telemetry worker with a mocked drone.
"""

# pylint: disable=broad-exception-caught

import multiprocessing as mp
import subprocess
import threading

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller

MOCK_DRONE_MODULE = "tests.integration.mock_drones.telemetry_drone"
CONNECTION_STRING = "tcp:localhost:12345"

# Please do not modify these
TELEMETRY_PERIOD = 1
NUM_TRIALS = 5
NUM_FAILS = 3


# =========================================================
# Utility functions
# =========================================================
def start_drone() -> None:
    subprocess.run(["python", "-m", MOCK_DRONE_MODULE], shell=True, check=False)


def stop(args: worker_controller.WorkerController) -> None:
    args.request_exit()


def read_queue(
    telemetry_queue: queue_proxy_wrapper.QueueProxyWrapper,
    main_logger: logger.Logger,
) -> None:
    while True:
        try:
            data = telemetry_queue.queue.get(timeout=1)
            main_logger.info(f"Telemetry: {data}")
        except Exception:
            break


# =========================================================
# Main
# =========================================================
def main() -> int:
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    assert config is not None

    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    assert main_logger is not None

    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    connection.mav.heartbeat_send(
        mavutil.mavlink.MAV_TYPE_GCS,
        mavutil.mavlink.MAV_AUTOPILOT_INVALID,
        0,
        0,
        0,
    )

    main_logger.info("Connected!")

    # =====================================================
    # Worker setup
    # =====================================================

    args = worker_controller.WorkerController()

    manager = mp.Manager()

    telemetry_queue = queue_proxy_wrapper.QueueProxyWrapper(
        manager,
        maxsize=10,
    )

    threading.Timer(
        TELEMETRY_PERIOD * NUM_TRIALS * 2 + NUM_FAILS,
        stop,
        (args,),
    ).start()

    threading.Thread(
        target=read_queue,
        args=(telemetry_queue, main_logger),
        daemon=True,
    ).start()

    telemetry_worker.telemetry_worker(
        connection,
        args,
        telemetry_queue,
    )

    return 0


if __name__ == "__main__":
    drone_process = mp.Process(target=start_drone)
    drone_process.start()

    result_main = main()

    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")

    drone_process.join()

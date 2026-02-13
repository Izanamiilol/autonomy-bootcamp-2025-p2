"""
Test the heartbeat sender worker with a mocked drone.
"""

# pylint: disable=broad-exception-caught

import multiprocessing as mp
import subprocess
import threading

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.heartbeat import heartbeat_sender_worker
from utilities.workers import worker_controller

MOCK_DRONE_MODULE = "tests.integration.mock_drones.heartbeat_sender_drone"
CONNECTION_STRING = "tcp:localhost:12345"

# Please do not modify these, these are for the test cases
HEARTBEAT_PERIOD = 1
NUM_TRIALS = 10


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
WORKER_NAME = "heartbeat_sender"
# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


# pylint: disable=duplicate-code
def start_drone() -> None:
    """
    Start the mocked drone.
    """
    subprocess.run(["python", "-m", MOCK_DRONE_MODULE], shell=True, check=False)


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def stop(args:worker_controller.WorkerController) -> None:
    """
    Stop the worker.
    """
    args.request_exit()


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """
    Start the heartbeat sender worker simulation.
    """

    # Create worker controller ONCE
    args = worker_controller.WorkerController()

    # Configuration settings
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    assert config is not None

    # Setup main logger
    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    assert main_logger is not None

    # Connect to mocked drone
    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    main_logger.info("Connected!")

    # Stop worker after required time
    threading.Timer(HEARTBEAT_PERIOD * NUM_TRIALS, stop, (args,)).start()

    # Run worker
    heartbeat_sender_worker.heartbeat_sender_worker(
        connection,
        args,
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

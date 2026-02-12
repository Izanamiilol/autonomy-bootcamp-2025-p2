"""
Bootcamp F2025

Main process to setup and manage all the other working processes
"""

import multiprocessing as mp
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.command import command
from modules.command import command_worker
from modules.heartbeat import heartbeat_receiver_worker
from modules.heartbeat import heartbeat_sender_worker
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from utilities.workers import worker_manager

CONNECTION_STRING = "tcp:localhost:12345"

# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================

QUEUE_SIZE = 10

NUM_HEARTBEAT_SENDERS = 1
NUM_HEARTBEAT_RECEIVERS = 1
NUM_TELEMETRY_WORKERS = 1
NUM_COMMAND_WORKERS = 1

TARGET_POSITION = command.Position(10, 20, 30)

# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """Main entry point."""

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
    connection.wait_heartbeat(timeout=30)

    controller = worker_controller.WorkerController()
    manager = mp.Manager()

    status_queue = queue_proxy_wrapper.QueueProxyWrapper(manager, QUEUE_SIZE)
    telemetry_queue = queue_proxy_wrapper.QueueProxyWrapper(manager, QUEUE_SIZE)
    command_queue = queue_proxy_wrapper.QueueProxyWrapper(manager, QUEUE_SIZE)

    workers = []

    # HEARTBEAT SENDER
    workers.append(
        worker_manager.WorkerManager(
            heartbeat_sender_worker.heartbeat_sender_worker,
            NUM_HEARTBEAT_SENDERS,
            (connection, controller),
            main_logger,
        )
    )

    # HEARTBEAT RECEIVER
    workers.append(
        worker_manager.WorkerManager(
            heartbeat_receiver_worker.heartbeat_receiver_worker,
            NUM_HEARTBEAT_RECEIVERS,
            (connection, controller, status_queue),
            main_logger,
        )
    )

    # TELEMETRY
    workers.append(
        worker_manager.WorkerManager(
            telemetry_worker.telemetry_worker,
            NUM_TELEMETRY_WORKERS,
            (connection, controller, telemetry_queue),
            main_logger,
        )
    )

    # COMMAND
    workers.append(
        worker_manager.WorkerManager(
            command_worker.command_worker,
            NUM_COMMAND_WORKERS,
            (
                connection,
                TARGET_POSITION,
                controller,
                telemetry_queue,
                command_queue,
            ),
            main_logger,
        )
    )

    for w in workers:
        w.start()

    main_logger.info("Started")

    start_time = time.time()
    run_time = 100

    try:
        while time.time() - start_time < run_time:

            while not status_queue.queue.empty():
                status = status_queue.queue.get()
                main_logger.info(f"Heartbeat status: {status}")

                if status == "Disconnected":
                    main_logger.error("Drone disconnected — stopping system")
                    raise KeyboardInterrupt

            while not command_queue.queue.empty():
                cmd = command_queue.queue.get()
                main_logger.info(cmd)

            time.sleep(0.1)

    except KeyboardInterrupt:
        main_logger.info("Shutdown requested")

    controller.request_exit()
    main_logger.info("Requested exit")

    command_queue.fill_and_drain_queue()
    telemetry_queue.fill_and_drain_queue()
    status_queue.fill_and_drain_queue()

    main_logger.info("Queues cleared")

    for w in workers:
        w.join()

    main_logger.info("Stopped")

    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")

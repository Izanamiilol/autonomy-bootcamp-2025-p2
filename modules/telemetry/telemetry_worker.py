"""
Telemetry worker that gathers GPS data.
"""

# pylint: disable=broad-exception-caught

import os
import pathlib

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers.worker_controller import WorkerController
from . import telemetry
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def telemetry_worker(
    connection: mavutil.mavfile,
    args: WorkerController,
    telemetry_queue: queue_proxy_wrapper.QueueProxyWrapper,
) -> None:
    """
    Worker process.
    Continuously gathers telemetry and pushes it to the queue.
    """

    # Instantiate logger
    worker_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{worker_name}_{process_id}", True)

    if not result or local_logger is None:
        print("ERROR: Worker failed to create logger")
        return

    local_logger.info("Logger initialized", True)

    # Instantiate Telemetry logic class
    result, telemetry_logic = telemetry.Telemetry.create(
        connection,
        args,
        local_logger,
    )

    if not result or telemetry_logic is None:
        local_logger.error("Failed to create Telemetry", True)
        return

    # Main loop
    while not args.is_exit_requested():
        try:
            args.check_pause()

            telemetry_data = telemetry_logic.run(args)

            if telemetry_data is not None:
                telemetry_queue.queue.put(telemetry_data)

        except Exception as exc:
            local_logger.error(f"Telemetry worker error: {exc}", True)

    local_logger.info("Telemetry worker exiting", True)


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

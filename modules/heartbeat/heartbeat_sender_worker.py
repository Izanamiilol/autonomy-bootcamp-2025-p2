"""
Heartbeat worker that sends heartbeats periodically.
"""

# pylint: disable=broad-exception-caught

import os
import pathlib
import time

from pymavlink import mavutil

from utilities.workers.worker_controller import WorkerController
from . import heartbeat_sender
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def heartbeat_sender_worker(
    connection: mavutil.mavfile,
    args: WorkerController,
) -> None:
    """
    Worker process.

    args: WorkerController instance controlling pause/exit
    """
    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    # Instantiate logger
    worker_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{worker_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create logger")
        return

    assert local_logger is not None
    local_logger.info("Logger initialized", True)

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================

    # Instantiate HeartbeatSender
    result, sender = heartbeat_sender.HeartbeatSender.create(connection, args)
    if not result or sender is None:
        local_logger.error("Failed to create HeartbeatSender", True)
        return

    # Main loop
    while not args.is_exit_requested():
        try:
            args.check_pause()

            sender.run(args)

            # Send heartbeat once per second
            time.sleep(1)

        except Exception as exc:
            local_logger.error(f"Heartbeat send failed: {exc}", True)

    local_logger.info("Heartbeat sender exiting", True)

    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

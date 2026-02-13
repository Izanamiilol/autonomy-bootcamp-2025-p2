"""
Heartbeat worker that receives heartbeats periodically.
"""

# pylint: disable=broad-exception-caught

import os
import pathlib

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers.worker_controller import WorkerController
from . import heartbeat_receiver
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def heartbeat_receiver_worker(
    connection: mavutil.mavfile,
    args: WorkerController,
    status_queue: queue_proxy_wrapper.QueueProxyWrapper,
) -> None:
    """
    Worker process.

    args: WorkerController instance controlling pause/exit
    status_queue: Queue for sending connection status back to main
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

    # Instantiate HeartbeatReceiver
    result, receiver = heartbeat_receiver.HeartbeatReceiver.create(
        connection,
        args,
        local_logger,
    )

    if not result or receiver is None:
        local_logger.error("Failed to create HeartbeatReceiver", True)
        return

    # Main loop
    while not args.is_exit_requested():
        try:
            args.check_pause()

            status = receiver.run(args)

            # Send status to main process
            status_queue.queue.put(status)

        except Exception as exc:
            local_logger.error(f"Heartbeat receiver error: {exc}", True)

    local_logger.info("Heartbeat receiver exiting", True)

    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

"""
Command worker to make decisions based on Telemetry Data.
"""

# pylint: disable=broad-exception-caught

import os
import pathlib

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from . import command
from ..common.modules.logger import logger


def command_worker(
    connection: mavutil.mavfile,
    target: command.Position,
    args,
    telemetry_queue: queue_proxy_wrapper.QueueProxyWrapper,
    command_queue: queue_proxy_wrapper.QueueProxyWrapper,
) -> None:
    """
    Worker process.
    """

    # Instantiate logger
    worker_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{worker_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create logger")
        return

    assert local_logger is not None
    local_logger.info("Logger initialized", True)

    # Instantiate Command logic
    result, command_logic = command.Command.create(
        connection,
        target,
        args,
        local_logger,
    )

    if not result or command_logic is None:
        local_logger.error("Failed to create Command", True)
        return

    # Main loop
    while not args.is_exit_requested():
        try:
            args.check_pause()

            try:
                telemetry_data = telemetry_queue.queue.get(timeout=0.1)
            except Exception:
                continue

            result_str = command_logic.run(telemetry_data)

            if result_str is not None:
                command_queue.queue.put(result_str)

        except Exception as exc:
            local_logger.error(f"Command worker error: {exc}", True)

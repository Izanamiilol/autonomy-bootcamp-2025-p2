"""
Mock drone for testing Heartbeat Sender.
"""

import os
import pathlib
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger

CONNECTION_STRING = "tcpin:localhost:12345"
HEARTBEAT_PERIOD = 1
NUM_TRIALS = 10
ERROR_TOLERANCE = 1e-2


def main() -> int:
    """
    Begin mock drone simulation to test a heartbeat sender worker.
    """
    # Mocked autopilot/drone
    # source_system = 1 (airside on drone)
    # source_component = 0 (autopilot)
    connection = mavutil.mavlink_connection(CONNECTION_STRING, source_system=1, source_component=0)

    # Instantiate logger after main starts
    drone_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{drone_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create drone logger")
        return -1

    # Get Pylance to stop complaining
    assert local_logger is not None

    local_logger.info("Logger initialized")

    # Since this one is timing sensitive and opening files take a while,
    # create logger before beginning. This causes a race condition, but it seems to work out.
    # The creation of this process is typically slower than main creating the log folder
    # If there are issues, don't worry, bootcamp reviewers will understand
    connection.wait_heartbeat()

    # Task is to recive heartbeats at a rate of 1Hz
    # Recieve NUM_TRIALS heartbeats to consider a scucess
    for _ in range(NUM_TRIALS):
        start = time.time()
        msg = connection.recv_match(
            type="HEARTBEAT", blocking=True, timeout=HEARTBEAT_PERIOD + ERROR_TOLERANCE
        )
        if not msg or msg.get_type() != "HEARTBEAT":
            local_logger.error(
                f"Drone: Sent incorrect message type or didn't recieve a message in time: {msg}"
            )
            return -2
        if abs((time.time() - start) - HEARTBEAT_PERIOD) > ERROR_TOLERANCE:
            local_logger.error(
                f"Drone: Most likely sent heartbeats too fast: measured period was {time.time() - start}s"
            )
            return -3
        if (
            msg.type != mavutil.mavlink.MAV_TYPE_GCS
            or msg.autopilot != mavutil.mavlink.MAV_AUTOPILOT_INVALID
        ):
            local_logger.error("Drone: Sent incorrect contents within heartbeat message.")
            return -4
        local_logger.info("Drone: Recieved heartbeat!")

    msg = connection.recv_match(
        type="HEARTBEAT", blocking=True, timeout=HEARTBEAT_PERIOD + ERROR_TOLERANCE
    )
    if msg and msg.get_type() == "HEARTBEAT":
        local_logger.error("Recieved extra heartbeat")
        return -5

    local_logger.info("Passed!")
    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Drone: Failed with return code {result_main}")
    else:
        print("Drone: Success!")

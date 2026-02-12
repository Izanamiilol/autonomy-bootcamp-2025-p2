"""
Mock drone for testing Heartbeat Receiver.
"""

import os
import pathlib
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger

CONNECTION_STRING = "tcpin:localhost:12345"
HEARTBEAT_PERIOD = 1
DISCONNECT_THRESHOLD = 5
NUM_TRIALS = 5
NUM_DISCONNECTS = 3


def main() -> int:
    """
    Begin mock drone simulation to test a heartbeat receiver worker.
    """
    # Mocked autopilot/drone
    # source_system = 1 (airside on drone)
    # source_component = 0 (autopilot)
    connection = mavutil.mavlink_connection(CONNECTION_STRING, source_system=1, source_component=0)
    connection.wait_heartbeat()

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

    # Task is to send trials heartbeats at a rate of 1Hz
    def send_heartbeats(trials: int) -> int:
        for _ in range(trials):
            try:
                connection.mav.heartbeat_send(
                    mavutil.mavlink.MAV_TYPE_GENERIC,
                    mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
                    0,
                    0,
                    0,
                )
            # Not strictly necessary, sends shouldn't raise exceptions
            except:  # pylint: disable=bare-except
                local_logger.critical("Drone: Could not send a heartbeat")
                return -3
            local_logger.info("Drone: Sent a heartbeat")
            time.sleep(HEARTBEAT_PERIOD)
        return 0

    if send_heartbeats(NUM_TRIALS) != 0:
        return -1

    # Do not send heartbeats for a period of time to mimick the drone disconnected
    time.sleep(HEARTBEAT_PERIOD * (DISCONNECT_THRESHOLD + NUM_DISCONNECTS))

    # Reconnect
    if send_heartbeats(NUM_TRIALS) != 0:
        return -1

    # Drop 1 heartbeat, should still be connected
    time.sleep(HEARTBEAT_PERIOD)

    if send_heartbeats(1) != 0:
        return -1

    local_logger.info("Passesd!")
    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Drone: Failed with return code {result_main}")
    else:
        print("Drone: Success!")

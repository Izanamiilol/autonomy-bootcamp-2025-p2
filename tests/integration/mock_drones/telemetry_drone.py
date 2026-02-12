"""
Mock drone for testing Telemetry.
"""

import os
import math
import pathlib
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger

CONNECTION_STRING = "tcpin:localhost:12345"
ATTITUDE_PERIOD = 1 / 3
POSITION_PERIOD = 1 / 2
TOTAL_PERIOD = 1
NUM_TRIALS = 5
YAW_SPEED = math.pi
X_SPEED = 1


def main() -> int:
    """
    Begin mock drone simulation to test a telemetry worker.
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

    # Task is to send ATTITUDE and LOCAL_POSITION_NED messages
    def send_telemetry(attitude_period: float, position_period: float) -> int:
        attitude_count = -1
        position_count = -1
        for i in range(NUM_TRIALS):
            # A TOTAL_PERIOD second long loop:
            start = time.time()
            now = start
            while now - start < TOTAL_PERIOD:
                if (
                    now - start
                ) // attitude_period + i * TOTAL_PERIOD // attitude_period > attitude_count:
                    attitude_count += 1
                    try:
                        yaw = YAW_SPEED * (attitude_count * attitude_period) % (2 * math.pi)
                        connection.mav.attitude_send(
                            int((now - start) * 1000) + TOTAL_PERIOD * i * 1000,
                            0,
                            0,
                            yaw if yaw <= math.pi else yaw - 2 * math.pi,  # Scale it to [-pi, pi]
                            0,
                            0,
                            YAW_SPEED,
                        )
                    # Not required, sends shouldn't raise exceptions
                    except:  # pylint: disable=bare-except
                        local_logger.error("Drone: Could not send attitude")
                        return -1
                    local_logger.info(f"Drone: Sent attitude {attitude_count}")

                if (
                    now - start
                ) // position_period + i * TOTAL_PERIOD // position_period > position_count:
                    position_count += 1
                    try:
                        connection.mav.local_position_ned_send(
                            int((now - start) * 1000) + TOTAL_PERIOD * i * 1000,
                            X_SPEED * (position_count * position_period),
                            0,
                            0,
                            X_SPEED,
                            0,
                            0,
                        )
                    # Not required, sends shouldn't raise exceptions
                    except:  # pylint: disable=bare-except
                        local_logger.error("Drone: Could not send position")
                        return -1
                    local_logger.info(f"Drone: Sent position {position_count}")

                now = time.time()
        return 0

    if send_telemetry(ATTITUDE_PERIOD, POSITION_PERIOD) != 0:
        return -2

    # Send nothing
    time.sleep(TOTAL_PERIOD)

    # Send only attitude
    connection.mav.attitude_send(
        999,
        1,
        2,
        3,
        555,
        555,
        555,
    )
    time.sleep(TOTAL_PERIOD)

    # Send only position
    connection.mav.local_position_ned_send(
        111,
        3,
        2,
        1,
        777,
        777,
        777,
    )
    time.sleep(TOTAL_PERIOD)

    # Swap speeds to make the other message send faster
    if send_telemetry(POSITION_PERIOD, ATTITUDE_PERIOD) != 0:
        return -2

    local_logger.info("Passed!")
    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Drone: Failed with return code {result_main}")
    else:
        print("Drone: Success!")

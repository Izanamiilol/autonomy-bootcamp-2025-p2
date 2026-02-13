"""
Decision-making logic.
"""

# pylint: disable=broad-exception-caught

import math
from typing import Tuple

from pymavlink import mavutil

from ..common.modules.logger import logger
from ..telemetry.telemetry import TelemetryData


class Position:
    """
    3D vector struct.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x: float = x
        self.y: float = y
        self.z: float = z


class Command:
    """
    Command class to make a decision based on received telemetry,
    and send out commands based upon the data.
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        target: Position,
        _args: object,
        local_logger: logger.Logger,
    ) -> Tuple[bool, "Command | None"]:
        """
        Factory method to create a Command instance.
        """
        try:
            obj = cls(cls.__private_key, connection, target, local_logger)
            return True, obj
        except Exception as exc:
            local_logger.error(f"Failed to create Command: {exc}", True)
            return False, None

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Command.__private_key, "Use create() method"

        self.connection: mavutil.mavfile = connection
        self.target: Position = target
        self.logger: logger.Logger = local_logger

    # =========================================================
    # MAIN DECISION LOOP
    # =========================================================
    def run(self, telemetry_data: TelemetryData) -> str | None:
        """
        Process telemetry and send commands to reach the target.
        """

        # =========================================================
        # ALTITUDE CONTROL
        # =========================================================
        dz: float = self.target.z - telemetry_data.z

        if abs(dz) > 0.5:
            climb_rate: float = 1.0  # required by test harness

            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                0,
                climb_rate,  # param1: climb rate
                0,
                0,
                0,
                0,
                0,
                float(self.target.z),  # param7: absolute altitude
            )

            return f"CHANGE_ALTITUDE: {1 if dz > 0 else -1}"

        # =========================================================
        # YAW CONTROL (RELATIVE ANGLE REQUIRED)
        # =========================================================
        dx: float = self.target.x - telemetry_data.x
        dy: float = self.target.y - telemetry_data.y

        desired_yaw: float = math.atan2(dy, dx)
        yaw_error: float = desired_yaw - telemetry_data.yaw

        yaw_error = (yaw_error + math.pi) % (2 * math.pi) - math.pi
        yaw_error_deg: float = math.degrees(yaw_error)

        if abs(yaw_error_deg) > 5:
            direction: int = 1 if yaw_error_deg > 0 else -1

            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,
                abs(yaw_error_deg),  # param1: angle
                5,  # param2: turning speed
                direction,  # param3: direction
                1,  # param4: RELATIVE
                0,
                0,
                0,
            )

            return f"CHANGE YAW: {yaw_error_deg}"

        return None

"""
Decision-making logic.
"""

# pylint: disable=broad-exception-caught

import math

from pymavlink import mavutil

from ..common.modules.logger import logger
from ..telemetry.telemetry import TelemetryData


class Position:
    """
    3D vector struct.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        """Initialize a position with x, y, z coordinates."""
        self.x = x
        self.y = y
        self.z = z


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
        _args,
        local_logger: logger.Logger,
    ):
        """
        Factory method to create a Command object safely.
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
        """
        Initialize the Command logic with connection, target, and logger.
        """
        assert key is Command.__private_key, "Use create() method"

        self.connection = connection
        self.target = target
        self.logger = local_logger

    # =========================================================
    # MAIN DECISION LOOP
    # =========================================================
    def run(self, telemetry_data: TelemetryData):
        """
        Process telemetry data and issue altitude or yaw commands.
        """

        # =========================================================
        # ALTITUDE CONTROL
        # =========================================================
        dz = self.target.z - telemetry_data.z

        if abs(dz) > 0.5:

            climb_rate = 1.0

            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                0,
                climb_rate,
                0,
                0,
                0,
                0,
                0,
                float(self.target.z),
            )

            return f"CHANGE_ALTITUDE: {1 if dz > 0 else -1}"

        # =========================================================
        # YAW CONTROL (RELATIVE ANGLE REQUIRED)
        # =========================================================
        dx = self.target.x - telemetry_data.x
        dy = self.target.y - telemetry_data.y

        desired_yaw = math.atan2(dy, dx)
        yaw_error = desired_yaw - telemetry_data.yaw

        yaw_error = (yaw_error + math.pi) % (2 * math.pi) - math.pi
        yaw_error_deg = math.degrees(yaw_error)

        if abs(yaw_error_deg) > 5:

            direction = 1 if yaw_error_deg > 0 else -1

            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,
                abs(yaw_error_deg),
                5,
                direction,
                1,
                0,
                0,
                0,
            )

            return f"CHANGE YAW: {yaw_error_deg}"

        return None

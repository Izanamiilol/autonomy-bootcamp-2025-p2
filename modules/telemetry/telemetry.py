"""
Telemetry gathering logic.
"""

# pylint: disable=broad-exception-caught
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
# pylint: disable=too-many-positional-arguments

from pymavlink import mavutil

from ..common.modules.logger import logger


class TelemetryData:
    """Struct for telemetry data."""

    def __init__(
        self,
        time_since_boot:int|None=None,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
        x_velocity: float | None = None,
        y_velocity: float | None = None,
        z_velocity: float | None = None,
        roll: float | None = None,
        pitch: float | None = None,
        yaw: float | None = None,
        roll_speed: float | None = None,
        pitch_speed: float | None = None,
        yaw_speed: float | None = None,
    ) -> None:
        self.time_since_boot = time_since_boot
        self.x = x
        self.y = y
        self.z = z
        self.x_velocity = x_velocity
        self.y_velocity = y_velocity
        self.z_velocity = z_velocity
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.roll_speed = roll_speed
        self.pitch_speed = pitch_speed
        self.yaw_speed = yaw_speed


class Telemetry:
    """Reads MAVLink position and attitude messages."""

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        args:object,
        local_logger: logger.Logger,
    ) -> tuple[bool,"Telemetry"]:
        """Create Telemetry safely."""
        try:
            return True, cls(cls.__private_key, connection, local_logger)
        except Exception as exc:
            local_logger.error(f"Failed to create Telemetry: {exc}", True)
            return False, None

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Telemetry.__private_key

        self.connection = connection
        self.logger = local_logger

        self.last_position = None
        self.last_attitude = None

    def run(self, args:object) -> TelemetryData|None:
        """
        Combine LOCAL_POSITION_NED and ATTITUDE into TelemetryData.
        """
        _ = args

        try:
            msg = self.connection.recv_match(
                type=["LOCAL_POSITION_NED", "ATTITUDE"],
                blocking=True,
                timeout=1,
            )

            if msg is None:
                return None

            if msg.get_type() == "LOCAL_POSITION_NED":
                self.last_position = msg
            elif msg.get_type() == "ATTITUDE":
                self.last_attitude = msg

            if self.last_position and self.last_attitude:
                return TelemetryData(
                    time_since_boot=max(
                        self.last_position.time_boot_ms,
                        self.last_attitude.time_boot_ms,
                    ),
                    x=self.last_position.x,
                    y=self.last_position.y,
                    z=self.last_position.z,
                    x_velocity=self.last_position.vx,
                    y_velocity=self.last_position.vy,
                    z_velocity=self.last_position.vz,
                    roll=self.last_attitude.roll,
                    pitch=self.last_attitude.pitch,
                    yaw=self.last_attitude.yaw,
                    roll_speed=self.last_attitude.rollspeed,
                    pitch_speed=self.last_attitude.pitchspeed,
                    yaw_speed=self.last_attitude.yawspeed,
                )

        except Exception as exc:
            self.logger.error(f"Telemetry error: {exc}", True)

        return None

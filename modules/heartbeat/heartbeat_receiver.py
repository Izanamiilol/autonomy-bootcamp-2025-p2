"""
Heartbeat receiving logic.
"""

# pylint: disable=broad-exception-caught

from pymavlink import mavutil
from utilities.workers import worker_controller

from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatReceiver:
    """
    HeartbeatReceiver class to receive heartbeats.
    """

    __private_key = object()
    __MAX_MISSED = 5

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        _args: worker_controller.WorkerController,
        local_logger: logger.Logger,
    )-> tuple[bool, "HeartbeatReceiver | None"]:
        """
        Falliable create (instantiation) method to create a HeartbeatReceiver object.
        """
        try:
            receiver = cls(cls.__private_key, connection, local_logger)
            return True, receiver
        except Exception as exc:
            local_logger.error(f"Failed to create HeartbeatReceiver: {exc}", True)
            return False, None

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is HeartbeatReceiver.__private_key, "Use create() method"

        self.connection = connection
        self.logger = local_logger
        self.missed_heartbeats = 0
        self.connected = False

    def run(self, _args: worker_controller.WorkerController)->str:
        """
        Attempt to receive a heartbeat message.
        If disconnected for over a threshold number of periods,
        the connection is considered disconnected.
        """

        msg = self.connection.recv_match(
            type="HEARTBEAT",
            blocking=True,
            timeout=1,
        )

        if msg is not None:
            self.missed_heartbeats = 0

            if not self.connected:
                self.connected = True
                self.logger.info("Connected", True)

            return "Connected"

        # Missed heartbeat
        self.missed_heartbeats += 1

        if self.missed_heartbeats >= self.__MAX_MISSED:
            if self.connected:
                self.connected = False
                self.logger.error("Disconnected", True)
            return "Disconnected"

        return "Connected"


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

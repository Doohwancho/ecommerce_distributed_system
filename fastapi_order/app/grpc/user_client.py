import grpc
import user_pb2
import user_pb2_grpc
from fastapi import HTTPException
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# gRPC channel options
CHANNEL_OPTIONS = [
    ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
    ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
    ('grpc.keepalive_time_ms', 10000),  # 10 seconds
    ('grpc.keepalive_timeout_ms', 5000),  # 5 seconds
    ('grpc.keepalive_permit_without_calls', True),
    ('grpc.http2.min_ping_interval_without_data_ms', 5000),  # 5 seconds
    ('grpc.dns_min_time_between_resolutions_ms', 10000),  # 10 seconds
]

class UserClient:
    def __init__(self):
        self.host = os.getenv("USER_SERVICE_HOST", "user-service")
        self.port = os.getenv("USER_SERVICE_GRPC_PORT", "50051")
        self.target = f"{self.host}:{self.port}"
        logger.info(f"Initialized UserClient with target: {self.target}")
        self.channel = None
        self.stub = None

    async def get_user(self, user_id: str):
        try:
            if not self.channel or self.channel._channel.is_closed():
                logger.info(f"Creating gRPC channel to {self.target}")
                self.channel = grpc.aio.insecure_channel(
                    self.target,
                    options=CHANNEL_OPTIONS
                )
                self.stub = user_pb2_grpc.UserServiceStub(self.channel)

            logger.info(f"Attempting to get user with ID: {user_id}")
            request = user_pb2.UserRequest(user_id=user_id)
            response = await self.stub.GetUser(request)
            logger.info(f"Successfully got user: {response}")
            return response
        except grpc.RpcError as e:
            logger.error(f"gRPC error while getting user: {e}")
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(status_code=404, detail="User not found")
            elif e.code() == grpc.StatusCode.UNAVAILABLE:
                logger.error(f"User service is unavailable. Target: {self.target}")
                raise HTTPException(status_code=503, detail="User service unavailable")
            else:
                logger.error(f"Unexpected gRPC error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        except Exception as e:
            logger.error(f"Unexpected error while getting user: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def close(self):
        if self.channel:
            logger.info("Closing gRPC channel")
            await self.channel.close()
            self.channel = None
            self.stub = None 
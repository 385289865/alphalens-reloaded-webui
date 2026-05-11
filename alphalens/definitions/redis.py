"""Redis service definition (Celery broker)."""

from alphalens import ServiceDef

service = ServiceDef(
    name="redis",
    display_name="Redis",
    description="Redis server for Celery task broker and result backend",
    command_dev=["redis-server", "--port", "6379"],
    command_prod=["docker", "run", "--rm", "-p", "6379:6379", "redis:7-alpine"],
    health_check="tcp:localhost:6379",
    order=10,
    port=6379,
    persistent=True,
)

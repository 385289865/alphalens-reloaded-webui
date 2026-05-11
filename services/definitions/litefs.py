"""LiteFS service definition for metadata.db replication.

This service is optional — only needed in production deployments
requiring read/write separation on metadata.db.
"""

from services import ServiceDef

service = ServiceDef(
    name="litefs",
    display_name="LiteFS",
    description="SQLite replication for metadata.db read/write separation",
    command_dev=["litefs", "mount", "-config", "litefs.yml"],
    command_prod=["litefs", "mount", "-config", "litefs.yml"],
    health_check="file:./db/metadata-replica.db",
    depends_on=[],
    order=5,
    persistent=True,
)

"""Vue 3 frontend service definition."""

from alphalens import ServiceDef, ROOT

FRONTEND_DIR = ROOT / "frontend"

service = ServiceDef(
    name="frontend",
    display_name="Vue 3 Frontend",
    description="Vite dev server for the Vue 3 frontend on port 5173",
    command_dev=["npm", "run", "dev", "--prefix", str(FRONTEND_DIR)],
    command_prod=["npm", "run", "build", "--prefix", str(FRONTEND_DIR)],
    health_check="http:http://localhost:5173",
    depends_on=["backend"],
    order=40,
    port=5173,
)

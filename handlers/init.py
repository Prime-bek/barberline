from .start import router as start_router
from .booking import router as booking_router
from .master import router as master_router
from .admin import router as admin_router
from .settings import router as settings_router
from .masters_management import router as masters_router

__all__ = [
    'start_router',
    'booking_router',
    'master_router',
    'admin_router',
    'settings_router',
    'masters_router'
]
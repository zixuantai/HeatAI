try:
    from app.services.auth_service import auth_service
except ModuleNotFoundError:
    from backend.app.services.auth_service import auth_service

__all__ = ["auth_service"]

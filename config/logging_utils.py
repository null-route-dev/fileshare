import logging
from functools import wraps


audit_logger = logging.getLogger("fileshare.audit")


def audit_log(action):
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            user = request.user.email if request.user.is_authenticated else "anonymous"
            file_id = kwargs.get("pk") or kwargs.get("file_id") or "unknown"

            try:
                result = func(self, request, *args, **kwargs)
                audit_logger.info(
                    f"{user} - {action} - file:{file_id} - SUCCESS",
                    extra={
                        "user": user,
                        "action": action,
                        "file_id": file_id,
                        "status": "SUCCESS",
                    },
                )
                return result
            except Exception as e:
                audit_logger.error(
                    f"{user} - {action} - file:{file_id} - FAILED: {str(e)}",
                    extra={
                        "user": user,
                        "action": action,
                        "file_id": file_id,
                        "status": "FAILED",
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator

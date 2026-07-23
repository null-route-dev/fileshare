import logging
import time
import json


logger = logging.getLogger("fileshare.access")


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        duration = (time.time() - start_time) * 1000

        log_data = {
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": f"{duration:.2f}",
        }

        if hasattr(request, "user") and request.user.is_authenticated:
            log_data["user"] = request.user.email

        logger.info(json.dumps(log_data))

        return response

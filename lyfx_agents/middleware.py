


## Only use this for debugging ##
import logging
logger = logging.getLogger(__name__)

class RequestLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log the request
        logger.info(f"REQUEST: {request.method} {request.path} {request.content_type}")
        
        # Print to console for immediate visibility
        print(f"🔍 REQUEST: {request.method} {request.path}")
        
        response = self.get_response(request)
        
        # Log the response
        print(f"🔍 RESPONSE: {response.status_code}")
        
        return response
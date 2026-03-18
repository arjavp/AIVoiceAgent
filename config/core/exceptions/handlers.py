import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data['status_code'] = response.status_code
        logger.warning(f"Handled Exception: {exc}")
    else:
        logger.error(f"Unhandled Exception: {exc}", exc_info=True)
        return Response({
            'detail': str(exc) or "Internal Server Error",
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response

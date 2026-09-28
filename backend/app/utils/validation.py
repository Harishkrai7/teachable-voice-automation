from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.models.schemas import ErrorResponse, ErrorDetail

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code="INVALID_REQUEST",
                message=f"Validation failed: {exc.errors()}"
            )
        ).model_dump()
    )

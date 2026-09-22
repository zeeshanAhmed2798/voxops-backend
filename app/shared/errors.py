"""Map application and database exceptions to safe, consistent JSON."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.response import BaseResponse


logger = logging.getLogger(__name__)


def _error(status_code: int, message: str, data=None) -> JSONResponse:
    body = BaseResponse[object](success=False, message=message, data=data)
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


def _integrity_message(exc: IntegrityError) -> tuple[int, str]:
    """Classify common PostgreSQL SQLSTATEs and SQLite test errors."""
    original = exc.orig
    code = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    text = str(original).lower()
    if code == "23505" or "unique constraint failed" in text:
        return 409, "A record with these values already exists."
    if code == "23503" or "foreign key constraint failed" in text:
        return 409, "This record is referenced by another record or contains an invalid reference."
    if code in ("23502", "23514") or "not null constraint failed" in text or "check constraint failed" in text:
        return 422, "The record violates a database constraint."
    return 409, "The record conflicts with existing data."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
        response = _error(exc.status_code, message)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        issues = [{"field": ".".join(str(part) for part in issue["loc"]), "message": issue["msg"]}
                  for issue in exc.errors()]
        return _error(422, "Request validation failed.", issues)

    @app.exception_handler(IntegrityError)
    async def integrity_error(_request: Request, exc: IntegrityError):
        logger.warning("Database integrity error", exc_info=exc)
        code, message = _integrity_message(exc)
        return _error(code, message)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_request: Request, exc: SQLAlchemyError):
        logger.exception("Database operation failed", exc_info=exc)
        return _error(503, "Database is temporarily unavailable.")

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, exc: Exception):
        logger.exception("Unexpected API error", exc_info=exc)
        return _error(500, "An unexpected server error occurred.")

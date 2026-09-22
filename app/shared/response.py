"""One predictable envelope for every API response."""

from typing import Generic, TypeVar

from pydantic import BaseModel


DataT = TypeVar("DataT")


class BaseResponse(BaseModel, Generic[DataT]):
    success: bool
    message: str
    data: DataT | None = None


def ok(message: str, data: DataT | None = None) -> BaseResponse[DataT]:
    return BaseResponse(success=True, message=message, data=data)


# Advertise the same error envelope in Swagger for all API routers.
ERROR_RESPONSES = {
    code: {"model": BaseResponse[object]}
    for code in (400, 401, 403, 404, 409, 422, 500, 503)
}

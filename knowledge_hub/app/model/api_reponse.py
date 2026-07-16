from dataclasses import dataclass
from http import HTTPStatus
from typing import Generic, TypeVar
from datetime import datetime

T = TypeVar("T")


@dataclass
class ApiResponse(Generic[T]):
    success: bool
    message: str
    code: int
    timestamp: str = datetime.utcnow().isoformat()
    data: T | None = None



class ResponseBuilder:

    @staticmethod
    def success(
        data: T = None,
        message: str = "Success",
    ) -> ApiResponse[T]:

        return ApiResponse(
            code=HTTPStatus.OK.value,
            success=True,
            message=message,
            data=data,
        )

    @staticmethod
    def failure(
        message: str,
        error_code: int=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    ) -> ApiResponse[None]:

        return ApiResponse(
            success=False,
            message=message,
            code=error_code,
        )
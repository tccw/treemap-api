from http import HTTPStatus
from starlite import HTTPException


def raise_bad_request_response(detail: str):
    raise HTTPException(
        status_code=HTTPStatus.BAD_REQUEST,
        detail=detail,
    )


def raise_server_error_response(detail: str):
    raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=detail)


def raise_unprocessable_entity_response(detail: str):
    raise HTTPException(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        detail=detail,
    )

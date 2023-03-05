from starlite import OpenAPIController


class MyOpenAPIController(OpenAPIController):
    path = "/api-docs"

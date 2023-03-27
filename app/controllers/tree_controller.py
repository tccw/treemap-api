from starlite import (
    Controller,
    get,
    Request,
)


class TreeController(Controller):
    path = "/trees"

    @get(path="/{species_name:str}")
    async def get_description(
        self, request: Request, species_name: str
    ) -> dict[str, str]:
        request.logger.info(f"get_description hit with species: {species_name}")
        return {"blurb": "This is a tree blurb with info."}

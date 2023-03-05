import datetime
from decimal import InvalidOperation
import io
from uuid import uuid4
from pathlib import Path
import os
from http import HTTPStatus
from typing import Any, Tuple
from starlite import (
    Body,
    Controller,
    Request,
    RequestEncodingType,
    post,
    get,
    HTTPException,
    Provide,
)
from azure.cognitiveservices.vision.contentmoderator import (
    ContentModeratorClient,
)
from azure.cognitiveservices.vision.contentmoderator.models import Evaluate, APIErrorException
from msrest.authentication import CognitiveServicesCredentials
from azure.identity import DefaultAzureCredential
from pymongo import MongoClient
from pymongo.results import InsertOneResult
from pymongo.collection import Collection

import filetype
import cloudinary.uploader
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
from models.requests import UserPhotoPointFeature, UserPhotoPostRequest

from models.responses import UserPhotoResponse, GetResponse


load_dotenv()

aad_credentials = DefaultAzureCredential()
DB_NAME = "treemap-db"
COLLECTION_NAME = "user-tree-photos"
MIN_IMAGE_DIM = 128


# https://learn.microsoft.com/en-us/azure/cosmos-db/mongodb/quickstart-python?tabs=azure-cli%2Cvenv-windows%2Cwindows#authenticate-the-client
cosmos_client = MongoClient(os.getenv("COSMOSDB_CONN_STR"))
db = cosmos_client[DB_NAME]
if DB_NAME not in cosmos_client.list_database_names():
    db.command({"customAction": "CreateDatabase", "offerThroughput": 400})

collection = db[COLLECTION_NAME]
if COLLECTION_NAME not in db.list_collection_names():
    # Creates a unsharded collection that uses the DBs shared throughput
    db.command({"customAction": "CreateCollection", "collection": COLLECTION_NAME})

moderator_client = ContentModeratorClient(
    endpoint=os.getenv("CONTENT_MODERATOR_ENDPOINT"),
    credentials=CognitiveServicesCredentials(os.getenv("CONTENT_MODERATOR_KEY1")),
)


def moderator_client_dep() -> ContentModeratorClient:
    return moderator_client


def db_client_dep() -> Collection:
    return collection


class PhotoController(Controller):
    path = "/photo"

    # moderator_client = ContentModeratorClient(
    #     endpoint=os.getenv("CONTENT_MODERATOR_ENDPOINT"),
    #     credentials=CognitiveServicesCredentials(os.getenv("CONTENT_MODERATOR_KEY1")),
    # )

    @post(
        path="/multi-part",
        dependencies={
            "collection": Provide(db_client_dep),
            "moderator": Provide(moderator_client_dep),
        },
    )
    async def post_multi_part(
        self,
        request: Request,
        collection: Collection,
        moderator: ContentModeratorClient,
        data: UserPhotoPostRequest = Body(media_type=RequestEncodingType.MULTI_PART),
    ) -> dict:
        (feature, image_byes) = await self.validate_request(data, request, moderator)

        upload_result = cloudinary.uploader.upload(
            image_byes, folder="yvr-user-photos", tags=["user-photo"], phash=True
        )
        return {"end": "point"}
        try:
            feature.properties.created_at_utc = upload_result["created_at"]
            feature.properties.public_id = upload_result["public_id"]
            feature.properties.full_size_url = upload_result["secure_url"]

            result: InsertOneResult = collection.insert_one(
                {
                    "type": feature.type,
                    "geometry": {
                        "type": feature.geometry.type,
                        "coordinates": feature.geometry.coordinates,
                    },
                    "properties": vars(feature.properties),
                }
            )

            if result.acknowledged:
                return {
                    "type": feature.type,
                    "geometry": {
                        "type": feature.geometry.type,
                        "coordinates": feature.geometry.coordinates,
                    },
                    "properties": {
                        **vars(feature.properties),
                        **{"_id": str(feature.inserted_id)},
                    },
                }
        except InvalidOperation as e:
            request.logger.error(f"Write request failed: {e}")

    @post(
        path="/user-entry",
        media_type="application/geo+json",
        dependencies={"collection": Provide(db_client_dep)},
    )
    async def post_user_entry(
        self, request: Request, data: UserPhotoPointFeature, collection: Collection
    ) -> dict[str, Any]:
        if data.type == "Feature" and data.geometry.type == "Point":
            try:
                data.properties.created_at_utc = datetime.datetime.utcnow()
                result: InsertOneResult = collection.insert_one(
                    {
                        "type": data.type,
                        "geometry": {
                            "type": data.geometry.type,
                            "coordinates": data.geometry.coordinates,
                        },
                        "properties": vars(data.properties),
                    }
                )

                if result.acknowledged:
                    return {
                        "type": data.type,
                        "geometry": {
                            "type": data.geometry.type,
                            "coordinates": data.geometry.coordinates,
                        },
                        "properties": {
                            **vars(data.properties),
                            **{"_id": str(result.inserted_id)},
                        },
                    }
            except InvalidOperation as e:
                request.logger.error(f"Write request failed: {e}")

        request.logger.info(
            (
                f"Recieved data with type: {data.type} and geometry: {data.geometry.type}"
                "which is not valid for this endpoint."
            )
        )

        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Endpoint only accepts GeoJSON Point Features.",
        )

    @post(path="/user-photo/{id:int}")
    async def post_user_photo(
        self,
        id: int,
        request: Request,
    ) -> dict[str, str]:
        data: bytes = await request.body()
        filekind = filetype.guess(data)

        if filekind.mime == "image/jpeg":
            try:
                eval = self.check_if_appropriate(data)
            except UnidentifiedImageError:
                request.logger.error("Could not parse the request body to a PIL Image.")
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="The request body could not be parsed as an image.",
                )
            except (ValueError, TypeError) as e:
                request.logger.error("Could not parse the request body to a PIL Image.")
                raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))

            if eval.result:
                request.logger.info(
                    (
                        f"ContentModerator blocked an image from IP: {request.client.host}"
                        f"-- racy_score = {eval.racy_classification_score} : "
                        f" adult_score = {eval.adult_classification_score} "
                    )
                )

                raise HTTPException(
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                    detail="Uploaded image was flagged as inappropriate for Treemap and will not be accepted.",
                )

            res = cloudinary.uploader.upload(
                data, folder="yvr-user-photos", tags=["user-photo"], phash=True
            )

            return UserPhotoResponse(
                created_at_utc=res["created_at"],
                public_id=res["public_id"],
                full_size_url=res["secure_url"],
            )

        if filekind.mime is None:
            request.logger.error("Could not determine the filetype of the posted file.")
        else:
            request.logger.error(
                f"/userphoto does not accept filetype: {filekind.extension} with MIME type: {filekind.mime}"
            )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Endpoint only accepts JPEG encoded images.",
        )

    @get(path="/user-entry", dependencies={"collection": Provide(db_client_dep)})
    async def get_user_entries(
        self, request: Request, collection: Collection
    ) -> GetResponse:
        offset_time = datetime.datetime.utcnow() - datetime.timedelta(days=14)
        two_weeks_ago_query = {"properties.created_at_utc": {"$gt": offset_time}}
        result = [
            entry for entry in collection.find(two_weeks_ago_query, {"_id": False})
        ]

        return GetResponse(type="list", data=result, next_token="")

    def check_if_appropriate(self, image: bytes) -> Evaluate:
        # must be > 128 x 128 px image, use pillow (PIL)

        with io.BytesIO(image) as stream:
            pic = Image.open(stream)
            if any(dim < 128 for dim in pic.size):
                raise ValueError(
                    (
                        "Image dimensions must be at least 128 x 128 pixels"
                        f"but recieved an image of size {pic.size[0]} x {pic.size[1]} pixels."
                    )
                )

            evaluation = self.moderator_client.image_moderation.evaluate_file_input(
                image_stream=stream, cache_image=True
            )

        return evaluation

    async def validate_request(
        self,
        data: UserPhotoPostRequest,
        request: Request,
        moderator: ContentModeratorClient,
    ) -> Tuple[UserPhotoPointFeature, bytes]:
        try:
            feature: UserPhotoPointFeature = data.feature
            file_bytes: bytes = await data.image.read()
            with io.BytesIO(file_bytes) as stream:
                image: Image = Image.open(stream)

                if image.get_format_mimetype() != "image/jpeg":
                    request.logger.error(
                        f"Expected MIME type 'image/jpeg' but recieved '{image.get_format_mimetype()}'"
                    )
                    raise_bad_request_response(
                        "Endpoint only accepts JPEG encoded images."
                    )

                eval: Evaluate = self.check_if_appropriate_multiform(
                    image, moderator
                )

                if eval.result:
                    request.logger.info(
                        (
                            f"ContentModerator blocked an image from IP: {request.client.host}"
                            f"-- racy_score = {eval.racy_classification_score} : "
                            f" adult_score = {eval.adult_classification_score} "
                        )
                    )

                    raise HTTPException(
                        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                        detail="Uploaded image was flagged as inappropriate for Treemap and will not be accepted.",
                    )
        except APIErrorException as e:
            request.logger.error("API error for content moderation: %s --- %s", e, e.inner_exception)
            raise_server_error_resposne("Content moderation failed.")
        except UnidentifiedImageError as e:
            request.logger.error("Failed to identify image type: %s", e)
            raise_bad_request_response("Could not determine the image type.")
        except (ValueError, TypeError) as e:
            request.logger.error("Failed to parse the image: %s", e)
            raise_bad_request_response("Invalid file values.")

        if feature.type != "Feature" or feature.geometry.type != "Point":
            request.logger.info(
                (
                    f"Recieved data with type: {data.type} and geometry: {data.geometry.type}"
                    "which is not valid for this endpoint."
                )
            )
            raise_bad_request_response("Endpoint only accepts GeoJSON Point Features.")

        return (feature, file_bytes)

    def check_if_appropriate_multiform(
        self, image: Image, moderator: ContentModeratorClient
    ) -> Evaluate:
        # must be > 128 x 128 px image, use pillow (PIL)
        if any(dim < MIN_IMAGE_DIM for dim in image.size):
            raise ValueError(
                (
                    f"Image dimensions must be at least {MIN_IMAGE_DIM} x {MIN_IMAGE_DIM} pixels"
                    f"but recieved an image of size {image.size[0]} x {image.size[1]} pixels."
                )
            )

        tmp_file: Path = Path(f"{uuid4()}.jpeg")
        image.save(tmp_file)
        with open(tmp_file, 'rb') as photo:
            evaluation = moderator.image_moderation.evaluate_file_input(
                media_type="image/jpeg",
                image_stream=photo
            )
        tmp_file.unlink(missing_ok=True)

        return evaluation


def raise_bad_request_response(detail: str):
    raise HTTPException(
        status_code=HTTPStatus.BAD_REQUEST,
        detail=detail,
    )


def raise_server_error_resposne(detail: str):
    raise HTTPException(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail=detail
    )

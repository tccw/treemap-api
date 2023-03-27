import datetime
from decimal import InvalidOperation
import io
from uuid import uuid4
from pathlib import Path
import os
from typing import List, Tuple
from starlite import (
    Body,
    Controller,
    Request,
    RequestEncodingType,
    post,
    get,
    Provide,
)
from azure.cognitiveservices.vision.contentmoderator import (
    ContentModeratorClient,
)
from azure.cognitiveservices.vision.contentmoderator.models import (
    Evaluate,
    APIErrorException,
)
from msrest.authentication import CognitiveServicesCredentials
from azure.identity import DefaultAzureCredential
from pymongo import MongoClient
from pymongo.results import InsertOneResult
from pymongo.collection import Collection

import cloudinary.uploader
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
from app.models.exceptions import (
    raise_unprocessable_entity_response,
    raise_bad_request_response,
    raise_server_error_response,
)
from app.models.requests import UserPhotoPointFeature, UserPhotoPostRequest
from app.models.responses import ResponseModel
from pydantic_geojson import FeatureCollectionModel


load_dotenv()

aad_credentials = DefaultAzureCredential()
DB_NAME = "treemap-db"
COLLECTION_NAME = "user-tree-photos"
MIN_IMAGE_DIM = 128
USER_PHOTO_TAG = "user-photos"
CLOUDINARY_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # e.g. 2017-08-11T12:24:32Z
DAYS = int(os.getenv("TIME_OFFSET_DAYS", 14))


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
    path = "/photos"
    dependencies = {"collection": Provide(db_client_dep)}

    @post(
        path=f"/{USER_PHOTO_TAG}",
        dependencies={"moderator": Provide(moderator_client_dep)},
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
            image_byes, folder="yvr-user-photos", tags=[USER_PHOTO_TAG], phash=True
        )

        try:
            feature.properties.created_at_utc = datetime.datetime.strptime(
                upload_result["created_at"], CLOUDINARY_DATE_FORMAT
            )
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
                        **{"_id": str(result.inserted_id)},
                    },
                }
        except (InvalidOperation, TypeError, AttributeError) as e:
            request.logger.error(f"Write request failed: {e}")
            request.logger.info(
                f"Removing image with public ID: {upload_result['public_id']}"
            )
            cloudinary.uploader.destroy(upload_result["public_id"])
            raise_server_error_response("Failed to record user photo.")

    @get(path=f"/{USER_PHOTO_TAG}", skip_rate_limiting=True)
    async def get_user_entries(
        self, request: Request, collection: Collection
    ) -> ResponseModel:
        """Gets user GeoJSON entries from user submitted photos

        Args:
            request (Request): the starlite request object
            collection (Collection): the cosmos db collection

        Returns:
            GetResponse: A FeatureCollection of all user photos within the last two weeks
        """
        offset_time = datetime.datetime.utcnow() - datetime.timedelta(days=DAYS)
        two_weeks_ago_query = {"properties.created_at_utc": {"$gt": offset_time}}
        result: List[UserPhotoPointFeature] = [
            UserPhotoPointFeature(**entry)
            for entry in collection.find(two_weeks_ago_query, {"_id": False})
        ]

        feature_collection = FeatureCollectionModel(features=result)

        return ResponseModel(type="object", data=feature_collection)

    async def validate_request(
        self,
        data: UserPhotoPostRequest,
        request: Request,
        moderator: ContentModeratorClient,
    ) -> Tuple[UserPhotoPointFeature, bytes]:
        """
        Verifies that a request:
            - contains a valid GeoJSON Point feature
            - has a JPG image file attached
        """
        feature: UserPhotoPointFeature = data.feature
        if not is_valid_feature(feature):
            request.logger.info(
                (
                    f"Recieved data with type: {feature.type} and geometry: {feature.geometry.type} "
                    f"at location lat: {feature.geometry.coordinates.lat}, lon: {feature.geometry.coordinates.lon}"
                    "which is not valid for this endpoint."
                )
            )
            raise_bad_request_response("Endpoint only accepts GeoJSON Point Features within the city of Vancouver.")

        try:
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

                eval: Evaluate = self.content_moderate_image(image, moderator)

                if eval.result:
                    request.logger.info(
                        (
                            f"ContentModerator blocked an image from IP: {request.client.host}"
                            f"-- racy_score = {eval.racy_classification_score} : "
                            f" adult_score = {eval.adult_classification_score} "
                        )
                    )

                    raise_unprocessable_entity_response(
                        "Uploaded image was flagged as inappropriate for Treemap and will not be accepted."
                    )

        except APIErrorException as e:
            request.logger.error(
                "API error for content moderation: %s --- %s", e, e.inner_exception
            )
            raise_server_error_response("Content moderation failed.")
        except UnidentifiedImageError as e:
            request.logger.error("Failed to identify image type: %s", e)
            raise_bad_request_response("Could not determine the image type.")
        except (ValueError, TypeError) as e:
            request.logger.error("Failed to parse the image: %s", e)
            raise_bad_request_response("Invalid file values.")

        return (feature, file_bytes)

    def content_moderate_image(
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
        try:
            tmp_file: Path = Path(f"{uuid4()}.jpeg")
            image.save(tmp_file)
            with open(tmp_file, "rb") as photo:
                evaluation = moderator.image_moderation.evaluate_file_input(
                    media_type="image/jpeg", image_stream=photo
                )
        except (ValueError, OSError) as e:
            raise ValueError from e
        finally:
            tmp_file.unlink(missing_ok=True)

        return evaluation


def is_valid_feature(feature: UserPhotoPointFeature) -> bool:
    return feature.type == "Feature" and feature.geometry.type == "Point" and is_valid_location(feature)


def is_valid_location(feature: UserPhotoPointFeature) -> bool:
    coords = feature.geometry.coordinates
    return (
        coords.lat > 49.196
        and coords.lat < 49.34
        and coords.lon > -123.27
        and coords.lon < -123.01
    )

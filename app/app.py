from starlite import Starlite, LoggingConfig, OpenAPIConfig
from dotenv import load_dotenv

import cloudinary
import os

from controllers.controllers import TreeController, PhotoController, MyOpenAPIController

load_dotenv()

logging_config = LoggingConfig(
    loggers={"street-trees": {"level": "INFO", "handlers": ["queue_listener"]}}
)

config = cloudinary.config(
    secure=True,
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
)

app = Starlite(
    route_handlers=[TreeController, PhotoController],
    logging_config=logging_config,
    openapi_config=OpenAPIConfig(
        title="My API", version="1.0.0", openapi_controller=MyOpenAPIController
    ),
)

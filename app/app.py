from starlite import CORSConfig, Starlite, LoggingConfig
from starlite.middleware import RateLimitConfig
from dotenv import load_dotenv

import cloudinary
import os

from app.controllers.controllers import PhotoController

load_dotenv()

logging_config = LoggingConfig(
    loggers={"street-trees": {"level": "INFO", "handlers": ["queue_listener"]}}
)

rate_limit_config = RateLimitConfig(
    rate_limit=("second", 1),
    exclude=["/schema"],
    exclude_opt_key="skip_rate_limiting"
)

dev_domain = os.getenv("DEV_REQUEST_DOMAIN", None)
if dev_domain is None:
    cors_config = CORSConfig(allow_origins=[os.getenv("CROSS_ORIGIN_DOMAIN")], allow_methods=["GET", "POST"])
else:
    cors_config = CORSConfig(
        allow_origins=[os.getenv("CROSS_ORIGIN_DOMAIN"), dev_domain],
        allow_methods=["GET", "POST"]
    )

config = cloudinary.config(
    secure=True,
    cloud_name=os.getenv("CLOUDINARY_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

app = Starlite(
    route_handlers=[PhotoController],
    logging_config=logging_config,
    middleware=[rate_limit_config.middleware],
    cors_config=cors_config,
    # cors_config=CORSConfig(allow_origins=['*']),
    openapi_config=None
)

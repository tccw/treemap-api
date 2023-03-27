from starlite import AllowedHostsConfig, CORSConfig, OpenAPIConfig, Starlite, LoggingConfig
from starlite.middleware import RateLimitConfig
from dotenv import load_dotenv

import cloudinary
import os
from controllers.openapi_controller import MyOpenAPIController

from controllers.controllers import PhotoController

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
    cors_config=CORSConfig(allow_origins=['*']),
    # allowed_hosts=AllowedHostsConfig(
    #     allowed_hosts=["*"]
    # ),
    # disabling OpenAPI docs until this issue is resolved: https://github.com/pydantic/pydantic/issues/3210
    # openapi_config=None
    openapi_config=OpenAPIConfig(
        title="Treemap API", version="0.1.0", openapi_controller=MyOpenAPIController
    ),
)

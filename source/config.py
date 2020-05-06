import os


class Config:
    HOST: str
    PORT: int

    APP_ID: int
    API_HASH: str
    SESSION: str
    CHANNEL_ID: int
    BOT_TOKEN: str

    DB_HOST: str
    DB_USER: str
    DB_PORT: str
    DB_PASSWORD: str

    FLIBUSTA_SERVER_HOST: str
    FLIBUSTA_SERVER_PORT: str

    FLIBUSTA_SERVER_DB_HOST: str
    FLIBUSTA_SERVER_DB_USER: str
    FLIBUSTA_SERVER_DB_PORT: str
    FLIBUSTA_SERVER_DB_PASSWORD: str

    @classmethod
    def configure(cls):
        cls.HOST = os.environ.get('HOST', 'localhost')
        cls.PORT = os.environ.get('PORT', 7080)

        cls.APP_ID = os.environ['APP_ID']
        cls.API_HASH = os.environ['API_HASH']
        cls.SESSION = os.environ['SESSION']
        cls.CHANNEL_ID = int(os.environ['CHANNEL_ID'])
        cls.BOT_TOKEN = os.environ['BOT_TOKEN']

        cls.DB_HOST = os.environ.get('DB_HOST', 'localhost')
        cls.DB_USER = os.environ.get('DB_USER', 'flibusta_channel')
        cls.DB_DATABASE = os.environ.get('DB_DATABASE', 'flibusta_channel')
        cls.DB_PASSWORD = os.environ['DB_PASSWORD']

        cls.FLIBUSTA_SERVER_HOST = os.environ.get('FLIBUSTA_SERVER_HOST', 'localhost')
        cls.FLIBUSTA_SERVER_PORT = os.environ.get('FLIBUSTA_SERVER_PORT', '7770')

        cls.FLIBUSTA_SERVER_DB_HOST = os.environ.get('FLIBUSTA_SERVER_DB_HOST', 'localhost')
        cls.FLIBUSTA_SERVER_DB_PORT = os.environ.get('FLIBUSTA_SERVER_DB_PORT', '5432')
        cls.FLIBUSTA_SERVER_DB_DATABASE = os.environ.get('FLIBUSTA_SERVER_DB_DATABASE', 'flibusta')
        cls.FLIBUSTA_SERVER_DB_USER = os.environ.get('FLIBUSTA_SERVER_DB_USER', 'flibusta')
        cls.FLIBUSTA_SERVER_DB_PASSWORD = os.environ['FLIBUSTA_SERVER_DB_PASSWORD']


Config.configure()

#######################################
## VM / production settings 
#######################################

import os
from .base import *


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False  #VM

CSRF_TRUSTED_ORIGINS = [
    'https://agents.lyfx.ai',
    'http://agents.lyfx.ai',  # Include HTTP version too, just in case
]

ALLOWED_HOSTS = [
    'agents.lyfx.ai',
    'localhost',
    '127.0.0.1',
]

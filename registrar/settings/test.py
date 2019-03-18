import os

from registrar.settings.base import *


# IN-MEMORY TEST DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
}
# END IN-MEMORY TEST DATABASE

LMS_BASE_URL = 'https://lms-service-base'
DISCOVERY_BASE_URL = 'https://discovery-service-base'

OAUTH2_PROVIDER_URL = 'https://test-provider/oauth2'
SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = OAUTH2_PROVIDER_URL

JWT_AUTH['JWT_ISSUERS'] = [{
    'SECRET_KEY': SOCIAL_AUTH_EDX_OAUTH2_SECRET,
    'ISSUER': OAUTH2_PROVIDER_URL,
    'AUDIENCE': SOCIAL_AUTH_EDX_OAUTH2_KEY,
}]

# CELERY
CELERY_TASK_ALWAYS_EAGER = True

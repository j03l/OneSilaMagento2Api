from enum import Enum

# Existing constants
CREATE = 'CREATE'
UPDATE = 'UPDATE'
DELETE = 'DELETE'
GET = 'GET'

SCOPE_GLOBAL = 'global'
SCOPE_STORE = 'store'
SCOPE_WEBSITE = 'website'

STORE_SCOPE_ALL = 'all'
STORE_SCOPE_DEFAULT = 'default'

TOKEN = 'TOK'
PASSWORD = 'PAS'

# Enums
class ModelMethod(Enum):
    GET = GET
    CREATE = CREATE
    UPDATE = UPDATE
    DELETE = DELETE

class Scope(Enum):
    GLOBAL = SCOPE_GLOBAL
    STORE = SCOPE_STORE
    WEBSITE = SCOPE_WEBSITE

class StoreCode(Enum):
    ALL = STORE_SCOPE_ALL
    DEFAULT = STORE_SCOPE_DEFAULT

class AuthenticationMethod(Enum):
    TOKEN = TOKEN
    PASSWORD = PASSWORD

from enum import Enum


class FileType(Enum):
    JSON = 'json'
    MD = 'md.zip'
    TEXT = 'txt'
    CSV = 'csv'


IMAGE = 'axarev/parsr'
ATTEMPT_LIMIT = 3
DOCKER_TIMEOUT = 1800 # 30 minutes

BASE_URL = 'http://localhost:3001/api/v1'
UPLOAD_URL = f"{BASE_URL}/document"
STATUS_URL = f"{BASE_URL}/queue"
JSON_URL = f"{BASE_URL}/json"
CSV_URL = f"{BASE_URL}/csv"
TEXT_URL = f"{BASE_URL}/text"
MD_URL = f"{BASE_URL}/markdown"
CHECK_URL = f"{BASE_URL}/check-installation"
MODULES_URL = f"{BASE_URL}/modules"
MODULE_CONFIG_URL = f"{BASE_URL}/module-config"
DEFAULT_CONFIG_URL = f"{BASE_URL}/default-config"

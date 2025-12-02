from ditupy.logging_config import setup_logging
from ditupy.schemas.types import DRMInfo
from ditupy.services.license_manager import LicenseManager

setup_logging()
drm_info_path = r"docs/content/desafio_siglo_xxi_14/drm_info.json"
device_path = (
    r"dumper-main/key_dumps/Android Emulator 5554/private_keys/4464/2137596953"
)
drm_info = DRMInfo.parse_file(drm_info_path)

# Obtiene las Key de cifrado
license_manager = LicenseManager(device_path=device_path)
keys = license_manager.get_keys(drm_info=drm_info)
print(keys)

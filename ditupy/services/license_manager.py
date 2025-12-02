import logging
from pathlib import Path
from typing import Dict

import requests
from pywidevine import Cdm
from pywidevine.device import Device, DeviceTypes
from pywidevine.pssh import PSSH

from ditupy.schemas.types import DRMInfo

logger = logging.getLogger(__name__)


class LicenseManager:
    license_url = "https://varnish-prod.avscaracoltv.com/AGL/1.6/A/ENG/ANDROID/ALL/CONTENT/LICENSE"

    def __init__(self, device_path: str):
        self.path_obj = Path(device_path)
        self.device = self._load_device(device_path)
        self.cdm = Cdm.from_device(self.device)

    def _load_device(self, device_path: str) -> Device:
        path_obj = Path(device_path)

        if not path_obj.exists():
            raise FileNotFoundError(
                f"No se encontró la ruta del dispositivo: {device_path}"
            )

        if path_obj.is_dir():
            logger.info(f"Cargando dispositivo desde carpeta: {path_obj}")
            client_id_path = path_obj / "client_id.bin"
            private_key_path = path_obj / "private_key.pem"

            if not client_id_path.exists() or not private_key_path.exists():
                raise FileNotFoundError(
                    "La carpeta debe contener 'client_id.bin' y 'private_key.pem'"
                )

            return Device(
                type_=DeviceTypes.ANDROID,
                security_level=3,
                flags=None,
                client_id=client_id_path.read_bytes(),
                private_key=private_key_path.read_bytes(),
            )
        else:
            logger.info(f"Cargando dispositivo desde archivo WVD: {path_obj}")
            return Device.load(str(path_obj))

    def _do_license_request(self, challenge: bytes, drm_info: DRMInfo) -> bytes:
        logger.info(f"Enviando POST a {self.license_url}")

        headers = {
            "User-Agent": "okhttp/4.12.0",
            "Restful": "yes",
            "Content-Type": "application/octet-stream",
        }

        resp = requests.post(
            self.license_url,
            headers=headers,
            cookies=drm_info.cookies.model_dump(),
            data=challenge,
        )

        if resp.status_code != 200:
            logger.error(f"Error Licencia ({resp.status_code}): {resp.text}")
            try:
                err_json = resp.json()
                logger.error(f"Detalle del error: {err_json}")
            except Exception as e:
                logger.error(f"No se pudo parsear JSON de error: {e}")
                raise e

        return resp.content

    def get_keys(self, drm_info: DRMInfo) -> Dict[str, str]:
        session_id = self.cdm.open()
        found_keys = {}
        try:
            pssh_obj = PSSH(drm_info.pssh_widevine)  #  AAAAQ3Bzc....0cnVzdCIBKg==
            challenge = self.cdm.get_license_challenge(session_id, pssh_obj)
            logger.debug(f"Challenge generado ({len(challenge)} bytes)")

            logger.info("Solicitando licencia al servidor...")
            license_response = self._do_license_request(challenge, drm_info)

            logger.debug(
                f"Respuesta de licencia recibida ({len(license_response)} bytes)"
            )

            self.cdm.parse_license(session_id, license_response)

            for key in self.cdm.get_keys(session_id):
                if key.type == "CONTENT":
                    kid = key.kid.hex
                    k = key.key.hex()
                    logger.info(f"KEY ENCONTRADA -> {kid}:{k}")
                    found_keys[kid] = k

        except Exception as e:
            logger.error(f"Error durante el proceso de licencia: {e}")
            raise e
        finally:
            self.cdm.close(session_id)

        return found_keys

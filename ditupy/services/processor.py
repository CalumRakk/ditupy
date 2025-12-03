import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class PostProcessor:
    def __init__(self, working_dir: Union[str, Path]):
        working_dir = Path(working_dir) if isinstance(working_dir, str) else working_dir
        self.working_dir = working_dir
        self.video_dir = working_dir / "video"
        self.audio_dir = working_dir / "audio"

    def _get_sorted_segments(
        self, directory: Path, init_name: str = "init.mp4"
    ) -> List[Path]:
        """
        Encuentra y ordena los segmentos numéricamente.
        """
        files = []
        init_file = None

        if not directory.exists():
            return []

        for f in directory.iterdir():
            if "init" in f.name:
                init_file = f
                continue
            if f.suffix == ".mp4" or f.suffix == ".m4s":  # A veces son .m4s
                files.append(f)

        def extract_number(p: Path):
            match = re.search(r"_(\d+)\.", p.name)
            return int(match.group(1)) if match else 0

        files.sort(key=extract_number)

        if init_file:
            files.insert(0, init_file)

        return files

    def _concatenate_binary(self, files: List[Path], output_path: Path):
        """Une archivos a nivel de bytes."""
        if not files:
            return

        logger.info(f"Uniendo {len(files)} segmentos en {output_path.name}...")
        with open(output_path, "wb") as outfile:
            for f in files:
                with open(f, "rb") as readfile:
                    shutil.copyfileobj(readfile, outfile)

    def _decrypt_track(
        self, encrypted_path: Path, keys: Dict[str, str]
    ) -> Optional[Path]:
        """
        Desencripta un track usando mp4decrypt (Bento4).
        Retorna la ruta del archivo desencriptado o None si falla.
        """
        if not keys:
            logger.warning("No se proporcionaron llaves de desencriptación.")
            return encrypted_path

        decrypted_path = encrypted_path.with_name(f"dec_{encrypted_path.name}")

        # Llaves para mp4decrypt. Formato: --key KID:KEY
        key_args = []
        for kid, key in keys.items():
            key_args.extend(["--key", f"{kid}:{key}"])

        cmd = [
            "mp4decrypt",
            "--show-progress",
            *key_args,
            str(encrypted_path),
            str(decrypted_path),
        ]

        try:
            logger.info(f"Desencriptando {encrypted_path.name}...")
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            return decrypted_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Error desencriptando: {e}")
            return None
        except FileNotFoundError:
            logger.error(
                "mp4decrypt no encontrado. Asegúrate de tener Bento4 instalado y en el PATH."
            )
            return None

    def process(
        self,
        output_filename: str,
        keys: Optional[Dict[str, str]] = None,
        cleanup: bool = True,
    ):
        """
        Orquesta la unión, (desencriptación) y el muxing final.
        """
        temp_video_enc = self.working_dir / "temp_video_enc.mp4"
        temp_audio_enc = self.working_dir / "temp_audio_enc.mp4"

        final_output = self.working_dir / output_filename

        video_files = self._get_sorted_segments(self.video_dir, "segment_init.mp4")
        video_track = None

        if video_files:
            self._concatenate_binary(video_files, temp_video_enc)
            if keys:
                video_track = self._decrypt_track(temp_video_enc, keys)
                if not video_track:
                    logger.error("Fallo crítico en desencriptación de video.")
                    return
            else:
                video_track = temp_video_enc
        else:
            logger.error("No se encontraron segmentos de video.")
            return

        audio_files = self._get_sorted_segments(self.audio_dir, "segment_init.mp4")
        audio_track = None

        if audio_files:
            self._concatenate_binary(audio_files, temp_audio_enc)
            if keys:
                audio_track = self._decrypt_track(temp_audio_enc, keys)
            else:
                audio_track = temp_audio_enc

        logger.info("Empaquetando contenedor final con FFmpeg...")
        cmd = ["ffmpeg", "-y", "-i", str(video_track)]

        if audio_track:
            cmd.extend(["-i", str(audio_track)])

        cmd.extend(["-c", "copy", "-movflags", "+faststart", str(final_output)])

        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            logger.info(f"¡Éxito! Video final creado en: {final_output}")

            if cleanup:
                logger.info("Limpiando temporales...")
                files_to_remove = [temp_video_enc, temp_audio_enc]
                if keys:
                    files_to_remove.append(video_track)
                    if audio_track:
                        files_to_remove.append(audio_track)

                self._cleanup_garbage(files_to_remove)

        except subprocess.CalledProcessError as e:
            logger.error(f"Error en FFmpeg: {e}")

    def _cleanup_garbage(self, files_to_remove: List[Path]):
        if self.video_dir.exists():
            shutil.rmtree(self.video_dir)
        if self.audio_dir.exists():
            shutil.rmtree(self.audio_dir)

        for f in files_to_remove:
            if f and f.exists():
                f.unlink()

    def _get_actual_duration(self, file_path: Path) -> float:
        """Obtiene la duración precisa usando ffprobe."""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            logger.error("No se pudo obtener la duración del archivo.")
            return 0.0

    def verify_integrity(
        self, file_path: Path, expected_duration: float, tolerance: float = 5.0
    ) -> bool:
        """
        Compara la duración del archivo con la esperada.
        :param tolerance: Segundos de diferencia aceptables.
        """
        if expected_duration <= 0:
            logger.warning("Duración esperada inválida, omitiendo verificación.")
            return True

        actual = self._get_actual_duration(file_path)
        diff = abs(actual - expected_duration)

        logger.info(
            f"Integridad: Esperado={expected_duration:.2f}s | Real={actual:.2f}s | Diff={diff:.2f}s"
        )

        if diff > tolerance:
            logger.error(
                f"VERIFICACIÓN FALLIDA: El video está incompleto o corrupto (Faltan ~{diff:.2f}s)"
            )
            return False

        logger.info("VERIFICACIÓN EXITOSA: El video está completo.")
        return True

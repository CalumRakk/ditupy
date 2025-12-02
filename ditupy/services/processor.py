import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Union

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

    def process(self, output_filename: str, cleanup: bool = True):
        """
        Orquesta la unión y el muxing final.
        """
        temp_video = self.working_dir / "temp_video_track.mp4"
        temp_audio = self.working_dir / "temp_audio_track.mp4"

        final_output = self.working_dir / output_filename

        video_files = self._get_sorted_segments(self.video_dir, "segment_init.mp4")
        if not video_files:
            logger.error("No se encontraron segmentos de video.")
            return

        self._concatenate_binary(video_files, temp_video)

        # Identificar y Unir Audio
        audio_files = self._get_sorted_segments(self.audio_dir, "segment_init.mp4")
        has_audio = False
        if audio_files:
            self._concatenate_binary(audio_files, temp_audio)
            has_audio = True
        else:
            logger.warning(
                "No se encontraron segmentos de audio. Se generará video mudo."
            )

        # Muxing con FFmpeg (Copia streams sin recodificar)
        logger.info("Empaquetando contenedor final con FFmpeg...")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(temp_video),
        ]

        if has_audio:
            cmd.extend(["-i", str(temp_audio)])

        # -c copy: copia los streams tal cual (encriptados)
        cmd.extend(["-c", "copy", "-movflags", "+faststart", str(final_output)])

        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            logger.info(f"¡Éxito! Video unificado creado en: {final_output}")

            if cleanup:
                logger.info("Limpiando segmentos basura y temporales...")
                self._cleanup_garbage(temp_video, temp_audio)

        except subprocess.CalledProcessError as e:
            logger.error(f"Error en FFmpeg: {e}")
        except FileNotFoundError:
            logger.error("FFmpeg no está instalado o no se encuentra en el PATH.")

    def _cleanup_garbage(self, temp_video: Path, temp_audio: Path):
        """
        Elimina solo lo que sobra: carpetas de segmentos y tracks temporales.
        Mantiene: El archivo final, manifest.mpd y drm_info.json.
        """
        # Eliminar carpetas de segmentos
        if self.video_dir.exists():
            shutil.rmtree(self.video_dir)
        if self.audio_dir.exists():
            shutil.rmtree(self.audio_dir)

        # Eliminar tracks intermedios unidos
        if temp_video.exists():
            temp_video.unlink()
        if temp_audio.exists():
            temp_audio.unlink()

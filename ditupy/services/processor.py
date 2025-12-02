import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class PostProcessor:
    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self.video_dir = working_dir / "video"
        self.audio_dir = working_dir / "audio"

    def _get_sorted_segments(
        self, directory: Path, init_name: str = "init.mp4"
    ) -> List[Path]:
        """
        Encuentra y ordena los segmentos numéricamente.
        Asume nombres como 'segment_10.m4s'.
        """
        files = []
        init_file = None

        for f in directory.iterdir():
            if "init" in f.name:
                init_file = f
                continue
            if f.suffix == ".mp4":
                files.append(f)

        # Ordenar por el número dentro del nombre del archivo
        # Ejemplo: segment_5.m4s -> 5
        def extract_number(p: Path):
            match = re.search(r"_(\d+)\.mp4", p.name)
            return int(match.group(1)) if match else 0

        files.sort(key=extract_number)

        if init_file:
            files.insert(0, init_file)

        return files

    def _concatenate_binary(self, files: List[Path], output_path: Path):
        """Une archivos a nivel de bytes."""
        logger.info(f"Uniendo {len(files)} segmentos en {output_path.name}...")
        with open(output_path, "wb") as outfile:
            for f in files:
                with open(f, "rb") as readfile:
                    shutil.copyfileobj(readfile, outfile)

    def process(self, output_filename: str, cleanup: bool = True):
        """
        Orquesta la unión y el muxing final.
        output_filename: nombre del archivo final (ej: 'resultado.mp4')
        """
        temp_video = self.working_dir / "temp_video_track.mp4"
        temp_audio = self.working_dir / "temp_audio_track.mp4"
        final_output = self.working_dir.parent / output_filename

        # 1. Identificar y Unir Video
        video_files = self._get_sorted_segments(self.video_dir, "segment_init.mp4")
        if not video_files:
            logger.error("No se encontraron segmentos de video.")
            return
        self._concatenate_binary(video_files, temp_video)

        # 2. Identificar y Unir Audio
        audio_files = self._get_sorted_segments(self.audio_dir, "segment_init.mp4")
        if audio_files:
            self._concatenate_binary(audio_files, temp_audio)
        else:
            logger.warning(
                "No se encontraron segmentos de audio. Se generará video mudo."
            )

        # 3. Muxing con FFmpeg
        logger.info("Empaquetando con FFmpeg...")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(temp_video),
        ]

        if audio_files:
            cmd.extend(["-i", str(temp_audio)])

        # -c copy: copia los streams sin recodificar
        cmd.extend(["-c", "copy", "-movflags", "+faststart", str(final_output)])

        try:
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            logger.info(f"¡Éxito! Archivo creado en: {final_output}")

            if cleanup:
                logger.info("Limpiando archivos temporales...")
                shutil.rmtree(self.working_dir)

        except subprocess.CalledProcessError as e:
            logger.error(f"Error en FFmpeg: {e}")
        except FileNotFoundError:
            logger.error("FFmpeg no está instalado o no se encuentra en el PATH.")

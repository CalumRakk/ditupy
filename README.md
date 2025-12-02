🚧🔨👷‍♂️

# DituPy

Cliente y descargador de contenido VOD automatizado capaz de procesar streams DASH protegidos con Widevine.

## 🛠️ Requisitos Previos

Para que el sistema de descifrado y empaquetado funcione, necesitas instalar dos herramientas externas y agregarlas a las **Variables de Entorno (PATH)** de tu sistema.

### 1. FFmpeg
Esencial para unir audio/video y empaquetar el MP4 final.
- **Descarga:** [ffmpeg.org](https://ffmpeg.org/download.html) (o `winget install ffmpeg` en Windows).
- **Instalación:** Extrae el contenido y agrega la carpeta `/bin` a tu PATH.
- **Verificación:** Ejecuta `ffmpeg -version` en tu terminal.

### 2. Bento4 (Descifrado)
Necesario para desencriptar las pistas protegidas con DRM.
- **Descarga:** [Bento4 Binaries](https://www.bento4.com/downloads/).
- **Instalación:** Descarga el SDK para tu SO, extrae el ZIP y agrega la carpeta `/bin` a tu PATH.
- **Verificación:** Ejecuta `mp4decrypt` en tu terminal.

### 3. Widevine CDM (Content Decryption Module)
Necesitas un dispositivo Android volcado (dumped) válido (L3).
- Coloca tu carpeta de dispositivo (con `client_id.bin` y `private_key.pem`) o tu archivo `.wvd` en una ruta accesible.
- Configura la ruta en `debug_download_episode.py` o tu script de entrada.

## 🚀 Instalación del Proyecto

```bash
# Crear entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # O venv\Scripts\activate en Windows

# Instalar dependencias
pip install -r requirements.txt
from pathlib import Path

from ditupy.dash import DashManifest

xml_path = r"docs\content\desafio_siglo_xxi_14\manifest.mpd"
xml_content = Path(xml_path).read_text()
dash = DashManifest(xml_content)
period = dash.get_content_period()
video_rep = period.get_adaptation_sets("video")[0].get_best_representation()

if not video_rep:
    raise ValueError("No se encontró representación de video.")

protections = video_rep.get_content_protections()
for prot in protections:
    # Widevine UUID
    if "edef8ba9" in prot.scheme_id_uri.lower():
        print(f"PSSH Widevine encontrado: {prot.pssh}")

    # Common Encryption (CENC)
    if prot.default_kid:
        print(f"Default KID: {prot.default_kid}")

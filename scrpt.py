
from pathlib import Path

from ditupy.api.dash import DashManifest

path= r"D:\github Leo\caracoltv-dl\ditu\representaions\club_publicidad_1753884747679_1.xml"

xml_text= Path(path).read_text(encoding="utf-8")
manifest = DashManifest(xml_text, source_url="https://varnish.../file.mpd")

# El mejor video del primer periodo
period = manifest.get_periods()[0]
video_set = period.get_adaptation_sets(type_filter="video")[0]
best_rep = video_set.get_best_representation()

if not best_rep:
    raise ValueError("No se encontró representación de video.")

print(best_rep.initialization_url)
print(best_rep.codecs)
for url in best_rep.get_segments():
    print(url)
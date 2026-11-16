from pathlib import Path

from modules.discovery import estadisticas_ventanas
from modules.discovery_ranking import buscar_en_teselas
from modules.planetary_topography import ventana_mola

teselas = sorted(p.stem.upper() for p in Path("data/processed").glob("*.hgt"))
ref = ventana_mola(18.4, 77.7)  # Jezero
print(f"Jezero: pendiente {ref['pend_mediana']:.1f}°, relieve {ref['relieve']:.0f} m")

lista, resumen = buscar_en_teselas(teselas, estadisticas_ventanas, ref, {}, 2.0, 0.30)
for r in resumen:
    print(r)
print("\nLas 8 zonas más cercanas a la referencia:")
for z in lista[:8]:
    print(f"  {z['id_zona']}: distancia {z['distancia']:.2f} | {z['ventanas']} ventanas | "
          f"pend {z['pend_media']:.2f}° | relieve {z['relieve_medio']:.0f} m")
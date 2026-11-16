import sys
import zipfile
from pathlib import Path

if len(sys.argv) != 2:
    print("Uso: python procesar_tesela.py n18w072")
    sys.exit(1)

tesela = sys.argv[1].lower()
zip_path = Path("data/downloaded") / f"NASADEM_HGT_{tesela}.zip"
destino = Path("data/processed")
destino.mkdir(parents=True, exist_ok=True)

if not zip_path.exists():
    print(f"No encuentro {zip_path}")
    sys.exit(1)

with zipfile.ZipFile(zip_path) as z:
    nombres = z.namelist()
    hgt = [n for n in nombres if n.lower().endswith(".hgt")]
    if not hgt:
        print("El zip no contiene un archivo .hgt. Contenido:", nombres)
        sys.exit(1)

    salida_hgt = destino / f"{tesela.upper()}.hgt"
    with z.open(hgt[0]) as origen, open(salida_hgt, "wb") as salida:
        salida.write(origen.read())
    print("Listo:", salida_hgt)

    swb = [n for n in nombres if n.lower().endswith(".swb")]
    if swb:
        salida_swb = destino / f"{tesela.upper()}.swb"
        with z.open(swb[0]) as origen, open(salida_swb, "wb") as salida:
            salida.write(origen.read())
        print("Listo (máscara de agua):", salida_swb)
    else:
        print("Aviso: el zip no trae máscara de agua (.swb).")
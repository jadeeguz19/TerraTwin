import pandas as pd

crudo = pd.read_excel("data/TerraTwin_limpio.xlsx",
                        sheet_name="Regiones de referencia", header=None)
for i in range(10):
    print(i, [str(c)[:25] for c in crudo.iloc[i].tolist()[:4]])
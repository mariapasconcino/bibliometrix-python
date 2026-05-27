import pandas as pd

from www.services.metatagextraction import metaTagExtraction

# Creo un dataframe finto
data = pd.DataFrame({
    "AU": [["Smith J", "Doe A"]],
    "SO": ["JOURNAL OF TEST"],
    "JI": ["J TEST"],
    "PY": [2024],
    "DB": ["OPENALEX"],
    "C1": [["University of Naples, Italy"]],
    "RP": ["University of Naples, Italy"],
    "CR": [["Smith, 2020, SCIENCE"]]
})

# TEST SR
try:
    result = metaTagExtraction(data, Field="SR")
    print("✅ SR OK")
    print(result[["SR"]].head())

except Exception as e:
    print("❌ SR ERROR")
    print(e)

# TEST AU_CO
try:
    result = metaTagExtraction(data, Field="AU_CO")
    print("✅ AU_CO OK")
    print(result[["AU_CO"]].head())

except Exception as e:
    print("❌ AU_CO ERROR")
    print(e)

# TEST CR_SO
try:
    result = metaTagExtraction(data, Field="CR_SO")
    print("✅ CR_SO OK")
    print(result[["CR_SO"]].head())

except Exception as e:
    print("❌ CR_SO ERROR")
    print(e)
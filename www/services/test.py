from api_retriever import retrieve
from standardizer import standardize
from validator import validate


# ---------------- PUBMED TEST ----------------

print("\nTesting PubMed pipeline...\n")

records = retrieve(
    query="machine learning",
    platform="pubmed",
    total=5
)

print(f"Records fetched: {len(records)}")

df = standardize(records, source="pubmed")
df = validate(df)

print(df.shape)
print(df.head())


# ---------------- OPENALEX TEST ----------------

print("\nTesting OpenAlex pipeline...\n")

records = retrieve(
    query="machine learning",
    platform="openalex",
    total=5
)

print(f"Records fetched: {len(records)}")

df = standardize(records, source="openalex")
df = validate(df)

print(df.shape)
print(df.head())
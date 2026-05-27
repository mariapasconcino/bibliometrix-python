"""
mappings.py
-----------
Mapping dictionaries for PubMed and OpenAlex API responses.

Each dictionary maps raw JSON field names (exactly as returned by the API)
to the standard WoS field tags used internally by Bibliometrix.
"""

# ---------------------------------------------------------------------------
# PubMed mapping
# Raw JSON field name → WoS tag
# ---------------------------------------------------------------------------

PUBMED_MAPPING = {
    "uid":             "UT",
    "title":           "TI",
    "fulljournalname": "SO",   # full name → journal source
    "source":          "JI",   # abbreviated name → ISO abbreviation
    "pubdate":         "PY",
    "volume":          "VL",
    "issue":           "IS",
    "lang":            "LA",
    "doctype":         "DT",
    "lastauthor":      "RP",
}

# Fields that need special parsing logic (handled in standardizer.py):
# "authors"    → AU, AF  (list of dicts, need to extract 'name' key)
# "articleids" → DI, PMID (list of dicts, need to match 'idtype')
# "pages"      → BP, EP  (single string like "123-145", need to split)
# "references" → CR      (list, needs formatting)

# Fields with no PubMed equivalent (standardizer.py fills these with [] or ""):
# AB  - abstract not returned by eSummary API
# C1  - affiliations not in eSummary
# DE  - author keywords not in eSummary
# ID  - Keywords Plus, WoS-exclusive, always []
# TC  - times cited not in eSummary, always 0
# SR  - calculated field, computed last

# ---------------------------------------------------------------------------
# OpenAlex mapping
# Raw JSON field name → WoS tag
# ---------------------------------------------------------------------------

OPENALEX_MAPPING = {
    "id":               "UT",
    "doi":              "DI",
    "title":            "TI",
    "publication_year": "PY",
    "language":         "LA",
    "cited_by_count":   "TC",
    "type":             "DT",
}

# Fields that need special parsing logic (handled in standardizer.py):
# "primary_location"       → SO, JI  (nested dict)
# "authorships"            → AU, AF, C1, RP  (list of dicts)
# "referenced_works"       → CR  (list of OpenAlex IDs, needs formatting)
# "keywords"               → DE  (list of dicts, extract 'display_name')
# "abstract_inverted_index"→ AB  (inverted index, needs reconstruction)
# "biblio"                 → VL, IS, BP, EP  (nested dict)

# Fields with no OpenAlex equivalent (standardizer.py fills these):
# ID   - Keywords Plus, WoS-exclusive, always []
# PMID - PubMed-exclusive, always ""
# DB   - not from API, we set this to "OPENALEX" ourselves
# SR   - calculated field, computed last
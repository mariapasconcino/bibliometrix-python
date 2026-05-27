"""
standardizer.py
---------------
Transform phase of the ETL pipeline.

Takes a list of raw dictionaries from api_retriever.py and converts
them into a pandas DataFrame with the standard WoS column schema.

Main entry point:
    standardize(records, source) → pd.DataFrame
"""

import pandas as pd
from mappings import PUBMED_MAPPING, OPENALEX_MAPPING


# NOTE: SR() is copied directly from www/services/metatagextraction.py
# rather than imported. This is intentional.
# metatagextraction.py uses a relative import (from .utils import *)
# which only works when the file is loaded as part of a package.
# When imported directly in a notebook or standalone script, Python
# doesn't know it's part of a package and crashes with:
# "attempted relative import with no known parent package"
# Copying the function here avoids that problem entirely.

def SR(M):
    listAU = M["AU"].apply(lambda l: [x.strip() for x in l])
    if M["DB"].iloc[0].lower() == "scopus":
        listAU = listAU.apply(lambda l: [x.replace(" ", ",").replace(",,", ",").replace(" ", "") for x in l])
    FirstAuthors = listAU.apply(lambda l: l[0] if len(l) > 0 else "NA").str.replace(",", " ")
    no_art = M["JI"] == ""
    M.loc[no_art, "JI"] = M.loc[no_art, "SO"]
    J9 = M["JI"].str.replace(".", " ", regex=False).str.strip()
    SR_col = FirstAuthors + ", " + M["PY"].astype(str) + ", " + J9
    M["SR_FULL"] = SR_col.str.replace(r"\s+", " ", regex=True)
    st = i = 0
    while st == 0:
        ind = SR_col.duplicated()
        if ind.any():
            i += 1
            SR_col[ind] = SR_col[ind] + "-" + chr(96 + i)
        else:
            st = 1
    M["SR"] = SR_col.str.replace(r"\s+", " ", regex=True)
    return M

def apply_mapping(record: dict, mapping: dict) -> dict:
    """
    Renames raw API field names to WoS tags using the mapping dictionary.
    Only processes fields that appear in the mapping.
    Returns a new dictionary with WoS tag keys.
    """
    result = {}
    for raw_field, wos_tag in mapping.items():
        result[wos_tag] = record.get(raw_field, "")
    return result


def parse_pubmed_authors(record: dict) -> list:
    """
    Extracts author names from PubMed's raw authors field.
    Returns a list of strings e.g. ["Hudelo J", "Garot J"]
    """
    authors = record.get("authors", [])
    result = []
    for author in authors:
        name = author.get("name", "")
        if name:
            result.append(name)
    return result


def parse_pubmed_articleids(record: dict) -> dict:
    """
    Extracts DOI and PMID from PubMed's raw articleids field.
    Returns a dict with keys DI and PMID.
    """
    articleids = record.get("articleids", [])
    result = {"DI": "", "PMID": ""}
    for item in articleids:
        idtype = item.get("idtype", "")
        value = item.get("value", "")
        if idtype == "doi":
            result["DI"] = value
        elif idtype == "pubmed":
            result["PMID"] = value
    return result


def parse_pubmed_pages(record: dict) -> dict:
    """
    Extracts beginning and end page from PubMed's raw pages field.
    Returns a dict with keys BP and EP.
    """
    pages = record.get("pages", "")
    result = {"BP": "", "EP": ""}
    if "-" in pages:
        parts = pages.split("-")
        result["BP"] = parts[0].strip()
        result["EP"] = parts[1].strip()
    else:
        result["BP"] = pages.strip()
    return result


def parse_pubmed_references(record: dict) -> list:
    """
    Extracts cited references (CR) from PubMed's raw references field.
    Returns a list of strings, one per reference.
    """
    references = record.get("references", [])
    result = []
    for ref in references:
        value = ref.get("refsource", "")
        if value:
            result.append(value)
    return result


def standardize_pubmed(record: dict) -> dict:
    """
    Converts a single raw PubMed record into a WoS-schema dictionary.
    Calls all parsing functions and fills missing fields with safe defaults.
    """
    # Step 1: rename simple fields
    result = apply_mapping(record, PUBMED_MAPPING)

    # LA comes as a list from PubMed e.g. ['eng'], extract first element
    la = record.get("lang", "")
    result["LA"] = la[0] if isinstance(la, list) and len(la) > 0 else ""

    # Step 2: handle complex fields
    result["AU"] = parse_pubmed_authors(record)
    result["AF"] = parse_pubmed_authors(record)
    result.update(parse_pubmed_articleids(record))
    result.update(parse_pubmed_pages(record))
    result["CR"] = parse_pubmed_references(record)

    # Step 3: fill missing fields with safe defaults
    result["AB"] = ""
    result["C1"] = []
    result["DE"] = []
    result["ID"] = []
    result["TC"] = 0
    result["DB"] = "PUBMED"
    result["SR"] = ""

    return result






def parse_openalex_location(record: dict) -> dict:
    """
    Extracts journal name and ISO abbreviation from OpenAlex's
    primary_location field.
    Returns a dict with keys SO and JI.
    """
    result = {"SO": "", "JI": ""}
    location = record.get("primary_location", {})
    if not location:
        return result
    source = location.get("source", {})
    if not source:
        return result
    name = source.get("display_name", "")
    result["SO"] = name.upper()
    result["JI"] = name
    return result


def parse_openalex_authorships(record: dict) -> dict:
    """
    Extracts authors, full names, affiliations and reprint author
    from OpenAlex's raw authorships field.
    Returns a dict with keys AU, AF, C1, RP.
    """
    authorships = record.get("authorships", [])
    result = {"AU": [], "AF": [], "C1": [], "RP": ""}

    for authorship in authorships:
        # AU — short display name
        display_name = authorship.get("author", {}).get("display_name", "")
        if display_name:
            result["AU"].append(display_name)

        # AF — raw author name as recorded in the paper
        raw_name = authorship.get("raw_author_name", "")
        if raw_name:
            result["AF"].append(raw_name)

        # C1 — all affiliation strings for this author
        affiliations = authorship.get("raw_affiliation_strings", [])
        result["C1"].extend(affiliations)

        # RP — corresponding author name + affiliation
        if authorship.get("is_corresponding", False):
            affiliations_str = "; ".join(affiliations)
            result["RP"] = f"{raw_name} (corresponding author), {affiliations_str}"

    return result


def parse_openalex_abstract(record: dict) -> str:
    """
    Reconstructs the abstract (AB) from OpenAlex's inverted index format.
    The inverted index maps each word to a list of positions.
    Returns the abstract as a plain string, or "" if missing.
    """
    inverted_index = record.get("abstract_inverted_index", None)
    if not inverted_index:
        return ""

    # find the total number of words
    max_position = 0
    for positions in inverted_index.values():
        for pos in positions:
            if pos > max_position:
                max_position = pos

    # place each word at its correct position
    words = [""] * (max_position + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word

    return " ".join(words)



def parse_openalex_biblio(record: dict) -> dict:
    """
    Extracts volume, issue, and page numbers from OpenAlex's biblio field.
    Returns a dict with keys VL, IS, BP, EP.
    """
    biblio = record.get("biblio", {})
    result = {
        "VL": biblio.get("volume", "") or "",
        "IS": biblio.get("issue", "") or "",
        "BP": biblio.get("first_page", "") or "",
        "EP": biblio.get("last_page", "") or "",
    }
    return result


def parse_openalex_keywords(record: dict) -> list:
    """
    Extracts author keywords (DE) from OpenAlex's keywords field.
    Returns a list of strings e.g. ["Python", "Machine learning"]
    """
    keywords = record.get("keywords", [])
    result = []
    for kw in keywords:
        name = kw.get("display_name", "")
        if name:
            result.append(name)
    return result


def parse_openalex_references(record: dict) -> list:
    """
    Extracts referenced works (CR) from OpenAlex's referenced_works field.
    Returns a list of OpenAlex IDs as strings.
    Note: these are not formatted WoS reference strings — they are
    OpenAlex URLs. Citation network features will have limited accuracy.
    """
    references = record.get("referenced_works", [])
    return [ref for ref in references if ref]


def standardize_openalex(record: dict) -> dict:
    """
    Converts a single raw OpenAlex record into a WoS-schema dictionary.
    Calls all parsing functions and fills missing fields with safe defaults.
    """
    # Step 1: rename simple fields
    result = apply_mapping(record, OPENALEX_MAPPING)

    # Step 2: handle complex fields
    result.update(parse_openalex_location(record))
    result.update(parse_openalex_authorships(record))
    result["AB"] = parse_openalex_abstract(record)
    result.update(parse_openalex_biblio(record))
    result["DE"] = parse_openalex_keywords(record)
    result["CR"] = parse_openalex_references(record)

    # DI — strip URL prefix and handle None
    doi = record.get("doi", "") or ""
    result["DI"] = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

    # PY — OpenAlex returns an integer, cast to string
    py = record.get("publication_year", "")
    result["PY"] = str(py) if py is not None else ""

    # Step 3: fill missing fields with safe defaults
    result["ID"] = []
    result["PMID"] = ""
    result["DB"] = "OPENALEX"
    result["SR"] = ""

    return result





def standardize(records: list, source: str) -> pd.DataFrame:
    """
    Main entry point for the standardizer.
    Takes a list of raw records from api_retriever.py and returns
    a pandas DataFrame with the standard WoS column schema.

    Args:
        records: list of raw dictionaries from api_retriever.py
        source: "pubmed" or "openalex"
    """
    standardized = []

    for record in records:
        if source == "pubmed":
            standardized.append(standardize_pubmed(record))
        elif source == "openalex":
            standardized.append(standardize_openalex(record))
        else:
            raise ValueError(f"Unsupported source: {source}. Choose 'pubmed' or 'openalex'.")

    df = pd.DataFrame(standardized)
    df = SR(df)
    return df
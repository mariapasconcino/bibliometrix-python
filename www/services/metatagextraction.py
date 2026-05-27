from .utils import *


# ---------------------------------------------------------------------------
# PATCH: normalize_c1()
# Normalizes the C1 (affiliation) column to always be list[str].
# C1 can arrive as:
#   - list[str]  → kept as-is
#   - str        → split on ";" (Scopus/PubMed style)
#   - NaN/None   → []
# This fixes AU_CO, AU1_CO, AU_UN which all iterate over C1 and crashed
# when C1 was a plain string (iterating over characters instead of affiliations).
# ---------------------------------------------------------------------------
def normalize_c1(value):
    if isinstance(value, list):
        return [x.strip() for x in value if isinstance(x, str) and x.strip()]
    if isinstance(value, str) and value.strip():
        return [x.strip() for x in value.split(";") if x.strip()]
    return []


# ---------------------------------------------------------------------------
# PATCH: normalize_cr()
# Normalizes the CR (cited references) column to always be list[str].
# CR can arrive as:
#   - list[str]  → kept as-is
#   - str        → split on ";"
#   - NaN/None   → []
# This fixes CR_AU and CR_SO which previously used `else []` fallback,
# silently dropping all references when CR was a semicolon-delimited string.
# ---------------------------------------------------------------------------
def normalize_cr(value):
    if isinstance(value, list):
        return [x.strip() for x in value if isinstance(x, str) and x.strip()]
    if isinstance(value, str) and value.strip():
        return [x.strip() for x in value.split(";") if x.strip()]
    return []


# ---------------------------------------------------------------------------
# PATCH: normalize_au()
# Normalizes the AU (authors) column to always be list[str].
# Same pattern as normalize_c1/normalize_cr.
# Used in SR() to avoid AttributeError when AU is a string.
# ---------------------------------------------------------------------------
def normalize_au(value):
    if isinstance(value, list):
        return [x.strip() for x in value if isinstance(x, str) and x.strip()]
    if isinstance(value, str) and value.strip():
        return [x.strip() for x in value.split(";") if x.strip()]
    return []


# ---------------------------------------------------------------------------
# PATCH: get_db()
# Safely reads the DB value from the DataFrame and normalizes it to uppercase.
# Previously each function did M["DB"].iloc[0].lower() == "scopus" etc.,
# which was inconsistent and fragile (mixed case, missing column crashes).
# Now every function uses get_db() for a single consistent comparison point.
# ---------------------------------------------------------------------------
def get_db(M):
    if "DB" not in M.columns or M.empty:
        return ""
    val = M["DB"].iloc[0]
    if not isinstance(val, str):
        return ""
    return val.strip().upper()


def metaTagExtraction(df, Field="AU_CO", sep=";", aff_disamb=False):
    """
    Extract metadata tags from a DataFrame based on the specified field.

    Args:
        df: A DataFrame object containing the data.
        Field: The field to extract metadata tags from.
        sep: The separator used to split the metadata tags.
        aff_disamb: A boolean value indicating whether to disambiguate affiliations.

    Returns:
        A DataFrame with the extracted metadata tags.
    """
    M = df.get()

    if Field == "SR":
        M = SR(M)

    if Field == "CR_AU":
        M = CR_AU(M)

    if Field == "CR_SO":
        M = CR_SO(M)

    if Field == "AU_CO":
        M = AU_CO(M)

    if Field == "AU1_CO":
        M = AU1_CO(M)

    if Field == "AU_UN":
        if aff_disamb:
            M = AU_UN(M, sep)
        else:
            # PATCH: guard against C1 being a list instead of a string.
            # Previously M["C1"].str.replace() crashed with AttributeError
            # when C1 contained lists (non-WoS sources).
            # Now we normalize C1 to a joined string before applying str ops.
            if "C1" in M.columns:
                c1_str = M["C1"].apply(
                    lambda x: "; ".join(x) if isinstance(x, list) else (x if isinstance(x, str) else "")
                )
                M["AU_UN"] = c1_str.str.replace(r"\[.*?\] ", "", regex=True)
            else:
                M["AU_UN"] = ""

            if "RP" in M.columns:
                rp_series = M["RP"].apply(
                    lambda x: x if isinstance(x, str) else ""
                )
                M["AU1_UN"] = rp_series.str.split(sep).apply(
                    lambda l: l[0].strip() if isinstance(l, list) and l else ""
                )
                ind = M["AU1_UN"].str.find("),")
                a = ind[ind > -1].index
                M.loc[a, "AU1_UN"] = M.loc[a, "AU1_UN"].apply(
                    lambda x: x[x.find("),") + 2:].strip()
                )
            else:
                M["AU1_UN"] = ""

    df.set(M)

    return df


def SR(M):
    # PATCH: normalize AU before processing.
    # Previously M["AU"] was used directly; if AU was a semicolon-delimited
    # string (Scopus/PubMed), .apply(lambda l: [x.strip() for x in l])
    # would iterate over characters instead of authors.
    M["AU"] = M["AU"].apply(normalize_au)

    listAU = M["AU"].apply(lambda l: [x.strip() for x in l])

    # PATCH: use get_db() for consistent, case-insensitive DB comparison.
    # Previously: M["DB"].iloc[0].lower() == "scopus"
    # This missed "SCOPUS", "Scopus", and any other casing variant.
    db = get_db(M)
    if db == "SCOPUS":
        listAU = listAU.apply(
            lambda l: [x.replace(" ", ",").replace(",,", ",").replace(" ", "") for x in l]
        )

    FirstAuthors = listAU.apply(lambda l: l[0] if len(l) > 0 else "NA").str.replace(",", " ")

    # PATCH: guard against missing JI column.
    if "JI" not in M.columns:
        M["JI"] = ""
    if "SO" not in M.columns:
        M["SO"] = ""

    no_art = M["JI"] == ""
    M.loc[no_art, "JI"] = M.loc[no_art, "SO"]
    J9 = M["JI"].str.replace(".", " ", regex=False).str.strip()

    # PATCH: guard against missing PY column.
    if "PY" not in M.columns:
        M["PY"] = ""

    SR = FirstAuthors + ", " + M["PY"].astype(str) + ", " + J9
    M["SR_FULL"] = SR.str.replace(r"\s+", " ", regex=True)

    st = i = 0
    while st == 0:
        ind = SR.duplicated()
        if ind.any():
            i += 1
            SR[ind] = SR[ind] + "-" + chr(96 + i)
        else:
            st = 1
    M["SR"] = SR.str.replace(r"\s+", " ", regex=True)

    return M


def CR_AU(M):
    # PATCH: normalize CR before processing.
    # Previously: lambda x: x if isinstance(x, list) else []
    # This silently dropped all references when CR was a semicolon string.
    # Now normalize_cr() handles list, str, and NaN correctly.
    M["CR"] = M["CR"].apply(normalize_cr)

    listCAU = M["CR"].apply(lambda l: [x for x in l if len(x) > 10])
    FCAU = listCAU.apply(lambda l: [x.split(",")[0].strip() for x in l])
    M["CR_AU"] = FCAU.apply(lambda l: ";".join(l))

    return M


def CR_SO(M):
    # PATCH: normalize CR before processing (same reason as CR_AU).
    M["CR"] = M["CR"].apply(normalize_cr)

    listCAU = M["CR"]

    # PATCH: use get_db() for consistent DB comparison.
    # Previously: M["DB"].iloc[0].upper() != "SCOPUS"
    # This treated every non-Scopus source (PubMed, Dimensions, OpenAlex)
    # as WoS and applied the wrong CR parsing format.
    # Now we explicitly check for known DB values.
    db = get_db(M)

    if db == "SCOPUS":
        # Scopus CR format: "Author, Journal, Year, Vol, Page"
        # source name is at index 0
        FCAU = listCAU.apply(
            lambda l: [x.split(",")[0].strip() for x in l if len(x.split(",")) > 2]
        )
    else:
        # WoS CR format: "Author, Year, Journal, Vol, Page"
        # source name is at index 2
        FCAU = listCAU.apply(
            lambda l: [x.split(",")[2].strip() for x in l if len(x.split(",")) > 2]
        )

    M["CR_SO"] = FCAU.apply(lambda l: ";".join(l) if l else None)

    return M


def AU_CO(M, log=False):
    with open("www/static/countries.txt", "r") as file:
        countries = file.read().splitlines()

    # PATCH: normalize C1 to list[str] before iterating.
    # Previously the loop did `for c1 in C1.iloc[i]` assuming C1 was always
    # a list. When C1 was a plain string (Scopus/PubMed), it iterated over
    # individual characters — no country was ever found.
    if "C1" not in M.columns:
        M["C1"] = [[] for _ in range(len(M))]
    if "RP" not in M.columns:
        M["RP"] = [None] * len(M)

    M["C1"] = M["C1"].apply(normalize_c1)
    M["AU_CO"] = None

    C1 = M["C1"].copy()

    for i in range(len(C1)):
        if not C1.iloc[i]:
            rp_val = M["RP"].iloc[i]
            if isinstance(rp_val, str) and rp_val.strip():
                C1.at[i] = [rp_val.strip()]
            elif isinstance(rp_val, list):
                C1.at[i] = [x for x in rp_val if isinstance(x, str) and x.strip()]
            else:
                C1.at[i] = []

    results = []
    for i in range(len(M)):
        countries_found = []
        for c1 in C1.iloc[i]:
            if pd.notna(c1):
                ind = [
                    c.upper() for c in countries
                    if re.search(r'\b' + re.escape(c.upper()) + r'\b',
                                 c1.split(",")[-1].strip().upper())
                ]
                countries_found.extend(ind)
        results.append(countries_found)

    M["AU_CO"] = results

    M["AU_CO"] = M["AU_CO"].apply(
        lambda cl: [
            c.replace("UNITED STATES", "USA")
             .replace("RUSSIAN FEDERATION", "RUSSIA")
             .replace("TAIWAN", "CHINA")
             .replace("ENGLAND", "UNITED KINGDOM")
             .replace("SCOTLAND", "UNITED KINGDOM")
             .replace("WALES", "UNITED KINGDOM")
             .replace("NORTH IRELAND", "UNITED KINGDOM")
            for c in cl
        ]
    )

    if log:
        with open("affiliations.txt", "w", encoding="utf-8") as file:
            for affiliation in M["AU_CO"]:
                file.write(f"{affiliation}\n")

    return M


def AU1_CO(M, log=False):
    with open("www/static/countries.txt", "r") as file:
        countries = file.read().splitlines()

    # PATCH: normalize C1 to list[str] (same reason as AU_CO).
    if "C1" not in M.columns:
        M["C1"] = [[] for _ in range(len(M))]
    if "RP" not in M.columns:
        M["RP"] = [None] * len(M)

    M["C1"] = M["C1"].apply(normalize_c1)
    M["AU1_CO"] = None

    C1 = M["C1"].copy()

    for i in range(len(C1)):
        if not C1.iloc[i]:
            rp_val = M["RP"].iloc[i]
            if isinstance(rp_val, str) and rp_val.strip():
                C1.at[i] = [rp_val.strip()]
            elif isinstance(rp_val, list):
                C1.at[i] = [x for x in rp_val if isinstance(x, str) and x.strip()]
            else:
                C1.at[i] = []

    results = []
    for i in range(len(M)):
        first_country = None
        for c1 in C1.iloc[i]:
            if pd.notna(c1):
                last_part = c1.split(",")[-1].strip().upper()
                for country in countries:
                    if re.search(r'\b' + re.escape(country.upper()) + r'\b', last_part):
                        first_country = country.upper()
                        break
            if first_country:
                break
        results.append(first_country)

    M["AU1_CO"] = results

    M["AU1_CO"] = M["AU1_CO"].apply(
        lambda country: country
            .replace("UNITED STATES", "USA")
            .replace("RUSSIAN FEDERATION", "RUSSIA")
            .replace("TAIWAN", "CHINA")
            .replace("ENGLAND", "UNITED KINGDOM")
            .replace("SCOTLAND", "UNITED KINGDOM")
            .replace("WALES", "UNITED KINGDOM")
            .replace("NORTH IRELAND", "UNITED KINGDOM")
        if pd.notna(country) else None
    )

    if log:
        with open("first_author_countries.txt", "w", encoding="utf-8") as file:
            for affiliation in M["AU1_CO"]:
                file.write(f"{affiliation}\n")

    return M


def AU_UN(M, sep):
    # PATCH: normalize C1 to list[str] before joining to string.
    # Previously C1.str operations crashed when C1 contained lists.
    if "C1" not in M.columns:
        M["C1"] = [[] for _ in range(len(M))]
    if "RP" not in M.columns:
        M["RP"] = [None] * len(M)

    M["C1"] = M["C1"].apply(normalize_c1)

    # Join normalized list back to string for str.replace / str.split ops below
    C1 = M["C1"].apply(lambda l: "; ".join(l) if l else "")
    C1 = C1.str.replace(r"\[.*?\] ", "", regex=True)

    rp_series = M["RP"].apply(
        lambda x: x if isinstance(x, str) else ("; ".join(x) if isinstance(x, list) else "")
    )
    indna = C1 == ""
    C1[indna] = rp_series[indna]
    C1 = C1.str.strip()
    listAFF = C1.str.split(sep)

    uTags = [
        "UNIV", "COLL", "SCH", "INST", "ACAD", "ECOLE", "CTR", "SCI",
        "CENTRE", "CENTER", "CENTRO", "HOSP", "ASSOC", "COUNCIL", "FONDAZ",
        "FOUNDAT", "ISTIT", "LAB", "TECH", "RES", "CNR", "ARCH", "SCUOLA",
        "PATENT OFF", "CENT LIB", "HEALTH", "NATL", "LIBRAR", "CLIN", "FDN",
        "OECD", "FAC", "WORLD BANK", "POLITECN", "INT MONETARY FUND",
        "CLIMA", "METEOR", "OFFICE", "ENVIR", "CONSORTIUM", "OBSERVAT",
        "AGRI", "MIT ", "INFN", "SUNY ",
    ]

    def extract_affiliations(l):
        if not isinstance(l, list):
            return "NOTREPORTED"
        index = []
        for item in l:
            item = item.replace("(REPRINT AUTHOR)", "")
            affL = item.split(",")
            indd = [i for i, aff in enumerate(affL) if any(tag in aff for tag in uTags)]
            if not indd:
                index.append("NOTREPORTED")
            elif any(char.isdigit() for char in affL[indd[0]]):
                index.append("NOTDECLARED")
            else:
                index.append(affL[indd[0]])
        return ";".join(index)

    M["AU_UN"] = listAFF.apply(extract_affiliations)

    # PATCH: fix DB check for WoS.
    # Previously: M["DB"].iloc[0] in ["ISI", "OPENALEX"]
    # "ISI" is an obsolete alias; "Web_of_Science" was never included.
    # Now we use get_db() and check all known WoS identifiers.
    db = get_db(M)
    WOS_DB_NAMES = {"WEB_OF_SCIENCE", "ISI", "WOS"}
    if db in WOS_DB_NAMES and "C3" in M.columns:
        mask = M["C3"].notna() & (M["C3"] != "")
        M.loc[mask, "AU_UN"] = M.loc[mask, "C3"]
        M["AU_UN"] = M["AU_UN"].str.split(sep).apply(
            lambda l: sep.join([x.strip() for x in l]) if isinstance(l, list) else l
        )

    M["AU_UN"] = (
        M["AU_UN"]
        .str.replace(r"\\&", "AND", regex=True)
        .str.replace("&", "AND", regex=False)
    )

    # Build AU1_UN from RP
    RP = M["RP"].apply(
        lambda x: x if isinstance(x, str) else ("; ".join(x) if isinstance(x, list) else "")
    )
    AFF = RP.str.replace(r"\[.*?\] ", "", regex=True)
    indna2 = AFF == ""
    AFF[indna2] = C1[indna2]
    AFF = AFF.str.strip()
    listAFF2 = AFF.str.split(sep)

    M["AU1_UN"] = listAFF2.apply(extract_affiliations)
    M["AU1_UN"] = (
        M["AU1_UN"]
        .str.replace(r"\\&", "AND", regex=True)
        .str.replace("&", "AND", regex=False)
    )

    M["AU_UN_NR"] = None
    listAFF3 = M["AU_UN"].str.split(sep)
    cont = listAFF3.apply(lambda l: [i for i, x in enumerate(l) if x == "NR"] if isinstance(l, list) else [])

    for i, indices in enumerate(cont):
        if indices:
            c1_list = listAFF.iloc[i]
            if isinstance(c1_list, list):
                M.at[i, "AU_UN_NR"] = ";".join([c1_list[j] for j in indices if j < len(c1_list)])

    M["AU_UN"] = M["AU_UN"].replace({"NOTDECLARED": None, "NOTREPORTED": None})
    M["AU_UN"] = M["AU_UN"].str.replace("NOTREPORTED;", "", regex=False).str.replace(";NOTREPORTED", "", regex=False)
    M["AU_UN"] = M["AU_UN"].str.replace("NOTDECLARED;", "", regex=False).str.replace("NOTDECLARED", "", regex=False)

    return M
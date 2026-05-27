# Bibliometrix-Python Codebase Audit

## Purpose
This document maps every file in services/ and functions/ to the columns it depends on and any hardcoded WoS logic it contains.
It is used to verify that our ETL pipeline produces all required columns and to track which files need patching.

---

## www/services/
1) what it does
2) dependencies
3) columns used
4) WoS-specific logic
5) issues found 
6) relevant for ETL: yes/no

### biblionetwork.py
1) Takes the bibliographic DataFrame and builds a matrix showing how items (authors,   sources, references, countries) are connected to each other. For example, two authors are "connected" if they cite the same references. It's the core function for generating all network analyses in the dashboard.
2) **utils.py, cocmatrix.py**.
3) **AU, CR, SO, ID, DE, DB** and derived ones.
4) It has **db_name == "SCOPUS"**.
5) If any of the above columns are absent (AU, CR, etc.), cocMatrix() will fail because it will try to read that column from the DataFrame without finding it. Python will throw a KeyError and the whole things crashes.
6) **Yes**. Our ETL is responsible for producing the DataFrame that gets fed into functions like this one, if it fails to include AU, CR or whatever other column in the output (even as an empty list []) this function crashes immediatly.

### cocmatrix.py
1) Takes the bibliographic DataFrame and a column name (like AU or CR), and builds a matrix where rows are articles and columns are unique items (authors, keywords, references etc.). Each cell is 1 if that article contains that item, 0 otherwise. It's the building block that biblionetwork.py calls to create all its networks.
2) **utils.py**.
3) **SR, CR, AU, ID, DE, TI, AB** and derived ones.
4) No explicit DB checks.
5) It will crash if SR is missing (M.index = M["SR"] throws a KeyError immediately) and if the requested Field column is missing, it just prints a message and returns None (which then causes biblionetwork.py to crash when it tries to use that None because there is no error handling between the two functions: biblionetwork.py calls cocMatrix() and stores the result in WA; if the column is missing, cocMatrix() prints a message and returns None; biblionetwork.py doesn't check if WA is None — it immediately uses it in crossprod(WA, WA); crossprod tries to do matrix multiplication on None, which crashes with a TypeError).
6) **Yes**, SR must be present and correctly computed.

### couplingmap.py
1)  Builds and visualizes a "coupling map" — a bubble chart where clusters of related documents, authors, or sources are plotted by centrality vs impact. It combines network analysis, citation scoring, and cluster labeling into one visualization. It's one of the more complex files — it orchestrates many other services together.
2) **utils.py, cocmatrix.py, biblionetwork.py, termextraction.py, networkplot.py, histnetwork.py, metatagextraction.py, tabletag.py**.
3) **SR, AU, TC, DI, PY, DE, ID, TI, AB, SO**.
4) No explicit DB checks.
5) It will crash if SR (crashes immediately at metaTagExtraction(df, "SR")), TC (crashes in localCitations() at M['TC'].fillna(0)), AU (crashes in localCitations() at M['AU'].explode()), DI and PY (crashes when building the LCS output DataFrame) are missing.
6) **Yes**. SR, TC, AU, DI, PY, SO must all be present and correctly typed.

### format_functions.py
1) It takes raw bibliographic data from any supported source (WoS, Scopus, PubMed, Dimensions, Lens, Cochrane) and converts it into a standardized dictionary with WoS-style column names. It has one formatting function per column (format_au_column, format_cr_column etc.) and a main entry point process_single_file() that calls all of them and assembles the final output. **This is the most important file for our ETL, it's basically a rough draft of what the ETL needs to be.** The project specs asks us to build a clean, robust version of what this file is already attempting. So rather than starting from scratch, for our ETL we should: study this file carefully to understand the existing column mappings; replace the fragile direct access (entry['Abstract']) with safe .get() calls; ensure null handling throughout (empty string "" or [] instead of None); make sure SR is always correctly computed.
2) **utils.py, parsers.py**.
3) **AB, AF, AU, AU_UN, AU1_UN, BP, EP, CR, C1, DB, DE, DI, DT, EM, FU, FX, IS, JI, ID, LA, OA, OI, PMID, PU, PY, RP, SC, SN, SO, SR, TC, TI, UT, VL**
4) **Yes**, every single formatting function branches on source (Web_of_Science, Scopus, PubMed, Dimensions, The_Lens, Cochrane) and file_type. This is basically the dispatcher that the specs asks us to build.
5) Yes, several functions access raw source columns directly without safety checks (e.g. entry['Abstract'], entry['Author full names']) which will crash with a KeyError if the raw file has different column names than expected.
6) **Yes**.

### histnetwork.py
1) Builds a historical citation network. It figures out which papers in the dataset cite other papers in the same dataset (called "Local Citation Score" or LCS). It has two separate implementations: one for WoS and one for Scopus, and returns a network matrix plus citation statistics.
2) **utils.py, cocmatrix.py**.
3) **DB, DI, CR, TC, PY, SR, SR_FULL, TI, DE, ID, AU, BP, EP, LCS**
4) **Yes**. It explicitly checks **db == "Web_of_Science"** or **db == "Scopus"** and calls completely different functions for each. If DB contains anything else (e.g. "PUBMED", "DIMENSIONS"), it prints "Database not compatible" and returns None, meaning it silently fails for any source other than WoS and Scopus.
5) It will crash if: CR is missing (returns None immediately); SR_FULL is missing (crashes in the WoS branch when building LABEL); PY, AU, BP, EP are missing (crashes in the Scopus branch during merges).
6) **Yes**. DB values must exactly match "Web_of_Science" or "Scopus" for this function to work at all, and CR, PY, SR, TC must all be correctly populated.

### histplot.py
1) Takes the output of histNetwork() and draws a historical citation network chart: papers are plotted as bubbles positioned by publication year on the x-axis, with edges showing which papers cite which. It's purely a visualization function, it doesn't touch the raw DataFrame directly.
2) **utils.py, networkplot.py**
3) **None directly** from the bibliographic DataFrame, it only reads from histResults which is the output of histNetwork(). Internally it uses histResults['NetMatrix'] and histResults['histData'] which contain Paper, Title, Author_Keywords, KeywordsPlus.
4) **No**.
5) **Only indirectly**, if histNetwork() failed to produce a proper NetMatrix or histData, this function will crash. But that's histNetwork()'s problem, not yours.
6) **No**. This is a pure visualization layer, it never reads our standardized DataFrame directly.

### htmldownload.py
1) Takes an HTML file, renders it to a PNG screenshot using a headless Chrome browser, then overlays the bibliometrix logo on the bottom right. It's a utility for exporting visualizations as images.
2) **utils.py**.
3) **None**.
4) **No**.
5) **No**.
6) **No**.

### igraph2vis.py
1) Converts an igraph graph object into an interactive vis.js network visualization, saves it as an HTML file, and returns the path. It handles node sizing, coloring by cluster, edge styling, and label overlap removal. Pure visualization utility.
2) **utils.py**.
3) **None**.
4) **No**.
5) **No**.
6) **No**.

### metatagextraction.py
1) Computes derived columns that other functions need but that aren't in the raw data. Given a Field parameter, it generates one of: SR (short reference key), CR_AU (authors from cited references), CR_SO (sources from cited references), AU_CO (countries from affiliations), AU1_CO (first author's country), AU_UN (universities from affiliations). This is the file that generates most of the derived columns we shouldn't be our responsability based on the project specs (**must ask**).
2) **utils.py**.
3) **AU, JI, SO, PY, DB, CR, C1, RP**.
4) **Yes**, in multiple places: SR() checks db == "scopus" to format author names differently; CR_SO() checks db != "SCOPUS" to parse references differently; AU_UN() checks db in ["ISI", "OPENALEX"] for university extraction.
5) SR() crashes if AU, JI, SO, or PY are missing. AU_CO() and AU1_CO() crash if C1 and RP are both missing. CR_AU() and CR_SO() crash if CR is missing or not a list.
6) **Yes**. AU, JI, SO, PY, C1, RP must all be present and correctly typed for SR generation to work
**N.B.** This file is what *generates SR*, which is in our target schema and is required by almost every other function. So while we don't need to generate AU_CO, CR_AU etc., we do need to ensure AU, JI, SO, PY, C1, RP are correctly populated so that SR() inside this file can run without crashing. Our ETL feeds this function indirectly.

### networkplot.py
1) Takes a co-occurrence/coupling matrix (the output of biblionetwork.py) and builds an interactive network graph from it — handling clustering, layout, node sizing, edge weights, and color assignment. It's the core visualization engine for all network analyses in the dashboard.
2) **utils.py, cocmatrix.py**.
3) None directly from the bibliographic DataFrame, it only receives a pre-built NetMatrix as input.
4) **No**.
5) **No**.
6) **No**. If our ETL produces correct columns so that biblionetwork.py and cocmatrix.py can build the matrix successfully, this function will work automatically.

### parsers.py
1) Contains three raw file parsers, one each for Web of Science (parse_wos_data), PubMed (parse_pubmed_data), and Cochrane (parse_cochrane_data). Each parser reads a raw text file line by line and returns a list of dictionaries, one per article, with raw field tags as keys. This is the **Extract phase of the ETL**, it turns raw files into Python data structures before any column renaming or type enforcement happens.
2) **utils.py**.
3) **None**, these functions produce raw dictionaries from files, they don't read a DataFrame.
4) **Yes**, parse_wos_data is specifically built around the WoS plaintext format (two-letter tags, ER record separators, continuation lines starting with two spaces). The other parsers handle their own formats independently.
5) **No**. Even though parse_pubmed_data has a minor bug, if a continuation line appears before any key is set, key will be undefined and it will crash with a NameError.
6) **Yes**,  these are our Extract phase building blocks, especially parse_wos_data and parse_pubmed_data.

### plotlydownload.py
1) Takes an existing Plotly figure, adds the bibliometrix logo and a title, scales it up to high resolution, and exports it as a PNG image. Pure export utility.
2) **utils.py**.
3) **None**.
4) **No**.
5) **No**.
6) **No**.

### savereport.py
1) Saves analysis results (tables and plots) into a formatted Excel file with multiple sheets. Each sheet contains a styled table and the corresponding visualization. It's the reporting/export layer of the dashboard.
2) **utils.py, plotlydownload.py, htmldownload.py**.
3) **None**.
4) **No**.
5) **No**.
6) **No**.

### tabletag.py
1) Takes a specified column from the DataFrame, extracts all individual terms from it, counts their frequency, and returns a sorted dictionary of term → count. Used for word frequency analysis, keyword counts, citation counts etc. For AB and TI fields it first runs text mining to extract meaningful terms before counting.
2) **utils.py, termextraction.py**.
3) **SR, CR, DE, ID, C1, AB, TI (whichever is passed as tag parameter)**
4) **No** explicit DB checks.
5) If SR is missing it crashes immediately on drop_duplicates(subset=["SR"]); if whatever column is passes as tag is missing it crashes when trying to process it.
6) **Yes**, SR must always be present and all the tag columns (CR, DE, ID, AB, TI, C1) must exist and contain properly formatted lists for this function to work correctly.
   
### termextraction.py
1) Takes a text column (TI or AB), cleans it, removes stopwords, optionally applies stemming, and extracts n-grams using scikit-learn's CountVectorizer. Stores the result as a new column TI_TM or AB_TM. Called by tabletag.py before word frequency counting.
2) **utils.py**.
3) **TI** (default), **AB** (passed in by tabletag.py).
4) **No**
5) It crashes at M[field].astype(str) if whichever column is passed as field is absent.
6) **Yes**, both TI and AB must be present and populated as strings.

### thematicmap.py
1) Builds a thematic map, a bubble chart plotting research clusters by their "centrality" vs "density". It combines keyword co-occurrence network analysis, community detection, and cluster characterization into one visualization. One of the most complex files in the codebase, it orchestrates biblionetwork, termextraction, and networkplot together.
2) **utils.py, igraph2vis.py, termextraction.py, biblionetwork.py**.
3) **ID, DE, TI, AB, SR, TC, PY, DI, AU, SO**.
4) **No** explicit DB check, but heavily assumes WoS-style keyword fields (ID, DE) are properly populated.
5) If SR is missing, it crashes in cluster_assignment() immediately. If TC or PY missing, it crashes in cluster_assignment() when computing TCpY. If ID or DE missing, it crashes when building the network matrix via biblionetwork().
6) **Yes**. ID, DE, TC, PY, DI, AU, SO, SR must all be present and correctly populated

### utils.py
1) Central imports file for the entire services layer — every other service file starts with from .utils import *. It also defines two important shared things: the columns list (the master list of all expected DataFrame columns) and the ICONS dictionary for the UI. Think of it as the shared foundation the whole codebase builds on.
2) //
3) Defines the master columns list: AB, AF, AU, AU1_UN, AU_UN, BP, C1, CR, DB, DE, DI, DT, EM, EP, FU, FX, ID, IS, JI, LA, OA, OI, PMID, PU, PY, RP, SC, SN, SO, SR, TC, TI, UT, VL.
4) **No**.
5) **No**, it's an imports file.
6) **Yes**. This columns list is used in format_functions.py to add extra columns to each entry, so our ETL output must at minimum cover what's in the target schema.
**N.B.** The columns list defined here is our ground truth for what columns the codebase expects. Cross-referencing it with the target schema from the exam spec:
- Columns in utils.py but not in the target schema are AU1_UN, AU_UN, EM, FU, FX, OA, OI, PU, SC, SN. These are extra columns the codebase uses but our ETL doesn't need to guarantee;
- Column in the target schema but not in utils.py is SR_FULL, generated by metatagextraction.py as a derived column.

## Master Column Dependency Table — services/

### Columns from target schema

| Column | Used by |
|--------|---------|
| `DB` | biblionetwork, histnetwork, metatagextraction, cocmatrix |
| `SR` | cocmatrix, histnetwork, tabletag, thematicmap, metatagextraction |
| `AU` | biblionetwork, histnetwork, metatagextraction, thematicmap |
| `CR` | biblionetwork, cocmatrix, histnetwork, metatagextraction |
| `TI` | histnetwork, termextraction, thematicmap |
| `AB` | termextraction, thematicmap |
| `DE` | biblionetwork, thematicmap |
| `ID` | biblionetwork, thematicmap |
| `SO` | biblionetwork, histnetwork, metatagextraction |
| `JI` | metatagextraction |
| `PY` | histnetwork, thematicmap, metatagextraction |
| `TC` | histnetwork, thematicmap |
| `DI` | histnetwork, thematicmap |
| `C1` | metatagextraction |
| `RP` | metatagextraction |
| `AF` | format_functions |
| `BP` | histnetwork |
| `EP` | histnetwork |
| `VL` | format_functions |
| `IS` | format_functions |
| `LA` | format_functions |
| `DT` | format_functions |
| `PMID` | format_functions |
| `UT` | format_functions |


### Key takeaways

- `SR` is the most critical column — used by almost everything, computed from `AU`, `JI`, `PY`, `SO`
- `DB` must exactly match `"Web_of_Science"` or `"Scopus"` where branch logic exists
- `CR` must be a parsed Python list, not a raw semicolon-separated string
- `AU` must also be a parsed Python list
- `SR`, `TC`, `PY` have no crash protection — must always be present and correctly typed


---

## functions/
1) what it does
2) dependencies
3) columns used
4) WoS-specific logic
5) issues found 
6) relevant for ETL: yes/no



### get_affiliationproductionovertime.py
1) Counts cumulative publications per institution over time and draws a line chart for the top-k institutions.
2) **www.services**.
3) **AU_UN**, **PY**.
4) **Indirectly yes**: the function itself has no explicit WoS condition, but it depends on `AU_UN`, which is an internal/derived affiliation column usually built during WoS-oriented preprocessing.
5) Crashes if `AU_UN` is a plain string instead of a list, or if `PY` contains nulls.
6) **Yes**. `AU_UN` must be a `list[str]` per row, `PY` must be non-null and numeric. The ETL must build `AU_UN` from `C1` for non-WoS sources.

### get_annualproduction.py
1) Counts how many papers were published each year and draws a line chart.
2) **www.services**.
3) **PY**.
4) **No**.
5) Crashes if `PY` is missing, non-numeric, or contains nulls.
6) **Yes**. `PY` must be present, non-null, and numeric.


### get_authorlocalimpact.py
1) Calculates impact scores (h-index, g-index, m-index, total citations) for each author and draws a bubble chart of the top authors.
2) **www.services**.
3) **AU**, **TC**, **PY**.
4) **No**.
5) Crashes if `AU` is not a list. Index calculations may produce wrong results due to incorrect use of `transform`.
6) **Yes**. `AU` must be a `list[str]`, `TC` and `PY` must be non-null and numeric.


### get_authorproductionovertime.py
1) Counts publications and citations per author per year and draws a scatter plot for the top-k authors.
2) **www.services**.
3) **AU**, **PY**, **TC** (core); **TI**, **SO**, **DI** (secondary — used for the document table, missing ones handled with a warning).
4) **No**, but the fallback author splitting uses a comma which is WoS-specific.
5) Wrong author names for non-WoS sources due to comma-based splitting. Missing `DI` silently returns an empty document table.
6) **Yes**. `AU` must be a `list[str]`, `PY` and `TC` must be numeric, `TI`, `SO`, `DI` must be present as strings.


### get_averagecitations.py
1) Calculates average citations per year and draws a line chart.
2) **www.services**.
3) **PY**, **TC**.
4) **No**.
5) Crashes if `PY` or `TC` are missing or non-numeric. Division by zero possible if `PY` equals the current year.
6) **Yes**. `PY` and `TC` must be present, non-null, and numeric.


### get_bradfordlaw.py
1) Applies Bradford's Law to rank journals by publications, divides them into three zones, and draws a log-scale chart highlighting the core journals.
2) **www.services**.
3) **SO**.
4) **No**.
5) Crashes if `SO` is missing. Null values in `SO` are silently ignored, potentially skewing zone boundaries.
6) **Yes**. `SO` must be present, non-null, and a string.


### get_citedcountries.py
1) Ranks countries by total or average citations and draws a dot chart of the top-k countries.
2) **www.services**.
3) **TC** (core); **C1** or **RP** (secondary — needed by `metaTagExtraction` to extract the country).
4) **Yes**. `metaTagExtraction` is built for WoS-style affiliation strings.
5) If `C1` or `RP` are missing or wrongly formatted, the chart will be empty with no clear error. `TC` non-numeric values will cause a crash.
6) **Yes**. `TC` must be numeric and non-null. `C1` or `RP` must be populated correctly for country extraction to work.


### get_citeddocuments.py
1) Ranks papers by total citations or citations per year and draws a dot chart of the top-k documents.
2) **www.services**.
3) **SR**, **TC**, **PY** (core); **DI** (secondary — included in the output table).
4) **No**, but `SR` is expected in WoS format.
5) Empty chart with no error if `SR` is missing. Crashes if `TC` or `PY` are non-numeric. Division by zero possible if `PY` equals current year.
6) **Yes**. `SR` must be correctly built by the ETL, `TC` and `PY` must be numeric, `DI` should be present as a string.


### get_clusteringcoupling.py
1) Groups papers or authors into clusters based on shared references or keywords and draws an interactive network. Saves the result as an HTML file.
2) **www.services**; **couplingMap**, **avoid_net_overlaps**.
3) **None directly** — all column access is delegated to `couplingMap`.
4) **Yes**. `couplingMap` is built for WoS-style data, especially `SR` and `CR`.
5) No validation on the network returned by `couplingMap` — a broken network causes a hard crash. Temporary HTML file is never deleted.
6) **Indirect**. The ETL must ensure `SR`, `CR`, `AU`, `TC`, `PY`, `DE`, `ID` are correctly formatted for `couplingMap` to work.

### get_co_occurence_network.py
1) Builds a word or keyword co-occurrence network, plus a density heatmap, a statistics table, and a degree distribution plot.
2) **www.services**; **biblionetwork**, **network_plot**, **term_extraction**, **cocMatrix**, **avoid_net_overlaps**, **field_by_year**.
3) **None directly** — all column access delegated to internal functions. **PY** is accessed directly inside `field_by_year`.
4) **Yes**. Field names `ID`, `DE`, `TI`, `AB`, `WC` are WoS tags — non-WoS sources will produce an empty network.
5) If no field condition matches, the function silently returns nothing. Cluster colors are random on every run. Temporary HTML file is never deleted.
6) **Indirect**. The ETL must ensure `ID`, `DE`, `TI`, `AB`, `WC`, and `PY` are all present and correctly formatted.

### get_cocitation.py
1) Builds a co-citation network — meaning it finds which references, authors, or sources are cited together most often across papers, and draws an interactive network where each bubble is a reference/author/source and lines show how often they are cited together. Also produces a density heatmap, a cluster statistics table, and a degree distribution plot.
2) **www.services**.
3) **None directly** — all column access is delegated to `biblionetwork` and `metaTagExtraction`. `CR`, `CR_AU`, and `CR_SO` are checked for existence but not read directly.
4) **Yes**. `biblionetwork` and `metaTagExtraction` are built for WoS-style reference strings. Non-WoS sources with differently formatted references will produce empty or broken networks.
5) If `biblionetwork` returns an empty network the function crashes with no clear error. Cluster colors are randomly generated on every run. Temporary HTML file is never deleted.
6) **Indirect**. The ETL must ensure `CR` is present as a properly split list of reference strings, and `CR_AU`/`CR_SO` can be derived from it if needed.

### get_collaborationnetwork.py
1) Generates a collaboration network between authors, universities, or countries from a bibliographic DataFrame. It builds a graph via biblionetwork(), then produces four outputs: an interactive PyVis HTML network, a density heatmap, a cluster statistics table, and a normalized degree plot.
2) **www.services**
3) **AU**, then AU_UN, AU_CO.
4) **Yes**. There are two: metaTagExtraction() is called to derive AU_UN and AU_CO, this function is known to have hardcoded WoS parsing logic (affiliation string formats, country extraction patterns), so if affiliations from Scopus/PubMed are formatted differently it will silently produce empty or wrong values; biblionetwork() likely expects AU, AU_UN, AU_CO in WoS delimiter/format (semicolon-separated strings or lists).
5) **Yes**, metaTagExtraction() has hardcoded WoS affiliation parsing, so AU_UN and AU_CO will silently produce empty or wrong values for non-WoS sources.
6) **Indirectly**. The function itself is downstream of the ETL, but the pipeline must guarantee that AU is a proper list[str] and C1 is a list[str] with standardized affiliation strings so metaTagExtraction() can correctly extract AU_UN and AU_CO.

### get_correspondingauthorcountries.py
1) Extracts the corresponding author's country (AU1_CO) and all author countries (AU_CO) via metaTagExtraction(), then counts articles, single-country publications (SCP), and multi-country publications (MCP) per country. Returns a horizontal bar chart and a summary table.
2) **www.services**
3) AU1_CO (derived), AU_CO (derived), AU, C1, RP (implicitly required by metaTagExtraction()).
4) **Yes**. Both metaTagExtraction(Field="AU_CO") and metaTagExtraction(Field="AU1_CO") rely on WoS-style affiliation parsing of C1 and RP, as flagged in metatagextraction.py. Non-WoS sources will silently produce empty or wrong country values.
5) Issues: data.dropna(subset=["AU1_CO", "AU_CO"]) silently drops all rows if metaTagExtraction() fails to parse affiliations from non-WoS sources, producing an empty DataFrame with no error; no validation that C1 or RP exist before calling metaTagExtraction(), mirroring the crash pattern flagged in metatagextraction.py; top_k_countries is applied after sorting but the earlier top_country_names already takes all countries — the filtering step is redundant and misleading.
6) **Yes**. C1 and RP must be present and correctly formatted as list[str] with standardized affiliation strings so metaTagExtraction() can correctly derive AU_CO and AU1_CO. Without this, the function silently returns an empty result.

### get_countriesproduction.py
1) Extracts author countries via metaTagExtraction(), counts publication frequency per country, downloads world boundary geodata, and produces an interactive choropleth map and a summary table of scientific production by country.
2) **www.services**
3) AU_CO (derived), C1 (implicitly required by metaTagExtraction()).
4) **Yes**. metaTagExtraction(Field="AU_CO") relies on WoS-style affiliation parsing of C1, as flagged in metatagextraction.py.
5) No validation that C1 exists before calling metaTagExtraction(), mirroring the crash pattern flagged in metatagextraction.py. Country name normalization only corrects "USA" → "UNITED STATES OF AMERICA"; all other country name mismatches between the source data and the shapefile silently result in unmatched rows and zero counts. dropna is never called on AU_CO after explode(), so empty list entries produce NaN rows that pollute the country counts.
6) **Yes**. C1 must be present and correctly formatted as list[str] with standardized affiliation strings so metaTagExtraction() can correctly derive AU_CO. Country name formatting in C1 should also conform to WoS conventions to maximize matches against the shapefile.

### get_countriesproductionovertime.py
1) Extracts author countries via metaTagExtraction(), pairs each country with its publication year, computes cumulative article counts over time, and returns a line chart of the top-k countries' production over time plus the underlying DataFrame.
2) **www.services**.
3) AU_CO (derived), PY, C1 (implicitly required by metaTagExtraction())
4) **Yes**. metaTagExtraction(Field="AU_CO") relies on WoS-style affiliation parsing of C1, as flagged in metatagextraction.py. Non-WoS sources will silently produce empty or wrong country values.
5) Issues: no validation that C1 or PY exist before use, mirroring the crash pattern flagged in metatagextraction.py and thematicmap.py; years = data["PY"].repeat(nAFF).values[:len(affiliations)] silently misaligns years with affiliations if any AU_CO entry was NaN and got dropped by dropna() — the repeat is based on the full DataFrame length but AFF has already dropped rows; PY is never cast to a numeric type before astype(int) — if PY contains empty strings (as our ETL schema allows), this will crash.
6) **Yes**. C1 must be present and correctly formatted as list[str] so metaTagExtraction() can derive AU_CO. PY must be present, non-empty, and castable to integer for the year alignment logic to work correctly.


### get_data.py
1) Handles file upload from the Shiny dashboard UI. Depending on the selected mode, it processes one or more bibliographic files via biblio_json() or process_multiple_files(), loads the result into the reactive DataFrame df, and returns a status message to display in the UI.
2) **www.services**.
3) **No**.
4) **Indirectly**. biblio_json() and process_multiple_files() are the functions that actually parse and standardize the data — if those have WoS-specific assumptions (as flagged in parsers.py), the DataFrame loaded here will reflect those issues.
5) //
6) **Yes**. This is the entry point where our ETL must be plugged in. The "1B" path in particular must be routed through the standardization pipeline rather than calling pd.read_excel() directly, to ensure all downstream functions receive a correctly typed and validated DataFrame.

### get_database.py
1) Maps the user's UI selection to a human-readable database name string. Reads two Shiny input controls, input.select() (which tab is active) and input.database() (which source was chosen), and returns a plain string like "Web of Science" or "Scopus".
2) **www.services**.
3) **No**.
4) **None directly**. However this function is the gatekeeper that sets the DB value downstream. The string it returns must match whatever the ETL pipeline uses as the DB column value.
5) Two: DB value mismatch, the exam spec requires DB to hold standardised identifiers like "WEB_OF_SCIENCE" or "SCOPUS" while this function returns display strings ("Web of Science", "Scopus"), which are not the same - if DB is populated from this output, the contract is broken; UnboundLocalError risk, if input.select() returns anything outside "1A", "1B", "1C", the function reaches return database without ever assigning it, so it needs an else branch or a default.
6) **Yes**. Either this function's return values must be updated to match the schema DB identifiers, or the ETL Transform phase must normalise the returned string into the correct DB value before writing to the DataFrame.

### get_factorialanalysis.py
1) Builds a 2D interactive word map for conceptual structure analysis. It takes a DataFrame and a field (ID, DE, TI, AB), constructs a document-term matrix, runs a dimensionality reduction method (MCA, CA, or MDS), clusters the resulting term coordinates with hierarchical clustering, and returns an annotated Plotly scatter figure plus coordinate/cluster DataFrames. Also contains helpers: _to_seq (flatten values to list), eig_correction (Benzecri eigenvalue correction), avoidOverlaps (label deduplication — currently commented out), and assign_consistent_colors.
2) **www.services**.
3) **ID, DE, TI, AB**.
4) field="ID" default. ID (Keywords Plus) is a WoS-exclusive field — it does not exist in Scopus, PubMed, or Dimensions exports. Using ID as the default silently produces an empty or broken analysis on non-WoS data.
5) //
6) **Yes**. The ETL must ensure that: ID is a list[str] (WoS Keywords Plus) and dor non-WoS sources that lack ID, populate it as [] per the null contract — but also ensure the UI defaults field to DE (author keywords) for those sources, since an all-empty ID column will produce no usable analysis; DE, TI, AB are correctly typed (list[str] for DE, str for TI/AB).

### get_filters.py
1) Two functions. get_filters() enriches the DataFrame with computed filter metadata: min/max publication year, average citations per year, and Bradford's Law zone assignment per source journal. get_filtered_table() applies user-driven UI filters (year range, language, document type, avg citations, Bradford zone) to the enriched DataFrame, then passes the result to get_table() for display.
2) **www.services**.
3) **PY, TC, SO, LA, DT**.
4) **Yes**. LA and DT value sets are implicitly WoS-formatted. The UI populates filter options from whatever values exist in these columns. WoS uses "English" and "Article"; Scopus may use "English" but "Journal Article" for DT. If not normalised by ETL, the filter checkboxes will show mixed values and users may filter out valid records unintentionally. || Bradford zone logic assumes SO is a clean, standardised journal name. WoS and Scopus capitalise journal names differently, so the same journal can appear as two separate sources, splitting its frequency and producing wrong zone assignments.
5) Division by zero in Average_Citations_Per_Year. If PY == current_year, Years_Since_Publication = 1 — safe. But if PY > current_year (malformed data), the denominator goes negative. No guard exists. ETL should clamp PY to <= current_year. || TC nulls not handled. If TC contains NaN (not coerced to 0 by ETL), Average_Citations_Per_Year will be NaN, silently breaking the citations slider filter in get_filtered_table().
6) **Yes**. The ETL must: Cast TC to int, nulls → 0 || Cast PY to int, no nulls, clamped to valid range || Normalise SO to a consistent casing (uppercase) across sources || Normalise DT to a controlled vocabulary (e.g. "Article", "Review") so UI filters work identically regardless of source || Normalise LA to a consistent format (e.g. "ENGLISH").

### get_frequentwords.py
1) Two functions. get_frequent_words() produces a lollipop scatter chart and full frequency table of the most common words/keywords in a chosen field. It supports n-grams (for TI/AB), custom stopword removal, and synonym merging. table_tag() is the core extraction engine: it deduplicates by SR, routes to either term_extraction() (for free text fields TI/AB) or direct column access (for keyword fields DE/ID), then counts terms using Counter.
2) **www.services**.
3) SR, and one of DE, ID, TI, AB depending on word_type
4) **Yes**. ID (Keywords Plus) is WoS-exclusive. Selecting word_type="ID" on non-WoS data will operate on an empty or absent column with no error. || SR deduplication assumes SR is always populated. SR is a calculated field ("FirstAuthor, Year, Journal") generated by the WoS pipeline. If ETL does not produce it, drop_duplicates(subset='SR') will raise a KeyError. || eval(x) on DE/ID strings assumes the column was serialised as a Python list literal (e.g. "['kw1', 'kw2']"), which is a WoS/internal serialisation convention. Scopus CSV exports use semicolon-delimited strings, causing eval() to raise a SyntaxError or return the wrong structure.
5) remove_terms only applied for DE/ID, not for TI/AB. The guard if remove_terms and tag in ['DE', 'ID'] means stopword removal is silently skipped when analysing titles or abstracts, which is likely unintentional. || SR missing crashes silently. If SR is absent, drop_duplicates(subset='SR') raises KeyError with no informative message to the user.
6) **Yes**. The ETL must: Populate SR for all rows (non-empty string). || Ensure DE and ID are list[str], not raw strings — this eliminates the eval() hazard entirely. || Ensure ID is [] for non-WoS sources so the function degrades gracefully rather than crashing. || TI and AB must be str, not NaN/None.

### get_historiograph.py
1) Builds an interactive historiographic network map showing citation relationships between key papers over time. It calls metaTagExtraction() and histNetwork() from services to construct the citation graph, then histPlot() for the initial layout. It then rebuilds the graph with networkx, optionally removes isolated nodes, positions nodes on a timeline (x = year, y = cluster), computes node sizes from local citation scores (LCS), and renders an interactive pyvis HTML network saved to a temp file. Returns the plot object, a metadata DataFrame, and the temp HTML filename.
2) **www.services**.
3) **SR, CR, DOI, TI, DE, ID, PY**.
4) **Yes**. histNetwork() parses CR using WoS reference string format ("Author, Year, Journal, Vol, Page"). This is the most WoS-specific dependency in the entire codebase. Non-WoS CR strings will produce zero or wrong citation matches, resulting in an empty or disconnected graph. || metaTagExtraction(df, "SR") regenerates SR from WoS-style author/year/journal fields. If SR was not correctly populated by ETL, this call may produce malformed node identifiers that break edge matching. || node_label="ID" and node_label="DE" are swapped. The code maps "ID" → row.get("Author_Keywords") and "DE" → row.get("KeywordsPlus"), which is the reverse of the standard schema (DE = author keywords, ID = Keywords Plus). This is a WoS internal naming artefact from histNetwork() output columns.
5) DE/ID label mapping is inverted (as noted above). A user selecting node_label="DE" gets Keywords Plus, not author keywords. Needs a one-line swap or renaming in histNetwork() output. || eval() used again for DE/ID node labels (same pattern as get_frequentwords.py). Unsafe and redundant if ETL guarantees list[str].
6) **Yes, high priority**. The ETL must: Populate SR correctly as "FirstAuthor, Year, Journal" — it is the primary node key for the entire graph. || Normalise CR entries to WoS reference string format, as histNetwork() depends on it for edge construction. This is the single highest-risk dependency in the project for non-WoS sources. || Ensure DOI is str, empty string "" if missing (not NaN). || Ensure DE and ID are list[str] to eliminate the eval() calls.


### get_localcitedauthors.py
1) Finds which authors are most cited within the dataset itself (not globally), ranks them by local citation count, and draws a dot chart of the top-k authors.
2) **www.services**.
3) **AU**, **TC** (core); **SR** (must already exist or be built by `metaTagExtraction` before use).
4) **No** explicit DB checks, but `metaTagExtraction` and `histNetwork` are built for WoS-style data.
5) `AU` is exploded without checking if it is a proper list — plain strings will produce wrong results. If `histNetwork` returns an empty result the function crashes immediately. `SR` is rebuilt here by `metaTagExtraction`, which should instead already be present from the ETL.
6) **Yes**. `AU` must be a `list[str]`, `TC` must be non-null and numeric, and `SR` must be correctly built by the ETL pipeline.

### get_localciteddocuments.py
1) Finds which papers in the dataset are most cited by other papers in the same dataset (local citations), ranks them, and draws a dot chart of the top-k documents. Also returns a table with local citations, global citations, and normalized metrics per document.
2) **www.services**.
3) **SR**, **TC**, **DI**, **PY** (core).
4) **No** explicit DB checks, but `SR` is expected in WoS format and `histNetwork` is built for WoS-style data.
5) `SR` is rebuilt here internally instead of being taken from the ETL pipeline. If `TC` contains nulls, `fillna(0)` handles it, but the LC/GC ratio calculation will produce division by zero for papers with zero global citations. If `histNetwork` returns an empty result the function crashes immediately.
6) **Yes**. `SR` must be correctly built by the ETL, `TC` and `PY` must be non-null and numeric, and `DI` must be present as a string.

### get_localcitedreferences.py
1) Counts how many times each reference is cited across all papers in the dataset, ranks them, and draws a dot chart of the most cited references. Unlike global citation counts, this only looks at citations within the dataset itself.
2) **www.services**.
3) **CR** only.
4) **No** explicit DB checks, but the fallback string splitting uses the user-provided separator, which means the function can handle non-WoS sources if `CR` is correctly formatted as a list or delimited string.
5) Crashes if `CR` is missing entirely. If `CR` is an empty list or all nulls the chart will be empty with no clear error. The check `isinstance(data["CR"].iloc[0], list)` will crash if the DataFrame is empty.
6) **Yes**. `CR` must be present and correctly formatted as a `list[str]` where each element is an individual reference string.

### get_localcitedsources.py
1) Counts how many times each journal or source is cited across all papers in the dataset, ranks them, and draws a dot chart of the most locally cited sources. The source names are extracted from the cited references using `metaTagExtraction`.
2) **www.services**.
3) **CR** (needed by `metaTagExtraction` to extract `CR_SO`); **CR_SO** (derived column, used directly for counting).
4) **Yes**. `metaTagExtraction` parses source names from WoS-style reference strings. Non-WoS sources with differently formatted references will likely produce empty or wrong results.
5) Crashes if `CR_SO` is missing or empty. The check `isinstance(data["CR_SO"].iloc[0], list)` will crash if the DataFrame is empty. If `metaTagExtraction` fails silently, the chart will be empty with no clear error.
6) **Yes**. `CR` must be present as a properly formatted list of reference strings so that `metaTagExtraction` can correctly extract the source names into `CR_SO`.

### get_lotkalaw.py
1) Applies Lotka's Law to measure author productivity — it counts how many authors wrote exactly 1, 2, 3... papers, compares the observed distribution against the theoretical one, and draws a line chart showing both curves side by side.
2) **www.services**.
3) **AU** only.
4) **No** explicit DB checks.
5) Crashes if `AU` is missing or not a list — the list flattening `[author for sublist in data['AU'] for author in sublist]` will fail if any row is a plain string or null. If all authors wrote only one paper, `np.polyfit` may produce unreliable results with no warning.
6) **Yes**. `AU` must be present and correctly formatted as a `list[str]` per row.

### get_maininformations.py
1) Computes a comprehensive set of summary statistics for the dataset and adds them as new columns to the DataFrame. Metrics include: publication year range, unique sources, annual growth rate (CAGR), unique authors, single-authored documents, international co-authorship percentage, co-authors per document, unique author keywords, references per document, average document age, and average citations per document. Returns the enriched DataFrame. This is the main "overview" function used to populate the summary panel of the dashboard.
2) **www.services**.
3) **PY**, **SO**, **AU**, **TC**, **CR**, **DE** (core); **AU_CO** (derived — extracted by `metaTagExtraction()` if not already present).
4) `metaTagExtraction(df, "AU_CO")` is called to extract country information from WoS-style affiliation strings if `AU_CO` is missing. Non-WoS sources with differently formatted affiliations will produce wrong or empty country counts, causing the international co-authorship metric to be zero or incorrect.
5) `AU` is iterated as a list without a null guard — if any row contains a plain string instead of a list, the flattening `[author for sublist in AU_list for author in sublist]` will iterate over characters and produce wrong author counts silently. Same issue applies to `DE` and `CR`. CAGR calculation divides by `ny = max - min` which will be zero if all papers are from the same year, causing a `ZeroDivisionError`.
6) **Yes, high priority.** Ensure `AU`, `DE`, and `CR` are all `list[str]` — this function iterates over them directly and will silently produce wrong results if they are plain strings. Ensure `PY` is non-null and numeric to avoid crashes in year-range and age calculations. Ensure `TC` is numeric with nulls replaced by `0`. Ensure `C1` or `RP` are correctly populated so that `metaTagExtraction()` can extract `AU_CO` if needed.

### get_referencesspectroscopy.py
1) Generates a Reference Publication Year Spectroscopy (RPYS) analysis — a technique that identifies which historical years had the most influence on a research field by counting how often papers from each year are cited in the dataset's reference lists. It extracts publication years from each cited reference string, counts citations per year, computes a 5-year moving median deviation to highlight anomalous peaks, and returns an interactive dual-line chart, a year-level summary table, and a reference-level table with Google Scholar links.
2) **www.services**.
3) **CR** only.
4) Year extraction from reference strings uses the regex `r'\b\d{4},'` which matches a 4-digit year followed by a comma — this is the WoS reference string format ("Author, Year, Journal, Vol, Page"). Non-WoS reference formats that place the year differently (e.g. PubMed, Scopus) will produce zero year matches, resulting in an empty chart.
5) `df['CR'].apply(lambda x: [i for i in x])` assumes `CR` is already a list — if it arrives as a plain string it will iterate over characters and produce garbage silently. If `CR` is entirely empty or null the `year_seq.min()` call will crash. The year regex silently assigns `0` to references where no year is found, which then pollutes the year distribution if not filtered out.
6) **Yes, high priority.** Ensure `CR` is a `list[str]` where each element is a properly formatted reference string. The year regex `r'\b\d{4},'` requires the year to be followed by a comma — ETL must ensure CR entries follow the WoS format "Author, Year, Journal, Vol, Page" for year extraction to work correctly across all sources. References with no detectable year should be filtered out rather than assigned year `0`.

### get_relevantaﬃliations.py
1) Ranks institutions by number of publications and draws a dot chart of the top-k affiliations. Depending on the `disambiguation` parameter, it either uses `AU_UN` (a cleaned and disambiguated university name field) or the raw `C1` affiliation strings. Returns the chart and a summary table.
2) **www.services**.
3) **AU_UN** or **C1** depending on the `disambiguation` parameter — only one is used per call.
4) `AU_UN` is a WoS-derived column that contains disambiguated university names — it does not exist natively in non-WoS sources and must be built by the ETL from `C1`. If `disambiguation == "no"`, `C1` is used directly, which is more portable across sources.
5) Crashes immediately if `AU_UN` is missing when `disambiguation == "yes"`, or if `C1` is missing when `disambiguation == "no"` — no guard exists for either case. Both columns are expected to be `list[str]` per row — plain strings will produce wrong results after `explode()`. The docstring mentions `num_of_authors` and `frequency` as parameter names but the actual parameters are `num_of_affiliations` and `disambiguation`, indicating copy-paste drift.
6) **Yes.** Ensure `C1` is present as a `list[str]` of affiliation strings — it is the primary input when `disambiguation == "no"` and the source for building `AU_UN` when `disambiguation == "yes"`. Ensure `AU_UN` is derived from `C1` during the ETL Transform phase and stored as a `list[str]` of cleaned university names.

### get_relevantauthors.py
1) Ranks authors by number of publications, percentage of documents, or fractionalized count (where each author of a multi-authored paper gets a fractional credit), and draws a dot chart of the top-k authors. Returns the chart and a full ranking table.
2) **www.services**.
3) **AU** only.
4) **No** explicit DB checks, but `AU` is expected in WoS author format. The fallback `lambda x: x if isinstance(x, list) else []` silently replaces non-list values with an empty list instead of trying to parse them, which means authors from non-WoS sources arriving as delimited strings will be completely ignored.
5) Non-list `AU` values are silently dropped rather than parsed, so non-WoS sources that store authors as semicolon-delimited strings will produce an empty chart with no error. The `frequency` parameter values in the docstring (`"N. of Documents"`, `"Percentage"`, `"Fractionalized"`) do not match the actual values checked in the code (`"percentage"`, `"freq_measure"`), meaning the default `"N. of Documents"` always falls through to the raw count branch regardless of user selection.
6) **Yes.** Ensure `AU` is present and correctly formatted as a `list[str]` per row — non-list values are silently ignored, producing wrong author counts. Ensure author names follow a consistent format (e.g. `"Surname, Firstname"`) across all sources to avoid duplicate entries for the same author.

### get_relevantsources.py
1) Ranks journals or sources by number of publications and draws a dot chart of the top-k sources. Returns the chart and a full ranking table.
2) **www.services**.
3) **SO** only.
4) **No** explicit DB checks, but `SO` is the WoS tag for journal/source name. Sources using a different column name will crash immediately.
5) Crashes if `SO` is missing entirely. No check is performed on whether `SO` values are plain strings — if they arrive as lists the `value_counts()` will produce wrong results. No guard against an empty dataset after `dropna()`.
6) **Yes.** Ensure `SO` is present, non-null, and a plain string representing the journal or source name. Standardize casing consistently across sources (e.g. always uppercase) to avoid the same journal appearing multiple times under different capitalizations.

### get_sourceslocalimpact.py
1) Calculates impact scores (h-index, g-index, m-index, total citations, number of papers) for each journal or source, ranks them by the chosen metric, and draws a horizontal bar chart of the top-k sources. Returns the chart and the full ranking table.
2) **www.services**.
3) **SO**, **TC**, **PY**.
4) **No** explicit DB checks, but `SO`, `TC`, and `PY` are all WoS column tags. Sources using different names will crash immediately.
5) `h_calc` and `g_calc` are applied via `transform` instead of `agg`, which calls them once per row rather than once per group — this produces incorrect index values silently. `TC` and `PY` are cast with `errors='coerce'` and rows with nulls are dropped, but no warning is raised if a large fraction of rows is lost. Division by zero is possible in `m_index` if `today == PY_start - 1`, though extremely unlikely.
6) **Yes.** Ensure `SO` is present as a non-null string, `TC` is numeric with nulls replaced by `0`, and `PY` is a valid 4-digit year. The `h_calc` and `g_calc` functions need to be fixed to use `agg` instead of `transform` to produce correct index values — this is a bug in the function itself that the ETL cannot work around.

### get_sourcesproduction.py
1) Computes annual or cumulative publication counts per journal over time, selects the top-k sources by total output, and draws a multi-line chart showing each source's production trajectory. Returns the chart and the year-by-source matrix.
2) **www.services**.
3) **SO**, **PY** — both accessed directly and also passed to `cocMatrix()` internally.
4) **No** explicit DB checks, but `SO` and `PY` are WoS column tags. `cocMatrix()` is also built assuming WoS-style input.
5) `PY` is cast to `str` before `cocMatrix()` and back to `int` after — if `PY` contains nulls or non-numeric values this double cast will crash. If all papers belong to a single source `WSO.shape[1] == 1` is handled, but if `SO` is entirely missing `cocMatrix()` will crash with no clear error. No guard against `num_of_sources_production` being zero.
6) **Yes.** Ensure `SO` is present as a non-null string and `PY` is a valid 4-digit integer — both are cast and used in matrix operations that will crash silently or produce wrong results if the types are incorrect.

### get_status.py
1) Two small utility functions: `get_status()` converts a list of missing-value percentages into human-readable status labels (Excellent, Good, Acceptable, Poor, Critical, Completely missing), and `get_status_color()` maps each status label to a CSS background color for dashboard display. Used to give a quick visual quality assessment of the dataset columns.
2) **www.services**.
3) **None** — this file does not access any DataFrame column. It only processes a list of percentages passed in as a parameter.
4) **No**.
5) No input validation on `missing_percentage` — if a non-numeric value is passed, the comparisons will fail silently and return `"Unknown"`. The two functions are tightly coupled by string labels but there is no shared constant, so a typo in one function would break the other silently.
6) **No direct ETL relevance.** This is a pure utility file for dashboard display. The ETL pipeline does not need to produce any specific column for this function to work.

### get_table.py
1) Generates a metadata completeness report for the loaded dataset. It counts missing values, empty strings, and empty lists for every column, calculates the percentage of missing data per column, assigns a quality status (Excellent, Good, Acceptable, Poor, Critical, Completely missing), and displays the results as both a Plotly table and an interactive HTML data table with export buttons. This is the main data quality dashboard panel — it gives users an immediate overview of which columns are well populated and which need attention.
2) **www.services**; **get_status** (imported explicitly for status label and color functions).
3) **All columns present in the DataFrame** — it iterates over every column to compute missing value counts. The `column_descriptions` dictionary defines a fixed set of expected columns: `AB, AU, AU_UN, DB, DE, DT, LA, PU, PY, RP, SC, SO, SR, TC, TI, UT, C1, CR, OI, AU1_UN, EM, DI, BP, EP, SN, VL, ID, FU, FX, JI, OA, IS, PMID`.
4) **No** explicit DB checks, but the `column_descriptions` dictionary is entirely based on WoS field tags. Non-WoS columns not in this dictionary will still appear in the table but with no human-readable description.
5) The status color mapping in `create_plotly_table` uses `"Fair"` and `"Poor"` as keys, but `get_status()` never produces `"Fair"` — it produces `"Acceptable"` instead. This means the color for `"Acceptable"` rows will always fall through to `"white"`, losing the intended visual warning. Missing values are counted as NaN, empty string, single space, or empty list — but not `None`, which may slip through undetected.
6) **Yes.** The ETL must ensure all mandatory columns defined in the schema are present in the DataFrame — even if empty — so this function can report their completeness status correctly. Columns populated with `None` instead of `""` or `[]` will be undercounted in the missing value report, giving a false "Excellent" status.

### get_thematicevolution.py
1) Tracks how research themes evolve over time by splitting the dataset into user-defined time periods, running a full thematic map analysis on each period, and then computing inclusion, weighted inclusion, and stability indices to measure how strongly themes from one period carry over into the next. The results are visualised as an interactive network where nodes are research clusters and directed edges show thematic continuity between periods. Also returns a summary table of cluster transitions and the raw thematic map results per period. One of the most complex files in the codebase — it internally calls `thematic_map()`, `timeslice()`, and `plot_thematic_evolution()`.
2) **www.services**
3) **None directly** — all column access is delegated to `thematic_map()` and `timeslice()`. `PY` is the only column accessed directly inside `timeslice()`.
4) **Yes**. The field names `ID`, `DE`, `TI`, `AB` are WoS column tags passed to `thematic_map()` internally. Non-WoS sources using different names will produce empty results. `thematic_map()` also assumes WoS-style keyword formatting for `ID` and `DE`.
5) If `years` is not provided the function raises a `ValueError` immediately — no default is computed. If any time period produces zero clusters, the function prints a message and returns early with no chart and no clear error to the user. The `thematic_map()` return value is assumed to be a tuple but is also checked for being a dict — this inconsistency suggests the internal API is unstable and may break silently depending on the version. Temporary HTML file is never deleted.
6) **Yes, high priority.** Ensure `PY` is non-null and numeric — it is the only column used directly by `timeslice()` to split the data into periods, and wrong values will produce empty or misaligned time slices. Ensure `ID` and `DE` are `list[str]` — they are the primary inputs to `thematic_map()` for keyword network construction. For non-WoS sources that lack `ID`, populate it as `[]` per the null contract, but ensure the UI defaults the field to `DE` for those sources since an all-empty `ID` column will produce no usable analysis.

### get_thematicmap.py
1) A thin wrapper around the internal `thematic_map()` function. It passes all parameters directly to `thematic_map()`, which builds a keyword co-occurrence network, detects research clusters, and positions them on a centrality vs. density bubble chart. Returns the map figure, the HTML network file path, and three DataFrames: term-level data, cluster-level data, and document-to-cluster assignments.
2) **www.services**.
3) **None directly** — all column access is delegated entirely to `thematic_map()`.
4) **Yes**. The field names `ID`, `DE`, `TI`, `AB` are WoS column tags passed through to `thematic_map()`. Non-WoS sources using different names will produce empty results.
5) This file has no error handling of its own — if `thematic_map()` crashes or returns unexpected output, the exception propagates directly to the caller with no useful context. The return value assumes `thematic_map()` always returns exactly 5 values — if the internal API changes this will break silently.
6) **Yes.** Ensure `ID` and `DE` are `list[str]` — they are the primary inputs to `thematic_map()`. For non-WoS sources that lack `ID`, populate it as `[]` and ensure the UI defaults the field to `DE`, since an all-empty `ID` column will produce no usable analysis. Ensure `TI` and `AB` are non-null strings if those fields are selected.

### get_threefieldplot.py
1) Generates a Sankey diagram showing relationships between three user-selected bibliographic fields (e.g. authors → keywords → journals). For each field it builds a document-attribute matrix, computes co-occurrence counts between adjacent fields, and draws the flows as proportional bands connecting the three columns. Optionally derives extra columns like `CR_SO`, `AU_CO`, `AB_TM`, `TI_TM` via internal functions before building the matrices.
2) **www.services**; **textwrap**.
3) **None directly** — all column access is delegated to `cocMatrix()`, `metaTagExtraction()`, and `term_extraction()`. The actual columns consumed depend entirely on which fields the user selects.
4) **Yes**. All field names (`AU`, `DE`, `ID`, `SO`, `CR`, `TI`, `AB`, `WC`, `AU_CO`, `CR_SO`) are WoS column tags passed to `cocMatrix()`. Non-WoS sources using different names will produce empty matrices and a blank Sankey diagram with no error.
5) If any of the three `cocMatrix()` calls returns an empty matrix, the dot product for edge computation will silently produce an empty edge list and the diagram will render blank with no explanation. If `metaTagExtraction()` fails to extract `CR_SO` or `AU_CO`, those fields will be missing and `cocMatrix()` will crash immediately.
6) **Yes.** Ensure all potential field columns (`AU`, `DE`, `ID`, `SO`, `CR`, `TI`, `AB`, `C1`, `WC`) are present and correctly typed — `list[str]` for multi-value fields and `str` for scalar fields. Ensure `C1` is populated correctly so that `metaTagExtraction()` can derive `AU_CO` and `CR_SO` when those fields are selected.

### get_treemap.py
1) Counts the most frequent words or keywords in a selected field, and displays them as an interactive treemap where each rectangle's size represents the word's frequency. For title (`TI`) and abstract (`AB`) fields it first runs text mining to extract meaningful terms before counting. Also returns a full frequency table. Contains an internal helper function `table_tag()` that handles the actual word extraction and counting.
2) **www.services**.
3) **SR** (used inside `table_tag()` for deduplication); **DE**, **ID**, **TI**, **AB** (whichever is passed as `word_type`).
4) **No** explicit DB checks, but field names `DE`, `ID`, `TI`, `AB` are all WoS tags. Non-WoS sources using different names will produce empty results.
5) `SR` must be present for deduplication — if missing, `drop_duplicates(subset='SR')` crashes immediately. For `DE` and `ID`, `eval()` is called on string values — this is unsafe if the column contains arbitrary text instead of a properly formatted list string, and redundant if the ETL already guarantees `list[str]`. If `word_type` is not one of the handled cases, `text_data` will be an unprocessed column and the word extraction will silently produce wrong results.
6) **Yes.** Ensure `SR` is present and non-null. Ensure `DE` and `ID` are `list[str]` to eliminate the unsafe `eval()` call. Ensure `TI` and `AB` are non-null strings if those fields are selected.

### get_trendtopics.py
1) Identifies which words or keywords were most prominent in each time period by computing the median publication year for each term and plotting them as a bubble chart (term vs. year, bubble size = frequency). For title and abstract fields it first runs text mining before counting. Also returns the full trend data table. Contains an internal helper `field_by_year()` that builds the co-occurrence matrix and computes year quantiles per term.
2) **www.services**.
3) **PY** (accessed directly inside `field_by_year()`); **DE**, **ID**, **TI**, **AB**, or any derived field like `TI_TM`, `AB_TM` depending on `field_tt`.
4) **No** explicit DB checks, but field names are all WoS tags. Non-WoS sources using different names will produce empty results.
5) `PY` is used directly in `np.repeat(df['PY'], x)` without null checks — missing or non-numeric values will cause a crash. If the selected field is empty or missing, `cocMatrix()` will return an empty matrix and `np.quantile()` will crash on an empty array. If `term_extraction()` fails, the derived `TI_TM` or `AB_TM` column will be missing and the function crashes immediately.
6) **Yes.** Ensure `PY` is non-null and numeric — it is used directly in quantile calculations per term. Ensure `DE`, `ID`, `TI`, `AB` are correctly typed (`list[str]` for `DE`/`ID`, `str` for `TI`/`AB`) depending on the selected field.

### get_wordcloud.py
1) Generates an interactive word cloud rendered as a pyvis HTML network where each word is a text-only node, sized and coloured by frequency. It calls table_tag() (defined locally, identical to the one in get_frequentwords.py) to count terms, places nodes at random polar coordinates within a compact radius, applies ForceAtlas2 physics for slight jitter, saves the result to a temp HTML file, and returns the filename plus a full frequency table.
2) **www.services**.
3) **SR, and one of DE, ID, TI, AB**.
4) ID is WoS-exclusive, same as in get_frequentwords.py and get_wordfrequency.py. || SR deduplication assumes SR is always populated, same as get_frequentwords.py. || eval() on DE/ID strings, same unsafe pattern as get_frequentwords.py.
5) remove_terms silently not applied for TI/AB, inherited from table_tag() — same bug as in get_frequentwords.py.
6) **Yes**.  Same requirements as get_frequentwords.py: SR must be populated for all rows. || DE and ID must be list[str] to eliminate eval(). || ID must be [] for non-WoS sources. || TI and AB must be str, not NaN/None. ||

### get_wordfrequency.py
1) Plots word/keyword frequency over time as a multi-line chart, one line per term. It calls term_extraction() for free-text fields (TI/AB) or reads keyword columns directly (DE/ID), then passes data to keyword_growth() which builds a year × term frequency DataFrame (cumulative or per-year). Two helpers are defined locally: trim_years() (fills a year range with observed frequencies and optionally cumulates) and keyword_growth() (parses terms, applies synonym merging and stopword removal, selects top-N terms, and assembles the final time series).
2) **www.services**.
3) **PY, and one of DE, ID, TI, AB depending on field_wf**
4) ID is WoS-exclusive (Keywords Plus). Same risk as in get_frequentwords.py — passing field_wf="ID" on non-WoS data silently operates on an empty column. || keyword_growth() splits on sep=";" by default, which matches WoS keyword serialisation. Scopus uses "; " (with trailing space) so terms may arrive with leading spaces (e.g. " MACHINE LEARNING") that survive the .upper() call and prevent correct term matching or synonym replacement.
5) data['Year'].min() and data['Year'].max() in keyword_growth() will raise a ValueError if PY is empty after dropna. No guard exists for empty DataFrames after filtering. || Leading/trailing whitespace in terms not stripped before Counter/groupby. Terms like " MACHINE LEARNING" and "MACHINE LEARNING" are counted separately, fragmenting frequencies.
6) **Yes**. The ETL must: Cast PY to int with no nulls — required by keyword_growth() for year range construction. || Ensure DE and ID are list[str] so the isinstance(x, str) branch in keyword_growth() is never taken, avoiding semicolon-split issues entirely. || Ensure ID is [] for non-WoS sources. || TI and AB must be str, not NaN/None.

### get_worldmapcollaboration.py
1) Builds an interactive historiographic network map showing citation relationships between key papers over time. It calls metaTagExtraction() and histNetwork() from services to construct the citation graph, then histPlot() for the initial layout. It then rebuilds the graph with networkx, optionally removes isolated nodes, positions nodes on a timeline (x = year, y = cluster), computes node sizes from local citation scores (LCS), and renders an interactive pyvis HTML network saved to a temp file. Returns the plot object, a metadata DataFrame, and the temp HTML filename.
2) **www.services**.
3) **SR, CR, DOI, AU, TI, DE, ID, PY**
4) histNetwork() parses CR using WoS reference string format ("Author, Year, Journal, Vol, Page"). This is the most WoS-specific dependency in the entire codebase. Non-WoS CR strings will produce zero or wrong citation matches, resulting in an empty or disconnected graph. || metaTagExtraction(df, "SR") regenerates SR from WoS-style author/year/journal fields. If SR was not correctly populated by ETL, this call may produce malformed node identifiers that break edge matching. || node_label="ID" and node_label="DE" are swapped. The code maps "ID" → row.get("Author_Keywords") and "DE" → row.get("KeywordsPlus"), which is the reverse of the standard schema (DE = author keywords, ID = Keywords Plus). This is a WoS internal naming artefact from histNetwork() output columns.
5) DE/ID label mapping is inverted (as noted above). A user selecting node_label="DE" gets Keywords Plus, not author keywords. Needs a one-line swap or renaming in histNetwork() output. || eval() used again for DE/ID node labels (same pattern as get_frequentwords.py). Unsafe and redundant if ETL guarantees list[str]. || hist_data["GCS"] cast to int in tooltip without null guard — if GCS is NaN, int(row.get('GCS', 0)) will raise a ValueError because int(float('nan')) fails in Python.
6) **Yes, high priority**. Populate SR correctly as "FirstAuthor, Year, Journal" — it is the primary node key for the entire graph. || Normalise CR entries to WoS reference string format, as histNetwork() depends on it for edge construction. This is the single highest-risk dependency in the project for non-WoS sources. || Ensure DOI is str, empty string "" if missing (not NaN). || Ensure DE and ID are list[str] to eliminate the eval() calls.



---

## Summary

### All columns required across the entire codebase
| Column | Used by |
|--------|---------|
| AU | biblionetwork.py, get_authorlocalimpact.py (core direct dependency), get_authorproductionovertime.py (core direct dependency), get_clusteringcoupling.py (indirect dependency via couplingMap), get_collaborationnetwork.py (core direct dependency), get_correspondingauthorcountries.py (indirect dependency via metaTagExtraction), get_historiograph.py (secondary direct dependency), get_localcitedauthors.py (core direct dependency), get_lotkalaw.py (core direct dependency), get_maininformations.py (core direct dependency), get_relevantauthors.py (core direct dependency), get_table.py (schema-level expected column), get_threefieldplot.py (indirect dependency via cocMatrix), get_worldmapcollaboration.py (secondary direct dependency) |
| AB | get_co_occurence_network.py (indirect dependency), get_factorialanalysis.py (core direct dependency), get_frequentwords.py (conditional direct dependency), get_table.py (schema-level expected column), get_thematicmap.py (indirect dependency via thematic_map), get_threefieldplot.py (indirect dependency via cocMatrix / term_extraction), get_treemap.py (conditional direct dependency), get_trendtopics.py (conditional direct dependency), get_wordcloud.py (conditional direct dependency), get_wordfrequency.py (conditional direct dependency) |
| TI | get_authorproductionovertime.py (secondary direct dependency), get_co_occurence_network.py (indirect dependency), get_factorialanalysis.py (core direct dependency), get_frequentwords.py (conditional direct dependency), get_historiograph.py (secondary direct dependency),  get_table.py (schema-level expected column), get_thematicevolution.py (indirect dependency via thematic_map), get_thematicmap.py (indirect dependency via thematic_map), get_threefieldplot.py (indirect dependency via cocMatrix / term_extraction), get_treemap.py (conditional direct dependency), get_trendtopics.py (conditional direct dependency),  get_wordcloud.py (conditional direct dependency), get_wordfrequency.py (conditional direct dependency), get_worldmapcollaboration.py (secondary direct dependency)|
| PY | get_affiliationproductionovertime.py (core direct dependency), get_annualproduction.py (core direct dependency), get_authorlocalimpact.py (core direct dependency), get_authorproductionovertime.py (core direct dependency), get_averagecitations.py (core direct dependency), get_citeddocuments.py (core direct dependency), get_clusteringcoupling.py (indirect dependency via couplingMap), get_co_occurence_network.py (indirect dependency), get_countriesproductionovertime.py (core direct dependency), get_filters.py (core direct dependency), get_historiograph.py (core direct dependency), get_localciteddocuments.py (core direct dependency), get_maininformations.py (core direct dependency), get_sourceslocalimpact.py (core direct dependency), get_sourcesproduction.py (core direct dependency), get_table.py (schema-level expected column), get_thematicevolution.py (core direct dependency via timeslice), get_trendtopics.py (core direct dependency), get_wordfrequency.py (core direct dependency), get_worldmapcollaboration.py (core direct dependency)|
| AU_UN | get_affiliationproductionovertime.py (core direct dependency), get_collaborationnetwork.py (indirect derived dependency via metaTagExtraction), get_relevantaffiliations.py (conditional core direct dependency, used when disambiguation == "yes"), get_table.py (schema-level expected column)  |
| TC | get_authorlocalimpact.py (core direct dependency), get_authorproductionovertime.py (core direct dependency), get_averagecitations.py (core direct dependency), get_citedcountries.py (core direct dependency), get_citeddocuments.py (core direct dependency), get_clusteringcoupling.py (indirect dependency via couplingMap), get_filters.py (core direct dependency), get_localcitedauthors.py (core direct dependency), get_localciteddocuments.py (core direct dependency), get_maininformations.py (core direct dependency), get_sourceslocalimpact.py (core direct dependency), get_table.py (schema-level expected column)  |
| SO | get_authorproductionovertime.py (secondary direct dependency), get_bradfordlaw.py (core direct dependency), get_filters.py (core direct dependency), get_maininformations.py (core direct dependency),  get_relevantsources.py (core direct dependency), get_sourceslocalimpact.py (core direct dependency), get_sourcesproduction.py (core direct dependency), get_table.py (schema-level expected column), get_threefieldplot.py (indirect dependency via cocMatrix) |
| C1 | get_citedcountries.py (indirect dependency via metaTagExtraction), get_collaborationnetwork.py (indirect dependency via metaTagExtraction), get_correspondingauthorcountries.py (indirect dependency via metaTagExtraction), get_countriesproduction.py (indirect dependency via metaTagExtraction), get_countriesproductionovertime.py (indirect dependency via metaTagExtraction), get_maininformations.py (indirect dependency via metaTagExtraction, needed only if AU_CO must be derived), get_relevantaffiliations.py (conditional core direct dependency, used when disambiguation == "no"; also source field for deriving AU_UN), get_table.py (schema-level expected column), get_threefieldplot.py (indirect dependency via metaTagExtraction for AU_CO / CR_SO derivation) |
| RP | get_citedcountries.py (indirect dependency via metaTagExtraction), get_correspondingauthorcountries.py (indirect dependency via metaTagExtraction), get_maininformations.py (indirect dependency via metaTagExtraction, needed only if AU_CO must be derived), get_table.py (schema-level expected column)|
| SR | get_citeddocuments.py (core direct dependency), get_clusteringcoupling.py (indirect dependency via couplingMap), get_frequentwords.py (core direct dependency), get_historiograph.py (core direct dependency / also regenerated via metaTagExtraction), get_localcitedauthors.py (indirect / regenerated via metaTagExtraction), get_localciteddocuments.py (core direct dependency / also regenerated internally), get_table.py (schema-level expected column), get_treemap.py (core direct dependency for deduplication),  get_wordcloud.py (core direct dependency for deduplication), get_worldmapcollaboration.py (core direct dependency / also regenerated via metaTagExtraction)  |
| DI | get_authorproductionovertime.py (secondary direct dependency), get_citeddocuments.py (secondary direct dependency), get_localciteddocuments.py (secondary direct dependency), get_table.py (schema-level expected column)|
| DOI | get_historiograph.py (secondary direct dependency), get_worldmapcollaboration.py (secondary direct dependency) |
| CR | get_clusteringcoupling.py (indirect dependency via couplingMap), get_cocitation.py (indirect dependency via biblionetwork), get_historiograph.py (core direct dependency via histNetwork; WoS-style parsing dependency), get_localcitedreferences.py (core direct dependency), get_localcitedsources.py (indirect dependency via metaTagExtraction), get_maininformations.py (core direct dependency), get_referencesspectroscopy.py (core direct dependency), get_table.py (schema-level expected column), get_threefieldplot.py (indirect dependency via cocMatrix / metaTagExtraction), get_worldmapcollaboration.py (core direct dependency via histNetwork; WoS-style parsing dependency)|
| DE | get_clusteringcoupling.py (indirect dependency via couplingMap), get_co_occurence_network.py (indirect dependency), get_factorialanalysis.py (core direct dependency), get_frequentwords.py (conditional direct dependency), get_historiograph.py (secondary direct dependency), get_maininformations.py (core direct dependency), get_table.py (schema-level expected column), get_thematicevolution.py (indirect dependency via thematic_map), get_thematicmap.py (indirect dependency via thematic_map), get_threefieldplot.py (indirect dependency via cocMatrix), get_treemap.py (conditional direct dependency), get_trendtopics.py (conditional direct dependency),  get_wordcloud.py (conditional direct dependency), get_wordfrequency.py (conditional direct dependency), get_worldmapcollaboration.py (secondary direct dependency; DE/ID mapping inversion noted) |
| ID | get_clusteringcoupling.py (indirect dependency via couplingMap), get_co_occurence_network.py (indirect dependency), get_factorialanalysis.py (core direct dependency; default WoS-specific field), get_frequentwords.py (conditional direct dependency), get_historiograph.py (secondary direct dependency), get_table.py (schema-level expected column), get_thematicevolution.py (indirect dependency via thematic_map; WoS-default field), get_thematicmap.py (indirect dependency via thematic_map), get_threefieldplot.py (indirect dependency via cocMatrix), get_treemap.py (conditional direct dependency), get_trendtopics.py (conditional direct dependency), get_wordcloud.py (conditional direct dependency; WoS-specific field), get_wordfrequency.py (conditional direct dependency; WoS-specific field), get_worldmapcollaboration.py (secondary direct dependency; DE/ID mapping inversion noted)  |
| WC | get_co_occurence_network.py (indirect dependency),  get_threefieldplot.py (indirect dependency via cocMatrix) |
| CR_AU | get_cocitation.py (indirect derived dependency via metaTagExtraction / biblionetwork) |
| CR_SO | get_cocitation.py (indirect derived dependency via metaTagExtraction / biblionetwork), get_localcitedsources.py (indirect derived dependency via metaTagExtraction; then used directly for counting), get_threefieldplot.py (indirect derived dependency via metaTagExtraction)  |
| AU_CO | get_collaborationnetwork.py (indirect derived dependency via metaTagExtraction), get_correspondingauthorcountries.py (indirect derived dependency via metaTagExtraction), get_countriesproduction.py (indirect derived dependency via metaTagExtraction), get_countriesproductionovertime.py (indirect derived dependency via metaTagExtraction),  get_maininformations.py (indirect derived dependency via metaTagExtraction),  get_threefieldplot.py (indirect derived dependency via metaTagExtraction)  |
| AU1_CO |get_correspondingauthorcountries.py (indirect derived dependency via metaTagExtraction), get_table.py (schema-level expected column) |
| DB | get_database.py (core direct dependency), get_table.py (schema-level expected column) |
| LA | get_filters.py (core direct dependency), get_table.py (schema-level expected column) |
| DT | get_filters.py (core direct dependency),  get_table.py (schema-level expected column)  |
| PU | get_table.py (schema-level expected column) |
| SC | get_table.py (schema-level expected column) |
| UT | get_table.py (schema-level expected column) |
| OI | get_table.py (schema-level expected column) |
| EM | get_table.py (schema-level expected column) |
| BP | get_table.py (schema-level expected column) |
| EP | get_table.py (schema-level expected column) |
| SN | get_table.py (schema-level expected column) |
| VL | get_table.py (schema-level expected column) |
| FU | get_table.py (schema-level expected column) |
| FX | get_table.py (schema-level expected column) |
| JI | get_table.py (schema-level expected column) |
| OA | get_table.py (schema-level expected column) |
| IS | get_table.py (schema-level expected column) |
| PMID | get_table.py (schema-level expected column) |
| TI_TM | get_threefieldplot.py (indirect derived dependency via term_extraction) |
| AB_TM | get_threefieldplot.py (indirect derived dependency via term_extraction) |

### Files that need patching
| File | Line | Issue |
|------|------|-------|
| histnetwork.py | 37 | if db == "Web_of_Science" |
| biblionetwork.py | 94 | if db == "web_of_science" |
| format_functions.py | multiple | if source == "Web_of_Science" |
| couplingmap.py | multiple | Root dependency: assumes WoS-style SR/CR reconstruction through metaTagExtraction(), biblionetwork(), and histNetwork(); breaks bibliographic coupling on non-WoS sources |
| get_authorproductionovertime.py | 28 |fallback str(x).split(",") assumes WoS comma-separated author format
| get_citedcountries.py | 17 | metaTagExtraction(df, "AU1_CO") assumes WoS-style affiliation parsing |
| get_citeddocuments.py | 17 | metaTagExtraction(df, "SR") rebuilds SR from WoS-style fields |
| get_clusteringcoupling.py | 10 | couplingMap() built for WoS-style SR and CR |
| get_co_occurence_network.py | 38 | field names ID, DE, TI, AB, WC are WoS tags — ID is WoS-exclusive |
| get_cocitation.py | 47 | metaTagExtraction(M, Field="CR_AU") and metaTagExtraction(M, Field="CR_SO") parse WoS-style reference strings |
| get_collaborationnetwork.py | 55, 63 | metaTagExtraction(M, Field="AU_UN") and metaTagExtraction(M, Field="AU_CO") assume WoS-style affiliation strings |
 get_correspondingauthorcountries.py | 16,17 | metaTagExtraction(df, Field="AU_CO") and (df, Field="AU1_CO") assume WoS-style affiliation parsing |
| get_countriesproduction.py | 15 | metaTagExtraction(df, "AU_CO") assumes WoS-style affiliation parsing |
| get_countriesproductionovertime.py | 15 | metaTagExtraction(df, "AU_CO") assumes WoS-style affiliation parsing |
| get_database.py | 18-29 | database = "Web of Science" returns display string instead of standardized identifier (e.g. "WEB_OF_SCIENCE") |
| get_factorialanalysis.py | 42 | field="ID" default assumes WoS Keywords Plus — field does not exist in non-WoS sources |
| get_filters.py | 77-78 | LA and DT filter values assume WoS vocabulary ("Article", "English") — non-WoS sources may use different values |
| get_frequentwords.py | 106 -119 | drop_duplicates(subset='SR') assumes SR always populated — crashes with KeyError if SR missing, eval(x) on DE/ID assumes WoS-style Python list serialization — breaks with Scopus semicolon-delimited strings |
| get_historiograph.py | 30, 153-159 | metaTagExtraction(df, "SR") rebuilds SR from WoS-style author/year/journal fields eval() on Author_Keywords / KeywordsPlus — unsafe; DE/ID label mapping is inverted (WoS naming artefact) | 
| get_localcitedauthors.py | 22, 29 | metaTagExtraction(df, "SR") rebuilds SR from WoS-style author/year/journal fields / histNetwork() parses CR assuming WoS format Author, Year, Journal, Vol, Page|
| get_localciteddocuments.py | 16, 29 | metaTagExtraction(df, "SR") rebuilds SR from WoS-style fields / histNetwork() parses CR assuming WoS format Author, Year, Journal, Vol, Page |
| get_localcitedsources.py | 17 | metaTagExtraction(df, "CR_SO") parses source names from WoS-style reference strings |
| get_maininformations.py | 101 | metaTagExtraction(df, "AU_CO") assumes WoS-style affiliation parsing (C1/RP) to derive country per author |
| get_referencesspectroscopy.py | 35 | regex r'\b\d{4},' extracts year assuming WoS reference format Author, Year, Journal, Vol, Page — non-WoS formats produce zero year matches |
| get_relevantaffiliations.py | 20 | data["AU_UN"] is a WoS-derived column — does not exist natively in non-WoS sources and must be built by ETL from C1 |
| get_relevantauthors.py | 22 | fallback else [] silently drops non-list AU values — non-WoS sources with semicolon-delimited strings produce empty results |
| get_table.py | 91-125 | column_descriptions dictionary contains only WoS field tags — non-WoS columns appear without human-readable description |
| get_thematicevolution.py | 4, 98 | field="ID" default assumes WoS Keywords Plus — thematic_map() produces empty results on non-WoS sources |
| get_thematicmap.py | 4 | field="ID" default assumes WoS Keywords Plus — thematic_map() produces empty results on non-WoS sources |
| get_threefieldplot.py | 24, 26 | metaTagExtraction(df, "CR_SO") and metaTagExtraction(df, "AU_CO") assume WoS-style reference strings and affiliation parsing |
| get_treemap.py | 81, 91 | drop_duplicates(subset='SR') assumes SR always populated / eval(x) on DE/ID assumes WoS-style Python list serialization |
| get_trendtopics.py | 40, 105 | field_tt="ID" routed directly to cocMatrix() — WoS-exclusive field produces empty results on non-WoS sources / np.repeat(df['PY'], x) used without null check |
| get_wordcloud.py | 112, 125 | drop_duplicates(subset='SR') assumes SR always populated / eval(x) on DE/ID assumes WoS-style Python list serialization |
| get_wordfrequency.py | 135 | x.split(sep) with default sep=";" assumes WoS keyword serialization — Scopus uses "; " producing terms with leading spaces |
| get_worldmapcollaboration.py | 12 | metaTagExtraction(df, "AU_CO") assumes WoS-style affiliation parsing (C1/RP) to derive country per author |

## Notes
- `metatagextraction.py` is the primary root dependency for most WoS-specific parsing issues.
  It reconstructs derived fields such as `AU_CO`, `AU1_CO`, `AU_UN`, `CR_SO`, `CR_AU`, and `SR`.
  Patching this file first resolves cascading failures across many caller modules.

- `couplingmap.py` is a secondary root dependency for bibliographic coupling workflows.
  It relies on WoS-style `SR` and `CR` normalization through `metaTagExtraction()`,
  `biblionetwork()`, and `histNetwork()`.
  Caller-side fixes alone are insufficient if coupling normalization remains WoS-dependent.


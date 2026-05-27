from www.services import *


# ---------------------------------------------------------------------------
# PATCH: normalize_keyword_field()
# Identical to the version in get_frequentwords.py and get_treemap.py.
# Normalizes DE/ID values to list[str] without using eval().
# Handles: list[str], WoS serialized "['kw1']", Scopus "kw1; kw2",
#          comma-delimited fallback, NaN/None → [].
# ---------------------------------------------------------------------------
def normalize_keyword_field(x):
    if isinstance(x, list):
        return [str(k).strip() for k in x if str(k).strip()]
    if not isinstance(x, str) or not x.strip():
        return []
    s = x.strip()
    if s.startswith("["):
        import ast
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                return [str(k).strip() for k in parsed if str(k).strip()]
        except (ValueError, SyntaxError):
            pass
    if ";" in s:
        return [k.strip() for k in s.split(";") if k.strip()]
    return [k.strip() for k in s.split(",") if k.strip()]


def is_legible_on_white(color):
    """Restituisce True se il colore è leggibile su sfondo bianco"""
    r, g, b = mcolors.to_rgb(color)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return 0.2 < luminance < 0.6


def get_wordcloud(df, ngram, num_of_words_wc, field_wc, file_upload_terms_wc, file_upload_synonyms_wc):
    """
    Generate a word cloud and table of the most frequent words.

    Args:
        df: A DataFrame object containing the data.
        ngram: N-gram size for TI/AB fields.
        num_of_words_wc: The number of top frequent words to display.
        field_wc: The type of words to analyze (e.g., 'TI', 'AB', 'DE', 'ID').
        file_upload_terms_wc: File containing terms to remove.
        file_upload_synonyms_wc: File containing synonyms.

    Returns:
        HTML file path (str) and a DataFrame of the most frequent words.
    """

    # Load stopwords
    remove_terms = None
    if file_upload_terms_wc:
        with open(file_upload_terms_wc[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    # Load synonyms
    synonyms = None
    if file_upload_synonyms_wc:
        with open(file_upload_synonyms_wc[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on field type
    ngrams = int(ngram) if field_wc in ['TI', 'AB'] else 1

    # Get word counts
    words = table_tag(df, field_wc, ngrams, remove_terms, synonyms)

    # Create DataFrame of most frequent words
    word_counts = pd.DataFrame(words.items(), columns=['Words', 'Occurrences'])
    word_counts["Words"] = word_counts["Words"].str.capitalize()
    table = word_counts.sort_values(by='Occurrences', ascending=False)
    word_counts = word_counts.sort_values(by='Occurrences', ascending=False).head(num_of_words_wc)
    radius = 400

    word_frequencies = dict(zip(word_counts["Words"], word_counts["Occurrences"]))
    G = nx.Graph()

    colors = [c for c in mcolors.CSS4_COLORS.values() if is_legible_on_white(c)]

    sorted_words = sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)
    center_word = sorted_words[0][0]

    compact_radius = radius * 0.6

    for word, count in sorted_words:
        size = max(500, min(2000, count * 2.5))
        font_size = max(20, min(120, count * 1.5))
        color = random.choice(colors)

        theta = random.uniform(0, 2 * math.pi)
        r = compact_radius * math.sqrt(random.uniform(0, 1))
        pos_x = r * math.cos(theta)
        pos_y = r * math.sin(theta)

        G.add_node(word, label=word, title=f"{word}: {count}", color="rgba(0,0,0,0)",
                   font={"size": font_size, "color": color, "strokeWidth": 1, "face": "Arial"},
                   x=pos_x, y=pos_y)

    # Creazione della rete interattiva con Pyvis
    g = Network(width="100%", height="98vh", bgcolor="white", font_color="black")
    g.from_nx(G)

    for n in g.nodes:
        n["size"] = G.nodes[n["id"]]["size"]
        n["font"] = {
            "size": G.nodes[n["id"]]["font"]["size"],
            "color": G.nodes[n["id"]]["font"]["color"],
            "strokeWidth": 1,
            "face": "Arial"
        }
        n["shape"] = "text"

    g.force_atlas_2based(gravity=-30, central_gravity=0.01, spring_length=60,
                         spring_strength=0.08, damping=0.9)

    # Save the HTML file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = g.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        f.write(updated_html)

    return html_path.split(os.sep)[-1], table


def table_tag(df, tag, ngrams=1, remove_terms=None, synonyms=None):
    """
    Extract and count words from a specified field in the DataFrame.
    """
    M = df.get()

    # PATCH: guard drop_duplicates on SR.
    # Crashes with KeyError on non-WoS sources where SR may be absent.
    # Fall back to DI (DOI) if available, otherwise skip dedup.
    if "SR" in M.columns:
        M = M.drop_duplicates(subset="SR")
    elif "DI" in M.columns:
        M = M.drop_duplicates(subset="DI")

    # Get text data based on tag
    if tag in ['AB', 'TI']:
        text_data = term_extraction(df, field=tag, stemming=False, verbose=False,
                                    ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
        text_data = text_data.get()
        text_data = text_data[f"{tag}_TM"]
    else:
        # PATCH: guard against missing column (e.g. "ID" absent on non-WoS sources).
        if tag not in M.columns:
            return {}
        text_data = M[tag]

    # PATCH: replace eval() with normalize_keyword_field().
    # eval() crashed on Scopus "kw1; kw2" strings with SyntaxError.
    if tag in ['DE', 'ID']:
        text_data = text_data.apply(normalize_keyword_field)
        text_data = text_data[text_data.apply(len) > 0]

    # Process words
    if tag in ['DE', 'ID']:
        words = [
            word.strip().upper()
            for kw_list in text_data
            for word in kw_list
            if word.strip()
        ]
    else:
        words = [item for sublist in text_data for item in sublist]

    # Replace synonyms
    if synonyms:
        for key, syn_list in synonyms.items():
            words = [key if word in syn_list else word for word in words]

    # Count words
    word_counts = Counter(words)

    # Remove specified terms
    if remove_terms and tag in ['DE', 'ID']:
        remove_upper = {term.upper() for term in remove_terms}
        word_counts = {
            word: count
            for word, count in word_counts.items()
            if word.upper() not in remove_upper
        }

    return word_counts
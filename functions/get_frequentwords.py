from www.services import *


# ---------------------------------------------------------------------------
# PATCH: normalize_keyword_field()
# Normalizes a single value from DE or ID columns to list[str].
# DE/ID can arrive as:
#   - list[str]              → kept as-is (post-ETL normalized format)
#   - str "['kw1', 'kw2']"  → WoS Python-serialized list → parsed safely
#   - str "kw1; kw2"        → Scopus/PubMed semicolon-delimited → split on ";"
#   - str "kw1, kw2"        → comma-delimited fallback → split on ","
#   - NaN / None            → []
#
# Previously the code used eval(x) which:
#   - crashed with SyntaxError on Scopus/PubMed semicolon strings
#   - was unsafe on arbitrary input
#   - produced dirty tokens when applied to already-list values
# ---------------------------------------------------------------------------
def normalize_keyword_field(x):
    if isinstance(x, list):
        return [str(k).strip() for k in x if str(k).strip()]
    if not isinstance(x, str) or not x.strip():
        return []
    s = x.strip()
    # WoS Python-serialized list: starts with "[" — parse safely without eval()
    if s.startswith("["):
        import ast
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                return [str(k).strip() for k in parsed if str(k).strip()]
        except (ValueError, SyntaxError):
            pass
    # Scopus/PubMed semicolon-delimited
    if ";" in s:
        return [k.strip() for k in s.split(";") if k.strip()]
    # Comma-delimited fallback
    return [k.strip() for k in s.split(",") if k.strip()]


def get_frequent_words(df, ngram, num_of_words, word_type, file_upload_terms, file_upload_synonyms, field_separator_frequent=';'):
    """
    Generate a plot and table of the most frequent words.

    Args:
        df: A DataFrame object containing the data.
        ngram: N-gram size for TI/AB fields.
        num_of_words: The number of top frequent words to display.
        word_type: The type of words to analyze (e.g., 'TI', 'AB', 'DE', 'ID').
        field_separator_frequent: The separator used in the field.
        file_upload_terms: File containing terms to remove.
        file_upload_synonyms: File containing synonyms.

    Returns:
        A Plotly figure object and a DataFrame of the most frequent words.
    """

    # Load stopwords
    remove_terms = None
    if file_upload_terms:
        with open(file_upload_terms[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    # Load synonyms
    synonyms = None
    if file_upload_synonyms:
        with open(file_upload_synonyms[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on word_type
    ngrams = int(ngram) if word_type in ['TI', 'AB'] else 1
    print(ngrams)

    # Get word counts
    words = table_tag(df, word_type, ngrams, remove_terms, synonyms)

    # Create DataFrame of most frequent words
    word_counts = pd.DataFrame(words.items(), columns=['Words', 'Occurrences'])
    table = word_counts.sort_values(by='Occurrences', ascending=False)
    word_counts = word_counts.sort_values(by='Occurrences', ascending=False).head(num_of_words)

    # Create plot
    fig = px.scatter(
        word_counts,
        x="Occurrences",
        y="Words",
        text="Occurrences",
        size="Occurrences",
        size_max=60,
        color="Occurrences",
        color_continuous_scale=[(0, "lightblue"), (1, "darkblue")]
    )

    # Customize traces
    fig.update_traces(
        marker=dict(opacity=1, size=word_counts["Occurrences"]),
        textposition="middle center",
        textfont=dict(color="white", size=12)
    )

    # Add horizontal lines
    for _, row in word_counts.iterrows():
        fig.add_shape(
            type="line",
            x0=0,
            y0=row["Words"],
            x1=row["Occurrences"],
            y1=row["Words"],
            line=dict(color="LightGrey", width=3),
            layer="below"
        )

    # Update layout
    fig.update_layout(
        yaxis=dict(autorange="reversed", showgrid=True, gridcolor="lightgrey", zeroline=False),
        xaxis=dict(showgrid=True, gridcolor="lightgrey", zeroline=False),
        plot_bgcolor='white',
        font=dict(color="#444444"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=50 + 90 * len(word_counts),
        coloraxis_showscale=False,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
    )

    return fig, table


def table_tag(df, tag, ngrams=1, remove_terms=None, synonyms=None):
    """
    Extract and count words from a specified field in the DataFrame.
    """
    M = df.get()

    # PATCH: guard drop_duplicates on SR.
    # Previously: M.drop_duplicates(subset='SR') crashed with KeyError
    # when SR was absent (non-WoS sources without full ETL).
    # Now: dedup on SR only if it exists; fall back to DI (DOI) if available;
    # otherwise skip deduplication rather than crash.
    if "SR" in M.columns:
        M = M.drop_duplicates(subset="SR")
    elif "DI" in M.columns:
        M = M.drop_duplicates(subset="DI")
    # else: no deduplication — better than a crash

    # Get text data based on tag
    if tag in ['AB', 'TI']:
        text_data = term_extraction(df, field=tag, stemming=False, verbose=False,
                                    ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
        text_data = text_data.get()
        text_data = text_data[f"{tag}_TM"]

    else:
        # PATCH: guard against missing column.
        # Previously M[tag] crashed with KeyError when tag="ID" (WoS-exclusive
        # Keywords Plus) and the column was absent in non-WoS sources.
        if tag not in M.columns:
            return {}  # return empty counts — caller gets empty chart, not crash
        text_data = M[tag]

    # PATCH: normalize DE/ID using normalize_keyword_field() instead of eval().
    # Previously: eval(x) assumed WoS Python-serialized list format.
    # Scopus uses "kw1; kw2" → eval() raised SyntaxError.
    # PubMed uses "kw1, kw2" → eval() produced wrong tokens.
    # normalize_keyword_field() handles all formats safely.
    if tag in ['DE', 'ID']:
        text_data = text_data.apply(normalize_keyword_field)
        # Drop rows that produced empty lists
        text_data = text_data[text_data.apply(len) > 0]

    # Process words
    if tag in ['DE', 'ID']:
        # Each row is now a clean list[str] — flatten directly
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
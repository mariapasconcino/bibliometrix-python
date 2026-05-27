from www.services import *


# ---------------------------------------------------------------------------
# PATCH: normalize_keyword_field()
# Identical to the version in get_frequentwords.py.
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


def get_treemap(df, ngram, num_of_words, word_type, file_upload_terms, file_upload_synonyms, field_separator_frequent=';'):
    """
    Generate a treemap plot and table of the most frequent words.

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

    # Create TreeMap plot
    fig = px.treemap(
        word_counts,
        path=[px.Constant("Tree"), 'Words'],
        values='Occurrences',
        color='Occurrences',
        color_continuous_scale=[(0, "lightblue"), (1, "darkblue")],
    )

    # Update layout
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        height=800,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )

    # Add text to each cell
    fig.data[0].texttemplate = "%{label}<br>%{value} Occurrences<br>%{percentParent:.2%}"
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, table


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
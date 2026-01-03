def weighted_jaccard(tf_query, tf_doc):
    """
    Menghitung Weighted Jaccard Similarity antara dua dictionary TF.
    Rumus: Sum(min(wi, qi)) / Sum(max(wi, qi))
    """
    intersection = 0
    union = 0

    all_terms = set(tf_query.keys()).union(set(tf_doc.keys()))

    for term in all_terms:
        wq = tf_query.get(term, 0)
        wd = tf_doc.get(term, 0)

        intersection += min(wq, wd) # irisan atau pembilang
        union += max(wq, wd) # gabungan atau penyebut

    if union == 0:
        return 0.0
    
    return float (intersection / union)
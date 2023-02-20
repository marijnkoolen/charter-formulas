from typing import Dict, Generator, Tuple
from collections import Counter, defaultdict


def init_overlap_dict():
    return {
        'phrase1': [],
        'freq1': [],
        'dist': [],
        'phrase2': [],
        'freq2': [],
        'overlap_freq': []
    }


def init_matches_dict():
    return {
        'doc_id': [],
        'doc_length': [],
        'phrase': [],
        'start_offset': [],
        'end_offset': [],
        'rel_start': [],
        'rel_end': []
    }


def make_inverse_overlap(overlap: Dict[str, Dict[int, Counter]]) -> Dict[str, Dict[int, Counter]]:
    inverse_overlap = defaultdict(lambda: defaultdict(Counter))
    for phrase1 in overlap:
        for dist in overlap[phrase1]:
            for phrase2 in overlap[phrase1][dist]:
                inverse_overlap[phrase2][-dist][phrase1] = overlap[phrase1][dist][phrase2]
    return inverse_overlap


def get_phrase_overlap_info(main_phrase: str, overlap: Dict[str, Dict[int, Counter]],
                            inverse_overlap: Dict[str, Dict[int, Counter]]) -> Generator[Tuple[str, int, int], None, None]:
    for dist in overlap[main_phrase]:
        for overlap_phrase in overlap[main_phrase][dist]:
            overlap_freq = overlap[main_phrase][dist][overlap_phrase]
            yield overlap_phrase, dist, overlap_freq
    for dist in inverse_overlap[main_phrase]:
        for overlap_phrase in inverse_overlap[main_phrase][dist]:
            overlap_freq = inverse_overlap[main_phrase][dist][overlap_phrase]
            yield overlap_phrase, dist, overlap_freq


def make_matches_dict(candidate_phrase_matches, doc_length):
    matches = init_matches_dict()
    for candidate_phrase_match in candidate_phrase_matches:
        sent_id = candidate_phrase_match.doc_id
        doc_id = sent_id.split('____')[0]
        matches['doc_id'].append(doc_id)
        matches['doc_length'].append(doc_length[doc_id])
        matches['phrase'].append(candidate_phrase_match.candidate_phrase.phrase_string)
        matches['start_offset'].append(candidate_phrase_match.word_start)
        matches['end_offset'].append(candidate_phrase_match.word_end)
        matches['rel_start'].append(candidate_phrase_match.word_start / doc_length[doc_id])
        matches['rel_end'].append((doc_length[doc_id] - candidate_phrase_match.word_end) / doc_length[doc_id])
    return matches


def make_overlap_dict(candidate_phrase_freq: Counter, overlap: Dict[str, Dict[int, Counter]]):
    overlap_data = init_overlap_dict()
    for phrase1, freq1 in candidate_phrase_freq.most_common(10):
        for dist in overlap[phrase1]:
            for phrase2 in overlap[phrase1][dist]:
                freq2 = candidate_phrase_freq[phrase2]
                overlap_freq = overlap[phrase1][dist][phrase2]
                overlap_data['phrase1'].append(phrase1)
                overlap_data['freq1'].append(freq1)
                overlap_data['dist'].append(dist)
                overlap_data['phrase2'].append(phrase2)
                overlap_data['freq2'].append(freq2)
                overlap_data['overlap_freq'].append(overlap_freq)
    return overlap_data


def cluster_overlapping_phrases(candidate_phrase_freq: Counter,
                                overlap: Dict[str, Dict[int, Counter]]):
    formula_clusters = []
    clustered = set()
    inverse_overlap = make_inverse_overlap(overlap)
    for main_phrase, main_freq in candidate_phrase_freq.most_common():
        formula_cluster = defaultdict(dict)
        formula_cluster = {
            'core': {'phrase': main_phrase, 'dist': 0},
            'extension': [],
            'qualification': [],
            'variable': []
        }
        if main_phrase in clustered:
            continue
        # formula_cluster[0][main_phrase] = 'core'
        clustered.add(main_phrase)
        for overlap_phrase, dist, overlap_freq in get_phrase_overlap_info(main_phrase, overlap,
                                                                          inverse_overlap):
            # print(f"{main_phrase: <25}{dist: >4}\t{overlap_phrase: <25}{overlap_freq: >6}")
            overlap_phrase_freq = candidate_phrase_freq[overlap_phrase]
            if overlap_freq / main_freq > 0.75:
                formula_cluster['extension'].append({'phrase': overlap_phrase, 'dist': dist})
                # formula_cluster[dist][overlap_phrase] = 'extension'
            elif overlap_freq / overlap_phrase_freq > 0.75:
                formula_cluster['qualification'].append({'phrase': overlap_phrase, 'dist': dist})
                # formula_cluster[dist][overlap_phrase] = 'qualification'
            else:
                formula_cluster['variable'].append({'phrase': overlap_phrase, 'dist': dist})
                # formula_cluster[dist][overlap_phrase] = 'variable'
            if overlap_freq / overlap_phrase_freq > 0.5:
                clustered.add(overlap_phrase)
        formula_clusters.append(formula_cluster)
        if main_freq < 10:
            break
    return formula_clusters, clustered


def get_candidate_phrases(searcher, max_matches, phrase_type='sub_phrases', min_cooc_freq=100,
                          max_phrase_length=5, max_variables=1):
    candidate_phrase_matches = []

    overlap = defaultdict(lambda: defaultdict(Counter))

    queue = []
    prev_id = None

    extractor = searcher.extract_phrases_from_sents(phrase_type=phrase_type, min_cooc_freq=min_cooc_freq,
                                                    max_phrase_length=max_phrase_length,
                                                    max_variables=max_variables)
    for pi, candidate_phrase_match in enumerate(extractor):
        if candidate_phrase_match.doc_id != prev_id:
            queue = []
        if len(queue) == max_phrase_length:
            queue.pop(0)
        queue.append(candidate_phrase_match)

        for i in range(0, len(queue) - 1):
            if queue[i].word_end > queue[-1].word_start:
                phrase1 = queue[i].candidate_phrase.phrase_string
                phrase2 = queue[-1].candidate_phrase.phrase_string
                overlap[phrase1][len(queue) - i - 1].update([phrase2])

        candidate_phrase_matches.append(candidate_phrase_match)
        if (pi+1) % max_matches == 0:
            break
        prev_id = candidate_phrase_match.doc_id
    return candidate_phrase_matches, overlap

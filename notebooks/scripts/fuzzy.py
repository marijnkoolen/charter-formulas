from typing import Dict, List
from collections import defaultdict
from collections import Counter

from fuzzy_search.similarity import SkipgramSimilarity


SKIPGRAM_CONFIG = {}


def cluster_similar_phrases(phrases: List[str]):
    clustered_phrases = defaultdict(set)
    skip_sim = SkipgramSimilarity(ngram_length=2, skip_length=1, terms=phrases, max_length_diff=2)
    for phrase in phrases:
        for sim_phrase, sim_score in skip_sim.rank_similar(phrase, top_n=100, score_cutoff=0.6):
            if sim_phrase == phrase:
                continue
            # print(f"{phrase: <20}{sim_phrase: <20}\t{sim_score: >.2f}")
            clustered_phrases[phrase].add(sim_phrase)
            # clustered_phrases[sim_phrase].add(phrase)
    return clustered_phrases


def map_word_variants(candidate_phrase_freq: Counter, overlap: Dict[str, Dict[int, Counter]],
                      word_freq: Counter) -> Dict[str, str]:
    map_to = {
        'jnt': 'int',
        'sullen': 'zullen',
        'solen': 'zullen',
        'sien': 'zien'
    }

    map_from = defaultdict(set)
    for variant in map_to:
        map_from[map_to[variant]].add(variant)

    for phrase, freq in candidate_phrase_freq.most_common(100):
        for dist in overlap[phrase]:
            if abs(dist) > 1:
                continue
            overlap_phrases = [' '.join(phrase.split(' ')[-dist:]) for phrase in overlap[phrase][dist]]
            similar_words = cluster_similar_phrases(overlap_phrases)
            for word in similar_words:
                for sim_word in similar_words[word]:
                    if word_freq[sim_word] > word_freq[word]:
                        pref_word, alt_word = sim_word, word
                    elif word_freq[sim_word] == word_freq[word]:
                        pref_word, alt_word = sorted([sim_word, word])
                    else:
                        pref_word, alt_word = word, sim_word

                    for some_word in map_to:
                        if map_to[some_word] == some_word:
                            raise ValueError(f"word maps to itself: {some_word}")

                    if pref_word in map_to:
                        if alt_word == map_to[pref_word]:
                            continue
                        while pref_word in map_to:
                            pref_word = map_to[pref_word]

                    map_to[alt_word] = pref_word
                    map_from[pref_word].add(alt_word)

                    if alt_word in map_from:
                        for map_word in map_from[alt_word]:
                            map_to[map_word] = pref_word
                            map_from[pref_word].add(map_word)

    return map_to

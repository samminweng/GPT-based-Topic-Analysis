# Helper function for LDA topic modeling
import math
import os
import re
import string
import sys
from functools import reduce
from pathlib import Path
import plotly.graph_objects as go
import seaborn as sns
import inflect
import pandas as pd
from nltk import sent_tokenize, word_tokenize, pos_tag, ngrams
import copy

from BERTModelDocClusterUtility import BERTModelDocClusterUtility


class ClusterTopicUtility:

    @staticmethod
    def compute_topic_coherence_score(doc_n_grams, topic_words):
        # Build a mapping of word and doc ids
        def _build_word_docIds(_doc_n_grams, _topic_words):
            _word_docIds = {}
            for _word in _topic_words:
                try:
                    _word_docIds.setdefault(_word, list())
                    # Get the number of docs containing the word
                    for _doc in _doc_n_grams:
                        _doc_id = _doc[0]
                        _n_grams = _doc[1]
                        _found = next((_n_gram for _n_gram in _n_grams if _word.lower() in _n_gram.lower()), None)
                        if _found:
                            _word_docIds[_word].append(_doc_id)
                except Exception as _err:
                    print("Error occurred! {err}".format(err=_err))
                    sys.exit(-1)
            return _word_docIds

        # # Get doc ids containing both word i and word j
        def _get_docIds_two_words(_docId_word_i, _docIds_word_j):
            return [_docId for _docId in _docId_word_i if _docId in _docIds_word_j]

        try:
            word_docs = _build_word_docIds(doc_n_grams, topic_words)
            score = 0
            for i in range(0, len(topic_words)):
                try:
                    word_i = topic_words[i]
                    docs_word_i = word_docs[word_i]
                    doc_count_word_i = len(docs_word_i)
                    assert doc_count_word_i > 0
                    for j in range(i + 1, len(topic_words)):
                        word_j = topic_words[j]
                        docs_word_j = word_docs[word_j]
                        doc_word_i_j = _get_docIds_two_words(docs_word_i, docs_word_j)
                        doc_count_word_i_j = len(doc_word_i_j)
                        assert doc_count_word_i_j >= 0
                        coherence_score = math.log((doc_count_word_i_j + 1) / (1.0 * doc_count_word_i))
                        score += coherence_score
                except Exception as _err:
                    print("Error occurred! {err}".format(err=_err))
                    sys.exit(-1)
            avg_score = score / (1.0 * len(topic_words))
            return avg_score, word_docs
        except Exception as _err:
            print("Error occurred! {err}".format(err=_err))

    # Generate n-gram candidates from a text (a list of sentences)
    @staticmethod
    def generate_n_gram_candidates(sentences, n_gram_range):
        # Check if n_gram candidate does not have stop words, punctuation or non-words
        def _is_qualified(_n_gram):  # _n_gram is a list of tuple (word, tuple)
            try:
                qualified_tags = ['NN', 'NNS', 'JJ', 'NNP']
                # # # Check if there is any noun
                nouns = list(filter(lambda _n: _n[1].startswith('NN'), _n_gram))
                if len(nouns) == 0:
                    return False
                # # Check the last word is a nn or nns
                if _n_gram[-1][1] not in ['NN', 'NNS']:
                    return False
                # Check if all words are not stop word or punctuation or non-words
                for _i, _n in enumerate(_n_gram):
                    _word = _n[0]
                    _pos_tag = _n[1]
                    if bool(re.search(r'\d|[^\w]', _word.lower())) or _word.lower() in string.punctuation or \
                            _word.lower() in BERTModelDocClusterUtility.stop_words or _pos_tag not in qualified_tags:
                        return False
                # n-gram is qualified
                return True
            except Exception as _err:
                print("Error occurred! {err}".format(err=_err))

        # Convert n_gram tuples (pos tag and words) to a list of singular words
        def _convert_n_gram_to_words(_n_gram):
            _lemma_words = list()
            for _gram in _n_gram:
                _word = _gram[0]
                _pos_tag = _gram[1]
                _lemma_words.append(_word)
            return " ".join(_lemma_words)

        candidates = list()
        # Extract n_gram from each sentence
        for i, sentence in enumerate(sentences):
            try:
                words = word_tokenize(sentence)
                pos_tags = pos_tag(words)
                # Pass pos tag tuple (word, pos-tag) of each word in the sentence to produce n-grams
                _n_grams = list(ngrams(pos_tags, n_gram_range))
                # Filter out not qualified n_grams that contain stopwords or the word is not alpha_numeric
                for _n_gram in _n_grams:
                    if _is_qualified(_n_gram):
                        n_gram_words = _convert_n_gram_to_words(_n_gram)
                        candidates.append(n_gram_words)  # Convert n_gram (a list of words) to a string
            except Exception as _err:
                print("Error occurred! {err}".format(err=_err))
        return candidates

    @staticmethod
    def output_key_phrase_group_LDA_topics(clusters, cluster_no_list, folder, case_name):
        # Produce the output for each cluster
        results = list()
        for cluster_no in cluster_no_list:
            cluster = next(cluster for cluster in clusters if cluster['Cluster'] == cluster_no)
            result = {'cluster': cluster_no}
            # Added the grouped key phrase
            for i, group in enumerate(cluster['KeyPhrases']):
                # Convert the dictionary to a list
                word_docIds = group['word_docIds'].items()
                word_docIds = sorted(word_docIds, key=lambda w: w[1], reverse=True)
                result['group_' + str(i) + '_score'] = group['score']
                result['group_' + str(i)] = word_docIds

            # Added the LDA topics
            for i, topic in enumerate(cluster['LDATopics']):
                # Convert the dictionary to a list
                word_docIds = topic['word_docIds'].items()
                word_docIds = sorted(word_docIds, key=lambda w: w[1], reverse=True)
                result['LDATopic_' + str(i) + '_score'] = topic['score']
                result['LDATopic_' + str(i)] = word_docIds
            results.append(result)
        # Write to csv
        df = pd.DataFrame(results)
        path = os.path.join(folder, case_name + '_cluster_key_phrases_LDA_topics_summary.csv')
        df.to_csv(path, encoding='utf-8', index=False)

    # Group the doc (articles) by individual term
    @staticmethod
    def group_docs_by_terms(n_gram_range, doc_ids, doc_texts, topics_per_cluster):
        p = inflect.engine()

        # Convert the singular topic into the topic in plural form
        def get_plural_topic_form(_topic):
            # Get plural nouns of topic
            words = _topic.split(" ")
            last_word = words[-1]
            # Get plural word
            plural_word = p.plural(last_word)
            plural_topic = words[:-1] + [plural_word]
            return " ".join(plural_topic)

        try:
            docs_per_topic = []
            # Go through each article and find if each topic appear in the article
            for doc_id, doc_text in zip(doc_ids, doc_texts):
                try:
                    # Convert the preprocessed text to n_grams
                    sentences = sent_tokenize(BERTModelDocClusterUtility.preprocess_text(doc_text))
                    # Obtain the n-grams from the text
                    n_grams = BERTModelDocClusterUtility.generate_n_gram_candidates(sentences, n_gram_range)
                    # For each topic, find out the document ids that contain the topic
                    for item in topics_per_cluster:
                        try:
                            topic = item['term']
                            score = item['score']
                            freq = item['freq']  # Total number of frequencies in this cluster
                            cluster_ids = item['cluster_ids']  # A list of cluster that topic appears
                            # The topic appears in the article
                            if topic in n_grams:
                                # Check if docs_per_topic contains the doc id
                                doc_topic = next((d for d in docs_per_topic if d['term'] == topic), None)
                                # Include the doc ids of the topics mentioned in the articles
                                if doc_topic:
                                    doc_topic['doc_ids'].append(doc_id)
                                else:
                                    docs_per_topic.append({'term': topic, 'score': score, 'freq': freq,
                                                           'cluster_ids': cluster_ids,
                                                           'plural': get_plural_topic_form(topic),
                                                           'doc_ids': [doc_id]})
                        except Exception as err:
                            print("Error occurred! {err}".format(err=err))
                except Exception as err:
                    print("Error occurred! {err}".format(err=err))
            # Sort topics by score
            sorted_docs_per_topics = sorted(docs_per_topic, key=lambda t: t['score'], reverse=True)
            return sorted_docs_per_topics
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # Get topics (n_grams) by using standard TF-IDF and the number of topic is max_length
    @staticmethod
    def get_n_gram_terms(approach, docs_per_cluster_df, folder):
        # A folder that stores all the topic results
        temp_folder = os.path.join(folder, 'temp')
        Path(temp_folder).mkdir(parents=True, exist_ok=True)

        # Convert the texts of all clusters into a list of document (a list of sentences) to derive n-gram candidates
        def _collect_cluster_docs(_docs_per_cluster_df):
            # Get the clustered texts
            clusters = _docs_per_cluster_df[approach].tolist()
            doc_texts_per_cluster = _docs_per_cluster_df['Text'].tolist()
            _docs = []
            for cluster_no, doc_texts in zip(clusters, doc_texts_per_cluster):
                doc_list = []
                for doc_text in doc_texts:
                    try:
                        if isinstance(doc_text, str):
                            text = BERTModelDocClusterUtility.preprocess_text(doc_text.strip())
                            sentences = sent_tokenize(text)
                            doc_list.extend(sentences)
                    except Exception as _err:
                        print("Error occurred! {err}".format(err=_err))
                _docs.append({'cluster': cluster_no, 'doc': doc_list})  # doc: a list of sentences
            # Convert the frequency matrix to data frame
            df = pd.DataFrame(_docs, columns=['cluster', 'doc'])
            path = os.path.join(temp_folder, 'Step_1_cluster_doc.csv')
            # Write to temp output for validation
            df.to_csv(path, encoding='utf-8', index=False)
            return _docs

        # Create frequency matrix to track the frequencies of a n-gram in
        def _create_frequency_matrix(_docs, _n_gram_range):
            # Vectorized the clustered doc text and Keep the Word case unchanged
            frequency_matrix = []
            for doc in docs:
                cluster_no = doc['cluster']  # doc id is the cluster no
                sentences = doc['doc']
                freq_table = {}
                n_grams = BERTModelDocClusterUtility.generate_n_gram_candidates(sentences, _n_gram_range)
                for n_gram in n_grams:
                    n_gram_text = n_gram.lower()
                    if n_gram_text in freq_table:
                        freq_table[n_gram_text] += 1
                    else:
                        freq_table[n_gram_text] = 1
                frequency_matrix.append({'cluster': cluster_no, 'freq_table': freq_table})
            # Convert the frequency matrix to data frame
            df = pd.DataFrame(frequency_matrix, columns=['cluster', 'freq_table'])
            # Write to temp output for validation
            path = os.path.join(temp_folder, 'Step_2_frequency_matrix.csv')
            df.to_csv(path, encoding='utf-8', index=False)
            return frequency_matrix

        # Compute TF score
        def _compute_tf_matrix(_freq_matrix):
            _tf_matrix = {}
            # Compute tf score for each cluster (doc) in the corpus
            for _row in _freq_matrix:
                _cluster_no = _row['cluster']  # Doc id is the cluster no
                _freq_table = _row['freq_table']  # Store the frequencies of each word in the doc
                _tf_table = {}  # TF score of each word (1,2,3-grams) in the doc
                _total_topics_in_doc = reduce(lambda total, f: total + f, _freq_table.values(),
                                              0)  # Adjusted for total number of words in doc
                for _topic, _freq in _freq_table.items():
                    # frequency of a word in doc / total number of words in doc
                    _tf_table[_topic] = _freq / _total_topics_in_doc
                _tf_matrix[_cluster_no] = _tf_table
            return _tf_matrix

        # Collect the table to store the mapping between word to a list of clusters
        def _create_occs_per_topic(_freq_matrix):
            _occ_table = {}  # Store the mapping between a word and its doc ids
            for _row in _freq_matrix:
                _cluster_no = _row['cluster']  # Doc id is the cluster no
                _freq_table = _row['freq_table']  # Store the frequencies of each word in the doc
                for _topic, _count in _freq_table.items():
                    if _topic in _occ_table:  # Add the table if the word appears in the doc
                        _occ_table[_topic].add(_cluster_no)
                    else:
                        _occ_table[_topic] = {_cluster_no}
            # Convert the doc per word table (a dictionary) to data frame
            _df = pd.DataFrame(list(_occ_table.items()))
            # Write to temp output for validation
            _path = os.path.join(temp_folder, 'Step_3_occs_per_topic.csv')
            _df.to_csv(_path, encoding='utf-8', index=False)
            return _occ_table

        # Compute IDF scores
        def _compute_idf_matrix(_freq_matrix, _occ_per_topic):
            _total_cluster = len(_freq_matrix)  # Total number of clusters in the corpus
            _idf_matrix = {}  # Store idf scores for each doc
            for _row in _freq_matrix:
                _cluster_no = _row['cluster']  # Doc id is the cluster no
                _freq_table = _row['freq_table']  # Store the frequencies of each word in the doc
                _idf_table = {}
                for _topic in _freq_table.keys():
                    _counts = len(_occ_per_topic[_topic])  # Number of clusters the word appears
                    _idf_table[_topic] = math.log10(_total_cluster / float(_counts))
                _idf_matrix[_cluster_no] = _idf_table  # Idf table stores each word's idf scores
            return _idf_matrix

        # Compute tf-idf score matrix
        def _compute_tf_idf_matrix(_tf_matrix, _idf_matrix, _freq_matrix, _occ_per_topic):
            _tf_idf_matrix = {}
            # Compute tf-idf score for each cluster
            for _cluster_no, _tf_table in _tf_matrix.items():
                # Compute tf-idf score of each word in the cluster
                _idf_table = _idf_matrix[_cluster_no]  # idf table stores idf scores of the doc (doc_id)
                # Get freq table of the cluster
                _freq_table = next(f for f in _freq_matrix if f['cluster'] == _cluster_no)['freq_table']
                _tf_idf_list = []
                for _term, _tf_score in _tf_table.items():  # key is word, value is tf score
                    try:
                        _idf_score = _idf_table[_term]  # Get idf score of the word
                        _freq = _freq_table[_term]  # Get the frequencies of the word in cluster doc_id
                        _cluster_ids = sorted(list(_occ_per_topic[_term]))  # Get the clusters that the word appears
                        _score = float(_tf_score * _idf_score)
                        _tf_idf_list.append({'term': _term, 'score': _score, 'freq': _freq,
                                             'cluster_ids': _cluster_ids})
                    except Exception as _err:
                        print("Error occurred! {err}".format(err=_err))
                # Sort tf_idf_list by tf-idf score
                _tf_idf_matrix[str(_cluster_no)] = sorted(_tf_idf_list, key=lambda t: t['score'], reverse=True)
            return _tf_idf_matrix

        # Step 1. Convert each cluster of documents (one or more articles) into a single document
        docs = _collect_cluster_docs(docs_per_cluster_df)
        terms_list = []
        for n_gram_range in [1, 2]:
            try:
                # 2. Create the Frequency matrix of the words in each document (a cluster of articles)
                freq_matrix = _create_frequency_matrix(docs, n_gram_range)
                # 3. Compute Term Frequency (TF) and generate a matrix
                # Term frequency (TF) is the frequency of a word in a document divided by total number of words in the document.
                tf_matrix = _compute_tf_matrix(freq_matrix)
                # 4. Create the table to map the word to a list of documents
                occ_per_topic = _create_occs_per_topic(freq_matrix)
                # 5. Compute IDF (how common or rare a word is) and output the results as a matrix
                idf_matrix = _compute_idf_matrix(freq_matrix, occ_per_topic)
                # Compute tf-idf matrix
                tf_idf_matrix = _compute_tf_idf_matrix(tf_matrix, idf_matrix, freq_matrix, occ_per_topic)
                # Top_n_word is a dictionary where key is the cluster no and the value is a list of topic words
                terms_list.append({
                    'n_gram': n_gram_range,
                    'terms': tf_idf_matrix
                })
            except Exception as err:
                print("Error occurred! {err}".format(err=err))

        term_df = pd.DataFrame(terms_list, columns=['n_gram', 'terms'])
        # Write the topics results to csv
        term_df.to_json(os.path.join(temp_folder, 'TF-IDF_cluster_n_gram_terms.json'), orient='records')
        return terms_list  # Return a list of dicts

    # Output the cluster topics extracted by TF-IDF as a csv file
    @staticmethod
    def flatten_tf_idf_terms(cluster_no, folder):
        try:
            path = os.path.join(folder, 'TF-IDF_cluster_term_n_grams.json')
            cluster_df = pd.read_json(path)
            clusters = cluster_df.to_dict("records")
            cluster = next(cluster for cluster in clusters if cluster['Cluster'] == cluster_no)
            results = []
            for i in range(20):
                result = {'1-gram': "", '1-gram-score': 0, '1-gram-freq': 0, '1-gram-docs': 0, '1-gram-clusters': 0,
                          '2-gram': "", '2-gram-score': 0, '2-gram-freq': 0, '2-gram-docs': 0, '2-gram-clusters': 0,
                          'N-gram': "", 'N-gram-score': 0, 'N-gram-freq': 0, 'N-gram-docs': 0, 'N-gram-clusters': 0,
                          }
                for n_gram_num in ['1-gram', '2-gram', 'N-gram']:
                    try:
                        if i < len(cluster['Term-' + n_gram_num]):
                            n_gram = cluster['Term-' + n_gram_num][i]
                            result[n_gram_num] = n_gram['term']
                            result[n_gram_num + '-score'] = n_gram['score']
                            result[n_gram_num + '-freq'] = n_gram['freq']
                            result[n_gram_num + '-docs'] = len(n_gram['doc_ids'])
                            result[n_gram_num + '-clusters'] = len(n_gram['cluster_ids'])
                    except Exception as err:
                        print("Error occurred! {err}".format(err=err))
                results.append(result)
            n_gram_df = pd.DataFrame(results)
            path = os.path.join(folder, 'TF-IDF_cluster_#' + str(cluster_no) + '_flatten_terms.csv')
            n_gram_df.to_csv(path, encoding='utf-8', index=False)
            print('Output topics per cluster to ' + path)
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # Filter the overlapping topics of mix-grams (1, 2, 3) in a cluster, e.g. 'air' and 'air temperature' can be merged
    # if they appear in the same set of articles and the same set of clusters. 'air' topic can be merged to 'air temperature'
    @staticmethod
    def merge_n_gram_terms(n_gram_topics):
        try:
            # Sort n-grams by score
            sorted_n_grams = sorted(n_gram_topics, key=lambda _n_gram: _n_gram['score'], reverse=True)
            duplicate_topics = set()
            # Scan the mixed n_gram_topic and find duplicated topics to another topic
            for n_gram_topic in sorted_n_grams:
                topic = n_gram_topic['term']
                score = n_gram_topic['score']
                freq = n_gram_topic['freq']
                cluster_ids = set(n_gram_topic['cluster_ids'])  # a set of cluster ids
                doc_ids = set(n_gram_topic['doc_ids'])
                # Scan if any other sub topic have the same freq and cluster_ids and share similar topics
                # The topic (such as 'air') is a substring of another topic ('air temperature') so 'air' is duplicated
                relevant_topics = list(
                    filter(lambda _n_gram: _n_gram['term'] != topic and topic in _n_gram['term'] and
                                           _n_gram['freq'] == freq and
                                           len(set(_n_gram['doc_ids']) - doc_ids) == 0 and
                                           len(set(_n_gram['cluster_ids']) - cluster_ids) == 0,
                           sorted_n_grams))
                if len(relevant_topics) > 0:  # We have found other relevant topics that can cover this topic
                    duplicate_topics.add(topic)
            # Removed duplicated topics and single char (such as 'j')
            filter_topics = list(
                filter(lambda _n_gram: len(_n_gram['term']) > 1 and _n_gram['term'] not in duplicate_topics,
                       sorted_n_grams))
            # Sort by the score and  The resulting topics are mostly 2 or 3 grams
            filter_sorted_topics = sorted(filter_topics, key=lambda _n_gram: _n_gram['score'], reverse=True)
            return filter_sorted_topics[:50]  # Get top 50 topics
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    @staticmethod
    def visualise_cluster_results_by_iteration(title, results, file_path):
        try:
            df = pd.DataFrame(results)
            total_clusters = df['HDBSCAN_Cluster'].max() + 1
            # Visualise HDBSCAN clustering results using dot chart
            colors = sns.color_palette('tab20', n_colors=total_clusters).as_hex()
            marker_size = 8
            # Plot clustered dots and outliers
            fig = go.Figure()
            for cluster_no in range(0, total_clusters):
                dots = df.loc[df['HDBSCAN_Cluster'] == cluster_no, :]
                if len(dots) > 0:
                    marker_color = colors[cluster_no]
                    marker_symbol = 'circle'
                    name = 'Cluster {no}'.format(no=cluster_no)
                    fig.add_trace(go.Scatter(
                        name=name,
                        mode='markers',
                        x=dots['x'].tolist(),
                        y=dots['y'].tolist(),
                        marker=dict(line_width=1, symbol=marker_symbol,
                                    size=marker_size, color=marker_color)
                    ))
            # Add outliers
            outliers = df.loc[df['HDBSCAN_Cluster'] == -1, :]
            if len(outliers) > 0:
                fig.add_trace(go.Scatter(
                    name='Outlier',
                    mode='markers',
                    x=outliers['x'].tolist(),
                    y=outliers['y'].tolist(),
                    marker=dict(line_width=1, symbol='x',
                                size=2, color='gray', opacity=0.3)
                ))

            # title = 'Iteration = ' + str(iteration)
            # Figure layout
            fig.update_layout(title=title,
                              width=600, height=800,
                              legend=dict(orientation="v"),
                              margin=dict(l=20, r=20, t=30, b=40))
            # file_path = os.path.join(folder, 'iteration_' + str(iteration) + ".png")
            fig.write_image(file_path, format='png')
            print(
                "Output the images of clustered results to {path}".format(path=file_path))
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # Get the top 10 terms (obtained by TF-IDF) to represent the cluster
    @staticmethod
    def get_cluster_terms(terms, top_n=10):
        # Get top 10 terms
        cluster_terms = terms[:top_n]
        # Sort the cluster terms by number of docs and freq
        cluster_terms = sorted(cluster_terms, key=lambda t: (len(t['doc_ids']), t['freq']), reverse=True)
        # print(cluster_terms)
        return cluster_terms

    # Get the topic words from each group of key phrases
    @staticmethod
    def collect_topic_words_from_key_phrases(key_phrases, doc_n_grams):
        # create a mapping between word and frequencies
        def create_word_freq_list(_key_phrases, _doc_n_grams):
            def _create_bi_grams(_words):
                _bi_grams = list()
                if len(_words) == 2:
                    _bi_grams.append(_words[0] + " " + _words[1])
                elif len(_words) == 3:
                    _bi_grams.append(_words[1] + " " + _words[2])
                return _bi_grams

            # Get the docs containing the word
            def _get_doc_ids_by_key_phrase(_key_phrase, _doc_n_grams):
                doc_ids = list()
                for doc in _doc_n_grams:
                    doc_id = doc[0]
                    n_grams = doc[1]
                    found = list(filter(lambda n_gram: key_phrase.lower() == n_gram.lower(), n_grams))
                    if len(found) > 0:
                        doc_ids.append(doc_id)
                return doc_ids

            _word_freq_list = list()
            # Collect word frequencies from the list of key phrases.
            for key_phrase in key_phrases:
                try:
                    key_phrase_doc_ids = _get_doc_ids_by_key_phrase(key_phrase, _doc_n_grams)
                    words = key_phrase.split()
                    n_grams = words + _create_bi_grams(words)
                    # print(n_grams)
                    for n_gram in n_grams:
                        r = len(n_gram.split(" "))
                        found = next((wf for wf in _word_freq_list if wf['word'].lower() == n_gram.lower()), None)
                        if not found:
                            wf = {'word': n_gram.lower(), 'freq': 1, 'range': r, 'doc_ids': key_phrase_doc_ids}
                            if n_gram.isupper():
                                wf['word'] = n_gram
                            _word_freq_list.append(wf)
                        else:
                            # Updated doc id
                            found['freq'] += 1
                            found['doc_ids'] = found['doc_ids'] + key_phrase_doc_ids
                            # Remove duplicates
                            found['doc_ids'] = list(dict.fromkeys(found['doc_ids']))
                except Exception as err:
                    print("Error occurred! {err}".format(err=err))
            return _word_freq_list

        # Update top word frequencies and pick up top words that increase the maximal coverage
        def pick_top_words(_top_words, _candidate_words, _top_n):
            # Go through top_words and check if other top words can be merged.
            # For example, 'traffic prediction' can be merged to 'traffic'
            try:
                for i in range(0, len(_top_words)):
                    top_word = _top_words[i]
                    top_word_doc_ids = top_word['doc_ids']
                    for doc_id in top_word_doc_ids:
                        # Go through the remaining words and updates its doc_ids
                        for j in range(i+1, len(_top_words)):
                            other_word = _top_words[j]
                            other_word['doc_ids'] = list(filter(lambda id: id != doc_id, other_word['doc_ids']))
                        # Go through each candidate words
                        for k in range(0, len(_candidate_words)):
                            candidate_word = _candidate_words[k]
                            # Update the doc_id from
                            candidate_word['doc_ids'] = list(filter(lambda id: id != doc_id, candidate_word['doc_ids']))
                # Remove top word that does not have any doc
                _top_words = list(filter(lambda w: len(w['doc_ids']) > 0, _top_words))
                # Add the candidate words if any top word is removed from the list
                if len(_top_words) < _top_n:
                    # Sort all the words by doc_ids and frequencies
                    _candidate_words = sorted(_candidate_words, key=lambda wf: (len(wf['doc_ids']), wf['freq']), reverse=True)
                    all_words = _top_words + _candidate_words
                    return all_words[:_top_n]
                return _top_words
            except Exception as err:
                print("Error occurred! {err}".format(err=err))

        # Check if
        def is_found(_word, _new_top_words):
            _found = next((nw for nw in _new_top_words if nw['word'] == _word['word']), None)
            if _found:
                return True
            return False

        word_freq_list = create_word_freq_list(key_phrases, doc_n_grams)
        # Pick up top 5 frequent words
        top_n = 5
        # Sort by freq and the number of docs
        word_freq_list = sorted(word_freq_list, key=lambda wf: (wf['freq'], len(wf['doc_ids'])), reverse=True)
        print(word_freq_list)
        word_freq_clone = copy.deepcopy(word_freq_list)
        top_words = word_freq_clone[:top_n]
        candidate_words = word_freq_clone[top_n:]
        # is_same = False
        # iteration = 0
        # while not is_same and iteration < 10:
        #     # Pass the copy array to the function to avoid change the values of 'top_word' 'candidate_words'
        #     new_top_words = pick_top_words(top_words, candidate_words, top_n)
        #     # Check if new and old top words are the same
        #     is_same = True
        #     for new_word in new_top_words:
        #         found = next((w for w in top_words if w['word'] == new_word['word']), None)
        #         if not found:
        #             is_same = is_same & False
        #     # Make a copy of wfl
        #     word_freq_clone = copy.deepcopy(word_freq_list)
        #     # Replace the old top words with new top words
        #     top_words = list(filter(lambda word: is_found(word, new_top_words), word_freq_clone))
        #     candidate_words = list(filter(lambda word: not is_found(word, new_top_words), word_freq_clone))
        #     iteration += 1
        # Sort the top words by freq
        sorted(top_words, key=lambda wf: wf['freq'], reverse=True)
        # Return the top 3
        return list(map(lambda w: w['word'], top_words[:5]))

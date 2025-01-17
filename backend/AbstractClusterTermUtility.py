# Utility for finding article clusters
import math
import os
import re
import string
import sys
from functools import reduce
from pathlib import Path

import inflect
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
import umap
from nltk import sent_tokenize, word_tokenize, pos_tag, ngrams
from nltk.corpus import stopwords
from sklearn.metrics import pairwise_distances, silhouette_samples, silhouette_score

from AbstractClusterBERTUtility import AbstractClusterBERTUtility


class AbstractClusterTermUtility:
    # Static variable
    stop_words = list(stopwords.words('english'))

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
                            _word.lower() in AbstractClusterTermUtility.stop_words or _pos_tag not in qualified_tags:
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
    def get_n_gram_freq_terms(docs_per_cluster, cluster_no, n_gram_range):
        # Convert the texts of all clusters into a list of document (a list of sentences) to derive n-gram candidates
        def _collect_doc_terms(_cluster_docs, _n_gram_range):
            _doc_terms = []
            for _doc_id, _doc_text in zip(_cluster_docs['DocId'], _cluster_docs['Text']):
                try:
                    _text = AbstractClusterBERTUtility.preprocess_text(_doc_text.strip())
                    _sentences = sent_tokenize(_text)
                    _n_gram_terms = AbstractClusterTermUtility.generate_n_gram_candidates(_sentences, _n_gram_range)
                    _doc_terms.append({'DocId': _doc_id, 'terms': _n_gram_terms})
                except Exception as _err:
                    print("Error occurred! {err}".format(err=_err))
            return _doc_terms  #

        # Create frequency table to track the frequency of a term within a cluster
        def _create_freq_table(_doc_terms, _n_gram_range):
            # keep track of freq table
            _freq_table = {}
            for _doc_term in _doc_terms:
                for _term in _doc_term['terms']:
                    _term = _term.lower()
                    if _term in _freq_table:
                        _freq_table[_term] += 1
                    else:
                        _freq_table[_term] = 1
            return _freq_table

        # # Create range table to track the range of a term within a cluster
        # # Range: the number of abstracts a term appears within a cluster
        def _create_range_table(_freq_table, _doc_terms, _n_gram_range):
            _n_gram_terms = list(_freq_table.keys())
            _range_table = {}
            for _doc_term in _doc_terms:
                _doc_id = _doc_term['DocId']
                _terms = list(map(lambda t: t.lower(), _doc_term['terms']))
                # Check if the term appears in the abstract
                for _n_gram_term in _n_gram_terms:
                    if _n_gram_term in _terms:
                        if _n_gram_term not in _range_table:
                            _range_table[_n_gram_term] = list()
                        _range_table[_n_gram_term].append(_doc_id)
            return _range_table

        try:
            cluster_docs = next(docs for docs in docs_per_cluster if docs['Cluster'] == cluster_no)
            doc_terms = _collect_doc_terms(cluster_docs, n_gram_range)
            freq_table = _create_freq_table(doc_terms, n_gram_range)
            range_table = _create_range_table(freq_table, doc_terms, n_gram_range)
            # Merge freq and range dict
            n_gram_terms = list(freq_table.keys())
            results = list()
            for term in n_gram_terms:
                _freq = freq_table[term]
                _range = range_table[term]
                _score = _freq + len(_range)
                # _score = 0.4* _freq + 0.6* len(_range)
                results.append({'term': term, 'freq': _freq, 'range': len(_range), 'score': _score,
                                'doc_ids': _range})
            # Sort results by freq
            results = sorted(results, key=lambda r: r['score'], reverse=True)
            # results = sorted(results, key=lambda r: (r['range'], r['freq']), reverse=True)
            return results
        except Exception as _err:
            print("Error occurred! {err}".format(err=_err))
            sys.exit(-1)

    # Get topics (n_grams) by using standard TF-IDF and the number of topic is max_length
    @staticmethod
    def get_n_gram_tf_idf_terms(docs_per_cluster_df, folder, is_load=False):
        # A folder that stores all the topic results
        temp_folder = os.path.join(folder, 'temp')
        Path(temp_folder).mkdir(parents=True, exist_ok=True)
        if is_load:
            path = os.path.join(temp_folder, 'TF-IDF_cluster_n_gram_terms.json')
            term_list = pd.read_json(path).to_dict("records")
            return term_list

        # Convert the texts of all clusters into a list of document (a list of sentences) to derive n-gram candidates
        def _collect_cluster_docs(_docs_per_cluster_df):
            # Get the clustered texts
            clusters = _docs_per_cluster_df['Cluster'].tolist()
            doc_texts_per_cluster = _docs_per_cluster_df['Text'].tolist()
            _docs = []
            for cluster_no, doc_texts in zip(clusters, doc_texts_per_cluster):
                doc_list = []
                for doc_text in doc_texts:
                    try:
                        if isinstance(doc_text, str):
                            text = AbstractClusterBERTUtility.preprocess_text(doc_text.strip())
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
                n_grams = AbstractClusterTermUtility.generate_n_gram_candidates(sentences, _n_gram_range)
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
        for n_gram_range in [2]:
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
                    sentences = sent_tokenize(AbstractClusterBERTUtility.preprocess_text(doc_text))
                    # Obtain the n-grams from the text
                    n_grams = AbstractClusterTermUtility.generate_n_gram_candidates(sentences, n_gram_range)
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

    # Get the cluster parameters such as min_samples, dimension and min cluster size
    @staticmethod
    def update_clustering_scores(iterative_folder, model):
        # Load Clustering parameters
        path = os.path.join(iterative_folder, 'cluster_terms', 'iterative_clusters',
                            'AIMLUrbanStudyCorpus_iterative_summary.json')
        parameters = pd.read_json(path).to_dict("records")
        # Load all docs (including clean texts)
        path = os.path.join(iterative_folder, 'cluster', 'iteration_0', 'vectors', 'doc_vector_results.json')
        docs = pd.read_json(path).to_dict("records")
        iterations = np.unique(list(map(lambda p: p['iteration'], parameters)))
        updated_parameters = list()
        for iteration in iterations:
            try:
                # Find the parameters matching with doc_ids
                matched_parameters = list(filter(lambda c: c['iteration'] == iteration, parameters))
                assert len(matched_parameters) > 0, "Cannot find the parameters of an iteration"
                # Collect all the doc vectors and labels of the matched
                texts = []
                cluster_labels = []
                for parameter in matched_parameters:
                    cluster_no = parameter['Cluster']
                    for doc_id in parameter['DocIds']:
                        doc = next(doc for doc in docs if doc['DocId'] == doc_id)
                        assert doc is not None, "Cannot find doc"
                        texts.append(doc['Text'])
                        # cluster_doc_vectors.append(np_doc_vector)
                        cluster_labels.append(cluster_no)
                dimension = matched_parameters[0]['dimension']
                # Get all doc vectors
                doc_vectors = model.encode(texts, show_progress_bar=True)
                # Reduce the dimension of doc vectors into 2D to facilitate visualisation
                reduced_vectors = umap.UMAP(n_neighbors=150,
                                            min_dist=0,
                                            n_components=dimension,
                                            random_state=42,
                                            metric='cosine').fit_transform(doc_vectors.tolist())
                # Compute the cosine distance/similarity for each doc vectors
                distances = pairwise_distances(reduced_vectors, metric='cosine')
                # avg_score = silhouette_score(distances.tolist(), cluster_labels, metric='cosine')
                # print(avg_score)
                # Compute Silhouette Score of each individual cluster
                silhouette_scores = silhouette_samples(distances.tolist(), cluster_labels, metric='cosine')
                # print(silhouette_scores)
                # Update the score of each iterative clusters
                for parameter in matched_parameters:
                    cluster_no = parameter['Cluster']
                    cluster_silhouette_vals = silhouette_scores[np.array(cluster_labels) == cluster_no]
                    parameter['score'] = np.mean(cluster_silhouette_vals)
                    updated_parameters.append(parameter)
            except Exception as _err:
                print("Error occurred! {err}".format(err=_err))
                sys.exit(-1)
        df = pd.DataFrame(updated_parameters)
        # Write out to iterative summary
        path = os.path.join(iterative_folder, 'cluster_terms', 'iterative_clusters',
                            'AIMLUrbanStudyCorpus_iterative_summary.csv')
        df.to_csv(path, encoding='utf-8', index=False)
        # Write article corpus to a json file
        path = os.path.join(iterative_folder, 'cluster_terms', 'iterative_clusters',
                            'AIMLUrbanStudyCorpus_iterative_summary.json')
        df.to_json(path, orient='records')

    # Get TFIDF terms from each article by using standard TF-IDF
    @staticmethod
    def get_TFIDF_terms_from_individual_article(docs, folder, is_load=False):
        # Load the precomputed
        if is_load:
            path = os.path.join(folder, 'abstract_TFIDF_terms.json')
            return pd.read_json(path).to_dict("records")

        # Create frequency matrix to track the frequencies of n-grams
        def _create_frequency_matrix(_docs, _n_gram_range):
            # Clean the article text and convert the text into a list of sentences
            def _tokenize_docs(_docs):
                # Get the clustered texts
                _clean_docs = []
                for _doc in _docs:
                    _doc_text = _doc['Title'] + '. ' + _doc['Abstract']
                    _sentence_list = []
                    try:
                        _clean_text = AbstractClusterBERTUtility.preprocess_text(_doc_text.strip())
                        _sentence_list.extend(sent_tokenize(_clean_text))
                    except Exception as _err:
                        print("Error occurred! {err}".format(err=_err))
                    _clean_docs.append(_sentence_list)  # sentence_list: a list of sentences
                assert len(_clean_docs) == len(_docs), "Clean docs size is not correct"
                return _clean_docs

            # Tokenize the doc text
            _doc_sentences = _tokenize_docs(docs)
            # Compute the frequencies of n_grams
            _frequency_matrix = []
            for _sentences in _doc_sentences:
                _freq_table = {}  # Key: n_gram, Value: frequencies
                _n_gram_candidates = AbstractClusterTermUtility.generate_n_gram_candidates(_sentences,
                                                                                               _n_gram_range)
                for _n_gram in _n_gram_candidates:
                    _n_gram_text = _n_gram.lower()  # Lower the word cases to unify the words
                    if _n_gram_text in _freq_table:
                        _freq_table[_n_gram_text] += 1
                    else:
                        _freq_table[_n_gram_text] = 1
                _frequency_matrix.append(_freq_table)
            assert len(_frequency_matrix) == len(docs), "Inconsistent docs and frequencies"
            return _frequency_matrix

        # Compute TF score
        def _compute_tf_matrix(_docs, _freq_matrix):
            _tf_matrix = []
            # Compute tf score for each doc in the corpus
            for _freq_table in _freq_matrix:
                # Store the frequencies of each word in the doc
                _tf_table = {}  # TF score of each word (1,2, 3-grams) in the doc
                # Adjusted for total number of words in each doc
                _total_freq_in_doc = reduce(lambda total, f: total + f, _freq_table.values(), 0)
                for _term, _freq in _freq_table.items():
                    # frequency of a word in doc / total number of words in doc
                    _tf_table[_term] = _freq / _total_freq_in_doc
                _tf_matrix.append(_tf_table)
            return _tf_matrix

        # Collect the term occurrences across all docs
        def _create_occ_per_term(_docs, _freq_matrix):
            _occ_table = {}  # Store the mapping between a word and its doc ids
            for _doc, _freq_table in zip(_docs, _freq_matrix):
                _doc_id = _doc['DocId']
                for _term, _count in _freq_table.items():
                    if _term in _occ_table:  # Add the table if the word appears in the doc
                        _occ_table[_term].add(_doc_id)
                    else:
                        _occ_table[_term] = {_doc_id}
            return _occ_table

        # Compute IDF scores
        def _compute_idf_matrix(_docs, _freq_matrix, _occ_per_term):
            _total_docs = len(_docs)  # Total number of docs in the corpus
            _idf_matrix = []  # Store idf scores for each doc
            for _doc, _freq_table in zip(_docs, _freq_matrix):
                _doc_id = _doc['DocId']  # Doc id is the cluster no
                _idf_table = {}
                for _term in _freq_table.keys():
                    _occurrences = len(_occ_per_term[_term])  # Number of docs that a term appears
                    assert _occurrences > 0, "Occurrence is 0"
                    # Use the log to scale the scores
                    _idf_table[_term] = math.log10(_total_docs / float(_occurrences))
                _idf_matrix.append(_idf_table)  # Idf table stores each word's idf scores
            assert len(_idf_matrix) == len(_docs), "Inconsistent size"
            return _idf_matrix

        # Compute tf-idf score matrix
        def _compute_tf_idf_matrix(_tf_matrix, _idf_matrix, _freq_matrix, _occ_per_topic):
            _tf_idf_matrix = []
            # Compute tf-idf score for each cluster
            for _index, _tf_table in enumerate(_tf_matrix):
                # Compute tf-idf score of each word in the cluster
                _idf_table = _idf_matrix[_index]  # idf table stores idf scores of the doc (doc_id)
                # Get freq table of the cluster
                _freq_table = _freq_matrix[_index]
                _tf_idf_list = []
                for _term, _tf_score in _tf_table.items():  # key is word, value is tf score
                    try:
                        _idf_score = _idf_table[_term]  # Get idf score of the word
                        _freq = _freq_table[_term]  # Get the frequencies of the word in cluster doc_id
                        _doc_ids = sorted(list(_occ_per_topic[_term]))  # Get the clusters that the word appears
                        _score = float(_tf_score * _idf_score)
                        _tf_idf_list.append({'term': _term, 'score': _score, 'freq': _freq,
                                             'num_docs': len(_doc_ids), 'doc_ids': _doc_ids,
                                             'tf-score': _tf_score, 'idf-score': _idf_score})
                    except Exception as _err:
                        print("Error occurred! {err}".format(err=_err))
                # Sort tf_idf_list by tf-idf score
                _tf_idf_matrix.append(sorted(_tf_idf_list, key=lambda t: t['score'], reverse=True))
            return _tf_idf_matrix

        n_gram_results = {}
        for n_gram_range in [2]:
            try:
                # 2. Create the Frequency matrix of the words in each document (a cluster of articles)
                freq_matrix = _create_frequency_matrix(docs, n_gram_range)
                # 3. Compute Term Frequency (TF) and generate a matrix
                # Term frequency (TF) is the frequency of a word in a document divided by total number of words in the document.
                tf_matrix = _compute_tf_matrix(docs, freq_matrix)
                # 4. Create the table to map the word to a list of documents
                occ_per_term = _create_occ_per_term(docs, freq_matrix)
                # 5. Compute IDF (how common or rare a word is) and output the results as a matrix
                idf_matrix = _compute_idf_matrix(docs, freq_matrix, occ_per_term)
                # Compute tf-idf matrix
                tf_idf_matrix = _compute_tf_idf_matrix(tf_matrix, idf_matrix, freq_matrix, occ_per_term)
                # Top_n_word is a dictionary where key is the cluster no and the value is a list of topic words
                n_gram_results[n_gram_range] = tf_idf_matrix
            except Exception as err:
                print("Error occurred! {err}".format(err=err))
                sys.exit(-1)
        # sample_docs = [287, 367, 477]
        Path(os.path.join(folder, 'docs')).mkdir(parents=True, exist_ok=True)
        results = list()
        for index, doc in enumerate(docs):
            try:
                doc_id = doc['DocId']
                # Get 2-gram term
                bi_grams = n_gram_results[2][index]
                results.append({'DocId': doc_id, 'Terms': bi_grams})
            except Exception as err:
                print("Error occurred! {err}".format(err=err))
        path = os.path.join(folder, 'abstract_TFIDF_terms.json')
        df = pd.DataFrame(results)
        df.to_json(path, orient='records')
        return results  # Return a list of dicts

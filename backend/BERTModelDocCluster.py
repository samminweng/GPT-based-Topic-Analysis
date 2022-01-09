import os
from argparse import Namespace
import logging
from functools import reduce
import hdbscan
import numpy as np
import pandas as pd
import nltk
# # Sentence Transformer (https://www.sbert.net/index.html)
from sentence_transformers import SentenceTransformer
from nltk.tokenize import sent_tokenize, word_tokenize
import umap  # (UMAP) is a dimension reduction technique https://umap-learn.readthedocs.io/en/latest/
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import pairwise_distances
from BERTModelDocClusterUtility import BERTModelDocClusterUtility
import pickle
import seaborn as sns  # statistical graph library
import getpass

# Set logging level
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
# Set NLTK data path
nltk_path = os.path.join('/Scratch', getpass.getuser(), 'nltk_data')
if os.name == 'nt':
    nltk_path = os.path.join("C:", os.sep, "Users", getpass.getuser(), "nltk_data")
# Download all the necessary NLTK data
nltk.download('punkt', download_dir=nltk_path)
nltk.download('averaged_perceptron_tagger', download_dir=nltk_path)
nltk.download('stopwords', download_dir=nltk_path)
# Append NTLK data path
nltk.data.path.append(nltk_path)
# Set Sentence Transformer path
sentence_transformers_path = os.path.join('/Scratch', getpass.getuser(), 'SentenceTransformer')
if os.name == 'nt':
    sentence_transformers_path = os.path.join("C:", os.sep, "Users", getpass.getuser(), "SentenceTransformer")
Path(sentence_transformers_path).mkdir(parents=True, exist_ok=True)


# Cluster the document using BERT model
# Ref: https://towardsdatascience.com/topic-modeling-with-bert-779f7db187e6
class BERTModelDocCluster:
    def __init__(self):
        self.args = Namespace(
            case_name='CultureUrbanStudyCorpus',
            path='data',
            # We switched to 'sentence-transformers/all-mpnet-base-v2' which is suitable for clustering with
            # 768 dimensional dense vectors (https://huggingface.co/sentence-transformers/all-mpnet-base-v2)
            model_name='all-mpnet-base-v2',
            device='cpu',
            n_neighbors=150,
            min_dist=0.0,
            dimensions=[768, 400, 350, 300, 250, 200, 150, 100, 95, 90, 85, 80, 75, 70, 65, 60,
                        55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 9, 8, 7, 6, 5]
        )
        # BERTModelDocClusterUtility.clean_corpus(self.args.case_name)
        path = os.path.join('data', self.args.case_name, self.args.case_name + '_cleaned.csv')
        self.text_df = pd.read_csv(path)
        # # # # Load all document vectors without outliers
        self.text_df['Text'] = self.text_df['Title'] + ". " + self.text_df['Abstract']
        # # # # # # Create the folder path for output clustering files (csv and json)
        folder = os.path.join('output', self.args.case_name, 'cluster', 'doc_vectors')
        # Load doc vectors of Urban study corpus generated by BERT transformer model
        path = os.path.join(folder, self.args.model_name + '_embeddings.pkl')
        with open(path, "rb") as fIn:
            stored_data = pickle.load(fIn)
            self.text_df['DocVectors'] = stored_data['embeddings'].tolist()
        # Reduce the dimension of doc vectors into 2D to facilitate visualisation
        reduced_vectors = umap.UMAP(n_neighbors=self.args.n_neighbors,
                                    min_dist=self.args.min_dist,
                                    n_components=2,
                                    random_state=42,
                                    metric='cosine').fit_transform(self.text_df['DocVectors'].tolist())
        self.text_df['x'] = list(map(lambda x: round(x, 2), reduced_vectors[:, 0]))
        self.text_df['y'] = list(map(lambda y: round(y, 2), reduced_vectors[:, 1]))
        # Print out the reduced vector
        print(self.text_df)

    # Get the sentence embedding from the transformer model
    # Sentence transformer is based on transformer model (BERTto compute the vectors for sentences or paragraph (a number of sentences)
    def get_sentence_vectors(self):
        def clean_sentence(_sentences):
            # Preprocess the sentence
            cleaned_sentences = list()  # Skip copy right sentence
            for sentence in _sentences:
                if u"\u00A9" not in sentence.lower() and 'licensee' not in sentence.lower() \
                        and 'copyright' not in sentence.lower() and 'rights reserved' not in sentence.lower():
                    try:
                        cleaned_words = word_tokenize(sentence.lower())
                        # Keep alphabetic characters only and remove the punctuation
                        cleaned_sentences.append(" ".join(cleaned_words))  # merge tokenized words into sentence
                    except Exception as _err:
                        print("Error occurred! {err}".format(err=_err))
            return cleaned_sentences

        # Collect all the texts
        texts = list()
        # Search all the subject words
        for i, row in self.text_df.iterrows():
            try:
                sentences = clean_sentence(sent_tokenize(row['Text']))  # Clean the sentences
                text = " ".join(sentences)
                texts.append(text)
            except Exception as _err:
                print("Error occurred! {err}".format(err=_err))
        # Load Sentence Transformer
        model = SentenceTransformer(self.args.model_name, cache_folder=sentence_transformers_path,
                                    device=self.args.device)
        doc_vectors = model.encode(texts, show_progress_bar=True)
        folder = os.path.join('output', self.args.case_name, 'cluster', 'doc_vectors')
        Path(folder).mkdir(parents=True, exist_ok=True)
        path = os.path.join(folder, self.args.model_name + '_embeddings.pkl')
        # Store sentences & embeddings on disc
        with open(path, "wb") as f_out:
            pickle.dump({'texts': texts, 'embeddings': doc_vectors}, f_out,
                        protocol=pickle.HIGHEST_PROTOCOL)

    # Experiment UMAP + HDBSCAN clustering and evaluate the clustering results with 'Silhouette score'
    def evaluate_HDBSCAN_cluster_quality(self):
        # Collect clustering results and find outliers and the cluster of minimal size
        def collect_cluster_results(_results, _cluster_label):
            try:
                _found = next((r for r in _results if r['cluster_no'] == _cluster_label), None)
                if not _found:
                    _results.append({'cluster_no': _cluster_label, 'count': 1})
                else:
                    _found['count'] += 1
                return _results
            except Exception as _err:
                print("Error occurred! {err}".format(err=_err))

        try:
            # Experiment HDBSCAN clustering with different dimensions of vectors
            for dimension in self.args.dimensions:
                # Apply UMAP to reduce the dimensions of document vectors
                if dimension < 768:
                    # Run HDBSCAN on reduced dimensional vectors
                    reduced_vectors = umap.UMAP(
                        n_neighbors=self.args.n_neighbors,
                        min_dist=self.args.min_dist,
                        n_components=dimension,
                        random_state=42,
                        metric="cosine").fit_transform(self.text_df['DocVectors'].tolist())
                else:
                    # Run HDBSCAN on raw vectors
                    dimension = len(self.text_df.iloc[0]['DocVectors'])
                    reduced_vectors = np.vstack(self.text_df['DocVectors'])  # Convert to 2D numpy array
                # Store experiment results
                results = list()
                # Experiment HDBSCAN clustering with different parameters
                for min_samples in [None] + list(range(1, 21)):
                    for min_cluster_size in range(5, 21):
                        for epsilon in [0.0]:
                            result = {'dimension': dimension,
                                      'min_cluster_size': min_cluster_size,
                                      'min_samples': str(min_samples),
                                      'epsilon': epsilon,
                                      'outliers': 'None',
                                      'total_clusters': 'None',
                                      'cluster_results': 'None',
                                      'Silhouette_score': 'None'}
                            try:
                                df = pd.DataFrame()
                                # Compute the cosine distance/similarity for each doc vectors
                                distances = pairwise_distances(reduced_vectors, metric='cosine')
                                # Cluster reduced vectors using HDBSCAN
                                labels = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size,
                                                         min_samples=min_samples,
                                                         cluster_selection_epsilon=epsilon,
                                                         metric='precomputed').fit_predict(
                                    distances.astype('float64')).tolist()
                                # Aggregate the cluster results
                                cluster_results = reduce(lambda pre, cur: collect_cluster_results(pre, cur),
                                                         labels, list())
                                # Sort the results
                                cluster_results = sorted(cluster_results, key=lambda c: c['cluster_no'])
                                df['clusters'] = labels
                                df['vectors'] = distances.tolist()
                                # Sort cluster result by count
                                result['cluster_labels'] = labels
                                result['outliers'] = next(
                                    (cr['count'] for cr in cluster_results if cr['cluster_no'] == -1), 0)
                                result['total_clusters'] = len(cluster_results)
                                result['cluster_results'] = cluster_results
                                # Compute silhouette score for clustered dots
                                cluster_df = df[df['clusters'] != -1]
                                if len(cluster_df) > 0:
                                    cluster_labels = cluster_df['clusters'].tolist()
                                    cluster_vectors = np.vstack(cluster_df['vectors'].tolist())
                                    result['Silhouette_score'] = BERTModelDocClusterUtility.compute_Silhouette_score(
                                        cluster_labels,
                                        cluster_vectors)
                            except Exception as _err:
                                print("Error occurred! {err}".format(err=_err))
                            print(result)
                            results.append(result)
                # Output the clustering results of a dimension
                folder = os.path.join('output', self.args.case_name, 'cluster', 'experiments', 'hdbscan')
                Path(folder).mkdir(parents=True, exist_ok=True)
                # Output the detailed clustering results
                result_df = pd.DataFrame(results,
                                         columns=['dimension', 'min_samples', 'min_cluster_size', 'epsilon',
                                                  'Silhouette_score', 'total_clusters', 'outliers',
                                                  'cluster_results', 'cluster_labels'])
                # Output cluster results to CSV
                path = os.path.join(folder, 'HDBSCAN_cluster_doc_vector_results_' + str(dimension) + '.csv')
                result_df.to_csv(path, encoding='utf-8', index=False)
                path = os.path.join(folder, 'HDBSCAN_cluster_doc_vector_results_' + str(dimension) + '.json')
                result_df.to_json(path, orient='records')
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # Output the summary of HDBSCAN clustering results and plots the clustering dot chart
    def summarize_HDBSCAN_cluster_experiment_results(self):
        try:
            # Find the best results in each dimension
            d_results = list()
            parent_folder = os.path.join('output', self.args.case_name, 'cluster')
            folder = os.path.join(parent_folder, 'experiments', 'hdbscan')
            for dimension in self.args.dimensions:
                path = os.path.join(folder, 'HDBSCAN_cluster_doc_vector_results_' + str(dimension) + '.json')
                df = pd.read_json(path)
                results = df.to_dict("records")
                d_result = {'dimension': dimension, 'Silhouette_score': 0}
                for result in results:
                    score = result['Silhouette_score']
                    # Check if the score is better than 'best' parameter
                    if score != 'None' and float(score) >= d_result['Silhouette_score']:
                        d_result['Silhouette_score'] = float(score)
                        d_result['min_samples'] = None if result['min_samples'] == 'None' else int(
                            result['min_samples'])
                        d_result['min_cluster_size'] = int(result['min_cluster_size'])
                        d_result['epsilon'] = float(result['epsilon'])
                        d_result['total_clusters'] = result['total_clusters']
                        d_result['outliers'] = result['outliers']
                        d_result['cluster_results'] = result['cluster_results']
                        d_result['cluster_labels'] = result['cluster_labels']
                d_results.append(d_result)
            # Output the best clustering results
            d_result_df = pd.DataFrame(d_results,
                                       columns=['dimension', 'min_samples', 'min_cluster_size', 'epsilon',
                                                'Silhouette_score', 'total_clusters', 'outliers',
                                                'cluster_results', 'cluster_labels'])
            folder = os.path.join(parent_folder, 'experiments')
            path = os.path.join(folder, 'HDBSCAN_cluster_doc_vector_result_summary.csv')
            d_result_df.to_csv(path, encoding='utf-8', index=False)
            path = os.path.join(folder, 'HDBSCAN_cluster_doc_vector_result_summary.json')
            d_result_df.to_json(path, orient='records')
            # Get the highest score of d_results
            # # Load all document vectors without outliers
            df = self.text_df.copy(deep=True)
            # # # Reduce the doc vectors to 2 dimension using UMAP dimension reduction for visualisation
            for d_result in d_results:
                # Apply UMAP to reduce the dimensions of document vectors
                cluster_labels = d_result['cluster_labels']
                folder = os.path.join(parent_folder, 'experiments', 'hdbscan', 'images')
                Path(folder).mkdir(parents=True, exist_ok=True)
                # Output cluster results to png files
                BERTModelDocClusterUtility.visualise_cluster_results(cluster_labels,
                                                                     df['x'].tolist(), df['y'].tolist(),
                                                                     d_result, folder)
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # Cluster document vectors with HDBSCAN using best parameters obtained from experiment results
    def cluster_doc_vectors_with_best_parameter_by_hdbscan(self):
        try:
            parent_folder = os.path.join('output', self.args.case_name, 'cluster')
            # Load best clustering results at each dimension
            path = os.path.join(parent_folder, 'experiments',
                                'HDBSCAN_cluster_doc_vector_result_summary.json')
            df = pd.read_json(path)
            df = df.sort_values(by=['Silhouette_score'], ascending=False)
            best_result = df.head(1).to_dict(orient='records')[0]

            # Get the parameter of the best clustering results
            cluster_df = self.text_df.copy(deep=True)
            dimension = int(best_result['dimension'])
            min_cluster_size = int(best_result['min_cluster_size'])
            min_samples = int(best_result['min_samples'])
            epsilon = float(best_result['epsilon'])
            # Reduce the doc vectors to specific dimension
            reduced_vectors = umap.UMAP(
                n_neighbors=self.args.n_neighbors,
                min_dist=self.args.min_dist,
                n_components=dimension,
                random_state=42,
                metric="cosine").fit_transform(cluster_df['DocVectors'].tolist())
            # Compute the cosine distance/similarity for each doc vectors
            distances = pairwise_distances(reduced_vectors, metric='cosine')
            # Cluster the documents with minimal cluster size using HDBSCAN
            # Ref: https://hdbscan.readthedocs.io/en/latest/index.html
            clusters = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size,
                                       min_samples=min_samples,
                                       cluster_selection_epsilon=epsilon,
                                       metric='precomputed'
                                       ).fit(distances.astype('float64'))
            # Update the cluster to 'cluster_df'
            cluster_labels = clusters.labels_.tolist()
            cluster_df['HDBSCAN_Cluster'] = cluster_labels
            # Re-index and re-order the columns of cluster data frame
            cluster_df = cluster_df.reindex(columns=['HDBSCAN_Cluster', 'DocId',
                                                     'Cited by', 'Year', 'Document Type', 'Title', 'Abstract',
                                                     'Author Keywords', 'Authors', 'DOI', 'x', 'y'])
            # Output the result to csv and json file
            path = os.path.join(parent_folder, self.args.case_name + '_clusters.csv')
            cluster_df.to_csv(path, encoding='utf-8', index=False)
            # Output to a json file
            path = os.path.join(parent_folder, self.args.case_name + '_clusters.json')
            cluster_df.to_json(path, orient='records')
            print('Output the clustered results to ' + path)
            # Output HDBSCAN clustering information (condense tree)
            folder = os.path.join(parent_folder, 'hdbscan_clustering')
            Path(folder).mkdir(parents=True, exist_ok=True)
            # Output cluster results to png
            BERTModelDocClusterUtility.visualise_cluster_results(cluster_labels,
                                                                 cluster_df['x'].tolist(), cluster_df['y'].tolist(),
                                                                 best_result, folder)
            # Output condense tree of the best cluster results
            condense_tree = clusters.condensed_tree_
            # Save condense tree to csv
            tree_df = condense_tree.to_pandas()
            path = os.path.join(folder, 'HDBSCAN_cluster_tree.csv')
            tree_df.to_csv(path, encoding='utf-8')
            # Plot condense tree graph
            condense_tree.plot(select_clusters=True,
                               selection_palette=sns.color_palette('deep', 40),
                               label_clusters=True,
                               max_rectangles_per_icicle=150)
            image_path = os.path.join(folder, 'HDBSCAN_clustering_condense_tree.png')
            plt.savefig(image_path)
            print("Output HDBSCAN clustering image to " + image_path)
            return best_result
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # Derive the topic words from each cluster of documents
    def derive_topics_from_cluster_docs_by_TF_IDF(self):
        approach = 'HDBSCAN_Cluster'
        try:
            parent_folder = os.path.join('output', self.args.case_name, 'cluster')
            path = os.path.join(parent_folder, self.args.case_name + '_clusters.json')
            # Load the documents clustered by
            clustered_doc_df = pd.read_json(path)
            # Update text column
            clustered_doc_df['Text'] = clustered_doc_df['Title'] + ". " + clustered_doc_df['Abstract']
            # Group the documents and doc_id by clusters
            docs_per_cluster_df = clustered_doc_df.groupby([approach], as_index=False) \
                .agg({'DocId': lambda doc_id: list(doc_id), 'Text': lambda text: list(text)})
            # Get top 100 topics (1, 2, 3 grams) for each cluster
            n_gram_topic_list = BERTModelDocClusterUtility.get_n_gram_topics(approach, docs_per_cluster_df,
                                                                             parent_folder, is_load=False)
            results = []
            for i, cluster in docs_per_cluster_df.iterrows():
                try:
                    cluster_no = cluster[approach]
                    doc_ids = cluster['DocId']
                    doc_texts = cluster['Text']
                    result = {"Cluster": cluster_no, 'NumDocs': len(doc_ids), 'DocIds': doc_ids}
                    n_gram_topics = []
                    # Collect the topics of 1 gram, 2 gram and 3 gram
                    for n_gram_range in [1, 2, 3]:
                        n_gram_topic = next(n_gram_topic for n_gram_topic in n_gram_topic_list
                                            if n_gram_topic['n_gram'] == n_gram_range)
                        # Collect top 300 topics of a cluster
                        cluster_topics = n_gram_topic['topics'][str(cluster_no)][:300]
                        # Create a mapping between the topic and its associated articles (doc)
                        doc_per_topic = BERTModelDocClusterUtility.group_docs_by_topics(n_gram_range,
                                                                                        doc_ids, doc_texts,
                                                                                        cluster_topics)
                        n_gram_type = 'Topic-' + str(n_gram_range) + '-gram'
                        result[n_gram_type] = doc_per_topic
                        n_gram_topics += doc_per_topic
                    result['Topic-N-gram'] = BERTModelDocClusterUtility.merge_n_gram_topic(n_gram_topics)
                    results.append(result)
                    print('Collect the clustered results of cluster #{no}'.format(no=cluster_no))
                except Exception as _err:
                    print("Error occurred! {err}".format(err=_err))
            # Write the result to csv and json file
            cluster_df = pd.DataFrame(results, columns=['Cluster', 'NumDocs', 'DocIds',
                                                        'Topic-1-gram', 'Topic-2-gram', 'Topic-3-gram', 'Topic-N-gram'])
            folder = os.path.join(parent_folder, 'topics', 'n_grams')
            Path(folder).mkdir(parents=True, exist_ok=True)
            path = os.path.join(folder, 'TF-IDF_cluster_topic_n_grams.csv')
            cluster_df.to_csv(path, encoding='utf-8', index=False)
            # # # Write to a json file
            path = os.path.join(folder, 'TF-IDF_cluster_topic_n_grams.json')
            cluster_df.to_json(path, orient='records')
            print('Output topics per cluster to ' + path)
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # Combine TF-IDF and BERT key phrase extraction Topics into a single file
    def combine_and_summary_topics_from_clusters(self):
        try:
            parent_folder = os.path.join('output', self.args.case_name, 'cluster', 'topics')
            folder = os.path.join(parent_folder, 'n_grams')
            # Load cluster topics
            path = os.path.join(folder, 'TF-IDF_cluster_topic_n_grams.json')
            tf_idf_df = pd.read_json(path)
            # Write out to csv and json file
            cluster_df = tf_idf_df.reindex(columns=['Cluster', 'NumDocs', 'DocIds', 'Topic-N-gram'])
            cluster_df.rename(columns={'Topic-N-gram': 'TF-IDF-Topics'}, inplace=True)
            total_clusters = cluster_df['Cluster'].max() + 1
            # # Output top 50 topics by 1, 2 and 3-grams at specific cluster
            for cluster_no in range(-1, total_clusters):
                BERTModelDocClusterUtility.flatten_tf_idf_topics(cluster_no, folder)
            # Output cluster df to csv or json file
            folder = os.path.join('output', self.args.case_name, 'cluster')
            path = os.path.join(folder, self.args.case_name + '_TF-IDF_cluster_topics.csv')
            cluster_df.to_csv(path, encoding='utf-8', index=False)
            path = os.path.join(folder, self.args.case_name + '_TF-IDF_cluster_topics.json')
            cluster_df.to_json(path, orient='records')
            # Output a summary of top 10 Topics of each cluster
            clusters = cluster_df.to_dict("records")
            summary_df = cluster_df.copy(deep=True)
            total = summary_df['NumDocs'].sum()
            summary_df['Percent'] = list(map(lambda c: c['NumDocs'] / total, clusters))
            summary_df['Topics'] = list(
                map(lambda c: ", ".join(list(map(lambda t: t['topic'], c['TF-IDF-Topics'][:10]))), clusters))
            summary_df = summary_df.reindex(columns=['Cluster', 'NumDocs', 'Percent', 'DocIds', 'Topics'])
            # Output the summary as csv
            path = os.path.join(parent_folder, 'TF-IDF_cluster_topic_summary.csv')
            summary_df.to_csv(path, encoding='utf-8', index=False)

        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # # Re-cluster outliers and see if any clusters can be found in the outliers
    def re_cluster_outliers_by_hdbscan(self):
        try:
            # Get the outliers identified by HDBSCAN
            folder = os.path.join('output', self.args.case_name, 'cluster')
            path = os.path.join(folder, self.args.case_name + '_clusters.json')
            # Get the best clustering of highest silhouette score
            cluster_df = pd.read_json(path)
            # # Get all the outliers
            outlier_df = cluster_df[cluster_df['HDBSCAN_Cluster'] == -1]
            outlier_df = outlier_df.drop(columns=['HDBSCAN_Cluster', 'x', 'y'])
            # Re-order
            print('The number of outliers {c}'.format(c=len(outlier_df)))
            folder = os.path.join('data', self.args.case_name + '_Outlier')
            path = os.path.join(folder, self.args.case_name + '_Outlier_cleaned.csv')
            # Save outlier df to another corpus
            outlier_df.to_csv(path, encoding='utf-8', index=False)
        except Exception as err:
            print("Error occurred! {err}".format(err=err))


# Main entry
if __name__ == '__main__':
    try:
        mdc = BERTModelDocCluster()
        # mdc.get_sentence_vectors()
        # mdc.evaluate_HDBSCAN_cluster_quality()
        # mdc.summarize_HDBSCAN_cluster_experiment_results()
        # mdc.cluster_doc_vectors_with_best_parameter_by_hdbscan()
        # mdc.derive_topics_from_cluster_docs_by_TF_IDF()
        # mdc.combine_and_summary_topics_from_clusters()
        # mdc.re_cluster_outliers_by_hdbscan()
    except Exception as err:
        print("Error occurred! {err}".format(err=err))

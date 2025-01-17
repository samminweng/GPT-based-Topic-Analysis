from datetime import datetime
import os
import sys
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

import seaborn as sns  # statistical graph library
import getpass

# Set logging level
from AbstractClusterBERTUtility import AbstractClusterBERTUtility

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
class AbstractClusterBERT:
    def __init__(self, _iteration):  # , _cluster_no):
        self.args = Namespace(
            case_name='AIMLUrbanStudyCorpus',
            # cluster_no=_cluster_no,
            # cluster_folder='cluster_' + str(_cluster_no),
            iteration=_iteration,
            in_folder='iteration_' + str(_iteration),
            path='data',
            # We switched to 'sentence-transformers/all-mpnet-base-v2' which is suitable for clustering with
            # 768 dimensional dense vectors (https://huggingface.co/sentence-transformers/all-mpnet-base-v2)
            model_name='all-mpnet-base-v2',
            device='cpu',
            n_neighbors=150,
            min_dist=0.0,
            dimensions=[768, 200, 150, 100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20],
            min_samples=[30, 25, 20, 15, 10],
            # min_samples=[None],
            min_cluster_size=[100, 80, 50]
            # min_cluster_size=[10, 15, 20, 25, 30, 35, 40, 45, 50]
        )
        # BERTModelDocClusterUtility.clean_corpus(self.args.case_name)
        path = os.path.join('data', self.args.case_name,  # self.args.cluster_folder,
                            self.args.in_folder, self.args.case_name + '_cleaned.csv')
        self.text_df = pd.read_csv(path)
        # # # # # Load all document vectors without outliers
        self.text_df['Text'] = self.text_df['Title'] + ". " + self.text_df['Abstract']
        # Filter out dimensions > the length of text df
        self.args.dimensions = list(filter(lambda d: d < len(self.text_df) - 5 and d != 768, self.args.dimensions))
        print(self.text_df)

    # Get the sentence embedding from the transformer model
    # Sentence transformer is based on transformer model (BERTto compute the vectors for sentences or paragraph (a number of sentences)
    def get_sentence_vectors(self, is_load=False):
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

        if is_load:
            # Get all the doc ids of text_df
            doc_ids = self.text_df['DocId'].tolist()
            # Load doc vectors
            path = os.path.join('output', self.args.case_name,  # self.args.cluster_folder,
                                'cluster', self.args.in_folder, 'vectors', 'doc_vector_results.json')
            df = pd.read_json(path)
            df = df[df['DocId'].isin(doc_ids)]
            # Add 'DocVectors' 'x' and 'y'
            self.text_df['DocVectors'] = df['DocVectors'].tolist()
            self.text_df['x'] = df['x'].apply(lambda x: round(x, 2)).tolist()
            self.text_df['y'] = df['y'].apply(lambda y: round(y, 2)).tolist()
        else:
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
            self.text_df['DocVectors'] = doc_vectors.tolist()
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
        folder = os.path.join('output', self.args.case_name,  # self.args.cluster_folder,
                              'cluster', self.args.in_folder, 'vectors')
        Path(folder).mkdir(parents=True, exist_ok=True)
        path = os.path.join(folder, 'doc_vector_results.csv')
        self.text_df.to_csv(path, encoding='utf-8', index=False)
        path = os.path.join(folder, 'doc_vector_results.json')
        self.text_df.to_json(path, orient='records')

    # Experiment UMAP + HDBSCAN clustering and evaluate the clustering results with 'Silhouette score'
    def run_HDBSCAN_cluster_experiments(self):
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
                    reduced_vectors = np.vstack(self.text_df['DocVectors'])  # Convert to 2D numpy array
                start = datetime.now()
                # Store experiment results
                results = list()
                # Experiment HDBSCAN clustering with different parameters
                for min_samples in self.args.min_samples:
                    for min_cluster_size in self.args.min_cluster_size:
                        for epsilon in [0.0]:
                            result = {'dimension': dimension,
                                      'min_cluster_size': min_cluster_size,
                                      'min_samples': str(min_samples) if min_samples is not None else 'None',
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
                                    result['Silhouette_score'] = AbstractClusterBERTUtility.compute_Silhouette_score(
                                        cluster_labels,
                                        cluster_vectors)
                            except Exception as _err:
                                print("Error occurred! {err}".format(err=_err))
                                sys.exit(-1)
                            # print(result)
                            results.append(result)
                end = datetime.now()
                difference = (end - start).total_seconds()
                print("Experiment time difference {d} second".format(d=difference))
                print("Complete clustering the vectors at dimension = {d}".format(d=dimension))
                # Output the clustering results of a dimension
                folder = os.path.join('output', self.args.case_name,  # self.args.cluster_folder,
                                      'cluster', self.args.in_folder, 'experiments', 'hdbscan')
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
            parent_folder = os.path.join('output', self.args.case_name,     # self.args.cluster_folder,
                                         'cluster', self.args.in_folder)
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
                folder = os.path.join(parent_folder, 'experiments', 'images')
                Path(folder).mkdir(parents=True, exist_ok=True)
                # Output cluster results to png files
                AbstractClusterBERTUtility.visualise_cluster_results(cluster_labels,
                                                                     df['x'].tolist(), df['y'].tolist(),
                                                                     d_result, folder)
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # Cluster document vectors with HDBSCAN using best parameters obtained from experiment results
    def cluster_doc_vectors_with_best_parameter_by_hdbscan(self):
        try:
            parent_folder = os.path.join('output', self.args.case_name,     # self.args.cluster_folder,
                                         'cluster', self.args.in_folder)
            # Load best clustering results at each dimension
            path = os.path.join(parent_folder, 'experiments',
                                'HDBSCAN_cluster_doc_vector_result_summary.json')
            ex_results = pd.read_json(path).to_dict("records")
            sorted_ex_results = sorted(ex_results, key=lambda e: e['Silhouette_score'], reverse=True)
            best_result = sorted_ex_results[0]
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
            AbstractClusterBERTUtility.visualise_cluster_results(cluster_labels,
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

    # Collect the documents of each cluster
    def derive_cluster_docs(self):
        approach = 'HDBSCAN_Cluster'
        try:
            parent_folder = os.path.join('output', self.args.case_name,     # self.args.cluster_folder,
                                         'cluster', self.args.in_folder)
            path = os.path.join(parent_folder, self.args.case_name + '_clusters.json')
            # Load the documents clustered by
            clustered_doc_df = pd.read_json(path)
            # Update text column
            clustered_doc_df['Text'] = clustered_doc_df['Title'] + ". " + clustered_doc_df['Abstract']
            # Group the documents and doc_id by clusters
            docs_per_cluster_df = clustered_doc_df.groupby([approach], as_index=False) \
                .agg({'DocId': lambda doc_id: list(doc_id), 'Text': lambda text: list(text)})
            # Write the result to csv and json file
            cluster_df = docs_per_cluster_df[['HDBSCAN_Cluster', 'DocId', 'Text']]
            cluster_df = cluster_df.rename(columns={'DocId': 'DocIds'})
            cluster_df['NumDocs'] = cluster_df['DocIds'].apply(len)
            total = cluster_df['NumDocs'].sum()
            cluster_df['Percent'] = cluster_df['NumDocs'].apply(lambda c: c / total)
            # Reorder the columns
            cluster_df = cluster_df[['HDBSCAN_Cluster', 'Percent', 'NumDocs', 'DocIds']]
            # Output the cluster summary as csv
            path = os.path.join(parent_folder, self.args.case_name + '_cluster_docs.csv')
            cluster_df.to_csv(path, encoding='utf-8', index=False)
            path = os.path.join(parent_folder, self.args.case_name + '_cluster_docs.json')
            cluster_df.to_json(path, orient='records')
            print('Output cluster docs to ' + path)
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # # Re-cluster outliers and see if any clusters can be found in the outliers
    def output_outliers_as_corpus(self):
        try:
            # Get the outliers identified by HDBSCAN
            folder = os.path.join('output', self.args.case_name,    # self.args.cluster_folder,
                                  'cluster', self.args.in_folder)
            path = os.path.join(folder, self.args.case_name + '_clusters.json')
            # Get the best clustering of highest silhouette score
            cluster_df = pd.read_json(path)
            # # Get all the outliers
            outlier_df = cluster_df[cluster_df['HDBSCAN_Cluster'] == -1]
            outlier_df = outlier_df.drop(columns=['HDBSCAN_Cluster', 'x', 'y'])
            # Re-order
            print('The number of outliers {c}'.format(c=len(outlier_df)))
            folder = os.path.join('data', self.args.case_name,  # self.args.cluster_folder,
                                  'iteration_' + str(self.args.iteration + 1))
            Path(folder).mkdir(parents=True, exist_ok=True)
            path = os.path.join(folder, self.args.case_name + '_cleaned.csv')
            # Save outlier df to another corpus
            outlier_df.to_csv(path, encoding='utf-8', index=False)
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

        # Collect all the article clusters < 40 articles as a single file

    def collect_article_cluster_results(self):
        folder = os.path.join('output', self.args.case_name)
        # Load corpus
        corpus_path = os.path.join(folder, 'iteration', self.args.case_name + '_clusters.json')
        corpus = pd.read_json(corpus_path).to_dict("records")
        folder_names = ['cluster_0', 'cluster_1', 'cluster_2', 'cluster_3', 'iteration', 'cluster_-1']
        cluster_results = list()
        article_results = list()
        current_cluster_no = 1
        for folder_name in folder_names:
            try:
                iterative_folder = os.path.join(folder, folder_name)
                cluster_path = os.path.join(iterative_folder,
                                            self.args.case_name + '_cluster_terms_key_phrases_LDA_topics.json')
                clusters = pd.read_json(cluster_path).to_dict("records")
                # filter cluster > 40 articles
                clusters = list(filter(lambda c: len(c['DocIds']) < 40, clusters))
                for cluster in clusters:
                    doc_ids = cluster['DocIds']
                    score = cluster['Score']
                    # Get all the articles
                    articles = list(filter(lambda a: a['DocId'] in doc_ids, corpus))
                    assert len(articles) < 40, "Article cluster > 40"
                    assert len(articles) > 0, "Article cluster is empty"
                    assert len(articles) == len(doc_ids), "Article cluster is not matched"
                    # Update the cluster and articles
                    for article in articles:
                        article['Cluster'] = current_cluster_no
                        article['Score'] = score
                    article_results = article_results + articles
                    cluster['Cluster'] = current_cluster_no
                    current_cluster_no = current_cluster_no + 1
                # Add the cluster results
                cluster_results = cluster_results + clusters
            except Exception as _err:
                print("Error occurred! {err}".format(err=_err))
                sys.exit(-1)
        # Sort article results by DocId
        article_results = sorted(article_results, key=lambda c: c['DocId'])
        # Write article corpus
        articles_df = pd.DataFrame(article_results, columns=['Cluster', 'Score', 'DocId', 'Cited by', 'Year',
                                                             'Document Type', 'Title', 'Abstract', 'Author Keywords',
                                                             'Authors', 'DOI', 'x', 'y'])
        # articles_df = articles_df.rename(columns={"Cluster": "HDBSCAN_Cluster"})
        out_folder = os.path.join(folder, self.args.cluster_folder)
        Path(out_folder).mkdir(parents=True, exist_ok=True)
        # Write article corpus to csv file
        path = os.path.join(out_folder, self.args.case_name + '_clusters.csv')
        articles_df.to_csv(path, encoding='utf-8', index=False)
        # Write article corpus to a json file
        path = os.path.join(out_folder, self.args.case_name + '_clusters.json')
        articles_df.to_json(path, orient='records')


# Main entry
if __name__ == '__main__':
    try:
        # cluster_no = 2
        # BERTArticleClusterUtility.collect_cluster_as_corpus('AIMLUrbanStudyCorpus', cluster_no)
        # Re-cluster large cluster into sub-clusters
        iteration = 0
        mdc = AbstractClusterBERT(iteration)
        mdc.get_sentence_vectors(is_load=True)
        mdc.run_HDBSCAN_cluster_experiments()
        mdc.summarize_HDBSCAN_cluster_experiment_results()
        mdc.cluster_doc_vectors_with_best_parameter_by_hdbscan()
        mdc.derive_cluster_docs()
        mdc.output_outliers_as_corpus()
    except Exception as err:
        print("Error occurred! {err}".format(err=err))

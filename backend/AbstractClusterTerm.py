import getpass
import os
import sys
from argparse import Namespace
from pathlib import Path

import pandas as pd

from AbstractClusterTermUtility import AbstractClusterTermUtility

# Set Sentence Transformer path
sentence_transformers_path = os.path.join('/Scratch', getpass.getuser(), 'SentenceTransformer')
if os.name == 'nt':
    sentence_transformers_path = os.path.join("C:", os.sep, "Users", getpass.getuser(), "SentenceTransformer")
Path(sentence_transformers_path).mkdir(parents=True, exist_ok=True)


class AbstractClusterTermTFIDF:
    def __init__(self):
        self.args = Namespace(
            case_name='AIMLUrbanStudyCorpus',
            embedding_name='OpenAIEmbedding',
            model_name='curie',
            phase='abstract_clustering_phase',
            path='data',
        )

    # Derive the distinct from each cluster of documents
    def derive_cluster_terms_by_TFIDF(self):
        try:
            term_folder = os.path.join('output', self.args.case_name + '_' + self.args.embedding_name, self.args.phase,
                                       'cluster_terms')
            Path(term_folder).mkdir(parents=True, exist_ok=True)
            # Get the cluster docs
            path = os.path.join('output', self.args.case_name + '_' + self.args.embedding_name, self.args.phase,
                                self.args.case_name + '_clusters.json')
            # Load the documents clustered by
            clustered_doc_df = pd.read_json(path)
            # Update text column
            clustered_doc_df['Text'] = clustered_doc_df['Title'] + ". " + clustered_doc_df['Abstract']
            # Group the documents and doc_id by clusters
            docs_per_cluster_df = clustered_doc_df.groupby(['Cluster'], as_index=False) \
                .agg({'DocId': lambda doc_id: list(doc_id), 'Text': lambda text: list(text)})
            # Get 2-gram for each cluster
            n_gram_term_list = AbstractClusterTermUtility.get_n_gram_tf_idf_terms(docs_per_cluster_df,
                                                                                  term_folder,
                                                                                  is_load=False)
            # Load cluster results
            path = os.path.join('output', self.args.case_name + '_' + self.args.embedding_name, self.args.phase,
                                self.args.case_name + '_iterative_clustering_summary.json')
            cluster_result_df = pd.read_json(path)
            cluster_result_df['text'] = docs_per_cluster_df['Text']
            cluster_results = cluster_result_df.to_dict("records")
            # print(cluster_results)
            for cluster_result in cluster_results:
                try:
                    cluster_no = cluster_result['cluster']
                    doc_ids = cluster_result['doc_ids']
                    doc_texts = cluster_result['text']
                    # n_gram_terms = []
                    # Collect the 2-gram words
                    for n_gram_range in [2]:
                        n_gram = next(n_gram for n_gram in n_gram_term_list
                                      if n_gram['n_gram'] == n_gram_range)
                        # Collect top 300 terms
                        cluster_terms = n_gram['terms'][str(cluster_no)][:300]
                        # Create a mapping between the topic and its associated abstracts (docs)
                        doc_per_term = AbstractClusterTermUtility.group_docs_by_terms(n_gram_range,
                                                                                      doc_ids, doc_texts,
                                                                                      cluster_terms)
                        cluster_result[str(n_gram_range) + '-grams'] = doc_per_term
                        # n_gram_terms += doc_per_term
                    # result['Term-N-gram'] = AbstractClusterTermTFIDFUtility.merge_n_gram_terms(n_gram_terms)
                    # results.append(result)
                    print('Derive term of cluster #{no}'.format(no=cluster_no))
                except Exception as _err:
                    print("Error occurred! {err}".format(err=_err))
                    sys.exit(-1)
            # Write the result to csv and json file
            cluster_df = pd.DataFrame(cluster_results, columns=['cluster', '2-grams'])
            cluster_df.rename(columns={'2-grams': 'terms'}, inplace=True)
            folder = os.path.join(term_folder)
            Path(folder).mkdir(parents=True, exist_ok=True)
            path = os.path.join(folder, 'TFIDF_cluster_terms.csv')
            cluster_df.to_csv(path, encoding='utf-8', index=False)
            # # # Write to a json file
            path = os.path.join(folder, 'TFIDF_cluster_terms.json')
            cluster_df.to_json(path, orient='records')
            print('Output terms per cluster to ' + path)
        except Exception as err:
            print("Error occurred! {err}".format(err=err))

    # Extract distinct term from each abstract
    def derive_abstract_terms_by_TFIDF(self):
        try:
            # Load the corpus
            path = os.path.join('output', self.args.case_name + '_' + self.args.embedding_name, self.args.phase,
                                self.args.case_name + '_clusters.json')
            docs = pd.read_json(path).to_dict("records")
            folder = os.path.join('output', self.args.case_name + '_' + self.args.embedding_name, self.args.phase,
                                  'TFIDF_terms', 'abstract_terms')
            Path(folder).mkdir(parents=True, exist_ok=True)
            abstract_terms = AbstractClusterTermUtility.get_TFIDF_terms_from_individual_article(docs, folder,
                                                                                                is_load=True)
            # Update each doc with TFIDF terms
            for doc, terms in zip(docs, abstract_terms):
                doc_id = doc['DocId']
                assert terms['DocId'] == doc_id, "Cannot find TFIDF terms"
                doc['TFIDFTerms'] = terms['Terms']
            df = pd.DataFrame(docs)
            # Update the corpus with TFIDF terms
            df = df.reindex(columns=['Cluster', 'DocId', 'Cited by', 'Title', 'Author Keywords', 'Abstract',
                                     'Year', 'Source title', 'Authors', 'DOI', 'Document Type', 'x', 'y',
                                     'TFIDFTerms'])
            path = os.path.join('output', self.args.case_name + '_' + self.args.embedding_name, self.args.phase,
                                self.args.case_name + '_clusters.csv')
            df.to_csv(path, encoding='utf-8', index=False)
            # # # Write to a json file
            path = os.path.join('output', self.args.case_name + '_' + self.args.embedding_name, self.args.phase,
                                self.args.case_name + '_clusters.json')
            df.to_json(path, orient='records')
            print('Output TFIDF terms per doc to ' + path)
        except Exception as e:
            print("Error occurred! {err}".format(err=e))

    # Extract frequent terms per abstract cluster
    def derive_freq_terms_per_cluster(self):
        try:
            term_folder = os.path.join('output', self.args.case_name + '_' + self.args.embedding_name,
                                       self.args.phase, 'cluster_terms')
            Path(term_folder).mkdir(parents=True, exist_ok=True)
            folder = os.path.join('output', self.args.case_name + '_' + self.args.embedding_name, self.args.phase)
            # Get the cluster docs
            path = os.path.join(folder, self.args.case_name + '_clusters.json')
            # Load the documents clustered by
            clustered_doc_df = pd.read_json(path)
            # Update text column
            clustered_doc_df['Text'] = clustered_doc_df['Title'] + ". " + clustered_doc_df['Abstract']
            # Group the documents and doc_id by clusters
            docs_per_cluster_df = clustered_doc_df.groupby(['Cluster'], as_index=False) \
                .agg({'DocId': lambda doc_id: list(doc_id), 'Text': lambda text: list(text)})
            docs_per_clusters = docs_per_cluster_df.to_dict("records")
            # Load cluster results
            path = os.path.join(folder, self.args.case_name + '_iterative_clustering_summary.json')
            cluster_results = pd.read_json(path).to_dict("records")
            # Get top 10 frequent terms (2 grams) within each cluster
            for cluster_result in cluster_results:
                cluster_no = cluster_result['cluster']
                freq_terms = AbstractClusterTermUtility.get_n_gram_freq_terms(docs_per_clusters, cluster_no, 2)
                # Update with frequent terms
                cluster_result['freq_terms'] = freq_terms
                # Write output to csv
                df = pd.DataFrame(freq_terms)
                path = os.path.join(term_folder, 'freq_terms_cluster_' + str(cluster_no) + '.csv')
                df.to_csv(path, encoding='utf-8', index=False)
            # Write output to csv and json file
            df = pd.DataFrame(cluster_results)
            path = os.path.join(folder, self.args.case_name + '_cluster_terms.csv')
            df.to_csv(path, encoding='utf-8', index=False)
            path = os.path.join(folder, self.args.case_name + '_cluster_terms.json')
            df.to_json(path, orient='records')
        except Exception as err:
            print("Error occurred! {err}".format(err=err))


# Main entry
if __name__ == '__main__':
    try:
        ct = AbstractClusterTermTFIDF()
        # ct.derive_cluster_terms_by_TFIDF()
        # ct.derive_abstract_terms_by_TFIDF()
        ct.derive_freq_terms_per_cluster()
    except Exception as err:
        print("Error occurred! {err}".format(err=err))

# #  Summarize cluster terms and output to a single file
# def summarize_cluster_terms(self):
#     # Get top
#     def get_cluster_terms(terms, top_n=10):
#         # Get top 10 terms
#         cluster_terms = terms[:top_n]
#         # Sort the cluster terms by number of docs and freq
#         cluster_terms = sorted(cluster_terms, key=lambda t: (len(t['doc_ids']), t['freq']), reverse=True)
#         # print(cluster_terms)
#         return cluster_terms
#
#     try:
#         term_folder = os.path.join('output',  self.args.case_name + '_' + self.args.embedding_name,
#                                    self.args.phase, 'TFIDF_terms')
#         # Load cluster terms
#         path = os.path.join(term_folder, 'TFIDF_cluster_term.json')
#         cluster_df = pd.read_json(path)
#         # Write out to csv and json file
#         cluster_df['Terms'] = cluster_df['Terms'].apply(lambda terms: get_cluster_terms(terms, 10))
#         # # Output cluster df to csv or json file
#         path = os.path.join(term_folder, self.args.case_name + '_TFIDF_cluster_terms.csv')
#         cluster_df.to_csv(path, encoding='utf-8', index=False)
#         path = os.path.join(term_folder, self.args.case_name + '_TFIDF_cluster_terms.json')
#         cluster_df.to_json(path, orient='records')
#     except Exception as err:
#         print("Error occurred! {err}".format(err=err))
# Collect all iterative cluster results
# def collect_iterative_cluster_results(self):
#     cluster_folder = os.path.join('output', self.args.case_name, self.args.cluster_folder, 'cluster')
#     results = list()
#     # Go through each iteration 1 to last iteration
#     for i in range(0, self.args.last_iteration + 1):
#         try:
#             opt_dimension = 0
#             # Get the best dimension
#             folder = os.path.join(cluster_folder, self.args.in_folder + '_' + str(i))
#             clustering_folder = os.path.join(folder, 'hdbscan_clustering')
#             # Get the optimal dimension
#             for file in os.listdir(clustering_folder):
#                 file_name = file.lower()
#                 if file_name.endswith(".png") and file_name.startswith("dimension"):
#                     opt_dimension = int(file_name.split("_")[1].split(".png")[0])
#             # Get the best score of all clustering experiments
#             ex_folder = os.path.join(folder, 'experiments')
#             path = os.path.join(ex_folder, 'HDBSCAN_cluster_doc_vector_result_summary.json')
#             experiment_results = pd.read_json(path).to_dict("records")
#             best_result = next(r for r in experiment_results if r['dimension'] == opt_dimension)
#             min_samples = best_result['min_samples']
#             min_cluster_size = best_result['min_cluster_size']
#             score = best_result['Silhouette_score']
#             # Get summary of cluster topics
#             path = os.path.join(folder, self.args.case_name + '_cluster_docs.json')
#             clusters = pd.read_json(path).to_dict("records")
#             total_papers = reduce(lambda total, ct: ct['NumDocs'] + total, clusters, 0)
#             for cluster in clusters:
#                 results.append({
#                     "iteration": i, "total_papers": total_papers, "dimension": opt_dimension,
#                     "min_samples": min_samples, "min_cluster_size": min_cluster_size, "score": score,
#                     "Cluster": cluster['HDBSCAN_Cluster'], "NumDocs": cluster['NumDocs'],
#                     "Percent": cluster['Percent'],
#                     "DocIds": cluster['DocIds']
#                 })
#         except Exception as _err:
#             print("Error occurred! {err}".format(err=_err))
#     # Load the results as data frame
#     df = pd.DataFrame(results)
#     # Output cluster results to CSV
#     folder = os.path.join('output', self.args.case_name, self.args.cluster_folder, 'cluster_terms',
#                           'iterative_clusters')
#     Path(folder).mkdir(parents=True, exist_ok=True)
#     path = os.path.join(folder, self.args.case_name + '_iterative_summary.csv')
#     df.to_csv(path, encoding='utf-8', index=False)
#     path = os.path.join(folder, self.args.case_name + '_iterative_summary.json')
#     df.to_json(path, orient='records')
#     print(df)
#
# # Collect all the iterative cluster results and combine into a single cluster results
# # Output the iterative cluster results
# def output_iterative_cluster_results(self):
#     score_path = os.path.join('output', self.args.case_name, self.args.cluster_folder, 'cluster_terms',
#                               'iterative_clusters', self.args.case_name + '_iterative_summary.json')
#     scores = pd.read_json(score_path).to_dict("records")
#     # Load cluster results at 0 iteration as initial state
#     cur_cluster_no = -1
#     results = list()
#     # Go through each iteration 1 to last iteration
#     for iteration in range(0, self.args.last_iteration + 1):
#         try:
#             iter_score = list(filter(lambda s: s['iteration'] == iteration, scores))
#             score = iter_score[0]['score']
#             folder = os.path.join('output', self.args.case_name, self.args.cluster_folder, 'cluster')
#             # Load the clustered docs in each iteration
#             cluster_path = os.path.join(folder, self.args.in_folder + '_' + str(iteration),
#                                         self.args.case_name + '_clusters.json')
#             df = pd.read_json(cluster_path)
#             df['Score'] = score
#             cluster_df = df
#             total_cluster_no = cluster_df['HDBSCAN_Cluster'].max()
#             cluster_no_list = list(range(-1, total_cluster_no + 1))
#             # Added the clustered results
#             for cluster_no in cluster_no_list:
#                 # Get the clustered docs
#                 c_df = cluster_df[cluster_df['HDBSCAN_Cluster'] == cluster_no]
#                 docs = c_df.to_dict("records")
#                 if len(docs) < 40:
#                     for doc in docs:
#                         doc['HDBSCAN_Cluster'] = cur_cluster_no
#                     results.extend(docs)
#                     cur_cluster_no = cur_cluster_no + 1
#             copied_results = results.copy()
#             image_folder = os.path.join('output', self.args.case_name, self.args.cluster_folder,
#                                         'cluster_terms', 'images')
#             Path(image_folder).mkdir(parents=True, exist_ok=True)
#             file_path = os.path.join(image_folder, 'iteration_' + str(iteration) + ".png")
#             title = 'Iteration = ' + str(iteration)
#             # Visualise the cluster results
#             AbstractClusterTermTFIDFUtility.visualise_cluster_results_by_iteration(title, copied_results, file_path)
#         except Exception as _err:
#             print("Error occurred! {err}".format(err=_err))
#     # # Sort the results by DocID
#     results = sorted(results, key=lambda c: c['DocId'])
#     text_df = pd.DataFrame(results)
#     # Reorder the columns
#     text_df = text_df[['HDBSCAN_Cluster', 'Score', 'DocId', 'Cited by', 'Year', 'Document Type',
#                        'Title', 'Abstract', 'Author Keywords', 'Authors', 'DOI', 'x', 'y']]
#     # Output cluster results to CSV
#     folder = os.path.join('output', self.args.case_name, self.args.cluster_folder)
#     path = os.path.join(folder, self.args.case_name + '_clusters.csv')
#     text_df.to_csv(path, encoding='utf-8', index=False)
#     path = os.path.join(folder, self.args.case_name + '_clusters.json')
#     text_df.to_json(path, orient='records')
#     # print(text_df)
#
# #     # Update iterative clustering scores with individual Silhouette scores
# def update_iterative_article_cluster_results(self):
#     folder = os.path.join('output', self.args.case_name)
#     # Load sentence transformer
#     model = SentenceTransformer(self.args.model_name, cache_folder=sentence_transformers_path,
#                                 device=self.args.device)
#     folder_names = ['cluster_0', 'cluster_1', 'cluster_2', 'cluster_3', 'iteration', 'cluster_-1']
#     for folder_name in folder_names:
#         iterative_folder = os.path.join(folder, folder_name)
#         try:
#             AbstractClusterTermTFIDFUtility.update_clustering_scores(iterative_folder, model)
#             # Load the updated iterative clustering summary
#             path = os.path.join(iterative_folder, 'cluster_terms', 'iterative_clusters',
#                                 'AIMLUrbanStudyCorpus_iterative_summary.json')
#             iterative_clusters = pd.read_json(path).to_dict("records")
#             # Load the cluster results
#             path = os.path.join(iterative_folder,
#                                 self.args.case_name + '_cluster_terms_key_phrases_LDA_topics.json')
#             cluster_results = pd.read_json(path).to_dict("records")
#             for result in cluster_results:
#                 found_cluster = next(c for c in iterative_clusters if np.array_equal(c['DocIds'], result['DocIds']))
#                 assert found_cluster is not None, "Cannot find the article cluster"
#                 result['Score'] = found_cluster['score']
#             # Write output to article clusters
#             df = pd.DataFrame(cluster_results)
#             path = os.path.join(iterative_folder, self.args.case_name + '_cluster_terms_key_phrases_LDA_topics.csv')
#             df.to_csv(path, encoding='utf-8', index=False)
#             # Write article corpus to a json file
#             path = os.path.join(iterative_folder,
#                                 self.args.case_name + '_cluster_terms_key_phrases_LDA_topics.json')
#             df.to_json(path, orient='records')
#         except Exception as _err:
#             print("Error occurred! {err}".format(err=_err))
#             sys.exit(-1)

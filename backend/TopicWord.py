import os.path
import re
from argparse import Namespace
from pathlib import Path
import numpy as np
import nltk
import pandas as pd
import logging
from nltk.corpus import stopwords
# Set logging level
from TopicWordUtility import TopicWordUtility

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
nltk_path = os.path.join("C:", os.sep, "Users", "sam", "nltk_data")
Path(nltk_path).mkdir(parents=True, exist_ok=True)
nltk.data.path.append(nltk_path)
nltk.download('punkt', download_dir=nltk_path)
# Download all the necessary NLTK data
nltk.download('stopwords', download_dir=nltk_path)


# Compute the word vector of cluster topics and find the similar words of each topic
class TopicWord:
    def __init__(self):
        self.args = Namespace(
            case_name='UrbanStudyCorpus',
            approach='HDBSCAN',
            # Model name ref: https://github.com/RaRe-Technologies/gensim-data
            # model_name="glove-wiki-gigaword-50"  # small model for developing
            model_name="glove-wiki-gigaword-300"        # Larger GloVe model
            # model_name="word2vec-google-news-300"       # Google news model
        )
        # Load the cluster results as dataframe
        path = os.path.join('output', 'cluster', self.args.case_name + "_HDBSCAN_Cluster_topic_words.json")
        df = pd.read_json(path)
        self.clusters = df.to_dict("records")  # Convert to a list of dictionaries
        self.wv = TopicWordUtility.obtain_keyed_vectors(self.args.model_name, is_load=True)
        # Static variable
        self.stop_words = list(stopwords.words('english'))

        # print(vector)

    #
    # Ref: https://github.com/stanfordnlp/GloVe
    def compute_topics(self, cluster_no=15):
        try:
            # Get cluster 15
            cluster = list(filter(lambda c: c['Cluster'] == cluster_no, self.clusters))[0]
            results = []
            for n_gram_type in [2]:
                n_gram_results = []
                # Get top 30 bi-gram topics
                for n_gram in cluster['Topic'+str(n_gram_type)+ '-gram'][:30]:
                    try:
                        topic = n_gram['topic']
                        topic_words = list(filter(lambda w: w in self.wv, topic.split(" ")))
                        # Check both words must in model
                        if len(topic_words) == n_gram_type:
                            # add up the word vectors
                            vector_1 = self.wv[topic_words[0]] + self.wv[topic_words[1]]
                            vectors = []
                            for _word in topic_words:
                                vectors.append(self.wv[_word])
                            word_vector = np.add.reduce(vectors)
                            # avg_vector = np.true_divide(vector, n_gram_type)
                            # Find top 100 similar words by vector
                            similar_words = self.wv.similar_by_vector(word_vector, topn=100)
                            # Filter out no-word, duplicated topic words and stop words from similar words
                            similar_words = list(filter(lambda w: not re.search('[^\\w]', w[0].lower()), similar_words))
                            similar_words = list(filter(lambda w: w[0].lower() not in self.stop_words, similar_words))
                            # Filter out duplicated noun words
                            similar_words = TopicWordUtility.filter_duplicated_words(similar_words, topic)
                            # Get top 20 similar words
                            N = 20
                            result = {"topic": topic}
                            for i, w in enumerate(similar_words[:N]):
                                similarity = int(round(w[1] * 100))
                                result['top_' + str(i) + "_similar_word"] = w[0]
                            n_gram_results.append(result)
                    except Exception as err:
                        print("Error occurred! {err}".format(err=err))
                # List top 10 n-gram topic
                results += n_gram_results[:10]
            # Write the output as a csv or json file
            topic_word_df = pd.DataFrame(results)
            path = os.path.join('output', 'topic', self.args.case_name + '_' + self.args.approach + '_topic_similar_words.csv')
            topic_word_df.to_csv(path, encoding='utf-8', index=False)
            # # # Write to a json file
            path = os.path.join('output', 'topic', self.args.case_name + '_' + self.args.approach + '_topic_similar_words.json')
            topic_word_df.to_json(path, orient='records')
            # compute cosine similarity
            # score = self.wv.similarity('france', 'spain')
            # print(score)
        except Exception as err:
            print("Error occurred! {err}".format(err=err))


# Main entry
if __name__ == '__main__':
    topic_word = TopicWord()
    topic_word.compute_topics()

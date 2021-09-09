import collections
import json
import os
import re
import pandas as pd
import nltk
from nltk import word_tokenize, sent_tokenize
from nltk import ngrams
from nltk.corpus import words
from sklearn.feature_extraction.text import TfidfVectorizer


class Utility:

    # Clean number and stop words from a sentence
    @staticmethod
    def clean_sentence(sentences):
        # Preprocess the sentence
        cleaned_sentences = list()  # Skip copy right sentence
        for sentence in sentences:
            if u"\u00A9" not in sentence.lower() and 'licensee' not in sentence.lower():
                try:
                    cleaned_words = word_tokenize(sentence.lower())
                    # Keep alphabetic
                    cleaned_words = list(filter(lambda word: re.match(r'[^\W\d]*$', word), cleaned_words))
                    cleaned_sentences.append(" ".join(cleaned_words))  # merge tokenized words into sentence
                except Exception as err:
                    print("Error occurred! {err}".format(err=err))
        return cleaned_sentences

    # Create a text document
    @staticmethod
    def create_document(text):
        cleaned_sentences = Utility.clean_sentence([text['Title']] + sent_tokenize(text['Abstract']))
        document = ' '.join(cleaned_sentences)
        return document

    # Check if n_gram contains any word
    @staticmethod
    def check_words(n_gram, filter_words):
        n_gram_words = n_gram.split(" ")
        for word in n_gram_words:
            if word in filter_words:  # check if the word is in the filtered words.
                return True
        return False

    # Extract the terms from TFIDF
    @staticmethod
    def extract_terms_from_TFIDF(n_gram_type, corpus, stopwords, function_words):
        if n_gram_type == 'uni-gram':
            vectorizer = TfidfVectorizer(stop_words=stopwords, ngram_range=(1, 1))
        elif n_gram_type == 'bi-gram':
            vectorizer = TfidfVectorizer(ngram_range=(2, 2))
        else:
            vectorizer = TfidfVectorizer(ngram_range=(3, 3))
        # Compute tf-idf scores for each word in each sentence of the abstract
        vectors = vectorizer.fit_transform(corpus)
        feature_names = vectorizer.get_feature_names()
        dense = vectors.todense()
        dense_list = dense.tolist()
        dense_dict = pd.DataFrame(dense_list, columns=feature_names).to_dict(orient='records')
        key_terms = list()
        # Collect all the key terms of all the sentences in the text
        for dense in dense_dict:
            # Sort the terms by score
            filter_list = list(filter(lambda item: item[1] > 0, dense.items()))
            # Filter words containing stop words
            filter_list = list(filter(lambda item: not Utility.check_words(item[0], stopwords), filter_list))
            # Filter words containing function words
            filter_list = list(filter(lambda item: not Utility.check_words(item[0], function_words), filter_list))
            sorted_list = list(sorted(filter_list, key=lambda item: item[1], reverse=True))
            # Concatenate key terms
            key_terms.append(list(map(lambda item: item[0], sorted_list)))
        return key_terms

    @staticmethod
    def collect_term_freq_docID(n_gram_type, term_dict, terms, text):
        document = Utility.create_document(text)
        doc_id = text['DocId']
        for term in terms:
            # Include the terms/docID/Freq to 'term_dict'
            if term in term_dict:
                doc_id_set = term_dict[term]['docIDs']
                freq = term_dict[term]['freq']
            else:
                doc_id_set = set()
                freq = 0
            doc_id_set.add(doc_id)
            freq = freq + max(Utility.count_term_frequency(n_gram_type, term, document), 1)  # Minimal freq = 1
            term_dict[term] = {'freq': freq, 'docIDs': doc_id_set}
        return term_dict

    @staticmethod
    def get_author_keywords(author_keywords):
        # Fill in the record
        if isinstance(author_keywords, str):  # Check if author keywords is not empty but a string
            return list(map(lambda k: k.lower().strip(), author_keywords.split(";")))
        else:
            return []

    # Count how many time a term appear in the document
    @staticmethod
    def count_term_frequency(n_gram_type, term, document):
        tokens = word_tokenize(document)
        n_grams = tokens
        if n_gram_type == 'bi_gram':
            n_grams = list(map(lambda t: t[0] + " " + t[1], list(ngrams(tokens, 2))))
        elif n_gram_type == 'tri_gram':
            n_grams = list(map(lambda t: t[0] + " " + t[1] + " " + t[2], list(ngrams(tokens, 3))))
        return len(list(filter(lambda n_gram: n_gram == term, n_grams)))

    # Count how many documents in the corpus contain the term
    @staticmethod
    def create_collocation_document(collocations, text_df):
        col_doc_dict = dict()
        # GO through each collocation term and initialise the col_doc_dict
        for col in collocations:
            col_doc_dict[col] = set()
        # Iterate the document
        for i, text in text_df.iterrows():
            try:
                doc_id = text['DocId']
                document = Utility.create_document(text)
                for term, docIDs in col_doc_dict.items():
                    if term in document:
                        docIDs.add(doc_id)
                        col_doc_dict[term] = docIDs
            except Exception as err:
                print("Error occurred! {err}".format(err=err))
        return col_doc_dict

    @staticmethod
    def get_term_doc_ids(term, col_doc_dict):
        return col_doc_dict[term]

    @staticmethod
    def is_alpha(collocation):
        # english_check = re.compile(r'[a-z]')
        terms = collocation.split(" ")
        for term in terms:
            if not term.encode().isalpha():  # Check if the term is alphabetical
                return False
        return True

    # Find a list of bi_grams by (1) pointwise mutual information, (2) Chi-square (3) Likelihood ratios
    # Ref: https://www.nltk.org/howto/collocations.html
    @staticmethod
    def get_collocations(bigram_measures, finder, stopwords, function_words):
        associate_measures = ['Likelihood_ratio']  # ['PMI', 'Chi_square', 'Likelihood_ratio']
        try:
            # if associate_measure == 'PMI':
            #     scored_bi_grams = finder.score_ngrams(bigram_measures.pmi)
            # elif associate_measure == 'Chi_square':
            #     scored_bi_grams = finder.score_ngrams(bigram_measures.chi_sq)
            # else:
            # Find a list of bi_grams by likelihood collocations
            scored_bi_grams = finder.score_ngrams(bigram_measures.likelihood_ratio)
            # Convert bi_gram object to a list of dictionaries
            bi_grams_list = list(map(lambda bi_gram: {'collocation': bi_gram[0][0] + " " + bi_gram[0][1],
                                                      'score': bi_gram[1]}, scored_bi_grams))
            # Filter out bi_grams containing stopwords
            filtered_bi_grams = list(
                filter(lambda bi_gram: not Utility.check_words(bi_gram['collocation'], stopwords), bi_grams_list))
            # Filter out bi_gram containing function words
            filtered_bi_grams = list(
                filter(lambda bi_gram: not Utility.check_words(bi_gram['collocation'], function_words),
                       filtered_bi_grams))
            # Filter out bi_grams containing non-English words
            filtered_bi_grams = list(filter(lambda bi_gram:
                                            Utility.is_alpha(bi_gram['collocation']),
                                            filtered_bi_grams))
            # Sort the bi-grams by scores
            sorted_bi_grams = sorted(filtered_bi_grams, key=lambda bi_gram: bi_gram['score'], reverse=True)
            return sorted_bi_grams
        except Exception as err:
            print("Error occurred! {err}".format(err=err))


    # Group the document ids by article published year
    @staticmethod
    def group_doc_ids_by_year(text_df, doc_ids):
        year_doc_dict = {}
        for doc_id in doc_ids:
            try:
                doc = text_df.query('DocId == {id}'.format(id=doc_id))  # doc is a pd series
                doc_year = doc.iloc[0]['Year']  # Get the year of the doc
                if doc_year not in year_doc_dict:
                    year_doc_dict[doc_year] = list()
                year_doc_dict[doc_year].append(doc_id)
            except Exception as err:
                print("Error occurred! {err}".format(err=err))
        return year_doc_dict

    # Collect the years of document 'i' and 'j'
    @staticmethod
    def collect_doc_years(doc_ids_i, doc_ids_j):
        year_i = set(doc_ids_i.keys())
        year_j = set(doc_ids_j.keys())
        # Obtain the years that appear both term 'i' and 'j' using set intersection
        return sorted(list(year_i.intersection(year_j)))

        # # Group bigrams by first word in bigram.
        # prefix_keys = collections.defaultdict(list)
        # for key, scores in scored_bi_grams:
        #     prefix_keys[key[0]].append((key[1], scores))
        #
        # for key in prefix_keys:
        #     prefix_keys[key].sort(key=lambda x: -x[1])
        # if len(prefix_keys['machine']) > 0:
        #     print(prefix_keys['machine'])
        # # Filter out the bi-gram containing stop words
        # filter_bi_grams = list(filter(lambda bi_gram: bi_gram[0][0] not in stopwords and
        #                                               bi_gram[0][1] not in stopwords, scored_bi_grams))
        # Convert the n_gram to a list of bi_grams

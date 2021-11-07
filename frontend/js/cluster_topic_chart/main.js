'use strict';
const corpus = 'UrbanStudyCorpus';

// Document ready event
$(function () {
    // Document (article abstract and title) and key terms data
    const doc_file_path = 'data/doc_cluster/' + corpus + '_doc_terms.json';
    // HDBSCAN cluster and topic words data
    const cluster_topics_file_path = 'data/doc_cluster/' + corpus + '_HDBSCAN_Cluster_topic_words.json';
    // Get the cluster groups
    const cluster_group_file_path = 'data/doc_cluster/' + corpus + '_cluster_groups.json';
    $.when(
        $.getJSON(doc_file_path), $.getJSON(cluster_topics_file_path),
        $.getJSON(cluster_group_file_path)
    ).done(function (result1, result2, result3) {
        const doc_data = result1[0];
        const cluster_data = result2[0];
        const cluster_groups = result3[0];
        // console.log(doc_key_terms);
        const chart = new WordTree(cluster_groups, cluster_data, doc_data);
    });



})

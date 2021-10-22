'use strict';
const corpus = 'UrbanStudyCorpus';
const params = new URLSearchParams(window.location.search);

// Load cluster data and display the results
function load_cluster_data_display_results(cluster_approach, cluster_topic_words, doc_key_terms) {
    // Select cluster number
    let selected_cluster_no = 2;
    if(params.has('cluster')){
        selected_cluster_no = parseInt(params.get('cluster'));
    }

    // Populate the cluster list
    const cluster_no_list = cluster_topic_words[cluster_approach].map(c => c['Cluster']);
    $('#cluster_no').empty();
    // Fill in the cluster no options
    for (const cluster_no of cluster_no_list) {
        const option = $('<option value=' + cluster_no + '>#' + cluster_no + '</option>');
        if (cluster_no === selected_cluster_no) {
            option.attr("selected", "selected");
        }
        $('#cluster_no').append(option);
    }
    // Set the cluster #2 as default cluster
    const topic_btn = new TopicBtnListView(selected_cluster_no, cluster_topic_words[cluster_approach], doc_key_terms);
    // Bind the change to cluster no
    $('#cluster_no').on('change', function (event) {
        const cluster_number = parseInt(this.value);
        const topic_btn = new TopicBtnListView(cluster_number, cluster_topic_words[cluster_approach], doc_key_terms);
    });

}


// Document ready event
$(function () {
    // Document (article abstract and title) and key terms data
    const doc_key_terms_file_path = 'data/doc_cluster/' + corpus + '_doc_terms.json';

    // HDBSCAN cluster and topic words data
    const hdbscan_cluster_topic_words_file_path = 'data/doc_cluster/' + corpus + '_HDBSCAN_Cluster_topic_words.json';
    // KMeans cluster and topic words data
    const kmeans_cluster_topic_words_file_path = 'data/doc_cluster/' + corpus + '_KMeans_Cluster_topic_words.json';
    $.when(
        $.getJSON(doc_key_terms_file_path), $.getJSON(hdbscan_cluster_topic_words_file_path),
        $.getJSON(kmeans_cluster_topic_words_file_path),
    ).done(function (result1, result2, result3) {
        const doc_key_terms = result1[0];
        const cluster_topic_words = {"HDBSCAN": result2[0], "KMeans": result3[0]};
        // Change the cluster approach
        $('#cluster_approach').selectmenu({
            change: function (event, data) {
                const cluster_approach = data.item.value;
                load_cluster_data_display_results(cluster_approach, cluster_topic_words, doc_key_terms);
            }
        });
        load_cluster_data_display_results('HDBSCAN', cluster_topic_words, doc_key_terms);
        // Set up print /download as a pdf
        $('#download_as_pdf').button();
        $('#download_as_pdf').click(function (event) {
            window.print();
        });

    })
});
function ClusterDocList(cluster, corpus_data, corpus_key_phrases) {
    const cluster_no = cluster['Cluster'];
    const cluster_topics = cluster['TF-IDF-Topics'].slice(0, 30);
    const cluster_key_phrases = cluster['Grouped_Key_Phrases'];
    const cluster_docs = corpus_data.filter(d => cluster['DocIds'].includes(parseInt(d['DocId'])));
    const cluster_link = $('<a target="_blank" href="cluster_list.html?cluster='+ cluster_no + '">Cluster #' + cluster_no + '</a>');

    // Create a Top 10 Topic region
    function create_cluster_top_topic_div(){
        // Create a div to display a list of topic (a link)
        $('#cluster_doc_topic').empty();
        const topic_text = cluster_topics.slice(0, 10).map(topic => topic['topic'] + ' (' + topic['doc_ids'].length + ')').join(" ");

        const topic_div = $('<div>' +
            '<h3><span class="fw-bold">Top 10 topics: </span>' + topic_text + '</h3>' +
            '<div><p></p></div></div>');
        const topic_p = topic_div.find("p");
        // Add top 30 topics (each topic as a link)
        for (const selected_topic of cluster_topics) {
            const link = $('<button type="button" class="btn btn-link btn-sm"> '
                + selected_topic['topic'] + ' (' + selected_topic['doc_ids'].length + ')' + "</button>");
            // Click on the link to display the articles associated with topic
            link.click(function () {
                $('#cluster_doc_heading').empty();
                $('#cluster_doc_heading').append(cluster_link);
                $('#cluster_doc_heading').append(
                    $('<span> has ' + selected_topic['doc_ids'].length + ' articles about '
                        + '<span class="search_term">' + selected_topic['topic'] + '</span></span>'));
                // Add the reset button to display all the cluster articles
                const reset_btn = $('<button class="mx-1">' +
                    '<span class="ui-icon ui-icon-closethick"></span></button>');
                reset_btn.button();
                reset_btn.click(function (event) {
                    // // Get the documents about the topic
                    const doc_list_heading = new ClusterDocList(cluster, cluster_docs);
                });
                // Update the heading
                $('#cluster_doc_heading').append(reset_btn);
                // Get a list of docs in relation to the selected topic
                const topic_docs = cluster_docs.filter(d => selected_topic['doc_ids'].includes(d['DocId']));
                // Create a list of articles associated with topic
                const doc_list = new DocList(topic_docs, cluster_topics, selected_topic);

            });
            topic_p.append(link);
        }
        // Set accordion
        topic_div.accordion({
            icons: null,
            collapsible: true,
            heightStyle: "fill",
            active: 2
        });
        $('#cluster_doc_topic').append(topic_div);
    }



    function _createUI() {
        // Create a div to display
        $('#cluster_doc_heading').empty();
        $('#cluster_doc_heading').append(cluster_link);
        $('#cluster_doc_heading').append($('<span> has ' +cluster_docs.length+ ' articles</span>'));

        // Create a div to display top 10 Topic of a cluster
        create_cluster_top_topic_div();

        // Create doc list
        const doc_list = new DocList(cluster_docs, cluster_topics, null, corpus_key_phrases);
    }

    _createUI();
}
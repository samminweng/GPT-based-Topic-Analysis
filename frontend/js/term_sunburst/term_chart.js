// Draw the term chart and document list
function TermChart(cluster, cluster_docs){
    const lda_topics = cluster['LDATopics'];
    const groups = cluster['KeyPhrases'];
    const sub_groups = cluster['SubGroups'];
    console.log("group of key phrases", groups)
    // const phrase_total = groups.reduce((pre, cur) => pre + cur['NumPhrases'], 0);

    // Main entry
    function createUI(){
        try{
            $('#sub_group').empty();
            $('#doc_list').empty();
            $('#key_phrase_chart').empty();
            // Display key phrase groups as default graph
            const graph = new BarChart(groups, sub_groups, cluster, cluster_docs);
        }catch (error){
            console.error(error);
        }
    }
    createUI();
}

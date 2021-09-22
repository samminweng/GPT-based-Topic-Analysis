// Create scatter graph
function ScatterGraph(total_clusters, doc_cluster_data) {
    const width = 600;
    const height = 600;
    // Get the color of collocation
    const colors = function (cluster_no) {
        const color_plates = [
            "#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c", "#98df8a", "#d62728", "#ff9896", "#9467bd",
            "#c5b0d5", "#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d",
            "#17becf", "#9edae5"];
        return color_plates[cluster_no];
    }

    // Draw google chart
    function drawChart() {
        let data = [];
        for (let cluster_no = 0; cluster_no < total_clusters; cluster_no++) {
            const cluster_data = doc_cluster_data.filter(d => d['Cluster'] === cluster_no);
            // const topic_words = Utility.get_topic_words_cluster(total_clusters, cluster_no);
            let data_point = {'x': [], 'y': [], 'label': []};
            for (const dot of cluster_data) {
                data_point['x'].push(dot.x);
                data_point['y'].push(dot.y);
                data_point['label'].push("Doc id: " + dot.DocId);   // Tooltip label
            }

            let trace = {
                'x': data_point['x'], 'y': data_point['y'], 'text': data_point['label'],
                'name': 'Cluster ' + cluster_no, 'mode': 'markers', 'type': 'scatter',
                'marker': {color: colors(cluster_no)}
            };
            data.push(trace);
        }
        // Define the layout
        let layout = {
            autosize: false,
            width: width,
            height: height,
            margin: {
                l: 50,
                r: 50,
                b: 100,
                t: 100,
                pad: 3
            },
            xaxis: {range: [0, 10]},
            yaxis: {range: [0, 10]},
            annotations: []
        }

        // Get the cluster number
        Plotly.newPlot('doc_cluster', data, layout);
        // Add event
        const doc_cluster_div = document.getElementById('doc_cluster');
        doc_cluster_div.on('plotly_click', function (data) {
            const point = data.points[0];
            // Get the doc id from text
            const cluster_no = parseInt(point.data.name.split(" ")[1]);
            // Get cluster documents
            const documents = Utility.get_cluster_documents(total_clusters, cluster_no);
            // console.log(doc_cluster_div.layout.annotations)
            // Add an annotation to the clustered dots.
            const new_annotation = {
                x: point.xaxis.d2l(point.x), y: point.yaxis.d2l(point.y),
                bordercolor: point.fullData.marker.color,
                text: '<b>Cluster ' + cluster_no + '</b> <br>' +
                    '<i>' + documents.length + ' articles</i><br>'
            };
            Plotly.relayout('doc_cluster', 'annotations[0]', new_annotation);
        });
    }


    // Create the network graph using D3 library
    function _createUI() {
        $('#doc_cluster').empty();
        $('#doc_cluster').css('width', width).css('height', height);
        drawChart();

    }

    _createUI();
}

// // Get the number of documents for a collocation node
// function get_node_size(node_name) {
//     let num_doc = Utility.get_number_of_documents(node_name, collocation_data);
//     let radius = Math.sqrt(num_doc);
//     // let radius = num_doc / max_doc_ids * max_radius;
//     return Math.round(radius);  // Round the radius to the integer
// }
//
// // Get the number of documents for a link (between two terms
// function get_link_size(link) {
//     let source = link.source;
//     let target = link.target;
//     let occ = occurrence_data['occurrences'][source.id][target.id];
//     return Math.max(1.5, Math.sqrt(occ.length));
// }
//
// // Get the link color
// function get_link_color(link) {
//     let source = link.source;
//     let target = link.target;
//     let source_color = colors(source.name);
//     let target_color = colors(target.name);
//     if (source_color !== target_color) {
//         // Scale the color
//         return d3.schemeCategory10[7];
//     }
//     return source_color;
// }
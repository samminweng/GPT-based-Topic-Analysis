// Create D3 network graph using collocation and
function D3NetworkGraph(searched_term, term_map, occurrences) {
    const width = 600;
    const height = 600;
    const max_radius = 30;
    const font_size = 12;
    const distance = 200;
    const strength = -400;
    const {nodes, links} = TermChartUtility.create_node_link_data(searched_term, term_map, occurrences);
    const max_node_size = TermChartUtility.get_max_node_size(nodes);
    console.log(nodes);
    console.log(links);
    // Get the color of collocation
    const colors = function (d) {
        return d3.schemeCategory10[d.group];
    }

    // Get the number of documents for a collocation node
    function get_node_size(node_name) {
        let tm = term_map.find(tm => tm[0] === node_name);
        let num_doc = tm[1].length;
        return Math.min(num_doc*2, max_radius);
        // let radius = Math.sqrt(num_doc);
        // let radius = num_doc / max_node_size * max_radius;
        // return Math.round(radius);  // Round the radius to the integer
    }

    // Get the link color
    function get_link_color(link) {
        let source = link.source;
        let target = link.target;
        let source_color = colors(source);
        let target_color = colors(target);
        if (source_color !== target_color) {
            // Scale the color
            return d3.schemeCategory10[7];
        }
        return source_color;
    }

    // Drag event function
    const drag = function (simulation) {

        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        return d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }

    function _create_d3_network_graph(svg) {
        // Simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(distance))
            .force("charge", d3.forceManyBody().strength(strength))
            .force('center', d3.forceCenter(width / 2, height / 2));

        // Initialise the links
        const link = svg.append('g')
            .attr("stroke-opacity", 0.1)
            .selectAll('line')
            .data(links)
            .join("line")
            .attr("stroke", d => get_link_color(d))
            .attr("stroke-width", d => d.value);

        // Initialise the nodes
        const node = svg.append('g')
            .selectAll("g")
            .data(nodes)
            .join("g")
            .on("click", function (d, n) {// Add the onclick event
                // console.log(n.name);
                // let key_term = n.name;
                // // Check if the selected item
                // if (!$('#selected_term_1').is(':empty') && !$('#selected_term_2').is(':empty')) {
                //     alert("Please clear the terms");
                //     return;
                // }
                // // Update the selected_term_1
                // if ($('#selected_term_1').is(':empty')) {
                //     const group_1 = Utility.get_group_number(key_term);
                //     $('#selected_term_1')
                //         .attr('class', 'keyword-group-' + group_1)
                //         .text(key_term);
                //     // let doc_list_view = new DocumentListView([key_term], collocation_data, corpus_data);
                //     return;
                // }
                // // Update the selected_term_2
                // const group_2 = Utility.get_group_number(key_term);
                // $('#selected_term_2').attr('class', 'keyword-group-' + group_2).text(key_term);
                // // Get the key term 1 and key term 2
                // let collocation_1 = $('#selected_term_1').text();
                // let collocation_2 = $('#selected_term_2').text();
                // let key_terms = [collocation_1, collocation_2]
                // let doc_list_view = new DocumentListView(key_terms, collocation_data, corpus_data);
            }).call(drag(simulation));

        // Add the circles
        node.append("circle")
            .attr("stroke", "white")
            .attr("stroke-width", 1.5)
            .attr("r", d => get_node_size(d.name))
            .attr("fill", d => colors(d));

        // Add node label
        node.append("text")
            .attr("class", "lead")
            .attr('x', 10)
            .attr('y', "0.31em")
            .text(d => {
                return d.name;
            });
        // Tooltip
        node.append("title")
            .text(d => "'" + d.name + "' has " + term_map.find(tm => tm[0] === d.name)[1].length + " articles");

        // Simulate the tick event
        simulation.on('tick', () => {
            link.attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
    }


    // Create the network graph using D3 library
    function _createUI() {
        $('#term_chart').empty(); // Clear the SVG graph
        try {
            // Add the svg node to 'term_map' div
            const svg = d3.select('#term_chart')
                .append("svg").attr("viewBox", [0, 0, width, height])
                .style("font", font_size + "px sans-serif");
            _create_d3_network_graph(svg);
        } catch (error) {
            console.error(error);
        }
    }

    _createUI();
}

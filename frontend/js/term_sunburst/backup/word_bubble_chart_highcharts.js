// Create a word network chart using highchart library
// Ref: https://www.highcharts.com/docs/chart-and-series-types/network-graph
// API: https://api.highcharts.com/highcharts/
function WordBubbleChart(group, cluster_docs, color) {
    const height = 400;
    const topic_words = group['topic_words'].concat(["others"]);
    const group_key_phrases = group['key-phrases'];
    const group_docs = cluster_docs.filter(d => group['DocIds'].includes(d['DocId']));
    const word_key_phrase_dict = Utility.create_word_key_phrases_dict(topic_words, group_key_phrases);
    const word_doc_dict = Utility.create_word_doc_dict(topic_words, group_docs, word_key_phrase_dict);

    // Highlight key terms
    function mark_key_terms(div, terms, class_name) {
        if (terms !== null) {
            // Check if the topic is not empty
            for (const term of terms) {
                // Mark the topic
                const mark_options = {
                    "separateWordSearch": false,
                    "accuracy": {
                        "value": "partially",
                        "limiters": [",", ".", "'s", "/", ";", ":", '(', ')', '‘', '’', '%', 's', 'es']
                    },
                    "acrossElements": true,
                    "ignorePunctuation": ":;.,-–—‒_(){}[]!'\"+=".split(""),
                    "className": class_name
                }
                div.mark(term, mark_options);
            }
        }
        return div;
    }

    // Create a tooltip
    function create_tooltip(id, text) {
        // console.log("this.point", this.point);
        let div = $('<div>' + text + '</div>');
        if (!id.includes("paper#")) {
            // Highlight title word
            const title_word = id;
            div = mark_key_terms(div, [title_word], 'key_term');
        } else {
            const doc_id = parseInt(id.split("paper#")[1]);
            // Get the title words linking to this doc
            let words = [];
            for (const title_word of topic_words) {
                if (word_doc_dict[title_word].includes(doc_id)) {
                    words.push(title_word);
                }
            }
            div = mark_key_terms(div, words, 'key_term');
        }
        return div.html();
    }

    // Display a detail chart for title word
    function display_word_paper_chart(topic_word) {
        $('#term_occ_chart').empty();
        // console.log(topic_word);
        // Get all the nodes
        const collect_nodes_links = function (word_docs) {
            let nodes = [];
            let links = [];
            // Create a title word node
            const key_phrases = word_key_phrase_dict[topic_word];
            nodes.push({
                id: topic_word,
                name: topic_word,
                text: topic_word,
                color: color,
                marker: {
                    radius: Math.min(Math.sqrt(key_phrases.length) * 5 + 10, 30)
                },
                dataLabels: {
                    backgroundColor: color,
                    allowOverlap: false,
                    style: {
                        color: 'white',
                        fontSize: '16px',
                        textOutline: true
                    }
                }
            });
            // Add word node and link between word and paper
            // Add link
            for (let i = 0; i < word_docs.length; i++) {
                const doc = word_docs[i];
                const doc_id = doc['DocId'];
                const word_key_phrase = doc['KeyPhrases'].find(phrase => key_phrases.includes(phrase));
                // const key_phrases = doc['KeyPhrases'].filter(phrase => phrase !== word_key_phrase);
                const text = doc['KeyPhrases'].join(";<br>");
                const id = "paper#" + doc_id
                nodes.push({
                    id: id,
                    name: "<span>" + word_key_phrase + "</span>",
                    text: text,
                    color: 'gray',
                    // opacity: 0.5,
                    marker: {
                        radius: 20
                    },
                    dataLabels: {
                        format: '{point.name}',
                        style: {
                            color: 'black',
                            fontSize: '12px',
                            textOutline: true,
                        },
                        align: 'left',
                        useHTML: true,
                        verticalAlign: 'bottom',
                    }
                });
                const link = {from: topic_word, to: id}
                links.push(link);
            }
            return [nodes, links];
        };

        // $('term_occ_chart').empty();
        const word_docs = group_docs.filter(d => word_doc_dict[topic_word].includes(d['DocId']));
        const [nodes, links] = collect_nodes_links(word_docs);
        Highcharts.chart('term_occ_chart', {
            chart: {
                type: 'networkgraph',
                height: height,
            },
            title: {
                text: ''
            },
            tooltip: {
                backgroundColor: 'white',
                borderColor: 'black',
                borderRadius: 10,
                borderWidth: 3,
                formatter: function () {
                    return create_tooltip(this.point.id, this.point.text);
                }
            },
            plotOptions: {
                networkgraph: {
                    keys: ['from', 'to'],
                    layoutAlgorithm: {
                        enableSimulation: false,
                        linkLength: 100,
                        integration: 'verlet',
                        approximation: 'barnes-hut',
                        // gravitationalConstant: 0.1
                    }
                }
            },
            series: [{
                dataLabels: {
                    enabled: true,
                    linkFormat: '',
                    allowOverlap: false
                },
                data: links,
                nodes: nodes
            }]
        });

        $('#back_btn').show();
    }

    // Display the papers for all words
    function display_all_word_chart() {
        $('#term_occ_chart').empty();
        // Get all the nodes
        const collect_nodes_links = function () {
            let nodes = [];
            let links = [];
            // // Add the paper
            for (let i = 0; i < group_docs.length; i++) {
                const doc = group_docs[i];
                const doc_id = doc['DocId'];
                const text = doc['KeyPhrases'].join(";<br>");
                nodes.push({
                    id: "paper#" + doc_id,
                    name: '',
                    text: text,
                    color: 'gray',
                    marker: {
                        radius: 5
                    },
                    dataLabels: {
                        enabled: false,
                    }
                });
            }
            // Add word node and link between word and paper
            for (let i = 0; i < topic_words.length; i++) {
                const title_word = topic_words[i];
                const word_docs = word_doc_dict[title_word];
                // Check if the word appear in word_neighbour_phrases_dict
                const key_phrases = word_key_phrase_dict[title_word];
                if(key_phrases.length>0){
                    nodes.push({
                        id: title_word,
                        name: "<div>" + title_word + "</div>",
                        text: "<div>" + key_phrases.join(";<br>") + '</div>',
                        color: color,
                        marker: {
                            radius: Math.min(Math.sqrt(key_phrases.length) * 5 + 10, 30)
                        },
                        dataLabels: {
                            backgroundColor: color,
                            allowOverlap: false,
                            style: {
                                color: 'white',
                                fontSize: '14px',
                                textOutline: true
                            }
                        }
                    });
                    // Add link
                    for (const doc_id of word_docs) {
                        const link = {from: title_word, to: "paper#" + doc_id}
                        links.push(link);
                    }
                }
            }

            return [nodes, links];

        };
        const [nodes, links] = collect_nodes_links();
        // Create highcharts
        let chart = Highcharts.chart('term_occ_chart', {
            chart: {
                type: 'networkgraph',
                height: height,
            },
            title: {
                text: ''
            },
            tooltip: {
                backgroundColor: 'white',
                borderColor: 'black',
                borderRadius: 10,
                borderWidth: 3,
                opacity: 0,
                formatter: function () {
                    return create_tooltip(this.point.id, this.point.text);
                }
            },
            plotOptions: {
                networkgraph: {
                    keys: ['from', 'to'],
                    layoutAlgorithm: {
                        enableSimulation: false,
                        linkLength: 20,
                        // friction: -0.1,
                        approximation: 'barnes-hut',
                        integration: 'euler',
                    }
                }
            },
            series: [{
                dataLabels: {
                    enabled: true,
                    // align: 'center',
                    linkFormat: '',
                    allowOverlap: false,
                    style: {
                        color: "black",
                        textOutline: false,
                        textAlign: 'center',
                        style: {
                            fontSize: '9px'
                        },
                        useHTML: true,
                    }
                },
                data: links,
                nodes: nodes,
                // Add the onclick event to display the chart for a single title word
                events: {
                    click: function (event) {
                        console.log("event", event);
                        const id = event.point.id;
                        // Check if clicking on any title word
                        const found = topic_words.find(w => w === id);
                        if (found) {
                            console.log(word_doc_dict);
                            display_word_paper_chart(found);
                        }
                    }
                }
            }]
        });
        $('#back_btn').hide();
    }

    function _createUI() {
        // display_word_paper_chart("others");
        display_all_word_chart();
        // Add click event
        $('#back_btn').button();
        $('#back_btn').click(function (event) {
            display_all_word_chart();
        });

    }

    _createUI();

}



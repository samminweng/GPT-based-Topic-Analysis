// Create a text view to display the content of the article
function DocView(doc, keywords) {
    const container = $('<div class="card text-dark bg-light">' +
        '<div class="card-body">' +
        '<p class="card-text">' +
        '</p>' +
        '</div></div>');
    this.get_container = function () {
        return container;
    }

    // Highlight key terms
    function mark_key_terms(div, terms, class_name) {
        // Check if the topic is not empty
        for (const term of terms) {
            if(term !== null){
                // Mark the topic
                const mark_options = {
                    "separateWordSearch": false,
                    // "accuracy": {
                    //     "value": "exactly",
                    //     "limiters": [",", ".", "'s", "/", ";", ":", '(', ')', '‘', '’', '%', 's', 'es', '-']
                    // },
                    "acrossElements": true,
                    "ignorePunctuation": ":;.,-–—‒_(){}[]!'\"+=".split(""),
                    "className": class_name
                }
                div.mark(term, mark_options);
            }
        }
        return div;
    }

    function _createUI() {
        const doc_key_phrases = doc['KeyPhrases'];
        // Add Key Phrase
        const key_phrase_div = $('<div class="container border-info">' +
            '<p class="lead">' + doc_key_phrases.join(", ") + '</p>' +
            '</div>');
        //


        container.find(".card-text").append(key_phrase_div);
        // Add the title
        let title_div = $('<div></div>');
        title_div.append($('<span class="fw-bold">Title: </span><span>' + doc['Title'] + '</span>'));

        container.find(".card-text").append(title_div);
        // Add the abstract
        let abstract_div = $('<div class="col"></div>');
        // const short_abstract = doc['Abstract'].substring(0, 150) + '...';
        abstract_div.append($('<span class="fw-bold">Abstract: </span><span class="abstract">' + doc['Abstract'] + '</span>'));
        abstract_div = mark_key_terms(abstract_div, keywords, 'search_terms');
        container.find(".card-text").append(abstract_div);

        // Add author keywords
        let author_keyword_div = $('<div class="col"></div>');
        author_keyword_div.append($('<span class="fw-bold">Author Keywords: </span><span>' + doc['Author Keywords'] + '</span>'));
        container.find(".card-text").append(author_keyword_div);
        // Add authors
        let author_div = $('<div class="col"></div>');
        author_div.append($('<span class="fw-bold">Authors: </span><span>' + doc['Authors'] + '</span>'));
        container.find(".card-text").append(author_div);

        // Add citation
        const paper_info_div = $('<div></div>');
        paper_info_div.append($('<span><span class="fw-bold">Cited by </span>' + doc['Cited by'] + ' articles</span>'));
        // Add Year
        paper_info_div.append($('<span><span class="fw-bold"> Year </span>' + doc['Year'] + ' </span>'))
        // Add DOI link
        paper_info_div.append($('<span><span class="fw-bold"> DOI </span>' +
            '<a target="_blank" href="https://doi.org/' + doc['DOI'] + '">' + doc['DOI'] + '</a>' +
            '</span>'));
        container.find(".card-text").append(paper_info_div);
    }

    _createUI();
}


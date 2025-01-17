// Create a div to display the grouped key phrases
function KeywordClusterView(keyword_group, docs) {
    const group_no = keyword_group['group'];
    const score = keyword_group['score'].toFixed(2);
    const keywords = keyword_group['keywords'];
    const color_no = group_no - 1;
    const color = color_plates[color_no];

    // Display keywords in accordion
    function displayKeywordList() {
        const keyword_div = $('<div class="container-sm small"></div>');
        // Get the number of rows by rounding upto the closest integer
        const num_row = Math.ceil(keywords.length / 3) + 1;
        // Add each key phrase
        for (let i = 0; i < num_row; i++) {
            // Create a new row
            const row = $('<div class="row"></div>');
            for (let j = 0; j < 3; j++) {
                const index = i + j * num_row;
                const col = $('<div class="col-sm border-bottom text-sm-start text-truncate"></div>')
                if (index < keywords.length) {
                    const keyword = keywords[index];
                    const btn = $('<a href="#keyword_cluster_view" class="link-primary small">' + keyword+ '</a>');
                    // Click the keyword button to display the relevant article
                    // btn.button();
                    btn.click(function(event){
                       const matched_docs = docs.filter(d => {
                           const article_keywords = d['GPTKeywords'];
                           const found = article_keywords.find(k => k.toLowerCase() === keyword.toLowerCase());
                           if(found)
                                return true;
                           return false;
                       });
                       const doc_list = new DocList(matched_docs, [keyword], group_no-1);
                    });
                    col.append(btn);
                }
                row.append(col);
            }
            keyword_div.append(row);
        }
        return keyword_div;
    }


    function _createUI() {
        $('#keyword_group_view').empty();
        // Heading
        const container = $('<div class="container-sm"></div>');
        const heading = $('<div>' +
                          '<span class="fw-bold" style="color:' + color + '">Keyword Group #' + group_no + ' </span>' +
                          ' (' + score + ') contains ' + keywords.length + ' keywords' + ' across ' + docs.length + ' articles</div>');
        // A list of grouped key phrases
        container.append(heading);
        container.append(displayKeywordList());
        $('#keyword_group_view').append(container);
        const doc_list = new DocList(docs, keywords, color_no);
    }

    _createUI();
}

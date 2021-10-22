// Display a list of research articles for key term 1 and key term 2.
function DocumentListView(documents, topic) {
    // Create a pagination to show the documents
    function createPagination(docTable) {
        // Create the table
        let pagination = $("<div></div>");
        // Pagination
        pagination.pagination({
            dataSource: function (done) {
                let result = [];
                for (let i = 0; i < documents.length; i++) {
                    result.push(documents[i]);
                }
                done(result);
            },
            totalNumber: documents.length,
            pageSize: 5,
            showNavigator: true,
            formatNavigator: '<span style="color: #f00"><%= currentPage %></span>/<%= totalPage %> pages, <%= totalNumber %> articles',
            position: 'top',
            showGoInput: true,
            showGoButton: true,
            callback: function (documents, pagination) {
                docTable.find('tbody').empty();
                for (let document of documents) {
                    let row = $('<tr class="d-flex"></tr>');
                    // Add the year
                    let col = $('<td class="col-1">' + document['Year'] + '</td>');
                    row.append(col);
                    // Add the title
                    col = $('<td class="col-11"></td>');
                    let textView = new TextView(document, topic);
                    col.append(textView.get_container());
                    row.append(col);
                    docTable.find('tbody').append(row);
                }
            }
        });
        return pagination;
    }

    function _createUI() {
        $('#document_list_view').empty();
        const container = $('<div class="container p-3"></div>');
        // If the topic is passed to the doc list view, display a summary
        if(topic.length> 0){
            const heading = $('<div class="h5 mb-3">' + documents.length + ' articles mention '+ topic[0] + '</div>');
            container.append($('<div class="row p-3"><div class="col"></div></div>').find(".col").append(heading));
        }
        // A list of cluster documents
        const documentTable = $('<table class="table table-striped">' +
            '<thead class="thead-light">' +
            '<tr class="d-flex">' +
            '    <th class="col-1">Year</th>' +
            '    <th class="col-11">Articles</th>' +
            '</tr>' +
            '</thead>' +
            '<tbody></tbody></table>');
        const pagination = createPagination(documentTable);
        // Add the pagination
        container.append($('<div class="row p-3"><div class="col"></div></div>').find(".col").append(pagination));
        container.append($('<div class="row p-3"><div class="col"></div></div>').find(".col").append(documentTable));
        $('#document_list_view').append(container);

    }

    _createUI();
}
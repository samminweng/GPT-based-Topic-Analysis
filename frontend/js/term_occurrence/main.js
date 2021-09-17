'use strict';
const corpus = 'UrbanStudyCorpus';
const corpus_file_path = 'data/term_occurrence/' + corpus + '.json';
const collocation_file_path = 'data/term_occurrence/' + corpus + '_collocations.json';
const occurrence_file_path = 'data/term_occurrence/' + corpus + '_occurrences.json';
// Document ready event
$(function () {
    // Load collocations
    $.when(
        $.getJSON(corpus_file_path), $.getJSON(collocation_file_path), $.getJSON(occurrence_file_path)
    ).done(function (result1, result2, result3){
        const corpus_data = result1[0];
        const collocation_data = result2[0];
        const occurrence_data = result3[0];
        const ending_year = 2021;
        // console.log(collocation_data);
        let network_chart = new NetworkChart(corpus_data, collocation_data, occurrence_data, ending_year);
        // Add event to the year range
        $('#year_range').on('change', function(e){
            let value = e.target.value;
            let ending_year = 0;
            if(value === "0") {
                ending_year = 2010;
            }else if(value === "1") {
                ending_year = 2015;
            }else if(value === "2"){
                ending_year = 2018;
            }else if(value === "3") {
                ending_year = 2021;
            }
            $('#year_range_label').text(ending_year);
            let network_chart = new NetworkChart(corpus_data, collocation_data, occurrence_data, ending_year);
            // console.log(value);
        });
        // Add the event to clear the selected key terms
        $('#clear-label').on('click', function(d){
            // Clear the select items and list view
            $('#selected_term_1').empty();
            $('#selected_term_2').empty();
            $('#text_list_view').empty();
        })


    });




});
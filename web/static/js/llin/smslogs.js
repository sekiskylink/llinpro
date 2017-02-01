$(function (){
    var options = {
            chart: {
                renderTo: 'graph',
                defaultSeriesType: 'column'
            },
            title: {
                text: 'Incoming & Outgoing SMS'
            },
            xAxis: {
                categories: [
                    'MTN',
                    'AIRTEL',
                    'AFRICEL',
                    'UTL',
                ]
            },
            yAxis: {
                title: {
                    text: 'No. of SMS'
                }
            },
            series: [],
            /*
            series: [{
                name: 'Incoming',
                data: [212, 31, 0, 0]
            }, {
                name: 'Outgoing',
                data: [5150, 1335, 4559, 147]
            }],
            */
    };
    $('.gwe').click(function(){
        $.get('kannelseries', {id: $(this).attr('value')}, function(data){
            options.series = [];
            options.categories = [];

            // Split the lines
            var lines = data.split('\n');


            // Iterate over the lines and add categories or series
            $.each(lines, function(lineNo, line) {


                var items = line.split(',');
                var series = {
                    data: []
                };
                $.each(items, function(itemNo, item) {
                    if (itemNo == 0) {
                        series.name = item;
                    } else {
                        series.data.push(parseFloat(item));
                    }
                });

                options.series.push(series);
            });
            var chart = new Highcharts.Chart(options);
        });
        return false;
    });

    $('.regenerate').click(function(){
        $.get('refresh', {month: $(this).attr('value')}, function(data){
            var x = 1;
        });
        return false;
    });

});

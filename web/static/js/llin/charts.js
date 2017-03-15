$(function (){
    var options = {
            chart: {
                renderTo: 'graph',
                type: 'column',
				options3d: {
					enabled: false,
					alpha: 10,
					beta: 25,
					depth: 70
				}
                // defaultSeriesType: 'column'
            },
            title: {
                text: 'Coverage'
            },
            subtitle: {
                text: 'Distribution to sub-county level'
            },
			plotOptions: {
				column: {
					depth: 25
				}
			},
            xAxis: {
                categories: []
            },
            yAxis: {
                title: {
                    text: 'Percentage Coverage'
                }
            },
            series: [],

    };
    $('#generate').click(function(){
        var chart_type = $('#chart').val();
        var wave = $('#wave').val();
        var threeD = $('#3d').val();
        options.chart.options3d.enabled = false;
        if (threeD == 'on'){
            options.chart.options3d.enabled = true;
        }
        var title = chart_type == 'coverage' ? 'Coverage':
            chart_type == 'total_bales' ? 'Bales Distributed':
            chart_type == 'cb' ? 'Coverage & Bales Distributed':
            chart_type == 'acks' ? 'Acknowledgements':
            chart_type == 'variance' ? 'Variance': 'Coverage';

        var ytitle = chart_type == 'coverage' ? 'Percentage':
            chart_type == 'total_bales' ? 'No. of Bales Distributed':
            chart_type == 'cb' ? 'Coverage & Bales Distributed':
            chart_type == 'acks' ? 'No. of Acknowledgements':
            chart_type == 'variance' ? 'No. of Variances': 'Coverage';
        options.title = {'text': "Wave " + wave + " " + title}

        options.subtitle.text = chart_type == 'coverage' ? 'Percentage distribution per district':
            chart_type == 'total_bales' ? 'Number of bales distributed per district':
            chart_type == 'acks' ? 'Number of distribution acknowledgements per district':
            chart_type == 'variance' ? 'Number of distributions with variance per district': '';

        options.series = [];
        options.yAxis.title.text = ytitle;
        $.get('chartdata', {chart_type: chart_type, wave: wave}, function(data){
            // Split the lines
            var lines = data.split('\n');
            $.each(lines, function(lineNo, line) {
				if (lineNo == 0){
                    var items = line.split(',');
                    var x = {
                        categories: []
                    }
                    $.each(items, function(itemNo, item) {
                        x.categories.push(item);
                    });
                    options.xAxis = x;
                }
                else if (lineNo == 1)
                {
                    var items = line.split(',');

                    var series = {
                        name: title,
                        data: []
                    };
                    $.each(items, function(itemNo, item) {
                        series.data.push(parseFloat(item));
                    });

				    options.series.push(series);
                }

            });
            var chart = new Highcharts.Chart(options);
        });

        return false;
    });

});

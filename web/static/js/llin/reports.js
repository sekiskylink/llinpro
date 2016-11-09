$(function (){
    var options = {
        chart: {
            renderTo: 'graph',
            type: 'line',
            marginRight: 130,
            marginBottom: 25
        },
        title: {
            text: 'Contacts per Campaign Event',
            x: -20 //center
        },
        subtitle: {
            text: 'Shows number of contacts per event',
            x: -20
        },
        xAxis: {
            categories: []
        },
        yAxis: {
            title: {
                text: 'Number of Contacts'
            },
            /*
            plotLines: [{
                value: 0,
                width: 1,
                color: '#808080'
            }]
            */
        },
        tooltip: {
            formatter: function() {
                    return '<b>'+ this.series.name +'</b><br/>'+
                    this.x +': '+ this.y;
            }
        },
        legend: {
            layout: 'vertical',
            align: 'right',
            verticalAlign: 'top',
            x: -10,
            y: 100,
            borderWidth: 0
        },
        series: []
    }

    $('#contact_field').change(function(){
        var field = $(this).val();
        $.get('/fieldcontacts', {field:field}, function(data){
            $('#contact-res').html(data);
            $('#ctable').DataTable({
                dom: 'Bfrtip',
                buttons: [
                    'copy', 'csv', 'excel', 'pdf', 'print'
                ]
            });
        });
    });

    $('.stat').click(function(){
        $.getJSON('/campaignseries', {campaign_id: $(this).attr('value')}, function(data){
            options.xAxis.categories = data[0]['data'];
            options.series[0] = data[1];
            var chart = new Highcharts.Chart(options);
            chart.setTitle(null, { text: 'Shows contacts that reached event (Days Relative to: '+ data[2]['relative_to'] + ')'});
        });
        return false;
    });

});

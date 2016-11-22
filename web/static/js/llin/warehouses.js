$(function(){
    $('#warehouse').change(function(){
        warehouseid = $(this).val();
        if (warehouseid == '')
            return;
        $('#warehouse_branch').empty();
        $('#warehouse_branch').append("<option value='' selected='selected'>Select Warehouse Branch</option>");
        $.get(
            '/api/v1/warehousebranches/' + warehouseid,
            {},
            function(data){
                for (i in data){
                    val = data[i]["id"];
                    txt = data[i]["name"];
                    $('#warehouse_branch').append(
                        $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
    });
});

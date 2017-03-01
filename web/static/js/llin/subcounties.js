$(function(){
    $('#district').change(function(){
        var districtid = $(this).val();
        if (districtid == '0' || districtid == "")
            return;
        $('#location').val(districtid);
        $.get(
            '/api/v1/loc_children/' + districtid,
            {xtype:'district', xid: districtid},
            function(data){
                var subcounties = data;
                $("#mydata_body").empty();
                for(var i in subcounties){
                    val = subcounties[i]["id"];
                    txt = subcounties[i]["name"];
                    $('#subcounty').append(
                        $(document.createElement("option")).attr("value",val).text(txt)
                    );
                    markup = "<tr><td>" + i + "</td><td>" +txt + "</td><td><a href='/subcounties?ed=";
                    // markup += val + "' class='btn btn-primary btn-xs'><i class='fa fa-edit'></i></a>";
                    markup += val + "'><i class='fa fa-edit'></i></a>";
                    markup += "&nbsp;&nbsp;&nbsp;<a href='/subcounties?d_id=" + val + "'><i class='fa fa-trash'></i></a>";
                    $('#village').append(
                            $("#mydata_body").append(markup)
                    );
                }
            },
            'json'
        );
    });

});

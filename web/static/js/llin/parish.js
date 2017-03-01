$(function(){
    $('#district').change(function(){
        var districtid = $(this).val();
        if (districtid == '0' || districtid == "")
            return;
        $('#location').val(districtid);
        $('#subcounty').empty();
        $('#subcounty').append("<option value='' selected='selected'>Select Sub County</option>");
        $.get(
            '/api/v1/loc_children/' + districtid,
            {xtype:'district', xid: districtid},
            function(data){
                var subcounties = data;
                for(var i in subcounties){
                    val = subcounties[i]["id"];
                    txt = subcounties[i]["name"];
                    $('#subcounty').append(
                        $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
    });

    /*When subcounty is changed*/
    $('#subcounty').change(function(){
        var subcountyid = $(this).val();
        if (subcountyid == '0' || subcountyid == '')
            return;
        $('#location').val(subcountyid);
        $.get(
            '/api/v1/loc_children/' + subcountyid,
            {},
            function(data){
                var parishes = data;
                for(var i in parishes){
                    val = parishes[i]['id'];
                    txt = parishes[i]['name'];
                    markup = "<tr><td>" + i + "</td><td>" +txt + "</td><td><a href='/parishes?ed=";
                    // markup += val + "' class='btn btn-primary btn-xs'><i class='fa fa-edit'></i></a>";
                    markup += val + "'><i class='fa fa-edit'></i></a>";
                    markup += "&nbsp;&nbsp;&nbsp;<a href='/parishes?d_id=" + val + "'><i class='fa fa-trash'></i></a>";
                    $("#mydata_body").append(markup)
                }
            },
            'json'
        );
    });

});

$(function(){
    $('#district').change(function(){
        var districtid = $(this).val();
        if (districtid == '0' || districtid == "")
            return;
        $('#location').val(districtid);
        $('#subcounty').empty();
        $('#parish').find('option').remove().end();
        $('#village').find('option').remove().end();
        $('#subcounty').append("<option value='' selected='selected'>Select Sub County</option>");
        $('#parish').append("<option value='' selected='selected'>Select Parish</option>");
        $('#village').append("<option value='' selected='selected'>Select Village</option>");
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
        $('#parish').empty();
        $('#village').find('option').remove().end();
        $('#dpoint').empty();
        $('#parish').append("<option value='' selected='selected'>Select Parish</option>");
        $('#village').append("<option value='' selected='selected'>Select Village</option>");
        $('#dpoint').append("<option value='' selected='selected'>Select Distribution Point</option>");
        $.get(
            '/api/v1/loc_children/' + subcountyid,
            {},
            function(data){
                var parishes = data;
                for(var i in parishes){
                    val = parishes[i]['id'];
                    txt = parishes[i]['name'];
                    $('#parish').append(
                            $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
    });

    /*When parish is changed*/
    $('#parish').change(function(){
        var parishid = $(this).val();
        if (parishid == '0' || parishid == '')
            return;
        $('#location').val(parishid);
        $('#village').empty();
        $('#village').append("<option value='' selected='selected'>Select Village</option>");
        $.get(
            '/api/v1/loc_children/' + parishid,
            {},
            function(data){
                var villages = data;
                $("#mydata_body").empty();
                for(var i in villages){
                    val = villages[i]['id'];
                    txt = villages[i]['name'];
                    markup = "<tr><td>" + i + "</td><td>" +txt + "</td><td><a href='/adminunits?ed=";
                    // markup += val + "' class='btn btn-primary btn-xs'><i class='fa fa-edit'></i></a>";
                    markup += val + "'><i class='fa fa-edit'></i></a>";
                    markup += "&nbsp;&nbsp;&nbsp;<a href='/adminunits?d_id=" + val + "'><i class='fa fa-trash'></i></a>";
                    $('#village').append(
                            $("#mydata_body").append(markup)
                    );
                }
            },
            'json'
        );
    });

});

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

    $('.details_btn').click(function(){
        id_val = $(this).attr('id');
        $.get(
            '/api/v1/dispatchrecord/' + id_val,
            {},
            function(data){
                $('#modal_res').html(data);
            });
    });

    $('.sms_btn').click(function(){
        id_val = $(this).attr('id');
        $('#modal_res2').html("");
        $.get(
            '/api/v1/dispatchsms/' + id_val,
            {},
            function(data){
                // var d = JSON.parse(data);
                txt = data["sms"];
                to_subcounty = data["to_subcounty"];
                $('#sms').text(txt);
                $('#to_subcounty').val(to_subcounty);
            });
    });

    $('#sendsms').click(function(){
        $('#modal_res2').css({'color': 'green'});
        to_subcounty = $('#to_subcounty').val()
        sms = $('#sms').val()
        $.post(
            '/api/v1/dispatchsms/0',
            {to_subcounty:to_subcounty, sms:sms},
            function(data){
            $('#modal_res2').html(data);
        });
        return false;
    });

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
        $('#parish').empty();
        $('#parish').append("<option value='' selected='selected'>Select Parish</option>");
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

});

$(function(){
    $('#district').change(function(){
        var districtid = $(this).val();
        if (districtid == '0' || districtid == "")
            return;
        $('#location').val(districtid);
        $('#subcounty').empty();
        $('#villages').empty();
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
        $.get(
            '/api/v1/subcountylocations/' + subcountyid,
            {},
            function(data){
                var $select = $('#villages');
                $.each(data, function(key, value){
                    var group = $('<optgroup label="' + key + '" />');
                    $.each(value, function(){
                        $('<option />').html(this.name).attr('value',this.id).appendTo(group);
                    });
                    group.appendTo($select);
                });
            },
            'json'
        );
    });

});

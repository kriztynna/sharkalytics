function editCompany(){
    // make the form, pre-populate values with the current data
    $('#web_row').html('<input type="text" class="form-control" id="website_input" value="'+current_data.website+'">');
    $('#people').html('<input type="text" class="form-control" id="people_input" value="'+current_data.people+'">');
    $('#desc').html('<input type="text" class="form-control" id="desc_input" value="'+current_data.desc+'">');
    $('#cat_row').html('<input type="text" class="form-control" id="cat_input" value="'+current_data.cat+'">');

    // insert field for additional comments
    $(' #info ').append('<tr><td>notes</td><td><input type="text" class="form-control" id="admin_notes" placeholder="optional message with additional information for the reviewer"></td></tr>')

    // substitute the "edit" button for "cancel" and "submit" buttons
    $('#buttons').html('<button class="btn btn-default" onclick="submitEdit();">submit</button><input id="cancel" type="button" class="btn btn-default" value="cancel" onclick="cancelEdit();" />');
}

function confirmEdit(){
    var this_page = location.href;
    var arg = this_page.indexOf("?");
    if (arg==-1){
        console.log('')
    }
    else {
        var this_page = this_page.slice(0,arg)
    }
    var req = this_page+'?submit=1'
    window.open(req, "_self");
}

function submitEdit(){
    // get the new values
    var website = $( "#website_input" ).val();
    var people = $( "#people_input" ).val();
    var desc = $( "#desc_input" ).val();
    var cat = $( "#cat_input" ).val();
    var admin_notes = $( "#admin_notes" ).val();
    var new_data = {"website":website, "people":people, "desc": desc, "cat": cat, "admin_notes": admin_notes}
    // compare against old values
    var keys = Object.keys(current_data);
    var edits = {};
    for (i=0; i<keys.length; i++) {
        k = keys[i]
        if (current_data[k]==new_data[k]){
            edits[k] = 0;
        }
        else {
            edits[k] = 1;
        }
    }

    var url = location.href;
    var start = url.indexOf("/company/");
    start = start + 9;
    var end = url.indexOf("?");
    if (end==-1) {
        var COID = url.slice(start)
    } else {
        var COID = url.slice(start, end);
    }
    
    // send the new data to the handler
    $.post(
        "/submitcompanyedit",
        {
            edits:edits,
            curr_data:current_data,
            new_data:new_data,
            COID:COID
        },
        confirmEdit
        );
}

function cancelEdit(COID){
    location.reload();
}

function insertInvestors() {
    if (deal==1){
        var investors_card = '<div class="card"><span class="small-title"><b>investors</b></span><table class="table"><tbody>';
        var array_length = investor_ids.length;
        for (var i = 0; i < array_length; i++) {
            var url = '/investor/'+investor_ids[i];
            var text = investor_names[i];
            var initials = text.replace(/[^A-Z]/g, '');
            var html_start = '<tr><td class="left-col"><a href="'+url+'" class="btn btn-default btn-circle"><b>'+initials+'</b></a></td><td style="vertical-align: middle;"><a href=';
            var html_full = html_start.concat(url, '>',text,'</a></td></tr>');
            investors_card = investors_card.concat(html_full);
        }
        investors_card = investors_card.concat('</tbody></table></div>');
        $( "#deal_info" ).append( $( investors_card ) );
    }
}

function insertSubmitConfirm(){
    if (submit==1){
        var confirmText = "<div class='alert alert-success' role='alert' id='confirm'><button type='button' class='close' data-dismiss='alert'><span aria-hidden='true'>&times;</span><span class='sr-only'>Close</span></button><strong>Yay!</strong> Thank you for submitting new data. Your edits will be posted as they are approved by a moderator.</div>"
        $( "#confirm_div" ).append(confirmText)    
        $('#confirm').appendTo('#confirm_div').slideDown('slow');
    }
    else if (submit==0){
        console.log('')
    }
    else {
        console.log('')
    }
}

$( document ).ready( insertDeal );
$( document ).ready( insertSubmitConfirm );
$( document ).ready( insertProductLinks );
$( document ).ready( insertCallCard );
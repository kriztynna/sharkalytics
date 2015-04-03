function prepareForm(){
    var keys = Object.keys(changes);
    var dimensions = ['cat', 'desc', 'people', 'website'];
    var to_insert = '<form class="form-horizontal" role="form" id="changeform"><table class="table" id="changestable"><tr><th></th><th>cat</th><th>desc</th><th>people</th><th>website</th></tr>';
    for (i=0;i<keys.length;i++){
        var change = JSON.parse(changes[i]);
        var old_data = change.curr_data;
        var new_data = change.new_data;
        var edits = change.edits;
        var COID = change.COID;
        var EID = change.EID;
        to_insert = to_insert.concat('<tr><td>edit #'+i+': <span id="COID'+i+'">'+COID+'</span></td>');
        for (j=0;j<dimensions.length;j++){
            var d = dimensions[j];
            if (old_data[d]==''){
                to_insert = to_insert.concat('<td>NA</td>');
            } else {
                to_insert = to_insert.concat('<td>'+old_data[d]+'</td>');
            }
        }
        to_insert = to_insert.concat('</tr><tr><td><span id="EID'+i+'">'+EID+'</span><input type="checkbox" id="edit'+i+'"></td>');
        for (j=0;j<dimensions.length;j++){
            var d = dimensions[j];
            if (edits[d]==1){
                var input = '<td><input type="text" value="'+new_data[d]+'" id="edit'+i+d+'"></td>';
                if (d=='desc') {
                    var input = input.replace('type="text"','type="textarea" rows="3"');
                }
                to_insert = to_insert.concat(input);
            } else if (edits[d]==0){
                to_insert = to_insert.concat('<td><input type="text" value="'+old_data[d]+'" id="edit'+i+d+'"></td>');
            }
            else {
                console.log('d was neither 0 or 1')
            }
        }
        to_insert = to_insert.concat('</tr>')
    }
    to_insert = to_insert.concat('<tr><td></td><td><button type="submit" class="btn btn-default" onclick="approveChanges();">Submit</button></td></tr></table></form>')
    $('#form-div').html(to_insert);
}

function confirmSubmit(){
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

function submitApprovedEdits(){
    // send the new data to the handler
    $.post(
        "/admin/submitapprovededits",
        {
            edits:edits,
        },
    confirmSubmit
    );
}

function approveChanges(){
    var edits_list = ['edit0', 'edit1', 'edit2', 'edit3', 'edit4'];
    for (i=0;i<edits_list.length;i++){
        var edit = '#'+edits_list[i]+':checked';
        var checked = $(edit).val();
        if (checked=='on'){
            processEdit(i);
        } else {
            console.log('')
        }
    }
    submitApprovedEdits()
}

var edits = {};
function processEdit(i){
    var edit_dict = {};
    var dimensions = ['cat', 'desc', 'people', 'website']
    var COID_id = '#COID'+i;
    var EID_id = '#EID'+i;
    edit_dict['COID'] = $(COID_id).html();
    edit_dict['EID'] = $(EID_id).html();
    for (j=0;j<dimensions.length;j++){
        var d = dimensions[j];
        var id = '#edit'+i+d;
        var value = $(id).val();
        edit_dict[d] = value;
    }
    edits[i] = edit_dict;
}

function insertSubmitConfirm(){
    if (submit==1){
        var confirmText = "<div class='alert alert-success' role='alert' id='confirm'><button type='button' class='close' data-dismiss='alert'><span aria-hidden='true'>&times;</span><span class='sr-only'>Close</span></button><strong>Yay!</strong> Edit approved.</div>"
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

$( document ).ready( insertSubmitConfirm )
$( document ).ready( prepareForm )

function createTable(){
    if (request.readyState == 4 && request.status == 200){
        var card_text = '';
        var JSONdata = JSON.parse(request.responseText);
        var episodes = Object.keys(JSONdata);
        
        for (i = episodes[0]; i <= episodes.length; i++) {
            card_text = card_text.concat('<div class="card"><span class="small-title"><b>episode '+i+'</b></span><table class="table"><tbody>')
            var episode = JSONdata[i];
            var cos = Object.keys(episode);
            for ( x = 0; x<cos.length;x++){
                var COID = episode[x]['COID'];
                var name = episode[x]['name'];
                var deal = episode[x]['deal'];
                if (deal==1){var glyph='<span class="glyphicon glyphicon-ok"></span>';}
                else if (deal==0){var glyph='<span class="glyphicon glyphicon-remove"></span>';}
                else {var glyph='';}
                card_text = card_text.concat('<tr><td style="width: 20em;"><a href="/company/'+COID+'">'+name+'</a></td><td>'+glyph+'</td></tr>')
            }
            card_text = card_text.concat('</tbody></table></div>')
        }
    $( "#companies" ).html(card_text)
    }
}

function loadCompanies(){
    var season = $( "#seasons_dropdown" ).val();
    request = new XMLHttpRequest();
    request.onreadystatechange = createTable;
    var req = 'companiespagedata?season='+season;
    var encoded_req = encodeURI(req)
    request.open("GET", encoded_req, true);
    request.send();
}

$( document ).ready( loadCompanies );
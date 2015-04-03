function insertData(){
    if (request.readyState == 4 && request.status == 200){
        var JSONdata = JSON.parse(request.responseText);
        var keys = Object.keys(JSONdata);
        keys.sort();
        keys.reverse();
        $( '#latest' ).html('<div class="small-title">Latest Episodes</div>');

        for (i=0; i<keys.length; i++) {
            k = keys[i];
            ep = JSONdata[k];
            var EPID = ep.EPID;
            var season = ep.season;
            var epnumber = ep.epnumber;
            var pitches = ep.pitches;
            var sharks = ep.sharks;
            var shark_deal_count = ep.shark_deal_count;
            var shark_deal_dollars = ep.shark_deal_dollars;
            var counts = ep.counts;
            var shark_count = counts['shark_count'];
            var pitch_count = counts['pitch_count'];

            // set up the episode text
            var episode_text = '<div class="card"><div class="card-title"><a href="/season/'+season+'">S'+season+'</a>:<a href="/episode/'+EPID+'">E'+epnumber+'</a></div>';

            // now set up the shark text
            var cast = '<div class="cast">Sharks: '
            var shark_counter = 1;
            for (s in sharks) {
                var link = '<a href="/investor/'+s+'">'+sharks[s]+'</a>';
                cast = cast.concat(link);
                if (shark_count>1 && shark_counter<shark_count){
                    cast = cast.concat(', ')
                } 
                shark_counter = shark_counter + 1
            }
            cast = cast.concat('</div>')

            // now set up the pitch text
            var pitches_text = '<table class="table"><tbody>';
            for (pitch in pitches) {
                if (pitches[pitch]['deal']==1){
                    pitches_text = pitches_text.concat('<tr><td><span class="glyphicon glyphicon-ok"></span></td>')
                }
                else if (pitches[pitch]['deal']==0){
                    pitches_text = pitches_text.concat('<tr><td></td>')
                }
                var co_link = '<td><a class="company-name" href="/company/'+pitches[pitch]['COID']+'">'+pitches[pitch]['name']+'</a>';
                pitches_text = pitches_text.concat(co_link);
                var cat_link = '<a href="/category/'+pitches[pitch]['CatID']+'">'+pitches[pitch]['category']+'</a>';
                pitches_text = pitches_text.concat(', a company in the '+cat_link+' space asking for '+pitches[pitch]['ask_usd']+' for '+pitches[pitch]['ask_pct']+'</td></tr>')
            }

            pitches_text = pitches_text.concat('</tbody></table>')
            cast = cast.concat('</div>')
            var all_in = episode_text+pitches_text+cast;

            $( "#latest" ).append( $( all_in ) );
        }
    }
}

function getMainPageData(){
    request = new XMLHttpRequest();
    request.onreadystatechange = insertData;
    var req = 'mainpagedata';
    var encoded_req = encodeURI(req);
    request.open("GET",encoded_req,true);
    request.send();
}

$( document ).ready( getMainPageData );
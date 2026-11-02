from backend.portraits import RosterParser,merge_roster,safe_image,portrait_for

def photo_url():return 'https://am-a.akamaihd.net/image?resize=320:&f=https%3A%2F%2Fstatic.lolesports.com%2Fplayers%2Fsample.png'

def test_official_roster_parser():
    p=RosterParser();p.feed('<article><img src="'+photo_url().replace('&','&amp;')+'" alt="Public professional name"><h3>Sample</h3></article>')
    assert len(p.players)==1 and p.players[0]['name']=='Sample'
    assert safe_image(p.players[0]['image_url'])

def test_ambiguous_handles_never_get_assigned():
    c={'portraits':{},'unmatched':[],'sources':[]}
    merge_roster(c,[{'name':'Sample','image_url':photo_url()}],[{'id':'1','name':'sample'},{'id':'2','name':'Ｓａｍｐｌｅ'}],'https://lolesports.com/en-US/teams/example')
    assert c['portraits']=={} and c['unmatched'][0]['reason']=='ambiguous'

def test_identity_source_and_no_remote_proxy():
    c={'portraits':{},'unmatched':[],'sources':[]}
    merge_roster(c,[{'name':'Sample','image_url':photo_url(),'source_name':'Sample Name'}],[{'id':'oe:sample','name':'sample'}],'https://lolesports.com/en-US/teams/example')
    photo=portrait_for('oe:sample',catalog=c)
    assert photo['external_player_id']=='oe:sample' and photo['photo_season'] is None
    assert not safe_image('https://am-a.akamaihd.net/image?f=http://127.0.0.1/secret')
    assert not safe_image('javascript:alert(1)')

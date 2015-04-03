from collections import OrderedDict
import csv 
import datetime
import json
import logging
import os

import jinja2
import MySQLdb
import urllib2
import StringIO
import webapp2


# Configure the Jinja2 environment.
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)


# Define your production Cloud SQL instance information.
_INSTANCE_NAME = 'sql-fortress:fortress-one'

class Handler(webapp2.RequestHandler):
    def connectToDB(self):
        start = datetime.datetime.now()
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
        else:
            db = MySQLdb.connect(host='127.0.0.1', port=3306, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
            # Alternatively, connect to a Google Cloud SQL instance using:
            # db = MySQLdb.connect(host='ip-address-of-google-cloud-sql-instance', port=3306, user='root')
        end = datetime.datetime.now()
        length = end-start
        length = length.total_seconds()
        logging.debug('DB connection time: %s seconds', length)
        return db

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)

class DebugPage(Handler):
    def get(self):
        db = self.connectToDB()
        cursor = db.cursor()
        increment = 50000
        min_deal_size = 0
        max_deal_size = 50000 #largest deal in shark tank history
        while max_deal_size<=2500000:
            label = max_deal_size-1
            cursor.execute('SELECT COUNT(DID) FROM deals WHERE deal_usd>=%s AND deal_usd<%s', [min_deal_size, max_deal_size])
            (tally,) = cursor.fetchone()
            if tally!=0:
                self.response.write('<br>%s to %s\t' % (min_deal_size, label))
                self.response.write(tally)
                min_deal_size=max_deal_size
                max_deal_size+=increment
            elif tally==0:
                max_deal_size+=increment
            else:
                self.response.write('whups, tally was neither 0 or not 0. we are screwed.')

class FixIDs(Handler):
    def get(self):
        db = self.connectToDB()
        cursor = db.cursor()

        cursor.execute('SELECT PID, COID, deal FROM pitches WHERE PID LIKE "% %"')
        results = cursor.fetchall()
        for row in results:
            (old_PID, COID, deal) = row
            new_PID = old_PID.replace(' ', '-')
            cursor.execute('UPDATE pitches SET PID=%s WHERE COID=%s',[new_PID, COID])
            db.commit()
            if deal==1:
                new_DID = new_PID
                cursor.execute('UPDATE deals SET DID=%s WHERE COID=%s',[new_DID, COID])
                db.commit()
                self.response.write(new_DID)
            self.response.write(new_PID)
        db.close()

class ReviewEditsPage(Handler):
    def get(self, submit=0):
        variables = {}
        changes = {}
        change_index = 0
        check_submit = self.request.get('submit')
        if check_submit=='1':
            variables['submit'] = 1
        else:
            variables['submit'] = 0

        db = self.connectToDB()
        cursor = db.cursor()
        cursor.execute('SELECT EID, changes FROM proposededits WHERE approved=0 AND type="company" ORDER BY submitted DESC LIMIT 5')
        results = cursor.fetchall()
        
        for row in results:
            c = json.loads(row[1])
            c['EID'] = row[0]
            c = json.dumps(c)
            changes[change_index] = c
            change_index+=1
        
        changes_json = json.dumps(changes)
        variables['changes'] = changes_json
        template = jinja_env.get_template('reviewedits.html')
        self.response.write(template.render(variables))

class SubmitApprovedEditsPage(Handler):
    def post(self):
        db = self.connectToDB()
        cursor = db.cursor()

        attrs = ['COID', 'website', 'people', 'cat', 'desc']
        edits = ['edits[0]', 'edits[1]', 'edits[2]', 'edits[3]', 'edits[4]']

        for e in edits:
            keyword = e+'[EID]'
            payload =  self.request.get(keyword)
            if payload!='':
                to_update = {}
                to_update['EID'] = payload
                for a in attrs:
                    spec_key = e+'['+a+']'
                    p = self.request.get(spec_key)
                    to_update[a] = p
                logging.debug(to_update)
                cursor.execute("UPDATE companies SET category=%s, description=%s, people=%s, website=%s WHERE COID=%s", [to_update['cat'], to_update['desc'], to_update['people'], to_update['website'], to_update['COID']])
                cursor.execute("UPDATE proposededits SET approved=1 WHERE EID=%s", [to_update['EID']])
                db.commit()
            elif payload=='':
                continue
            else:
                logging.debug("there was an error getting data from this keyword: %s", e)

        db.close()

class AddEpisode(Handler):
    def insertInvestorInfo(self, n, DID):
        db = self.connectToDB()
        cursor = db.cursor()

        logging.debug('inserting investor info')
        investors = {}
        for k, v in shark_dict.iteritems():
            invest_amt = self.request.get(k+'deal'+n)
            if invest_amt!='':
                investors[k] = int(invest_amt)
            elif invest_amt=='':
                investors[k] = 0
            else:
                logging.debug('this investor returned an unexpected result: '+invest_amt)
        logging.debug(investors)
        cursor.execute('UPDATE deals SET kharrington=%s, jfoxworthy=%s, rherjavec=%s, koleary=%s, djohn=%s, bcorcoran=%s, lgreiner=%s, mcuban=%s, jpdejoria=%s, stisch=%s, nwoodman=%s WHERE DID=%s', [investors['kharrington'], investors['jfoxworthy'], investors['rherjavec'], investors['koleary'], investors['djohn'], investors['bcorcoran'], investors['lgreiner'], investors['mcuban'], investors['jpdejoria'], investors['stisch'], investors['nwoodman'], DID] )
        db.commit()
    def get(self, submit=0):
        variables = {}
        check_submit = self.request.get('submit')
        if check_submit=='1':
            variables['submit'] = 1
        else:
            variables['submit'] = 0
        template = jinja_env.get_template('addepisode.html')
        self.response.write(template.render(variables))
    def post(self):
        db = self.connectToDB()
        cursor = db.cursor()

        # get the basic episode stats
        season = self.request.get('season')
        epnumber = self.request.get('epnumber')
        EPID = int(season) * 100 + int(epnumber)
        airdate = self.request.get('airdate')
        title = '' # for now don't have a place to enter it on the form. it's not important anyway.

        # get the cast
        sharks_in_ep = {}
        for k, v in shark_dict.iteritems():
            s = self.request.get(k)
            if s!='':
                sharks_in_ep[k] = 1
            else:
                sharks_in_ep[k] = 0

        # now get the company, pitch, and deal info
        list_of_pitches = ['1', '2', '3', '4']
        company_info = ['name', 'cat', 'description', 'people', 'website']
        pitch_info = ['ask_usd', 'ask_pct', 'special', 'dealcheck']
        deal_info = ['deal_usd', 'deal_pct', 'dealspecial']
        co_verification = []
        pitch_verification = []
        deal_verification = []

        for n in list_of_pitches:
            # first see if there was a deal
            if self.request.get('dealcheck'+n)=='1':
                dealcheck = '1'
            elif self.request.get('dealcheck'+n)=='':
                dealcheck = '0'
            else:
                logging.debug('deal returned an unexpected answer')

            # next, the company info
            company = {}
            for c in company_info:
                company[c] = self.request.get(c+n)
            # create the COID
            COID = company['name'].lower()
            COID = COID.replace(' ', '-')
            company['COID'] = COID
            # check category exists, or create new one
            cursor.execute('SELECT 1 FROM categories where name=%s', [company['cat']])
            try:
                (cat_check,) = cursor.fetchone()
                logging.debug('the category seems to exist: %s', company['cat'])
            except:
                logging.debug('category could not be found. inserting: %s', company['cat'])
                CatID = company['cat'].lower()
                CatID = CatID.replace(' ', '-')
                cursor.execute('INSERT INTO categories (CatID, name) VALUES (%s, %s)', [CatID, company['cat']])

            # insert company
            cursor.execute('INSERT INTO companies (COID, name, category, description, people, website, deal) VALUES (%s, %s, %s, %s, %s, %s, %s)', [company['COID'], company['name'], company['cat'], company['description'], company['people'], company['website'], dealcheck])
            db.commit()
            co_verification.append(company['COID'])

            # now the pitch info
            pitch = {}
            PID = COID+'-'+str(EPID)
            for p in pitch_info:
                pitch[p] = self.request.get(p+n)
            cursor.execute('INSERT INTO pitches (PID, COID, EPID, ask_usd, ask_pct, special, deal) VALUES (%s, %s, %s, %s, %s, %s, %s)', [PID, company['COID'], EPID, pitch['ask_usd'], pitch['ask_pct'], pitch['special'], dealcheck])
            db.commit()
            pitch_verification.append(PID)

            # now deal info
            deal = {}
            if dealcheck=='1':
                DID = PID
                for d in deal_info:
                    deal[d] = self.request.get(d+n)
                cursor.execute('INSERT INTO deals (DID, COID, EPID, deal_usd, deal_pct, other_terms) VALUES (%s, %s, %s, %s, %s, %s)', [DID, company['COID'], EPID, deal['deal_usd'], deal['deal_pct'], deal['dealspecial']])
                db.commit()
                self.insertInvestorInfo(n, DID)
                deal_verification.append(DID)

        # finally, enter the episode
        cursor.execute('INSERT INTO episodes (EPID, season, epnumber, airdate, title) VALUES (%s, %s, %s, %s, %s)', [EPID, season, epnumber, airdate, title])
        db.commit()
        cursor.execute('UPDATE episodes SET kharrington=%s, jfoxworthy=%s, rherjavec=%s, koleary=%s, djohn=%s, bcorcoran=%s, lgreiner=%s, mcuban=%s, jpdejoria=%s, stisch=%s, nwoodman=%s WHERE EPID=%s', [sharks_in_ep['kharrington'], sharks_in_ep['jfoxworthy'], sharks_in_ep['rherjavec'], sharks_in_ep['koleary'], sharks_in_ep['djohn'], sharks_in_ep['bcorcoran'], sharks_in_ep['lgreiner'], sharks_in_ep['mcuban'], sharks_in_ep['jpdejoria'], sharks_in_ep['stisch'], sharks_in_ep['nwoodman'], EPID])
        db.commit()

        # redirect to home page, where the results can be seen
        self.redirect('/')

########## Utils ##########
shark_dict = {"kharrington": "Kevin Harrington", "jfoxworthy": "Jeff Foxworthy", "rherjavec": "Robert Herjavec", "koleary": "Kevin O'Leary", "djohn": "Daymond John", "bcorcoran": "Barbara Corcoran", "lgreiner": "Lori Greiner", "mcuban": "Mark Cuban", "jpdejoria": "John Paul DeJoria", "stisch": "Steve Tisch", "nwoodman": 'Nick Woodman'}

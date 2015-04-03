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

from imports import *
from admin import *

# For new deployments, make a privatevariables.py file with your own values #
from privatevariables import *


# Configure the Jinja2 environment.
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)

class Handler(webapp2.RequestHandler):
    # from privatevariables getting database_name, user, passwd
    def connectToDB(self):
        start = datetime.datetime.now()
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + INSTANCE_NAME, db=database_name, user=user, passwd=passwd)
        else:
            db = MySQLdb.connect(host='127.0.0.1', port=3306, db=database_name, user=user, passwd=passwd)
            # Alternatively, connect to a Google Cloud SQL instance using:
            # db = MySQLdb.connect(host='ip-address-of-google-cloud-sql-instance', port=3306, user='root')
        end = datetime.datetime.now()
        length = end-start
        length = length.total_seconds()
        logging.debug('DB connection time: %s seconds', length)
        return db

    def verifyUA(self):
        # filters traffic from empty or disallowed UAs
        # used throughout the site
        if 'User-Agent' not in self.request.headers:
            return False

        user_agent = self.request.headers['User-Agent']
        if user_agent=='':
            return False

        # from privatevariables getting flagged_terms
        for f in flagged_terms:
            if f in user_agent:
                return False

        # if nothing so far has set off a False, then just return True and move along
        return True

    def verifyIP(self):
        # filters traffic from disallowed IPs, for when they get through despite dos.yaml
        # used in selected handlers
        if self.request.remote_addr:
            addr = self.request.remote_addr
            # from privatevariables getting flagged_IPs
            for IP in flagged_IPs:
                if addr==IP:
                    return False
            else:
                return True
        else:
            return False

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)

class MainPage(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID

        template = jinja_env.get_template('front.html')
        self.response.write(template.render(variables))

class MainPageData(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        variables = {}

        # look up the latest episode
        cursor.execute('SELECT EPID, season, epnumber FROM episodes ORDER BY EPID DESC LIMIT 5')
        results = cursor.fetchall()
        for row in results:
            ep_data = {}
            EPID = row [0]
            season = row[1]
            epnumber = row[2]
        
            ep_data['EPID'] = EPID
            ep_data['season'] = season
            ep_data['epnumber'] = epnumber

            # get episode stats: total invested, total deals, sharks with deals
            cursor.execute('SELECT SUM(deal_usd) FROM deals WHERE EPID=%s', [EPID])
            (total_invested,) = cursor.fetchone()
            cursor.execute('SELECT SUM(deal) FROM pitches WHERE EPID=%s', [EPID])
            (total_deals,) = cursor.fetchone()
            shark_deal_count = {}
            shark_deal_dollars = {}
            for SID, name in shark_dict.iteritems():
                query = 'SELECT COUNT(%s) FROM deals WHERE EPID=%%s and %s>0' % (SID, SID)
                cursor.execute(query, [EPID])
                (this_shark_deal_count,) = cursor.fetchone()
                if this_shark_deal_count > 0:
                    shark_deal_count[name] = this_shark_deal_count
                    query = 'SELECT SUM(%s) FROM deals WHERE EPID=%%s and %s>0' % (SID, SID)
                    cursor.execute(query, [EPID])
                    (this_shark_deal_dollars,) = cursor.fetchone()
                    this_shark_deal_dollars = "${:,}".format(int(this_shark_deal_dollars))
                    shark_deal_dollars[name] = this_shark_deal_dollars
            ep_data['shark_deal_count'] = shark_deal_count
            ep_data['shark_deal_dollars'] = shark_deal_dollars

            shark_count = 0
            new_shark_dict = {}
            for SID, name in shark_dict.iteritems():
                query = 'SELECT %s FROM episodes WHERE EPID=%%s' % SID
                cursor.execute(query, [EPID])
                (result,) = cursor.fetchone()
                if result==1:
                    new_shark_dict[SID] = name
                    shark_count+=1

            # find the pitches
            pitches = {}
            cursor.execute('SELECT PID, COID, ask_usd, ask_pct, deal FROM pitches WHERE EPID=%s', [EPID])
            results = cursor.fetchall()
            pitch_count = 0
            for row in results:
                PID = row[0]
                COID = row[1]
                ask_usd = row[2]
                ask_pct = row[3]
                deal = row[4]
                pitch_count+=1
                cursor.execute('SELECT name, category FROM companies WHERE COID=%s', [COID])
                (name, category) = cursor.fetchone()
                category = category.lower()
                cursor.execute('SELECT CatID FROM categories WHERE name=%s', [category])
                (CatID,) = cursor.fetchone()

                if deal==1:
                    cursor.execute('SELECT deal_usd, deal_pct FROM deals WHERE DID=%s', [PID])
                    (deal_usd, deal_pct) = cursor.fetchone()
                elif deal==0:
                    deal_usd = 0
                    deal_pct = 0
                else:
                    deal_usd = 0
                    deal_pct = 0
                    logging.debug('there was a problem parsing whether a deal got done')

                ask_usd = '${:,}'.format(ask_usd)
                ask_pct = '{:.0%}'.format(ask_pct)
                deal_usd = '${:,}'.format(deal_usd)
                deal_pct = '{:.0%}'.format(deal_pct)

                pitch = dict(COID=COID, name=name, category=category, CatID=CatID, ask_usd=ask_usd, ask_pct=ask_pct, deal=deal, deal_usd=deal_usd)
                pitches[PID] = pitch

            ep_data['counts'] = dict(shark_count=shark_count, pitch_count=pitch_count)
            ep_data['pitches'] = pitches
            ep_data['sharks'] = new_shark_dict
            variables[EPID] = ep_data

        json_output = json.dumps(variables)
        db.close()
        self.response.write(json_output)

class AboutPage(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID

        db = self.connectToDB()
        cursor = db.cursor()
        
        cursor.execute('SELECT COUNT(EPID) FROM episodes')
        (episode_count,) = cursor.fetchone()
        minutes = 43 # rough estimate of typical episode length not counting commercials
        total_minutes = minutes * int(episode_count)
        total_minutes = "{:,}".format(total_minutes)
        variables['total_minutes'] = total_minutes

        template = jinja_env.get_template('about.html')
        self.response.write(template.render(variables))
        db.close()

class SearchPage(Handler):
    def post(self):
        search_terms = self.request.get('search_terms')
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        variables['search_terms'] = search_terms
        template = jinja_env.get_template('search_results.html')
        self.response.write(template.render(variables))

class SearchResults(Handler):
    def searchSharkDB(self,search_terms):
        results = {}
        
        db = self.connectToDB()
        cursor = db.cursor()
        query = "SELECT COID, name FROM companies WHERE name LIKE '%%%s%%'" % search_terms
        cursor.execute("SELECT COID, name FROM companies WHERE name LIKE %s", [("%%%s%%" % search_terms)])
        co_results = cursor.fetchall()
        co_results_dict = {}
        co_count = 0
        for row in co_results:
            COID = row[0]
            name = row[1]
            co_results_dict[COID] = name
            co_count+=1
        results['co_results'] = co_results_dict
        
        # get investors
        new_shark_dict = {}
        shark_count = 0
        lc_search_terms = search_terms.lower()
        for SID, name in shark_dict.iteritems():
            lc_name = name.lower()
            if lc_search_terms in lc_name:
                new_shark_dict[SID] = name
                shark_count+=1
        results['shark_results'] = new_shark_dict
        
        # get categories
        cursor.execute("SELECT CatID, name FROM categories WHERE name LIKE %s", [("%%%s%%" % search_terms)])
        cat_results = cursor.fetchall()
        cat_results_dict = {}
        cat_count = 0
        for row in cat_results:
            CatID = row[0]
            name = row[1]
            cat_results_dict[CatID] = name
            cat_count+=1
        results['cat_results'] = cat_results_dict

        counts = dict(co_count=co_count, cat_count=cat_count, shark_count=shark_count)
        results['counts'] = counts

        db.close()
        return results

    def get(self):
        if not self.verifyUA():
            self.error(404)
            return
        if not self.verifyIP():
            self.redirect('/purchase')
            return

        search_terms = self.request.get('search_terms')
        variables = self.searchSharkDB(search_terms)
        json_output = json.dumps(variables)
        self.response.write(json_output)

class Episodes(Handler):
    def get(self, season=""):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        seasons = [1, 2, 3, 4, 5, 6]
        ep_count_by_season = {}

        # get episodes by season
        max_rows = 0
        for s in seasons:
            cursor.execute('SELECT COUNT(EPID) FROM episodes WHERE season=%s', [s])
            (episodes_in_season,) = cursor.fetchone()
            ep_count_by_season[s] = episodes_in_season
            if episodes_in_season>max_rows:
                max_rows=episodes_in_season
            cursor.execute('SELECT EPID, epnumber FROM episodes WHERE season=%s', [s])
            results = cursor.fetchall()
            seasons_eps = []
            for row in results:
                seasons_eps.append([row[0], row[1]])
            ep_count_by_season[s] = seasons_eps
        variables['amount_of_rows'] = int(max_rows)
        variables['ep_count_by_season'] = ep_count_by_season

        template = jinja_env.get_template('episodes.html')
        self.response.write(template.render(variables))
        db.close()

class Companies(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID

        # first get the summary stats
        # starting with total_pitches, total_deals, total_pct_success, and total_deal_usd
        cursor.execute('SELECT COUNT(PID) FROM pitches')
        (total_pitches,) = cursor.fetchone()
        cursor.execute('SELECT COUNT(DID) FROM deals')
        (total_deals,) = cursor.fetchone()
        total_pct_success = float(total_deals)/total_pitches
        cursor.execute('SELECT SUM(deal_usd) FROM deals')
        (total_deal_usd,) = cursor.fetchone()
        cursor.execute('SELECT SUM(ask_usd) FROM pitches')
        # now getting avg_delta_usd, more_less_usd 
        cursor.execute('SELECT AVG(deal_usd) FROM deals')
        (avg_deal_usd,) = cursor.fetchone()
        cursor.execute('SELECT AVG(ask_usd) FROM pitches WHERE deal=1')
        (avg_ask_usd,) = cursor.fetchone()
        avg_delta_usd = avg_deal_usd - avg_ask_usd
        if avg_delta_usd>0:
            more_less_usd = 'more than'
        elif avg_delta_usd<0:
            more_less_usd = 'less than'
            avg_delta_usd = abs(avg_delta_usd)
        elif avg_delta_usd==0:
            avg_delta_usd = ''
            more_less_usd = 'even with what'
        # now getting avg_deal_pct, avg_delta_pct, more_less_pct
        cursor.execute('SELECT AVG(deal_pct) FROM deals')
        (avg_deal_pct,) = cursor.fetchone()
        cursor.execute('SELECT AVG(ask_pct) FROM pitches WHERE deal=1')
        (avg_ask_pct,) = cursor.fetchone()
        avg_delta_pct = avg_deal_pct - avg_ask_pct
        if avg_delta_pct>0:
            more_less_pct = 'percentage points more than'
        elif avg_delta_pct<0:
            more_less_pct = 'percentage points less than'
            avg_delta_pct = abs(avg_delta_pct)
        elif avg_delta_pct==0:
            more_less_pct = 'even with what'
            avg_delta_pct = ''
        # now getting avg_deal_val and discount
        cursor.execute('SELECT AVG(deal_val) FROM (SELECT DID, deal_usd/deal_pct As deal_val FROM deals WHERE deal_pct>0) ValTable')
        (avg_deal_val,) = cursor.fetchone()
        cursor.execute('SELECT AVG(ask_val) FROM (SELECT pitches.PID, pitches.ask_usd/pitches.ask_pct As ask_val FROM pitches INNER JOIN deals on pitches.PID=deals.DID WHERE deals.deal_pct>0) ValTable')
        (avg_ask_val,) = cursor.fetchone()
        delta_val = float(avg_deal_val)/float(avg_ask_val)-1
        if delta_val>0:
            discount = 'a '+"{:.0%}".format(delta_val)+' premium to'
        elif delta_val<0:
            discount = 'a '+"{:.0%}".format(abs(delta_val))+' discount to'
            delta_val = abs(delta_val)
        elif delta_val==0:
            discount = 'even with'

        # now format and add to the variables dict
        variables['total_pitches'] = "{:,}".format(int(total_pitches))
        variables['total_deals'] = "{:,}".format(int(total_deals))
        variables['total_deal_usd'] = "${:,}".format(total_deal_usd)
        variables['total_pct_success'] = "{:.0%}".format(total_pct_success)
        variables['avg_delta_usd'] = "${:,}".format(int(avg_delta_usd))
        variables['avg_deal_pct'] = "{:.0%}".format(avg_deal_pct)
        variables['avg_delta_pct'] = "{:,}".format(int(avg_delta_pct*100))
        variables['avg_deal_val'] = "${:,}".format(int(avg_deal_val))
        variables['discount'] = discount

        # more_less_usd, more_less_pct, and discount might be a number or a string. have to check before formatting.
        if isinstance(more_less_usd, basestring):
            variables['more_less_usd'] = more_less_usd
        else:
            variables['more_less_usd'] = "${:,}".more_less_usd
        if isinstance(more_less_pct, basestring):
            variables['more_less_pct'] = more_less_pct
        else:
            variables['more_less_pct'] = "{:.0%}".format(more_less_pct)

        # Create a list of companies
        cursor.execute('SELECT COID, name, deal, website FROM companies')
        companylist = [];
        for row in cursor.fetchall():
          companylist.append(dict([('COID',row[0]),
                                 ('name',row[1]),
                                 ('deal',row[2]),
                                 ('website',row[3])
                                 ]))
        variables['companylist'] = companylist

        # Create the list of seasons for the drop down menu
        seasons = []
        cursor.execute('SELECT DISTINCT season FROM episodes')
        results = cursor.fetchall()
        for row in results:
            seasons.append(row[0])
        variables['seasons'] = seasons

        template = jinja_env.get_template('companies.html')
        self.response.write(template.render(variables))
        db.close()

class CompaniesPageData(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return
        if not self.verifyIP():
            self.error(404)
            return

        season = self.request.get('season')
        db = self.connectToDB()
        cursor = db.cursor()
        season_dict = {}
        cursor.execute('SELECT EPID, epnumber FROM episodes WHERE season=%s ORDER BY epnumber ASC', [season])
        ep_results = cursor.fetchall()
        for ep in ep_results:
            ep_list = []
            EPID = ep[0]
            epnumber = ep[1]
            cursor.execute('SELECT COID, deal FROM pitches WHERE EPID=%s ORDER BY COID ASC', [EPID])
            co_results = cursor.fetchall()
            cos_in_ep = []
            for co in co_results:
                COID = co[0]
                deal = co[1]
                cursor.execute('SELECT name FROM companies WHERE COID=%s', [COID])
                (name,) = cursor.fetchone()
                entry = dict(COID=COID,name=name,deal=deal)
                ep_list.append(entry)
            season_dict[str(epnumber)] = ep_list
        json_output = json.dumps(season_dict)
        self.response.write(json_output)

class CompanyPage(Handler):
    def get(self, COID, submit=0):
        if not self.verifyUA():
            self.error(404)
            return
        if not self.verifyIP():
            self.redirect('/purchase')
            return

        db = self.connectToDB()
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        check_submit = self.request.get('submit')
        if check_submit=='1':
            variables['submit'] = 1
        else:
            variables['submit'] = 0

        # get the company-specific data
        cursor = db.cursor()
        cursor.execute('SELECT name, people, website, category, description FROM companies WHERE COID=%s',[COID])
        row = cursor.fetchone()
        if row is None:
            db.close()
            self.redirect('/companies', permanent=True)
        else:
            variables['name'] = row[0]
            variables['people'] = row[1]
            variables['website'] = row[2]
            category = row[3]
            variables['category'] = category
            variables['desc'] = row[4]
            try:
                cursor.execute('SELECT CatID FROM categories WHERE name=%s', [category])
                (variables['CatID'],) = cursor.fetchone()
            except:
                logging.debug('the category %s is not found in the categories list', [category])

            # get the pitch data
            cursor = db.cursor()
            cursor.execute('SELECT PID, EPID, deal, ask_usd, ask_pct FROM pitches WHERE COID=%s ORDER BY EPID DESC',[COID])
            (PID, EPID, deal, ask_usd, ask_pct) = cursor.fetchone()
            ask_val = ask_usd/float(ask_pct)
            ask_usd = "${:,}".format(ask_usd)
            ask_val = "${:,}".format(int(ask_val))
            ask_pct = '{:.0%}'.format(ask_pct)
            variables['deal'] = deal
            variables['ask_usd'] = ask_usd
            variables['ask_pct'] = ask_pct
            variables['ask_val'] = ask_val

            # get the deal data
            if deal==1:
                cursor = db.cursor()
                cursor.execute('SELECT DID, deal_usd, deal_pct, other_terms FROM deals WHERE DID=%s',[PID])
                (DID, deal_usd, deal_pct, other_terms) = cursor.fetchone()
                try:
                    deal_val = deal_usd/float(deal_pct)
                    deal_val = "${:,}".format(int(deal_val))
                except:
                    deal_val = '(not available)'

                deal_usd = "${:,}".format(deal_usd)
                deal_pct = '{:.0%}'.format(deal_pct)
                variables['deal_usd'] = deal_usd
                variables['deal_pct'] = deal_pct
                variables['deal_val'] = deal_val
                variables['other_terms'] = other_terms
                # now the investors
                investor_ids = []
                investor_names = []
                cursor.execute('SELECT DID, kharrington, jfoxworthy, rherjavec, koleary, djohn, bcorcoran, lgreiner, mcuban, jpdejoria, stisch, nwoodman FROM deals WHERE DID=%s', [PID])
                row = cursor.fetchone()
                invest_dict = {}
                invest_dict['kharrington'] = row[1]
                invest_dict['jfoxworthy'] = row[2]
                invest_dict['rherjavec'] = row[3]
                invest_dict['koleary'] = row[4]
                invest_dict['djohn'] = row[5]
                invest_dict['bcorcoran'] = row[6]
                invest_dict['lgreiner'] = row[7]
                invest_dict['mcuban'] = row[8]
                invest_dict['jpdejoria'] = row[9]
                invest_dict['stisch'] = row[10]
                invest_dict['nwoodman'] = row[11]
                for k, v in invest_dict.iteritems():
                    if invest_dict[k]>0:
                        investor_ids.append(k)
                        investor_names.append(shark_dict[k])
                variables['investor_ids'] = investor_ids
                variables['investor_names'] = investor_names
            if deal==0:
                variables['investor_ids'] = 0
                variables['investor_names'] = 0

            # get the episode data
            cursor = db.cursor()
            cursor.execute('SELECT season, epnumber FROM episodes WHERE EPID=%s',[EPID])
            row = cursor.fetchone()
            variables['season'] = row[0]
            variables['epnumber'] = row[1]
            variables['EPID'] = EPID

            # get the eCommerce data
            cursor = db.cursor()
            cursor.execute('SELECT amazon FROM companies WHERE COID=%s', [COID])
            (amazon,) = cursor.fetchone()
            if amazon!='x' and amazon!=None:
                variables['buyit'] = 1
                variables['amazon'] = amazon
            else:
                variables['buyit'] = 0

            template = jinja_env.get_template('company.html')
            self.response.write(template.render(variables))
            db.close()

class SubmitCompanyEdit(Handler):
    def post(self):
        COID = self.request.get('COID')
        edits = {}
        new_data = {}
        curr_data = {}
        attrs = ['website', 'people', 'cat', 'desc']
        for a in attrs:
            req = 'edits['+a+']'
            edits[a] = self.request.get(req)
        for a in attrs:
            req = 'curr_data['+a+']'
            curr_data[a] = self.request.get(req)
        for a in attrs:
            req = 'new_data['+a+']'
            new_data[a] = self.request.get(req)
        new_data['admin_notes'] = self.request.get('new_data[admin_notes]')
        changes = dict(COID=COID, edits=edits, new_data=new_data, curr_data=curr_data)
        changes_json = json.dumps(changes)
        db = self.connectToDB()
        cursor = db.cursor()
        cursor.execute('INSERT INTO proposededits (type, changes) VALUES ("company", %s)', [changes_json])
        db.commit()
        db.close()

class Sharks(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        this_shark_dict = OrderedDict(shark_dict)
        names = OrderedDict(sorted(this_shark_dict.items(), key=lambda t: t[1]))
        initials = {}
        for k, v in names.iteritems():
            first, last = v.split(' ', 1)
            these_initials = first[0]+last[0]
            initials[k] = these_initials

        initials = OrderedDict(sorted(initials.items(), key=lambda t: t[1]))

        variables = {'names': names, 'initials': initials}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        template = jinja_env.get_template('sharks.html')
        self.response.write(template.render(variables))

class DealsPage(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID

        cursor.execute('SELECT COUNT(DID) FROM deals')
        (deal_count,) = cursor.fetchone()

        cursor.execute('SELECT COUNT(DID) FROM deals WHERE other_terms!=""')
        (special_deal_count,) = cursor.fetchone()

        cursor.execute('SELECT COUNT(DID) FROM deals WHERE deal_pct<=0')
        (no_equity_deal_count,) = cursor.fetchone()

        cursor.execute('SELECT season, epnumber, airdate FROM episodes ORDER BY EPID DESC LIMIT 0, 1')
        (season, epnumber, airdate) = cursor.fetchone()

        last_ep_date = datetime.datetime.strftime(airdate, '%B %d, %Y')

        variables['deal_count'] = deal_count
        variables['special_deal_count'] = special_deal_count
        variables['no_equity_deal_count'] = no_equity_deal_count
        variables['season'] = season
        variables['last_ep_date'] = last_ep_date
        variables['epnumber'] = epnumber
        template = jinja_env.get_template('deals.html')
        self.response.write(template.render(variables))

class ScatterplotRedirect(Handler):
    def get(self):
        self.redirect('/deals', permanent=True)

class Categories(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        cursor.execute('SELECT CatID, name FROM categories ORDER BY name ASC')
        results = cursor.fetchall()
        cat_dict = {}
        for row in results:
            cat_dict[row[0]] = row[1]

        companies = {}
        for k, v in cat_dict.iteritems():
            cursor.execute('SELECT COUNT(companies.COID) FROM companies INNER JOIN categories ON companies.category=categories.name WHERE categories.CatID=%s ORDER BY companies.name ASC LIMIT 3', [k])
            (count,) = cursor.fetchone()
            if count==0:
                logging.warning('Category %s has no companies in it', v)
            elif count>=1:
                cursor.execute('SELECT companies.COID, companies.name FROM companies INNER JOIN categories ON companies.category=categories.name WHERE categories.CatID=%s ORDER BY companies.name ASC LIMIT 3', [k])
                results = cursor.fetchall()
                co_list = []
                for row in results:
                    COID, name = row[0], row[1]
                    co_list.append(row[1])
                #company1 at pos0, company2 at pos1, company3 at pos 2
                companies[k] = co_list
            else:
                logging.error('something unexpected happened when querying for companies in the category %s', v)

        cat_dict = OrderedDict(cat_dict)
        ord_cat_dict = OrderedDict(sorted(cat_dict.items(), key=lambda t: t[1]))
        companies = OrderedDict(companies)
        ord_companies = OrderedDict(sorted(companies.items(), key=lambda t: t[1]))

        variables = {'cat_dict': ord_cat_dict, 'ord_companies': ord_companies}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        template = jinja_env.get_template('categories.html')
        self.response.write(template.render(variables))
        db.close()

class CategoryPage(Handler):
    def get(self, CatID):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        company_dict = {}

        cursor = db.cursor()
        cursor.execute('SELECT name FROM categories WHERE CatID=%s', [CatID])
        result = cursor.fetchone()
        if result is None:
            db.close()
            self.redirect('/categories', permanent=True)
        elif result is not None:
            (name,) = result
            variables['category'] = name

            cursor.execute('SELECT COID, name FROM companies WHERE category=%s', [name])
            results = cursor.fetchall()
            for row in results:
                COID = row[0]
                name = row[1]
                company_dict[COID] = name
            
            descriptions = {}
            for k, v in company_dict.iteritems():
                cursor.execute('SELECT description FROM companies WHERE COID=%s', [k])
                (description,) = cursor.fetchone()
                descriptions[k] = description

            company_dict = OrderedDict(company_dict)
            companies = OrderedDict(sorted(company_dict.items(), key=lambda t: t[1]))

            variables['companies'] = companies
            variables['descriptions'] = descriptions
            template = jinja_env.get_template('category.html')
            self.response.write(template.render(variables))
            db.close()
        else:
            logging.error('something unexpected happened')
            self.redirect('/categories')

class InvestorPage(Handler):
    def get(self, SID):
        if not self.verifyUA():
            self.error(404)
            return
        if not self.verifyIP():
            self.redirect('/purchase')
            return

        if SID in shark_dict:
            shark_name = shark_dict[SID]
            variables = {'name': shark_name}
            variables['SID'] = SID
            variables['Google_Analytics_ID'] = Google_Analytics_ID
        else:
            return

        # find number of episode appearances
        db = self.connectToDB()
        cursor = db.cursor()
        query = 'SELECT COUNT(EPID) FROM episodes WHERE %s=1' % SID
        cursor.execute(query)
        (appearances,)=cursor.fetchone()
        variables['appearances'] = appearances

        # find number of pitches heard
        query = 'SELECT COUNT(pitches.PID) FROM pitches INNER JOIN episodes ON episodes.EPID=pitches.EPID AND episodes.%s=1' % SID
        cursor.execute(query) # this is ok to do because we verified that the SID was valid at the top
        (pitches_heard,) = cursor.fetchone()
        variables['pitches_heard'] = pitches_heard
        
        # deal data
        # deal count
        query = 'SELECT COUNT(DID) FROM deals WHERE %s>0' % SID
        cursor.execute(query)
        (deal_count,) = cursor.fetchone()
        # deal dollars
        query = 'SELECT SUM(%s) FROM deals' % SID
        cursor.execute(query)
        (total_deal_dollars,) = cursor.fetchone()
        # group deal count
        query = 'SELECT COUNT(DID) FROM deals WHERE %s>0 AND %s<deal_usd' % (SID, SID)
        cursor.execute(query)
        (group_deal_count,) = cursor.fetchone()
        try:
            group_deal_pct = group_deal_count/float(deal_count)
        except:
            group_deal_pct = 0.0
        

        # deals with special terms
        query = "SELECT COUNT(DID) FROM deals WHERE %s>0 and other_terms!=''" % SID
        cursor.execute(query)
        (special_deal_count,) = cursor.fetchone()
        try:
            special_deal_pct = float(special_deal_count)/float(deal_count)
        except:
            special_deal_pct = 0.0

        # largest deal stats
        query = 'SELECT MAX(%s) FROM deals' % SID
        cursor.execute(query)
        (largest_deal_dollars,) = cursor.fetchone()
        query = 'SELECT COUNT(COID) from deals WHERE %s=%s' % (SID, largest_deal_dollars)
        cursor.execute(query)
        (how_many_deals_of_the_max_size,) = cursor.fetchone()
        if how_many_deals_of_the_max_size>1:
            logging.debug('there is more than one deal of this size, but the app will only display one.')
        elif how_many_deals_of_the_max_size==1:
            placeholder = 1 # preferable to just use the "continue" statement, but it doesn't work here
        else:
            logging.debug('there was a problem locating the max deal')

        query = 'SELECT COID, deal_pct, EPID, deal_usd, %s FROM deals WHERE %s=%%s' % (SID, SID)
        cursor.execute(query, [largest_deal_dollars]) # this is ok to do because we confirmed SID is valid at the top
        (COID,deal_pct,EPID,deal_usd,this_sharks_inv) = cursor.fetchone()
        largest_deal_pct = float(deal_pct) * float(this_sharks_inv)/float(deal_usd)
        variables['COID'] = COID
        
        # company data for the largest deal
        cursor.execute('SELECT name FROM companies WHERE COID=%s',[COID])
        row = cursor.fetchone()
        largest_deal_name = row[0]
        
        # list of deals, from in descending order by investment size
        query = 'SELECT DID, COID, EPID, deal_usd, deal_pct, %s FROM deals WHERE %s>0 ORDER BY %s DESC' % (SID, SID, SID)
        cursor.execute(query)
        deal_list = []
        results = cursor.fetchall()
        for row in results:
            DID = row[0]
            deal_usd = row[3] # refers to the total investment
            deal_dollars = row[5] # refers to the investment made by this particular shark
            deal_pct = row[5]/float(row[3]) * row[4] # this computes the pct attributable to this individual investor
            partners = [] # stays empty if there are no partners, but the variable needs to exist regardless
            if deal_dollars<deal_usd: # means this shark is not the sole investor
                shark_id_list = ['kharrington', 'jfoxworthy', 'rherjavec', 'koleary', 'djohn', 'bcorcoran', 'lgreiner', 'mcuban', 'jpdejoria', 'stisch', 'nwoodman']
                cursor.execute('SELECT kharrington, jfoxworthy, rherjavec, koleary, djohn, bcorcoran, lgreiner, mcuban, jpdejoria, stisch, nwoodman FROM deals WHERE DID=%s',[DID])
                all_sharks_tuple = cursor.fetchone()
                all_sharks = list(all_sharks_tuple) # now it's a list
                while len(all_sharks)>0:
                    if all_sharks[0]>0:
                        if shark_id_list[0]!=SID: # don't include yourself as a partner
                            name = shark_dict[shark_id_list[0]].split()
                            initials = ''.join(n[0].upper() for n in name)
                            this_partner = {'SID':shark_id_list[0], 'initials': initials}
                            partners.append(this_partner)
                    all_sharks.pop(0)
                    shark_id_list.pop(0)

            deal_dollars = "${:,}".format(deal_dollars)
            deal_pct = '{:.0%}'.format(deal_pct)
            deal_list.append(dict([
                ('COID',row[1]),
                ('name',row[1]), #placeholder
                ('deal_dollars',deal_dollars),
                ('deal_pct',deal_pct), 
                ('partners',partners)
                ]))

        # average deal valuation & avg_stake_taken
        total_deal_val = 0
        stake_taken_sum = 0
        query = 'SELECT DID, deal_usd, deal_pct, %s FROM deals WHERE %s>0' % (SID, SID)
        cursor.execute(query)
        for row in cursor.fetchall():
            this_deal_usd = row[1]
            this_deal_pct = row[2]
            this_deal_shark_inv = row[3]
            try:
                implied_valuation = this_deal_usd/this_deal_pct
            except:
                implied_valuation = 0
            total_deal_val += implied_valuation
            stake_taken_sum += this_deal_pct * this_deal_shark_inv/this_deal_usd
        try:
            avg_deal_val = total_deal_val/deal_count
        except:
            avg_deal_val = 0
        try:
            avg_stake_taken = stake_taken_sum/deal_count
        except:
            avg_stake_taken = 0

        # medians
        if deal_count%2==1:
            # median_inv_size
            limit = deal_count/2 # python's integer division floors. but the limit count starts from zero. this will effectively give us the number in the middle.
            query = 'SELECT %s FROM deals WHERE %s>0 ORDER BY %s ASC LIMIT %s, 1' % (SID, SID, SID, limit)
            cursor.execute(query)
            (median_inv_size,) = cursor.fetchone()
            # median_stake
            query = 'SELECT stake FROM (SELECT deal_pct*%s/deal_usd As stake FROM deals WHERE %s>0) StakeTable ORDER BY stake ASC LIMIT %s, 1' % (SID, SID, limit)
            cursor.execute(query)
            (median_stake,) = cursor.fetchone()
        elif deal_count%2==0:
            # median_inv_size
            start = deal_count/2-1
            query = 'SELECT %s FROM deals WHERE %s>0 ORDER BY %s ASC LIMIT %s, 2' % (SID, SID, SID, start)
            cursor.execute(query)
            (low,) = cursor.fetchone()
            (high,) = cursor.fetchone()
            median_inv_size = ( float(low) + float(high) ) / 2
            # median_stake
            query = 'SELECT stake FROM (SELECT deal_pct*%s/deal_usd As stake FROM deals WHERE %s>0) StakeTable ORDER BY stake ASC LIMIT %s, 2' % (SID, SID, start)
            cursor.execute(query)
            (low,) = cursor.fetchone()
            (high,) = cursor.fetchone()
            median_stake = ( float(low) + float(high) ) / 2
        else:
            print 'something went wrong with the deal_count%2 evaluation'

        # median valuation
        query = 'SELECT COUNT(DID) FROM deals WHERE %s>0 AND deal_pct>0' % (SID)
        cursor.execute(query)
        (straight_deal_count,) = cursor.fetchone() # amount of deals where we can do a simple $inv/%stake calculation for valuation
        if straight_deal_count%2==1:
            straight_limit = straight_deal_count/2
            query = 'SELECT val FROM (SELECT deal_usd/deal_pct As val FROM deals WHERE %s>0 AND deal_pct>0) ValTable Order BY val ASC LIMIT %s, 1' % (SID, straight_limit)
            cursor.execute(query)
            (median_deal_val,) = cursor.fetchone()
            # now for the discount
            query = 'SELECT ask_val FROM (SELECT pitches.PID, pitches.ask_usd/pitches.ask_pct As ask_val FROM pitches INNER JOIN deals on pitches.PID=deals.DID WHERE deals.%s>0 AND deals.deal_pct>0) ValTable ORDER BY ask_val ASC LIMIT %s, 1' % (SID, straight_limit)
            cursor.execute(query)
            try:
                (median_ask_val,) = cursor.fetchone()
                median_discount = (median_deal_val/median_ask_val - 1) * (-1)
                median_discount = '{:.0%}'.format(median_discount)
                median_ask_val = "${:,}".format(int(round(median_ask_val,0)))
            except:
                median_ask_val = '(n/a)'
                median_discount = '(not available)'
        elif straight_deal_count%2==0:
            start = straight_deal_count/2-1
            query = 'SELECT val FROM (SELECT deal_usd/deal_pct As val FROM deals WHERE %s>0 AND deal_pct>0) ValTable Order BY val ASC LIMIT %s, 2' % (SID, start)
            cursor.execute(query)
            (low,) = cursor.fetchone()
            (high,) = cursor.fetchone()
            median_deal_val = ( float(low) + float(high) ) / 2
            # now for the discount
            query = 'SELECT ask_val FROM (SELECT pitches.PID, pitches.ask_usd/pitches.ask_pct As ask_val FROM pitches INNER JOIN deals on pitches.PID=deals.DID WHERE deals.%s>0 AND deals.deal_pct>0) ValTable ORDER BY ask_val ASC LIMIT %s, 2' % (SID, start)
            cursor.execute(query)
            (low,) = cursor.fetchone()
            (high,) = cursor.fetchone()
            try:
                median_ask_val = ( float(low) + float(high) ) / 2
                median_discount = (median_deal_val/median_ask_val - 1) * (-1)
                median_discount = '{:.0%}'.format(median_discount)
                median_ask_val = "${:,}".format(int(round(median_ask_val,0)))
            except:
                median_ask_val = '(n/a)'
                median_discount = '(not available)'
        else:
            print 'something went wrong with the straight_deal_count%2 evaluation'

        # find this shark's group deal partners
        if group_deal_count>0:
            group_deal_partners = []
            for k, v in shark_dict.iteritems():
                query = 'SELECT COUNT(%s) FROM deals WHERE %s>0 AND %s>0 AND %s<deal_usd' % (k, k, SID, SID)
                cursor.execute(query)
                (this_sharks_group_deal_count,) = cursor.fetchone()
                group_deal_partners.append((k, this_sharks_group_deal_count))
            group_deal_partners_dict = OrderedDict(group_deal_partners)
            ord_group_deal_partners = OrderedDict(sorted(group_deal_partners_dict.items(), key=lambda t: t[1]))
            pop_the_shark = ord_group_deal_partners.popitem() # because every shark will partner with his or herself 100% of the time
            best_partner_id, best_partner_deal_count = ord_group_deal_partners.popitem() # the second shark in the list is the one with the most collaborations
            best_partners_list = []
            best_partners_list.append([best_partner_id, shark_dict[best_partner_id], best_partner_deal_count])
            loop = True
            while loop:
                if len(ord_group_deal_partners)>0:
                    next_partner_id, next_partner_deal_count = ord_group_deal_partners.popitem()
                    if next_partner_deal_count==best_partner_deal_count:
                        best_partners_list.append([next_partner_id, shark_dict[next_partner_id],next_partner_deal_count])
                    else:
                        loop = False
                else:
                    loop = False
            variables['best_partner_text'] = ', most frequently with'
            variables['best_partners_list'] = best_partners_list
        else:
            variables['best_partner_text'] = ''
            variables['best_partners_list'] = []

        # getting the names for deal_list here
        for d in deal_list:
            cursor.execute('SELECT name FROM companies WHERE COID=%s',[d['COID']])
            row = cursor.fetchone()
            d['name'] = row[0]

        # additional computed stats
        deals_over_pitches = deal_count/float(pitches_heard)
        try:
            avg_inv_size = float(total_deal_dollars)/float(deal_count)
        except:
            avg_inv_size = 0.0

        # books
        books = []
        query = 'SELECT title, link FROM books WHERE author="%s"' % (SID)
        cursor.execute(query)
        results = cursor.fetchall()
        for r in results:
            title = r[0]
            book_link = r[1]
            books.append(dict([
                ('title',title), 
                ('book_link',book_link)
                ]))

        # formatting and adding to variables list
        deals_over_pitches = '{:.0%}'.format(deals_over_pitches)
        variables['deals_over_pitches'] = deals_over_pitches

        avg_inv_size = "${:,}".format(int(round(avg_inv_size,0)))
        variables['avg_inv_size'] = avg_inv_size

        median_inv_size = "${:,}".format(int(round(median_inv_size,0)))
        variables['median_inv_size'] = median_inv_size

        deal_count = "{:,}".format(deal_count)
        variables['deal_count'] = deal_count

        total_deal_dollars = "${:,}".format(int(total_deal_dollars))
        variables['total_deal_dollars'] = total_deal_dollars

        group_deal_count = "{:,}".format(group_deal_count)
        variables['group_deal_count'] = group_deal_count

        group_deal_pct = '{:.0%}'.format(group_deal_pct)
        variables['group_deal_pct'] = group_deal_pct

        special_deal_count = "{:,}".format(special_deal_count)
        variables['special_deal_count'] = special_deal_count

        special_deal_pct = '{:.0%}'.format(special_deal_pct)
        variables['special_deal_pct'] = special_deal_pct

        largest_deal_dollars = "${:,}".format(largest_deal_dollars)
        variables['largest_deal_dollars'] = largest_deal_dollars
        
        largest_deal_pct = '{:.0%}'.format(largest_deal_pct)
        variables['largest_deal_pct'] = largest_deal_pct

        avg_deal_val = "${:,}".format(int(round(avg_deal_val)))
        variables['avg_deal_val'] = avg_deal_val

        median_deal_val = "${:,}".format(int(round(median_deal_val,0)))
        variables['median_deal_val'] = median_deal_val

        # already formatted
        variables['median_ask_val'] = median_ask_val

        avg_stake_taken = '{:.0%}'.format(avg_stake_taken)
        variables['avg_stake_taken'] = avg_stake_taken
        
        median_stake = '{:.0%}'.format(median_stake)
        variables['median_stake'] = median_stake

        variables['median_discount'] = median_discount
        
        season = int(EPID)/100
        variables['season'] = season
        variables['epnumber'] = int(EPID) - (season * 100)
        variables['EPID'] = EPID
        variables['largest_deal_name'] = largest_deal_name
        variables['deal_list'] = deal_list
        variables['books'] = books
        template = jinja_env.get_template('investor.html')
        self.response.write(template.render(variables))
        db.close()

class EpisodePage(Handler):
    def get(self, EPID):
        if not self.verifyUA():
            self.error(404)
            return
        if not self.verifyIP():
            self.redirect('/purchase')
            return

        db = self.connectToDB()
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        cursor = db.cursor()

        # get the participating sharks
        cursor.execute('SELECT airdate, kharrington, jfoxworthy, rherjavec, koleary, djohn, bcorcoran, lgreiner, mcuban, jpdejoria, stisch, nwoodman FROM episodes WHERE EPID=%s', [EPID])
        row = cursor.fetchone()
        in_ep_dict = {}
        in_ep_dict['kharrington'] = row[1]
        in_ep_dict['jfoxworthy'] = row[2]
        in_ep_dict['rherjavec'] = row[3]
        in_ep_dict['koleary'] = row[4]
        in_ep_dict['djohn'] = row[5]
        in_ep_dict['bcorcoran'] = row[6]
        in_ep_dict['lgreiner'] = row[7]
        in_ep_dict['mcuban'] = row[8]
        in_ep_dict['jpdejoria'] = row[9]
        in_ep_dict['stisch'] = row[10]
        in_ep_dict['nwoodman'] = row[11]
        sharks_in_ep = {}
        for k, v in in_ep_dict.iteritems():
            if in_ep_dict[k]>0:
                sharks_in_ep[k] = shark_dict[k]
        variables['sharks_in_ep'] = sharks_in_ep

        # initials
        initials = {}
        for SID, name in sharks_in_ep.iteritems():
            first, last = name.split(' ', 1)
            these_initials = first[0]+last[0]
            initials[SID] = these_initials
        variables['initials'] = initials

        # deal count
        cursor.execute('SELECT COUNT(DID) FROM deals WHERE EPID=%s',[EPID])
        (deal_count,) = cursor.fetchone()
        variables['deal_count'] = deal_count

        # get the companies pitching
        company_dict = {}
        cursor.execute('SELECT COID FROM pitches WHERE EPID=%s', [EPID])
        results = cursor.fetchall()
        for row in results:
            COID = row[0]
            cursor.execute('SELECT name FROM companies WHERE COID=%s', [COID])
            (name,) = cursor.fetchone()
            company_dict[COID] = name
        variables['company_dict'] = company_dict

        # deal dict
        deal_dict = {}
        cursor.execute('SELECT COID FROM deals WHERE EPID=%s', [EPID])
        results = cursor.fetchall()
        for row in results:
            COID = row[0]
            cursor.execute('SELECT name FROM companies WHERE COID=%s', [COID])
            (name,) = cursor.fetchone()
            deal_dict[COID] = name
        variables['deal_dict'] = deal_dict

        # get the total dollars invested
        cursor.execute('SELECT SUM(deal_usd) from deals WHERE EPID=%s', [EPID])
        (total_deal_dollars,) = cursor.fetchone()
        if (total_deal_dollars is None) or (total_deal_dollars==''):
            variables['total_deal_dollars'] = 0
        else:
            variables['total_deal_dollars'] = "${:,}".format(total_deal_dollars)

        season = int(float(EPID)/100)
        variables['season'] = season
        variables['epnumber'] = int(EPID) - season*100

        template = jinja_env.get_template('episode.html')
        self.response.write(template.render(variables))
        db.close()

class SeasonPage(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        cursor.execute('SELECT airdate, season, epnumber FROM episodes')

        episodelist = [];
        for row in cursor.fetchall():
          episodelist.append(dict([('airdate',row[0]),
                                 ('season',row[1]),
                                 ('epnumber',row[2])
                                 ]))

        variables = {'episodelist': episodelist}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        template = jinja_env.get_template('episodes.html')
        self.response.write(template.render(variables))
        db.close()

class SignUpPage(Handler):
    def get(self, submit=0):
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        check_submit = self.request.get('submit')
        if check_submit=='1':
            variables['submit'] = 1
        else:
            variables['submit'] = 0
        template = jinja_env.get_template('signup.html')
        self.response.write(template.render(variables))

class SubmitUserEmail(Handler):
    def post(self):
        email = self.request.get('email')
        logging.debug(email)
        db = self.connectToDB()
        cursor = db.cursor()
        cursor.execute('INSERT INTO signuplist (email) VALUES (%s)', [email])
        db.commit()
        db.close()

class PurchasePage(Handler):
    def get(self, submit=0):
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        check_submit = self.request.get('submit')
        if check_submit=='1':
            variables['submit'] = 1
        else:
            variables['submit'] = 0
        template = jinja_env.get_template('purchase.html')
        self.response.write(template.render(variables))

class Visualizations(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID

        template = jinja_env.get_template('visualizations.html')
        self.response.write(template.render(variables))

class HeatmapPage(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID

        group_deal_count_rankings = {}
        for SID, name in shark_dict.iteritems():
            query = 'SELECT COUNT(DID) FROM deals WHERE %s>0 AND %s<deal_usd' % (SID, SID)
            cursor.execute(query)
            (group_deal_count,) = cursor.fetchone()
            if group_deal_count>1:
                group_deal_count_rankings[SID] = group_deal_count
        
        new_shark_dict = OrderedDict(group_deal_count_rankings)
        ordered_shark_dict = OrderedDict(sorted(new_shark_dict.items(), key=lambda t: t[1], reverse=True))
        shark_list = []
        SID_list = []
        for SID, count in ordered_shark_dict.iteritems():
            SID_list.append(SID)
            shark_list.append(shark_dict[SID])

        variables['SID_list'] = SID_list
        variables['shark_list'] = shark_list

        cursor.execute('SELECT season, epnumber, airdate FROM episodes ORDER BY EPID DESC LIMIT 0, 1')
        (season, epnumber, airdate) = cursor.fetchone()

        last_ep_date = datetime.datetime.strftime(airdate, '%B %d, %Y')

        variables['season'] = season
        variables['last_ep_date'] = last_ep_date
        variables['epnumber'] = epnumber

        template = jinja_env.get_template('heatmap.html')
        self.response.write(template.render(variables))

class PairsDeals(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        SID1 = self.request.get('shark1')
        SID2 = self.request.get('shark2')
        if SID1=='' or SID2=='':
            print 'SID1 or SID2 is an empty string'
            return

        db = self.connectToDB()
        cursor = db.cursor()

        deals_dict = {}
        variables = {}

        query = 'SELECT COID, deal_usd, deal_pct FROM deals WHERE %s>0 AND %s>0' % (SID1, SID2)
        cursor.execute(query)
        results = cursor.fetchall()
        for row in results:
            COID = row[0]
            deal_usd = row[1]
            deal_pct = row[2]

            cursor.execute('SELECT name FROM companies WHERE COID=%s', [COID])
            (co_name,) = cursor.fetchone()
            deal_usd = "${:,}".format(deal_usd)
            deal_pct = '{:.0%}'.format(deal_pct)

            deal_properties = {'co_name': co_name, 'deal_usd': deal_usd, 'deal_pct': deal_pct}
            deals_dict[COID] = deal_properties

        variables['SID1'] = SID1
        variables['SID2'] = SID2
        variables['shark1name'] = shark_dict[SID1]
        variables['shark2name'] = shark_dict[SID2]
        variables['deals'] = deals_dict
        
        json_output = json.dumps(variables)
        db.close()
        self.response.write(json_output)

class Treemap(Handler):
    def get(self):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()
        variables = {}
        variables['Google_Analytics_ID'] = Google_Analytics_ID
        
        cursor.execute('SELECT season, epnumber, airdate FROM episodes ORDER BY EPID DESC LIMIT 0, 1')
        (season, epnumber, airdate) = cursor.fetchone()

        last_ep_date = datetime.datetime.strftime(airdate, '%B %d, %Y')

        variables['season'] = season
        variables['last_ep_date'] = last_ep_date
        variables['epnumber'] = epnumber

        template = jinja_env.get_template('treemap.html')
        self.response.write(template.render(variables))

class ChartData(Handler):
    def get(self, chart_id):
        if not self.verifyUA():
            self.error(404)
            return

        db = self.connectToDB()
        cursor = db.cursor()

        if chart_id=='treemap':
            data = {'name': 'treemap', 'children': []}

            for SID, name in shark_dict.iteritems():
                shark_link = '/investor/'+SID
                deals = []
                query = 'SELECT COUNT(DID) FROM deals WHERE %s>0' % (SID)
                cursor.execute(query)
                (count,) = cursor.fetchone()
                if count<=2:
                    continue
                query = 'SELECT COID, funded, %s FROM deals WHERE %s>0' % (SID, SID)
                cursor.execute(query)
                results = cursor.fetchall()
                
                for r in results:
                    COID = r[0]
                    funded = r[1]
                    dollars = r[2]
                    cursor.execute('SELECT name, status FROM companies WHERE COID=%s', [COID])
                    (co_name,status) = cursor.fetchone()
                    co_link = '/company/'+COID
                    investment = {'name': co_name, 'COID': COID, 'funded': funded, 'status':status, 'value': dollars}
                    deals.append(investment)
                
                this_shark = {'name': name, 'SID': SID, 'children': deals}
                data['children'].append(this_shark)

            json_output = json.dumps(data)
            self.response.write(json_output)


        if chart_id=='bubble':
            data = {'name': 'bubble_chart', 'children':[]}

            # get latest list of seasons
            cursor.execute('SELECT season FROM episodes GROUP BY season ORDER BY season ASC')
            results = cursor.fetchall()
            seasons = []
            for r in results:
                seasons.append(r[0])

            for s in seasons:
                name = 'season '+str(s)
                children = []
                EPID_min = str(s * 100)
                EPID_max = str( (s+1) * 100) 
                cursor.execute('SELECT companies.name, deals.deal_usd, companies.COID FROM companies INNER JOIN deals ON companies.COID=deals.COID WHERE deals.EPID>%s AND deals.EPID<%s ORDER BY deals.EPID ASC', [EPID_min, EPID_max])
                results = cursor.fetchall()
                for r in results:
                    co_name = r[0]
                    co_usd = r[1]
                    COID = r[2]
                    company = {'name': co_name, 'size': co_usd, 'COID': COID}
                    children.append(company)
                season = {'name': name, 'children': children}
                data['children'].append(season)

            json_output = json.dumps(data)
            self.response.write(json_output)


        if chart_id=='heatmap':
            heatmap_data = {}
            group_deal_count_rankings = {}
            self.response.write('shark1\tshark2\tvalue\tshark1_index\tshark2_index\tshark1_name\n')

            for SID, shark_name in shark_dict.iteritems():
                # first, establish if this shark even has any group deals
                query = 'SELECT COUNT(DID) FROM deals WHERE %s>0 AND %s<deal_usd' % (SID, SID)
                cursor.execute(query)
                (group_deal_count,) = cursor.fetchone()
                group_deal_partners = {}
                if group_deal_count>1:
                    group_deal_count_rankings[SID] = group_deal_count
                if group_deal_count>0:
                    for partner_SID, partner_name in shark_dict.iteritems():
                        if partner_SID==SID:
                            group_deal_count_with_this_partner = -5
                        else:
                            query = 'SELECT COUNT(%s) FROM deals WHERE %s>0 AND %s>0 AND %s<deal_usd' % (partner_SID, partner_SID, SID, SID)
                            cursor.execute(query)
                            (group_deal_count_with_this_partner,) = cursor.fetchone()
                        group_deal_partners[partner_SID] = group_deal_count_with_this_partner
                else:
                    continue
                heatmap_data[SID] = group_deal_partners

            shark1_index = 1
            new_shark_dict = OrderedDict(group_deal_count_rankings)
            ordered_shark_dict = OrderedDict(sorted(new_shark_dict.items(), key=lambda t: t[1], reverse=True))
            for shark1, popularity in ordered_shark_dict.iteritems():
                shark2_index = 1
                group_deal_data = heatmap_data[shark1]
                for shark2, popularity2 in ordered_shark_dict.iteritems():
                    self.response.write(shark1+'\t'+shark2+'\t'+str(group_deal_data[shark2])+'\t'+str(shark1_index)+'\t'+str(shark2_index)+'\t'+shark_dict[shark1]+'\n')
                    shark2_index+=1
                shark1_index+=1

        if chart_id=='total_investments_by_shark':
            shark_total_invested = {}
            for SID, name in shark_dict.iteritems():
                query = 'SELECT SUM(%s) FROM deals' % (SID)
                cursor.execute(query)
                (total_invested,) = cursor.fetchone()
                shark_total_invested[SID] = int(total_invested)
            ordered = OrderedDict(shark_total_invested)
            ordered_investments = OrderedDict(sorted(ordered.items(), key=lambda t: t[1], reverse=True))

            self.response.write('name\tvalue\n')
            for SID, total in ordered_investments.iteritems():
                self.response.write(shark_dict[SID]+'\t')
                self.response.write(str(total)+'\n')

        if chart_id=='scatterplot':
            self.response.write('Company,Asking,Deal,Special,COID\n')
            cursor.execute('SELECT pitches.ask_usd/pitches.ask_pct As ask_val, deals.deal_usd/deals.deal_pct As deal_val, deals.other_terms, deals.COID FROM deals INNER JOIN pitches ON deals.DID=pitches.PID WHERE deals.deal_pct>0')
            results = cursor.fetchall()
            for row in results:
                ask_val = int(round(row[0],0))
                deal_val = int(round(row[1],0))
                other_terms = row[2]
                if other_terms=='':
                    special='standard deal'
                else:
                    special = 'special terms'
                COID = row[3]
                cursor.execute('SELECT name FROM companies WHERE COID=%s', [COID])
                (name,) = cursor.fetchone()
                self.response.write(name+','+str(ask_val)+','+str(deal_val)+','+str(special)+','+COID+'\n')

        if chart_id=='scatterplot_under_4mm':
            self.response.write('Company,Asking,Deal,Special,COID\n')
            cursor.execute('SELECT pitches.ask_usd/pitches.ask_pct As ask_val, deals.deal_usd/deals.deal_pct As deal_val, deals.other_terms, deals.COID FROM deals INNER JOIN pitches ON deals.DID=pitches.PID WHERE deals.deal_pct>0')
            results = cursor.fetchall()
            for row in results:
                ask_val = int(round(row[0],0))
                deal_val = int(round(row[1],0))
                if ask_val>4000000:
                    continue
                other_terms = row[2]
                if other_terms=='':
                    special='standard deal'
                else:
                    special = 'special terms'
                COID = row[3]
                cursor.execute('SELECT name FROM companies WHERE COID=%s', [COID])
                (name,) = cursor.fetchone()
                self.response.write(name+','+str(ask_val)+','+str(deal_val)+','+str(special)+','+COID+'\n')

        if chart_id=='scatterplot_sharks':
            self.response.write('Company,Asking,Deal,Investor\n')
            cursor.execute('SELECT pitches.ask_usd/pitches.ask_pct As ask_val, deals.deal_usd/deals.deal_pct As deal_val, deals.COID, deals.DID FROM deals INNER JOIN pitches ON deals.DID=pitches.PID WHERE deals.deal_pct>0')
            results = cursor.fetchall()
            for row in results:
                ask_val = int(round(row[0],0))
                deal_val = int(round(row[1],0))
                if ask_val>4000000 or deal_val>4000000:
                    continue
                COID = row[2]
                DID = row[3]
                cursor.execute('SELECT name FROM companies WHERE COID=%s', [COID])
                (name,) = cursor.fetchone()
                investor = ''
                print 'investor is blank, see? ', investor
                for SID, shark_name in shark_dict.iteritems():
                    if investor!='multiple':
                        query = 'SELECT %s FROM deals WHERE DID="%s"' % (SID,DID)
                        print 'here is the query: ', query
                        cursor.execute(query)
                        (investment,) = cursor.fetchone()
                        print 'investment: ', investment
                        if investment!=0:
                            print 'investment is not 0'
                            if investor=='':
                                print 'and investor is empty'
                                investor=shark_name
                                print 'investor is now ', investor
                            else:
                                print 'already had investor: ', investor
                                investor='multiple'
                                print 'therefore investor is now ', investor
                self.response.write(name+','+str(ask_val)+','+str(deal_val)+','+investor+'\n')


########## Utils ##########
shark_dict = {"kharrington": "Kevin Harrington", "jfoxworthy": "Jeff Foxworthy", "rherjavec": "Robert Herjavec", "koleary": "Kevin O'Leary", "djohn": "Daymond John", "bcorcoran": "Barbara Corcoran", "lgreiner": "Lori Greiner", "mcuban": "Mark Cuban", "jpdejoria": "John Paul DeJoria", "stisch": "Steve Tisch", "nwoodman": "Nick Woodman"}


########## webapp2 ##########
app = webapp2.WSGIApplication(
	[
		('/', MainPage),
        ('/about', AboutPage),
        ('/chartdata/(.*)', ChartData), 
        ('/mainpagedata', MainPageData),
        ('/episodes', Episodes),
        ('/episode/(.*)', EpisodePage),
        ('/companies', Companies), 
        ('/company', Companies),
        ('/companiespagedata', CompaniesPageData),
        ('/categories', Categories), 
        ('/category', Categories), 
        ('/category/(.*)', CategoryPage), 
        ('/company/(.*)', CompanyPage), 
        ('/deals', DealsPage),
        ('/heatmap', HeatmapPage), 
        ('/investor/(.*)', InvestorPage),
        ('/pairsdeals', PairsDeals), 
        ('/purchase', PurchasePage),
        ('/scatterplot', ScatterplotRedirect),
        ('/search', SearchPage),
        ('/searchresults', SearchResults),
        ('/season/(.*)', Episodes), 
        ('/sharks', Sharks),
        ('/signup', SignUpPage),
        ('/submitcompanyedit', SubmitCompanyEdit),
        ('/submituseremail', SubmitUserEmail), 
        ('/treemap', Treemap), 
        ('/visualizations', Visualizations),
        ('/admin/addepisode', AddEpisode),
        ('/admin/debugpage', DebugPage), 
        ('/admin/fixIDs', FixIDs), 
        ('/admin/importdata/companies', ImportDataCompanies),
        ('/admin/importdata/deals', ImportDataDeals),
        ('/admin/importdata/episodes', ImportDataEpisodes),
        ('/admin/importdata/pitches', ImportDataPitches),
        ('/admin/reviewedits', ReviewEditsPage),
        ('/admin/submitapprovededits', SubmitApprovedEditsPage),
        ('/admin/updatecategorylist', UpdateCategoryList)
	],
	debug=True)



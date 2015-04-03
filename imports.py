import csv 
import logging
import os

import jinja2
import MySQLdb
import urllib2
import StringIO
import webapp2

# Define your production Cloud SQL instance information.
_INSTANCE_NAME = 'sql-fortress:fortress-one'

class UpdateCategoryList(webapp2.RequestHandler):
    def update_cat_list(self):
        # connect to the database
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
        else:
            db = MySQLdb.connect(host='127.0.0.1', port=3306, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
            # Alternatively, connect to a Google Cloud SQL instance using:
            # db = MySQLdb.connect(host='ip-address-of-google-cloud-sql-instance', port=3306, db='guestbook', user='root')
        cursor = db.cursor()

        # now find the companies and their different categories
        cursor.execute('SELECT DISTINCT category FROM companies')
        results = cursor.fetchall()
        logging.debug(results)

        # Now add these categories to the categories table
        for row in results:
            name = row[0]
            CatID = name.replace(' ','-')
            CatID = CatID.lower()
            cursor.execute('''
                INSERT INTO 
                categories (
                    CatID, 
                    name
                    ) 
                VALUES (%s, %s)''', 
                (
                    CatID, 
                    name
                    )
            )
            db.commit()
        db.close()
    def get(self):
        self.update_cat_list()

class ImportDataEpisodes(webapp2.RequestHandler):
    def get_data(self):
        # get the csv file
        to_be_imported = urllib2.Request('http://shark-base.appspot.com/static/csv/seasons2-5episodes.csv')
        response = urllib2.urlopen(to_be_imported).read()
        raw_data = StringIO.StringIO(response)
        csv_data = csv.reader(raw_data)
        csv_data.next()
        rows = []
        # extract the data
        for row in csv_data:
            logging.debug(row)
            new_row = dict.fromkeys(['EPID', 'season', 'epnumber', 'title', 'airdate', 'kharrington', 'jfoxworthy', 'rherjavec', 'koleary', 'bcorcoran', 'djohn', 'mcuban', 'lgreiner', 'stisch', 'jpdejoria', 'nwoodman'])
            new_row['EPID'] = row[0]
            new_row['season'] = row[1]
            new_row['epnumber'] = row[2]
            new_row['title'] = row[3]
            new_row['airdate'] = row[4]
            new_row['kharrington'] = row[5]
            new_row['jfoxworthy'] = row[6]
            new_row['rherjavec'] = row[7]
            new_row['koleary'] = row[8]
            new_row['bcorcoran'] = row[9]
            new_row['djohn'] = row[10]
            new_row['mcuban'] = row[11]
            new_row['lgreiner'] = row[12]
            new_row['stisch'] = row[13]
            new_row['jpdejoria'] = row[14]
            new_row['nwoodman'] = row[15]
            rows.append(new_row)

        # now connect to the database
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
        else:
            db = MySQLdb.connect(host='127.0.0.1', port=3306, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
            # Alternatively, connect to a Google Cloud SQL instance using:
            # db = MySQLdb.connect(host='ip-address-of-google-cloud-sql-instance', port=3306, db='guestbook', user='root')
        cursor = db.cursor()
        # Now add the new row
        # Note that the only format string supported is %s
        for row in rows:
            cursor.execute('''
                INSERT INTO 
                episodes (
                    EPID, 
                    season, 
                    epnumber, 
                    title, 
                    airdate, 
                    kharrington, 
                    jfoxworthy, 
                    rherjavec, 
                    koleary, 
                    bcorcoran, 
                    djohn, 
                    mcuban, 
                    lgreiner, 
                    stisch, 
                    jpdejoria,
                    nwoodman
                    ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', 
                (
                    row['EPID'], 
                    row['season'], 
                    row['epnumber'], 
                    row['title'], 
                    row['airdate'], 
                    row['kharrington'], 
                    row['jfoxworthy'], 
                    row['rherjavec'], 
                    row['koleary'], 
                    row['bcorcoran'], 
                    row['djohn'], 
                    row['mcuban'], 
                    row['lgreiner'], 
                    row['stisch'], 
                    row['jpdejoria'],
                    row['nwoodman']
                    )
            )
            db.commit()
        db.close()
    def get(self):
        self.get_data()

class ImportDataCompanies(webapp2.RequestHandler):
    def get_data(self):
        # get the csv file
        to_be_imported = urllib2.Request('http://shark-base.appspot.com/static/csv/newamazon.csv')
        response = urllib2.urlopen(to_be_imported).read()
        raw_data = StringIO.StringIO(response)
        csv_data = csv.reader(raw_data)
        csv_data.next()
        rows = []
        # extract the data
        for row in csv_data:
            new_row = dict.fromkeys(['COID', 'amazon'])
            new_row['COID'] = row[0]
            new_row['amazon'] = row[1]
            rows.append(new_row)

        # now connect to the database
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
        else:
            db = MySQLdb.connect(host='127.0.0.1', port=3306, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
        cursor = db.cursor()
        for row in rows:
            enter_update = 0
            # first check to see if there is an existing amazon link
            cursor.execute('SELECT amazon FROM companies WHERE COID=%s', [row['COID']])
            (existing_amazon,) = cursor.fetchone()
            cursor.execute('''
                UPDATE companies
                SET amazon=%s 
                WHERE COID=%s
                ''', 
                (
                    row['amazon'], 
                    row['COID']
                    )
            )
            db.commit()
            logging.debug('%s amazon was %s and is now %s' %(row['COID'], existing_amazon, row['amazon']))
        db.close()
    def get(self):
        self.get_data()

class ImportDataPitches(webapp2.RequestHandler):
    def get_data(self):
        # get the csv file
        to_be_imported = urllib2.Request('http://shark-base.appspot.com/static/csv/season5pitches.csv')
        response = urllib2.urlopen(to_be_imported).read()
        raw_data = StringIO.StringIO(response)
        csv_data = csv.reader(raw_data)
        csv_data.next()
        rows = []
        # extract the data
        for row in csv_data:
            logging.debug(row)
            new_row = dict.fromkeys(['PID', 'COID', 'EPID', 'deal', 'ask_usd', 'ask_pct', 'special'])
            new_row['PID'] = row[0]
            new_row['COID'] = row[1]
            new_row['EPID'] = row[2]
            new_row['deal'] = row[3]
            new_row['ask_usd'] = row[4]
            new_row['ask_pct'] = row[5]
            new_row['special'] = row[6]
            rows.append(new_row)

        # now connect to the database
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
        else:
            db = MySQLdb.connect(host='127.0.0.1', port=3306, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
            # Alternatively, connect to a Google Cloud SQL instance using:
            # db = MySQLdb.connect(host='ip-address-of-google-cloud-sql-instance', port=3306, db='guestbook', user='root')
        cursor = db.cursor()
        # Now add the new row
        # Note that the only format string supported is %s
        for row in rows:
            cursor.execute('''
                INSERT INTO 
                pitches (
                    PID,
                    COID,
                    EPID, 
                    deal, 
                    ask_usd, 
                    ask_pct,
                    special
                    ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)''', 
                (
                    row['PID'], 
                    row['COID'], 
                    row['EPID'], 
                    row['deal'], 
                    row['ask_usd'], 
                    row['ask_pct'], 
                    row['special']
                    )
            )
            db.commit()
        db.close()
    def get(self):
        self.get_data()

class ImportDataDeals(webapp2.RequestHandler):
    def get_data(self):
        # get the csv file
        to_be_imported = urllib2.Request('http://shark-base.appspot.com/static/csv/season4-5deals.csv')
        response = urllib2.urlopen(to_be_imported).read()
        raw_data = StringIO.StringIO(response)
        csv_data = csv.reader(raw_data)
        csv_data.next()
        rows = []
        # extract the data
        for row in csv_data:
            logging.debug(row)
            new_row = dict.fromkeys(['DID', 'COID', 'EPID', 'deal_pct', 'deal_usd', 'bcorcoran', 'djohn', 'koleary', 'rherjavec', 'kharrington', 'lgreiner', 'mcuban', 'jpdejoria', 'stisch', 'jfoxworthy', 'nwoodman', 'other_terms', 'admin_notes', 'source1', 'source2', 'source3'])
            new_row['DID'] = row[0]
            new_row['COID'] = row[1]
            new_row['EPID'] = row[2]
            new_row['deal_pct'] = row[3]
            new_row['deal_usd'] = row[4]
            new_row['bcorcoran'] = row[5]
            new_row['djohn'] = row[6]
            new_row['koleary'] = row[7]
            new_row['rherjavec'] = row[8]
            new_row['kharrington'] = row[9]
            new_row['lgreiner'] = row[10]
            new_row['mcuban'] = row[11]
            new_row['jpdejoria'] = row[12]
            new_row['stisch'] = row[13]
            new_row['jfoxworthy'] = row[14]
            new_row['nwoodman'] = row[15]
            new_row['other_terms'] = row[16]
            new_row['admin_notes'] = row[17]
            new_row['source1'] = row[18]
            new_row['source2'] = row[19]
            new_row['source3'] = row[20]
            rows.append(new_row)

        # now connect to the database
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
        else:
            db = MySQLdb.connect(host='127.0.0.1', port=3306, db='sharkbase', user='sharkbaseapp', passwd='perpetuity')
            # Alternatively, connect to a Google Cloud SQL instance using:
            # db = MySQLdb.connect(host='ip-address-of-google-cloud-sql-instance', port=3306, db='guestbook', user='root')
        cursor = db.cursor()
        # Now add the new row
        # Note that the only format string supported is %s
        for row in rows:
            cursor.execute('''
                INSERT INTO 
                deals (
                    DID,
                    COID,
                    EPID, 
                    deal_pct, 
                    deal_usd, 
                    bcorcoran, 
                    djohn, 
                    koleary, 
                    rherjavec,
                    kharrington, 
                    lgreiner,
                    mcuban, 
                    jpdejoria, 
                    stisch, 
                    jfoxworthy,
                    nwoodman,
                    other_terms, 
                    admin_notes, 
                    source1,
                    source2,
                    source3
                    ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', 
                (
                    row['DID'], 
                    row['COID'], 
                    row['EPID'], 
                    row['deal_pct'], 
                    row['deal_usd'], 
                    row['bcorcoran'], 
                    row['djohn'], 
                    row['koleary'], 
                    row['rherjavec'],
                    row['kharrington'], 
                    row['lgreiner'],
                    row['mcuban'],
                    row['jpdejoria'], 
                    row['stisch'], 
                    row['jfoxworthy'], 
                    row['nwoodman'],
                    row['other_terms'],
                    row['admin_notes'], 
                    row['source1'],
                    row['source2'],
                    row['source3']
                    )
            )
            db.commit()
        db.close()
    def get(self):
        self.get_data()
from extract_cookie_ids import extract_persistent_ids_from_dbs, extract_common_id_cookies
import cPickle
import os

def extract_id_cookies(db1, db2):
    """ 
    Compares two databases and returns the id cookie domain, name
    pairs as a dict
    """
    print "Pulling cookies from db1"
    cookies_db1 = extract_persistent_ids_from_dbs([db1], num_days = 90)
    print "Pulling cookies from db2"
    cookies_db2 = extract_persistent_ids_from_dbs([db2], num_days = 90)
    print "Extracting common ids"
    id_cookies = extract_common_id_cookies([cookies_db1, cookies_db2])
    return id_cookies

if __name__=='__main__':
    db1 = '../data/surveil_id_detection_roman.sqlite'
    db2 = '../data/surveil_id_detection_triton.sqlite'
    id_cookies = extract_id_cookies(db1, db2)
    cPickle.dump(id_cookies, open(os.path.join(os.path.dirname(__file__),'../data/id_cookies.p'),'wb'))

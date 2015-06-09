import os
import sys

def get_leaking_stats() :
    f = open('../data/identity_leaks.txt', 'r')

    site_list = []
    line_count = 0
    clear_leak_ctr = 0
    clear_email_ctr = 0
    clear_username_ctr = 0
    clear_fullname_ctr = 0
    clear_firstname_ctr = 0
    clear_email_uname_ctr = 0
    https_login_ctr = 0
    https_default_ctr = 0
    for line in f.readlines() :
        if line_count == 0 :
            line_count += 1
            continue
        line_count += 1

        data = line.split()
        if len(data) < 7 :
            line_count -= 1
            continue
        if (data[6] == '1' or data[5] == '1') and data[2] == '0' :
            clear_email_uname_ctr += 1

        if (data[3] == '1' or data[4] == '1' or data[5] == '1' or data[6] == '1' ) and data[2] == '0':
            clear_leak_ctr += 1
            site_list.append(data[0])
        if data[3] == '1' and data[2] == '0':
            clear_firstname_ctr += 1
        if data[4] == '1' and data[2] == '0':
            clear_fullname_ctr += 1
        if data[5] == '1' and data[2] == '0':
            clear_username_ctr += 1
        if data[6] == '1' and data[2] == '0':
            clear_email_ctr += 1
        if data[1] == '1' :
            https_login_ctr += 1
        if data[2] == '1' :
            https_default_ctr += 1
    print "Num sites " + str(line_count - 1)
    print "Leaking anything " + str(clear_leak_ctr)
    print "Leaking username or email " + str(clear_email_uname_ctr)
    print "Leaking first name " + str(clear_firstname_ctr)
    print "Leaking full name " + str(clear_fullname_ctr)
    print "Leaking username " + str(clear_username_ctr)
    print "Leaking email " + str(clear_email_ctr)
    print "With HTTPS Login " + str(https_login_ctr)
    print "With HTTPS default " + str(https_default_ctr)
    f.close()

def get_leaking_sites():
    f = open('../data/identity_leaks.txt', 'r')
    site_set = set()
    first_line = True
    for line in f.readlines() :
        if first_line:
            first_line = False
            continue

        data = line.split()
        if (data[3] == '1' or data[4] == '1' or data[5] == '1' or data[6] == '1' ) and data[2] == '0':
            site_set.add('http://'+data[0]+'/')
    f.close()
    return site_set

if __name__ == "__main__" :
    get_leaking_stats()

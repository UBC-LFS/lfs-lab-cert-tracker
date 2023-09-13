import re
from app.functions import *


def remove_special_chars(s):
    return re.findall(r'\b(?:[A-Za-z]\w*|\d+)\b', s.strip().lower())

def find_cert(certs, training_name):
    training_name = training_name.replace('Online', '')
    training_name = training_name.replace('Self Paced', '')
    training_name = training_name.replace('no longer required', '')
    
    d1 = {}
    l1 = remove_special_chars(training_name)
    for word in l1:
        if word in ['and','for','of','in','or','to','by']:
            continue
        if word in d1.keys(): d1[word] += 1
        else: d1[word] = 1
    
    best = None
    max_count = 0
    for cert in certs:
        d2 = {}
        l2 = remove_special_chars(cert.name)
        for word in l2:
            if word in ['and','for','of','in','or','to','by']:
                continue
            if word in d2.keys(): d2[word] += 1
            else: d2[word] = 1   
        
        count = 0
        for k, v in d1.items():
            if k in d2.keys() and d2[k] == v:
                count += 1
        if count > max_count:
            best = cert
            max_count = count
        
    return best if max_count / len(d1.keys()) > 0.70 else None


def find_cert2(certs, training_name):
    #training_name = training_name.replace('Online', '')
    #training_name = training_name.replace('(no longer required)', '')
    #training_name = training_name.strip().lower().split(' ')
    training_name = training_name.strip().lower()

    for cert in certs:
        found = True
        for word in cert.name.lower().strip().split(' '):
            if found and word.isalnum() and training_name.find(word) < 0:
                found = False
        
        if found:
            return cert
    
    return None

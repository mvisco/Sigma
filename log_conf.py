'''
Created on Apr 17, 2015

@author: mvisco
'''
import logging
import logging.config
    
def Logger(name):
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger(name)
    logger.setLevel('NOTSET')
    return logger
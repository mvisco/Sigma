'''
Created on Apr 24, 2015

@author: mvisco
'''

import persistent
class Server_instance_data(persistent.Persistent):
    '''
    classdocs
    '''


    def __init__(self, load,memory_free,memory_used,processes, label, time_stamp=0):
        '''
        Constructor
        '''       
        self.load = load
        self.memory_free = memory_free
        self.memory_used = memory_used
        self.processes= processes
        self.label = label
        self.time_stamp = time_stamp
        
    def print_instance(self):
        
        print 'load ', self.load, ' memory_free ', self.memory_free, ' memory_used ', self.memory_used, ' processes ' , self.processes, \
         ' label ', self.label, ' epoch time stamp ', self.time_stamp
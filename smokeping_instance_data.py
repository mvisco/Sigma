'''
Created on Apr 24, 2015

@author: mvisco
'''
import persistent

class Smokeping_instance_data(persistent.Persistent):
    '''
    classdocs
    '''


    def __init__(self, packet_loss, mean, std_dev, median, max_value , min_value, label, time_stamp=0):
        '''
        Constructor
        '''       
        self.packet_loss = packet_loss
        self.mean = mean
        self.std_dev = std_dev
        self.median = median
        self.max_value = max_value
        self.min_value = min_value
        self.label = label
        self.time_stamp = time_stamp
        
    def print_instance(self):
        print 'loss ', self.loss, ' mean ', self.mean, ' std_dev ', self.std_dev, ' median ' , self.median, ' max_value ', self.max_value, \
              ' min_value ', self.min_value, ' label ', self.label, ' epoch time stamp ', self.time_stamp
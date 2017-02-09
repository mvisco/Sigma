'''
Created on Apr 12, 2015

@author: mvisco
'''
import logging
import numpy as np
import threading
from worker import  Worker
from worker1 import Worker1

#logging.config.fileConfig('logging.conf')
#LOGGER = logging.getLogger(__name__)   

class Angel:
    '''
    classdocs
    '''

# This is a comment 
  
    def __init__(self,classifier,host_name, service):
        self.classifier=classifier
        self.host_name = host_name
        states = ['quiet', 'alerted, working']
        self.state=states[0]
        self.last_time_stamp = 0
        self.service = service
                            
    def quiet_state(self,features):
        
        # we are in this state when things are quiet       
        y=self.classifier.predict(features)
        logging.info ('label of instance is '+ str(y[0]))
        if y[0] == 1:
            # move to the alerted state
            self.state='alerted'
      
    def alerted_state(self,features):
        # we are in this state when we have found a bad instance 
        # if we receive another bad instance we move to working state 
        # otherwise we move back to quie state
        
        y=self.classifier.predict(features)
        logging.info ('label of instance is '+ str(y[0]))
        if y[0] == 1:
            # move to the working state
            self.state='working'
            if (self.service == 'smokeping_data'):
                thread1 =  Worker(self, self.host_name)
                thread1.start()
            else:
                thread1 =  Worker1(self, self.host_name)
                thread1.start()
            
        else:
            self.state='quiet'
        
    
    def working_state(self,features):
        # if we receive another bad instance we spawn a worker to go and collect data 
        # if we receive good instances we go back to alerted
        y=self.classifier.predict(features)
        logging.info('I am in working state')
        logging.info ('label of instance is '+ str(y[0]))
    
        
    def state_transition(self, instance):
        
        #log = Logger('root')
        
        logging.info( 'State transition for Angel has been called ' + self.host_name + ' Service is ' + self.service+  ' State is ' + self.state)
        a=instance
        if a.time_stamp == self.last_time_stamp:
            # we already processed this data
            logging.info( 'we already processed this instance .. returning '+ str(a.time_stamp))
            return
        self.last_time_stamp = a.time_stamp
        print ' processing this time stamp data ', a.time_stamp
        if self.service == 'smokeping_data':
            x = [a.packet_loss, a.mean, a.std_dev, a.median, a.median, a.min_value ]
            features = np.array(x)
        else:
            
            x = [a.load,a.memory_free,a.memory_used,a.processes]
            features = np.array(x)
        
        if (self.state == 'quiet'):
            self.quiet_state(features)
            
        elif (self.state == 'alerted'):
            self.alerted_state(features)
            
        elif ( self.state == 'working'):
            self.working_state(features) 
            
        else:
            print  "Angel in bad state", self.host_name
    
    def callback(self, name):
        # this gets called from workers when they are done
        lock = threading.Lock()
        lock.acquire()
        try:
            logging.info( 'Worker returned, moving Angel back to quiet state')
            self.state = 'quiet'
            
        finally:
            lock.release() # release lock, no matter what

        

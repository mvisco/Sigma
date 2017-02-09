from fabric.api import local
import numpy as np
import ZODB.FileStorage
import transaction
import random as rd
from sklearn import linear_model
from instance_object import Instance_Object
import yaml
from angel import Angel
import time
import logging
import logging.config
import requests
import json
from server_instance_data import Server_instance_data

def sigma_main():
      
    file_name = 'logs/log'+time.strftime("%b%d%H%M%S", time.localtime())  
    logging.config.fileConfig('logging.conf',defaults={'logfilename': file_name})
    logging.info("Reading yaml configuration file")
    # read configuration and do what is appropriate
    f = open('config.yaml')
    dataMap = yaml.safe_load(f)
    
    smokeping_node = dataMap['smokeping_node']
    user = dataMap['user']
    rdd_dir = dataMap['rdd_dir_path']
    domain_name = dataMap['domain_name']
    hosts = dataMap['hosts'] 
    services = dataMap['services'] 
    graphite_server = dataMap['graphite_server'] 
    f.close()
              
    # We assume that we have the training DB under DB directory so let's train classifiers and instantiate angels
    angels_dict = {}
    
    for host in hosts:
        for service in services:
            logging.info( 'Training classifier for '+ host+' '+service)
            logreg = train_classifier(host, service)
            angel=Angel(logreg,host,service)
            angels_dict[host+service] = angel
    
    # Now we can start the main loop because we have everything in place
    end_time = int(time.time())
    start_time  = end_time -60
    
    while True:
             
        logging.info( 'Main loop start-time and end-time '+ str(start_time) + ' ' + str(end_time))
        dest_dir = 'tmp1'
        remote_file = ''
        
        for i in range (0,len(hosts)):       
            remote_file = remote_file + hosts[i]+'.rrd'
            if (i != len(hosts)-1):
                remote_file = remote_file + ','
        # get all rrd files of interest and store them locally   
        dest_file='tmp1/'      
        local ('scp {}@{}:{} {}'.format(user,smokeping_node,rdd_dir+'/\{'+remote_file+'\}',dest_dir), capture=True) 
        print ' '       
        do_not_change_start_time = False
        
        # Collect realtime smokeping data
        service = 'smokeping_data'
        for host in hosts:       
            remote_file = host+'.rrd'        
            dest_file='tmp1/'+remote_file       
            #data_file='tmp1/'+host+'.data'
            #local ('scp {}@{}:{} {}'.format(user,smokeping_node,rdd_dir+'/'+remote_file,dest_dir), capture=True)
            data_file='tmp1/'+host+'.data'
            local ('rrdtool fetch {} AVERAGE --start {} --end {} > {}'.format(dest_file,start_time,end_time,data_file))
            logging.info( 'created data file '+ data_file)
            # create instance
            input_file = open(data_file, 'r')
            i=1
            list_instances = []
            
            for line in input_file:
                if (':' in line):
                    line_list = line.split(' ')
                    time_stamp = int(line_list[0].strip(':'))
                    if time_stamp != (start_time+60):
                        continue
                    #print line_list
                    
                    # if no content in the packet loss section skip it most likely there is no data
                    if line_list[2] == '-nan':
                        # Ugly Hack: if we get here it means that we are processing start_time+60 but there is nothing yet in it 
                        # set a flag so we do not change start_time and next iteration we process the same timestamp
                        # we should find something there then
                        do_not_change_start_time = True
                        continue
                    list_instances = create_instance(line_list,i,host, list_instances)
                    do_not_change_start_time = False
                    #print list_instances
                    
                    i=i+1
            input_file.close()
            # send instance data to the Angel
            if list_instances:
                angels_dict[host+service].state_transition(list_instances[0])
                   
        
        print "       "
        # Collect data from graphite now
        service = 'server_data'
        for host in hosts:
            #TEMP CODE ----- TEMP CODE 
            # to deal with the fact that host names are different in graphite right now 
            if (host != 'mario-ubuntu-01'):
                host_graphite = host+'-his-internal'
            else:
                host_graphite = host
            list_instances = graphite_instance(graphite_server, host_graphite)
            if list_instances:
                # send data to the associated angel
                angels_dict[host+service].state_transition(list_instances[0])
                   
        logging.info( 'sleeping for 10 seconds')
        logging.info('     ')
        time.sleep(10)
        if do_not_change_start_time == False:
            start_time = calculate_start_time(data_file)
        end_time  = int(time.time())
                    
def create_instance(line_list, j, host_name, list_instances):
    
    pings = []     
    i=0
    for element in line_list:
        if (i == 0):
            time_string = element.strip(':')
            time_stamp = int(time_string)
            i = i+1
            continue
        if ( i == 1 or i == 23 ):
            i = i+1
            continue
        if i == 2:
            loss = float(element)
            i = i+1
            continue      
        # remember element is a string; also with have packet losses the rest of the elements can be nan so we need to deal with that 
        # otherwise scikit is going to blow up 
        if (element != '-nan'):
            pings.append(float(element))
        else:
            pings.append(0)
        i = i+1
    x = np.array(pings)
    #print x
    instance = Instance_Object(loss, x.mean(), x.std(), x[9], x.max(), x.min(), 0, time_stamp)
    list_instances.append(instance)
    return list_instances
     
def train_classifier(host_name, service):
    storage = ZODB.FileStorage.FileStorage('DB/training_data.fs')
    db = ZODB.DB(storage)
    connection = db.open()
    root = connection.root()
    if not root.data:
        print 'no instances'
        return
    features = []
    label = []
    
    # Depending on the service that  we are training the classifier on, we need to build different instances
    
    if (service == 'smokeping_data'):    
        for instance in root[host_name]['smokeping_data']:
            a =  instance
            x = [a.packet_loss, a.mean, a.std_dev, a.median, a.median, a.min_value ]
            y = a.label
            features.append(x)
            label.append(y)
            #print a.packet_loss, " " , a.mean, " " , a.std_dev, " " , a.median , " " ,a.max_value, " ", a.min_value, " " , a.label
    if (service == 'server_data'):
        for instance in root[host_name]['server_data']:
            a =  instance
            x = [a.load, a.memory_free, a.memory_used, a.processes ]
            y = a.label
            features.append(x)
            label.append(y)
        
    connection.close()
    db.close()
    storage.close()  
    features = np.array(features)
    label = np.array(label)
    #print features 
    #print 
    #print label
    logreg = linear_model.LogisticRegression(C=1e5)
    logreg.fit(features,label)
    #params = logreg.get_params(deep=True)
    #print params
    print 'score is ',logreg.score(features,label)
    #c=logreg.predict(features)
    #print c
    # create instance to be predicted
    #X=[0,1.18833333e-03 , 1.18833333e-03,1.18833333e-03,1.18833333e-03,6.31666667e-04]
    #X=np.array(X)
    #c=logreg.predict(X)
    #print c   
    return logreg
    
def get_yaml_file():
    f = open('config.yaml')
    dataMap = yaml.safe_load(f)
    print dataMap
    node = dataMap['smokeping_node']
    hosts = dataMap['hosts']
    print node, hosts
    create = dataMap['create_local_data']
    if create:
        print 'create is true ' , create
    else:
        print 'create is false ' , create
    
    f.close()
    
def get_hosts_names(file_name, domain_name):
    host_list = []
    input_file = open(file_name, 'r')
    found_alert_section=False
    # we look for the host lines in the file but we have to skip the Alerts section because it may contain hosts as well
    domain_name = '-'+domain_name
    for line in input_file:
        if ('+ Alerts' in line):
            found_alert_section=True
            continue
        if "host " in line and not found_alert_section:
            host = line.split('= ')[1]
            host1=host.strip('\r\n')           
            host1=host1.replace(domain_name,'')
            host_list.append(host1)
    input_file.close()
    return host_list

def get_current_data():
        # read configuration
    f = open('config.yaml')
    dataMap = yaml.safe_load(f)
    smokeping_node = dataMap['smokeping_node']
    user = dataMap['user']
    targets_file = dataMap['targets_file']
    rdd_dir = dataMap['rdd_dir_path']
    domain_name = dataMap['domain_name']
    hosts = dataMap['hosts']
    f.close()
    #get current time in epoch
    end_time = int(time.time())
    start_time  = end_time -120
    print 'strat-time and end-time ', start_time, end_time
    dest_dir = 'tmp1'
     
    for host in hosts:
       
        remote_file = host+'.rrd'        
        dest_file='tmp1/'+remote_file       
        data_file='tmp1/'+host+'.data'
        local ('scp {}@{}:{} {}'.format(user,smokeping_node,rdd_dir+'/'+remote_file,dest_dir))
        local ('rrdtool fetch {} AVERAGE --start {} --end {} > {}'.format(dest_file,start_time,end_time,data_file))
        print 'created data file ', data_file
        # get instance
        input_file = open(data_file, 'r')
        i=1
        list_instances = []
        # creating profiling data
        for line in input_file:
            if (':' in line):
                line_list = line.split(' ')
                #print line_list
                if line_list[2] == '-nan':
                    continue
                list_instances = create_instance(line_list,i,host, list_instances)
                #print list_instances
                i=i+1
        input_file.close()
        
        
    # create instance from current data
    
    
def calculate_start_time(input_file):
    input_file = open(input_file, 'r')
    for line in input_file:
        if (':' in line):
            line_list = line.split(' ')
            return  (int(line_list[0].strip(':')))
    input_file.close()            
    
  
def graphite_instance(graphite_server, host):
    
    URI_MEMORY_FREE='.memory.memory-free&format=json&from=-3min'
    URI_MEMORY_USED='.memory.memory-used&format=json&from=-3min'
    URI_LOAD = '.load.load.shortterm&format=json&from=-3min'
    URI_PS_SLEEPING = '.processes.ps_state-sleeping&format=json&from=-3min'
    URI_PS_RUNNING = '.processes.ps_state-running&format=json&from=-3min'
    
    URI_COMMON='/render?target='
    URI_HOME='http://'+graphite_server
    
    logging.info('getting graphite data for host '+ host)
       
    url = URI_HOME+URI_COMMON+host+URI_MEMORY_FREE;
    session = requests.Session()
    payload = session.get(url, verify=False)
    a = json.loads(payload.content)
    value_list = a[0]['datapoints']
    memory_free_list = []
    for value in value_list:
        memory_free_list.append(value[0])
        #get a time stamp from the here we need to send it to the instance object
        timestamp = value[1]
    #print len(memory_free_list)
     
    matrix = np.array(memory_free_list)
    time.sleep(1)
    
    url = URI_HOME+URI_COMMON+host+URI_MEMORY_USED;
    session = requests.Session()
    payload = session.get(url, verify=False)
    a = json.loads(payload.content)
    value_list = a[0]['datapoints']
    memory_used_list = []
    for value in value_list:
        memory_used_list.append(value[0])
    #print len(memory_used_list)
    matrix = np.vstack([matrix, memory_used_list])
    
    url = URI_HOME+URI_COMMON+host+URI_LOAD;
    session = requests.Session()
    payload = session.get(url, verify=False)
    a = json.loads(payload.content)
    value_list = a[0]['datapoints']
    load_list = []
    for value in value_list:
        load_list.append(value[0])
    #print len(load_list)
    matrix = np.vstack([matrix, load_list])
    
    url = URI_HOME+URI_COMMON+host+URI_PS_SLEEPING;
    session = requests.Session()
    payload = session.get(url, verify=False)
    a = json.loads(payload.content)
    value_list = a[0]['datapoints']
    ps_sleeping_list = []
    for value in value_list:
        ps_sleeping_list.append(value[0])
    #print len(ps_sleeping_list)
    matrix = np.vstack([matrix, ps_sleeping_list])
    
    url = URI_HOME+URI_COMMON+host+URI_PS_RUNNING;
    session = requests.Session()
    payload = session.get(url, verify=False)
    a = json.loads(payload.content)
    value_list = a[0]['datapoints']
    ps_running_list = []
    for value in value_list:
        ps_running_list.append(value[0])
    #print len(ps_running_list)
    matrix = np.vstack([matrix, ps_running_list])
    
    # create the instances now because we have all necessary data in the matrix. Remember each column of the matrix is an 
    # instance, we will need to check if there are none values. Loop on all columns.....
    list_instance = []
    for x in range(matrix.shape[1]):
        column = matrix[:,x]
        if list(column).count(None)> 0:
            # skip this instance
            continue
        #create the status quo instances. It is better to normalize the data because the numbers range is to high
        total_memory = column[0]+column[1]
        total_processes = column[3]+column[4]
        instance = Server_instance_data(column[2],column[0]/total_memory, column[1]/total_memory,total_processes/100.0,0, time_stamp = timestamp )
        list_instance.append(instance)
    if not list_instance:
        logging.info('No data received from graphite for time stamp ' + str(timestamp))
    else:
        instance.print_instance()
    print "   "
    return list_instance

if __name__ == "__main__":
    sigma_main()
    #read_instances('grafana-server')
    #cleanDB()
    #classifier()
    #get_yaml_file()
    #get_current_data()
    #try_log()
    #calculate_start_time('tmp1/mario-postgres-02.data')
    #graphite_client()



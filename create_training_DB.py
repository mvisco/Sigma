'''
Created on Apr 24, 2015

@author: mvisco
'''

from fabric.api import local
import numpy as np
import ZODB.FileStorage
import transaction
import random as rd
import yaml
import time
import logging
import logging.config
import requests
import json
from smokeping_instance_data import Smokeping_instance_data
from server_instance_data import Server_instance_data


def create_training_DB():
    
    file_name = 'logs/create_training_db_log'+time.strftime("%b%d%H%M%S", time.localtime())  
    logging.config.fileConfig('logging.conf',defaults={'logfilename': file_name})
    
    logging.info("Reading yaml configuration file")
    # read configuration and do what is appropriate
    f = open('config.yaml')
    dataMap = yaml.safe_load(f)
    smokeping_node = dataMap['smokeping_node']
    user = dataMap['user']
    targets_file = dataMap['targets_file']
    rdd_dir = dataMap['rdd_dir_path']
    domain_name = dataMap['domain_name']
    hosts = dataMap['hosts']   
    graphite_server = dataMap['graphite_server']
    f.close()
    
    # Make sure DB is clean before we proceed
    cleanDB()
    # define instance disctionary
    instances_dictionary = {}
    
    # Get data from smokeping and store it locally
    create_local_rrd_data(smokeping_node,user,targets_file,rdd_dir,domain_name,hosts)
    
    # create smokeping instances
    for host in hosts:
        data_file = 'tmp/'+host+'.data'
        smokeping_instances = create_smokeping_instances(data_file,host)
        instances_dictionary['smokeping_data'] = smokeping_instances
        
        #TEMP CODE ----- TEMP CODE 
        # to deal with the fact that host names are different in graphite right now 
        if (host != 'mario-ubuntu-01'):
            host_graphite = host+'-his-internal'
        else:
            host_graphite = host
        create_server_data(graphite_server, host_graphite, instances_dictionary)
        
        storage = ZODB.FileStorage.FileStorage('DB/training_data.fs')
        db = ZODB.DB(storage)
        connection = db.open()
        root = connection.root()
        root[host]=instances_dictionary
        transaction.get().commit()
        connection.close()
        db.close()
        storage.close()
        logging.info("Done creating the DB for hostname" + host)
          

def create_smokeping_instances(file_name,host_name):
    input_file = open(file_name, 'r')
    i=1
    list_instances = []
    # creating profiling data
    for line in input_file:
        if (':' in line):
            line_list = line.split(' ')
            #print line_list
            if line_list[2] == '-nan':
                continue
            list_instances = create_instance(line_list,i,host_name, list_instances)
            i=i+1
    input_file.close()
    # creating error data
    input_file = open(file_name, 'r')
    for line in input_file:
        if (':' in line):
            line_list = line.split(' ')
            if line_list[2] == '-nan':
                continue
            #print line_list
            if (rd.random() <= 0.5):
                loss=0
            else:
                loss=1
                                         
            list_instances = create_bad_instance(line_list,i,loss, host_name, list_instances)
            i=i+1
    input_file.close()
    return list_instances
    
            
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
    instance = Smokeping_instance_data(loss, x.mean(), x.std(), x[9], x.max(), x.min(), 0, time_stamp)
    list_instances.append(instance)
    return list_instances
    
def create_bad_instance(line_list, j, loss_threshold, host_name, list_instances):
    
    pings = []     
    i=0
    for element in line_list:
        if ( i == 0 or i == 1 or i == 23 ):
            i = i+1
            continue
        if i == 2:
            loss = float(element)
            i = i+1
            continue      
        # remember element is a string        
        pings.append(float(element)+(rd.random()/100.0))
        i = i+1
    x = np.array(pings)
    if loss_threshold==1:
        loss = loss+10*rd.random()
    else:
        loss =0
    instance = Smokeping_instance_data(loss, x.mean(), x.std(), x[9], x.max(), x.min(), 1)
    list_instances.append(instance)
    return list_instances 
  
 
def create_server_data(graphite_server, host, instances_dictionary):
    
    URI_MEMORY_FREE='.memory.memory-free&format=json&from=-30min'
    URI_MEMORY_USED='.memory.memory-used&format=json&from=-30min'
    URI_LOAD = '.load.load.shortterm&format=json&from=-30min'
    URI_PS_SLEEPING = '.processes.ps_state-sleeping&format=json&from=-30min'
    URI_PS_RUNNING = '.processes.ps_state-running&format=json&from=-30min'
    
    URI_COMMON='/render?target='
    URI_HOME='http://'+graphite_server
       
    url = URI_HOME+URI_COMMON+host+URI_MEMORY_FREE;
    session = requests.Session()
    payload = session.get(url, verify=False)
    a = json.loads(payload.content)
    value_list = a[0]['datapoints']
    memory_free_list = []
    for value in value_list:
        memory_free_list.append(value[0])
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
    print len(memory_used_list)
    matrix = np.vstack([matrix, memory_used_list])
    
    url = URI_HOME+URI_COMMON+host+URI_LOAD;
    session = requests.Session()
    payload = session.get(url, verify=False)
    a = json.loads(payload.content)
    value_list = a[0]['datapoints']
    load_list = []
    for value in value_list:
        load_list.append(value[0])
    print len(load_list)
    matrix = np.vstack([matrix, load_list])
    
    url = URI_HOME+URI_COMMON+host+URI_PS_SLEEPING;
    session = requests.Session()
    payload = session.get(url, verify=False)
    a = json.loads(payload.content)
    value_list = a[0]['datapoints']
    ps_sleeping_list = []
    for value in value_list:
        ps_sleeping_list.append(value[0])
    print len(ps_sleeping_list)
    matrix = np.vstack([matrix, ps_sleeping_list])
    
    url = URI_HOME+URI_COMMON+host+URI_PS_RUNNING;
    session = requests.Session()
    payload = session.get(url, verify=False)
    a = json.loads(payload.content)
    value_list = a[0]['datapoints']
    ps_running_list = []
    for value in value_list:
        ps_running_list.append(value[0])
    print len(ps_running_list)
    matrix = np.vstack([matrix, ps_running_list])
    
    # create the instances now because we have all necessary data in the matrix. Remember each column of the matrix is an 
    # instance, we will need to check if there are none values. Loop on all columns.....
    list_instances = []
    for x in range(matrix.shape[1]):
        column = matrix[:,x]
        if list(column).count(None)> 0:
            # skip this instance
            continue
        #create the status quo instances. It is better to normalize the data because the numbers range is to high
        total_memory = column[0]+column[1]
        total_processes = column[3]+column[4]
        instance = Server_instance_data(column[2],column[0]/total_memory, column[1]/total_memory,total_processes/100.0,0 )
        list_instances.append(instance)
        # create the bad instances
        # These are the assumption load approx increases by 50%, memory approx by 20%, processes by apprx 10%. Keep in mind that these 
        # numbers are not accurate they are just a magnitude of levels
        instance = Server_instance_data(column[2]+(0.3+rd.random()/10.0),(column[0]/total_memory), \
                                        (column[1]/total_memory),(total_processes/100.0),1 )
        list_instances.append(instance)
     
    instances_dictionary['server_data'] = list_instances  
        
def create_local_rrd_data(smokeping_node,user,targets_file,rdd_dir,domain_name,hosts):
        
    # get the Targets file from smokeping server
    local ('scp {}@{}:{} tmp/old_Targets'.format(user,smokeping_node,targets_file))
    #print 'done reading the targets file'
    
    # get the host names from the target file
    host_list = get_hosts_names('tmp/old_Targets', domain_name)
    print host_list
    dest_dir = 'tmp'

    # extract the data locally
    for host in host_list:
        if host in hosts:
            remote_file = host+'.rrd'        
            dest_file='tmp/'+remote_file       
            data_file='tmp/'+host+'.data'
            local ('scp {}@{}:{} {}'.format(user,smokeping_node,rdd_dir+'/'+remote_file,dest_dir))
            local ('rrdtool fetch {} AVERAGE -r 300 -s -900 > {}'.format(dest_file,data_file))
            print 'created data file ', data_file
            
    print 'Done creating local data'
    
def cleanDB():     
    storage = ZODB.FileStorage.FileStorage('DB/training_data.fs')
    db = ZODB.DB(storage)
    connection = db.open()
    root = connection.root()
    instance = []
    for i in root:
        instance.append(i)
    for i in instance:
        del root[i]
        transaction.get().commit()
    connection.close()
    db.close()
    storage.close()

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

def read_instances(host_name):
    storage = ZODB.FileStorage.FileStorage('DB/training_data.fs')
    db = ZODB.DB(storage)
    connection = db.open()
    root = connection.root()
    if not root.data:
        print 'no instances'
        return
    print root.items()
    #a=root[host_name][1]
    #print a
    for instance in root[host_name]['smokeping_data']:
        print instance
        a =  instance
        print a.packet_loss, " " , a.mean, " " , a.std_dev, " " , a.median , " " ,a.max_value, " ", a.min_value, " " , a.label
        
    for instance in root[host_name]['server_data']:
        print instance 
        a = instance
        print a.load," ", a.memory_free, " ", a.memory_used, " " , a.processes, " ", a.label  
    

if __name__ == "__main__":
    #sigma_main()
    read_instances('mario-ubuntu-01')
    #cleanDB()
    #classifier()
    #get_yaml_file()
    #get_current_data()
    #try_log()
    #calculate_start_time('tmp1/mario-postgres-02.data')
    #graphite_client()
    #create_training_DB()
    #instance_dictionary = {}
    #create_server_data('10.203.31.143',['mario-ubuntu-01'], instance_dictionary)
    
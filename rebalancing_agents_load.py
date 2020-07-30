#!/opt/openstackclient-3.9.0/bin/python

import openstack, inspect, math
import sys, os, re, threading, queue, argparse
from optparse import OptionParser

adhcp_nets = {}
hash_adhcp = {}
hash_net = {}
al3_routers = {}
hash_al3 = {}
hash_router = {}
average_l3_by_ag = 0
average_net_by_ag  0

def average(hash_agent):
    return math.ceil(sum(list(map((lambda x :len(hash_agent[x])), hash_agent)))/len(hash_agent))
    
def pair_list_nb_by_id_asc(hash_agent):
    return sorted((list(map((lambda x :(x, len(hash_agent[x]))), hash_agent))), key=itemgetter(1), reverse=False)

def pair_list_nb_by_id_dsc(hash_agent):
    return sorted((list(map((lambda x :(x, len(hash_agent[x]))), hash_agent))), key=itemgetter(1), reverse=True)

def get_agent_id_form_network(auth, network):
    return list(map((lambda x : x.id), auth.network.network_hosting_dhcp_agents(network)))

def init_conn():
    try:
        conn=openstack.connect()
        auth = conn.connect_as(username=os.environ["OS_USERNAME"], password=os.environ["OS_PASSWORD"], project_name='admin')
        return auth
    except Exception as e:
        print("Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return None

def init_data_dhcp(auth):
    global adhcp_nets,hash_adhcp,hash_dhcp
    try:
        dhcp_agents = list(auth.network.agents("DHCP agent"))
        nb_gl_networks = 0
        for dhcp_agent in dhcp_agents:
            if "neut-m" not in dhcp_agent.host or dhcp_agent.is_active is False:
                continue
            hash_adhcp[dhcp_agent.id] = dhcp_agent
            adhcp_nets[dhcp_agent.id] = {}
            for net in auth.network.dhcp_agent_hosting_networks(dhcp_agent):
                adhcp_nets[dhcp_agent.id][net.id] = net
                hash_net[net.id] = net
            nb_gl_networks += len(adhcp_nets[dhcp_agent.id])            
        average_net_by_ag = average(adhcp_nets)        
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)

def init_data_l3(auth):
    global al3_routers,hash_al3,hash_router
    try:
        l3_agents = list(auth.network.agents("L3 agent"))
        nb_gl_routers = 0
        for l3_agent in l3_agents:
            if "neut-m" not in l3_agent.host or l3_agent.is_active is False:
                continue
            hash_al3[l3_agent.id] = l3_agent
            al3_routers[l3_agent.id] = {}
            for router in auth.network.agent_hosted_routers(l3_agent):
                al3_routers[l3_agent.id][router.id] = router
                hash_router[router.id] = router
            nb_gl_routers += len(al3_routers[l3_agent.id])

        average_l3_by_ag = average(al3_routers)
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)


def get_agent_network(agent, asc_agent, agent_net, average_network):
    for ag in asc_agent:
        if ag[0][1] > average_network:
            print("In %s Can't find a new agent lower to %d" % (inspect.stack()[0][3],average_network))
            return None
        if agent != ag[0] and ag[0] not in agent_net:
            return ag[0]
    return None

def get_agent_router(agent, asc_agent, average_router):
    for ag in asc_agent:
        if ag[0][1] > average_network:
            print("In %s Can't find a new agent lower to %d" % (inspect.stack()[0][3],average_router))
            return None
        if agent != ag[0]:
            return ag[0]
    return None

def adding_removing_network(auth, agent, average_network):
    try:
        asc_agent = pair_list_nb_by_id_asc(adhcp_nets)

        while len(adhcp_nets[agent]) <= average_network:
            if os.path.exist(stop_file):
                print("Find file %s : stopping" %s stop_file)
                return -2            
            keys = adhcp_nets[agent].keys()
            if len(keys] == 0:
                return  -1
            net = keys[0]
            agent_net =  get_agent_id_form_network(net)
            new_agent = get_agent_network(agent, asc_agent, agent_net, average_network)
            if new_agent is None:                
                return -1
            resp1 = auth.network.add_dhcp_agent_to_network(new_agent, hash_net[net])
            resp2 = auth.network.remove_dhcp_agent_to_network(agent, hash_net[net])
            adhcp_nets[new_agent][net] = adhcp_nets[agent][net]
            del(adhcp_nets[agent][net])
            asc_agent = pair_list_nb_by_id_asc(adhcp_nets)

        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)

def adding_removing_router(auth, agent, average_router):
    try:
        asc_agent = pair_list_nb_by_id_asc(al3_routers)

        while len(al3_routers[al3_routers]) <= average_router:
            if os.path.exist(stop_file):
                print("Find file %s : stopping" %s stop_file)
                return -2            
            keys = al3_routers[agent].keys()
            if len(keys] == 0:
                return
            net = keys[0]
            new_agent = get_agent_router(agent, asc_agent)
            resp1 = auth.network.(new_agent, hash_net[net])
            resp2 = auth.network.(agent, hash_net[net])
            adhcp_nets[new_agent][net] = adhcp_nets[agent][net]
            del(adhcp_nets[agent][net])
            asc_agent = pair_list_nb_by_id_asc(al3_routers)
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)
        
def balancing_network(auth):
    try:
        average_network = average(adhcp_nets)
        dsc_agent = pair_list_nb_by_id_dsc(adhcp_nets)
        while [ 1 ]:
            if os.path.exist(stop_file):
                print("Find file %s : stopping" %s stop_file)
                return -2
            if dsc_agent[0][1] <= average_network:
                break
            else:
                ret = moving_removing_network(dsc_agent[0][0], average_network)
                if ret != 0:
                    return -1
            dsc_agent = pair_list_nb_by_id_dsc(adhcp_nets)            
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)

def balancing_router(auth):
    try:
        average_router = average(adhcp_nets)
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)

def evacuate_network(auth):
    try:
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)

def evacuate_router(auth):
    try:
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)

def main():
    try:

        parser = argparse.ArgumentParser(description="Requilibrage de charge des agents/evacuation des routeurs/reseau sur un agent")
        
        parser.add_argument("-n", "--node", action= "store", dest="node", \
                            default=None, \
                            help="Neutron node for evacuate")

        parser.add_argument("--action", action= "store", dest="action", \
                            default=None, choices = [ "balancing", "evacuate"],\
                            help="action to perform choices balancing or evacuate")

        args = parser.parse_args()

        node = args.node
        action = args.action

        if action not in ["balancing", "evacuate"]:
            print("Syntaxe is Wrong action is not balancing or evacuate Value %s" % action)
            sys.exit(1)

        if action == "evacuate" and node is None:
            print("Syntaxe is Wrong for action evacuate missing Node")
            sys.exit(1)

        if action == "evacuate" and "neut-m" in node:
            print("Syntaxe is Wrong for action evacuate Wrong node name exxpecting name containing neut-m")
            sys.exit(1)
            
        auth = init_conn()

        init_data_dhcp(auth)

        init_data_l3(auth)

        if action == "balancing":
            balancing_network(auth)
            balancing_router(auth)            

        if action == "evacuate":
            evacuate_network(auth)
            evacuate_router(auth)            

    except Exception as e:
        print("Error in init_conn Err : %s" % e)
        sys.exit(1)

#################################### MAIN #####################################

if __name__ == '__main__':
    main()

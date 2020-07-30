#!/opt/openstackclient-3.9.0/bin/python

import openstack, inspect, math
import sys, os, re, threading, queue, argparse
from optparse import OptionParser

#### Variable Globale
adhcp_nets = {}
hash_adhcp = {}
hash_net = {}
al3_routers = {}
hash_al3 = {}
hash_router = {}
average_l3_by_ag = 0
average_net_by_ag  0
stop_file="/tmp/rebalancing_agents_load.stop"

## Calcul le nombre de reseau ou routeur moyen
def average(hash_agent):
    return math.ceil(sum(list(map((lambda x :len(hash_agent[x])), hash_agent)))/len(hash_agent))

## retourne une liste de paire (UUID agent, nb router/network) trie de maniere croissant par le nombre
def pair_list_nb_by_id_asc(hash_agent):
    return sorted((list(map((lambda x :(x, len(hash_agent[x]))), hash_agent))), key=itemgetter(1), reverse=False)

## retourne une liste de paire (UUID agent, nb routers/reseaux trie de maniere decroissant par le nombre
def pair_list_nb_by_id_dsc(hash_agent):
    return sorted((list(map((lambda x :(x, len(hash_agent[x]))), hash_agent))), key=itemgetter(1), reverse=True)

## retourne la paire d'agent gerant un reseau
def get_agent_id_form_network(auth, network):
    return list(map((lambda x : x.id), auth.network.network_hosting_dhcp_agents(network)))

## Etablissement de la connexion
def init_conn():
    try:
        conn=openstack.connect()
        auth = conn.connect_as(username=os.environ["OS_USERNAME"], password=os.environ["OS_PASSWORD"], project_name='admin')
        return auth
    except Exception as e:
        print("Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return None

## Initialisation des tableaux de travail pour les agents DHCP
def init_data_dhcp(auth):
    global adhcp_nets,hash_adhcp,hash_dhcp
    try:
        adhcp_nets = {}
        hash_adhcp = {}
        hash_net = {}
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

## Initialisation des tableaux de travail pour les agents L3
def init_data_l3(auth):
    global al3_routers,hash_al3,hash_router
    try:
        al3_routers = {}
        hash_al3 = {}
        hash_router = {}
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

## Get New agent possedant le moins de reseau et dont le reseau n'y est pas déjà positionné 
def get_agent_network(agent, asc_agent, agent_net, average_network):
    try:
        for ag in asc_agent:
            if ag[0][1] > average_network:
                print("In %s Can't find a new agent lower or egal to average %d" % (inspect.stack()[0][3],average_network))
                return None
            if agent != ag[0] and ag[0] not in agent_net:
                return ag[0]
        return None
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1

## Get New agent possedant le moins de routeur 
def get_agent_router(agent, asc_agent, average_router):
    try:
        for ag in asc_agent:
            if ag[0][1] > average_network:
                print("In %s Can't find a new agent lower or egal to average %d" % (inspect.stack()[0][3],average_router))
                return None
            if agent != ag[0]:
                return ag[0]
        return None
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1
    
## pour un agent on deplace les reseaux sur d'autres agent pour retomber en dessous de la moyenne
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

## pour un agent on deplace les routeurs sur d'autres agent pour retomber en dessous de la moyenne
def adding_removing_router(auth, agent, average_router):
    try:
        asc_agent = pair_list_nb_by_id_asc(al3_routers)

        while len(al3_routers[agent]) <= average_router:
            if os.path.exist(stop_file):
                print("Find file %s : stopping" %s stop_file)
                return -2            
            keys = al3_routers[agent].keys()
            if len(keys] == 0:
                return -1
            router = keys[0]
            new_agent = get_agent_router(agent, asc_agent)
            if new_agent is None:                
                return -1            
            resp1 = auth.network.add_router_to_agent(new_agent, hash_router[router])
            resp2 = auth.network.remove_router_from_agent(agent, hash_router[router])
            al3_routers[new_agent][router] = al3_routers[agent][souter]
            del(al3_routers[agent][router])
            asc_agent = pair_list_nb_by_id_asc(al3_routers)
            
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)

## On balance les agents les plus charges en reseau 
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
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1

## On balance les agents les plus charges en routeur
def balancing_router(auth):
    try:
        average_router = average(al3_routers)
        dsc_agent = pair_list_nb_by_id_dsc(al3_routers)
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
            dsc_agent = pair_list_nb_by_id_dsc(al3_routers)            
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1

## Retourne l'UUID de l'agent DHCP pour le noeud
def get_agent_dhcp_from_node(node):
    try:
        for agent in hash_adhcp.keys():
            if hash_adhcp[agent].host == node:
                return agent
        return None
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1
    
## Retourne l'UUID de l'agent L3 pour le noeud
def get_agent_l3_from_node(node):
    try:
        for agent in hash_al3.keys():
            if hash_al3[agent].host == node:
                return agent
        return None
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1

## Evacue les reseaux sur les autres agents
def evacuate_network(auth, node):
    try:
        agent = get_agent_dhcp_from_node(node)
        if agent is None:
            print("Exit Can't find agent DHCP for node %s" % node)
            return -1
        data_agent = adhcp_nets[agent]
        del(adhcp_nets[agent])
        average_network = average(adhcp_nets)

        for net in data_agent.keys():
            if os.path.exist(stop_file):
                print("Find file %s : stopping" %s stop_file)
                return -2            
            agent_net =  get_agent_id_form_network(net)
            new_agent = get_agent_network(agent, asc_agent, agent_net, average_network)
            if new_agent is None:                
                return -1
            resp1 = auth.network.add_dhcp_agent_to_network(new_agent, hash_net[net])
            resp2 = auth.network.remove_dhcp_agent_to_network(agent, hash_net[net])
            adhcp_nets[new_agent][net] = data_agent[net]
            asc_agent = pair_list_nb_by_id_asc(adhcp_nets)
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1

## Evacue les routeurs sur les autres agents
def evacuate_router(auth, node):
    try:
        agent = get_agent_router_from_node(node)
        if agent is None:
            print("Exit Can't find agent L3 for node %s" % node)
            return -1
        data_agent = al3_routers[agent]
        del(al3_routers[agent])
        average_router = average(al3_routers)
        asc_agent = pair_list_nb_by_id_asc(al3_routers)
            
        for router in data_agent.keys():
            if os.path.exist(stop_file):
                print("Find file %s : stopping" %s stop_file)
                return -2            
            agent_router =  get_agent_id_form_router(router)
            new_agent = get_agent_router(agent, asc_agent, average_router)
            if new_agent is None:                
                return -1
            resp1 = auth.network.(new_agent, hash_net[net])
            resp2 = auth.network.(agent, hash_net[net])
            al3_routers[new_agent][net] = data_agent[net]
            asc_agent = pair_list_nb_by_id_asc(al3_routers)
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1

## Bilan du placements des reseaux et routeurs sur les agents
def check_load():
        try:
            print("# Network by agent:\n")
            asc_agent = pair_list_nb_by_id_asc(adhcp_nets)

            for ag in asc_agent:
                print("Agent: %s # Network : %d" % (ag[0], ag[1]))

            print("# Router by agent:\n")
            asc_agent = pair_list_nb_by_id_asc(al3_routers)

            for ag in asc_agent:
                print("Agent: %s # Network : %d" % (ag[0], ag[1]))
                
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)
            
        
def main():
    try:

        #### Argument Parser in Python 
        parser = argparse.ArgumentParser(description="Requilibrage de charge des agents/evacuation des routeurs/reseau sur un agent")

        ### Specification du noeud Neutron pour l'evacuation
        parser.add_argument("-n", "--node", action= "store", dest="node", \
                            default=None, \
                            help="Neutron node for evacuate")

        ### Action Balancing ou evacuation des reseaux et routeurs
        parser.add_argument("--action", action= "store", dest="action", \
                            default=None, choices = [ "balancing", "evacuate"],\
                            help="action to perform choices balancing or evacuate")

        args = parser.parse_args()

        ### recuperation des paramètres
        node = args.node
        action = args.action

        ### verfication des arguments
        if action not in ["balancing", "evacuate"]:
            print("Syntaxe is Wrong action is not balancing or evacuate Value %s" % action)
            sys.exit(1)

        if action == "evacuate" and node is None:
            print("Syntaxe is Wrong for action evacuate missing Node")
            sys.exit(1)

        if action == "evacuate" and "neut-m" in node:
            print("Syntaxe is Wrong for action evacuate Wrong node name exxpecting name containing neut-m")
            sys.exit(1)

        ### Initialisation de la connection
        auth = init_conn()

        ### Etat initiale Agent DHCP
        init_data_dhcp(auth)

        ### Etat initiale Agent L3        
        init_data_l3(auth)

        ### Check de l'équilibrage au demarrage
        check_load()
        
        ### Balancing des reseaux et routeurs
        if action == "balancing":
            if balancing_network(auth) != 0:
                print("Exit !!! something is wrong in balancing_network")
                sys.exit(1)
            if balancing_router(auth) != 0:
                print("Exit !!! something is wrong in balancing_router")
                sys.exit(1)

        ### Evacuation des reseaux et routeurs
        if action == "evacuate":
            if evacuate_network(auth, node) != 0:
                print("Exit !!! something is wrong in evacuate_network")
                sys.exit(1)

            if evacuate_router(auth, node) != 0:
                print("Exit !!! something is wrong in evacuate_router")
                sys.exit(1)

        ### Etat initiale Agent DHCP
        init_data_dhcp(auth)

        ### Etat initiale Agent L3        
        init_data_l3(auth)

        ### Check de l'equilibrage a la fin
        check_load()        
            
        sys.exit(0)
    except Exception as e:
        print("Error in init_conn Err : %s" % e)
        sys.exit(1)

#################################### MAIN #####################################

if __name__ == '__main__':
    main()

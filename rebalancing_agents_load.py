#!/opt/openstackclient-3.9.0/bin/python

import openstack, inspect, math, logging, datetime, subprocess
import sys, os, re, threading, queue, argparse
from optparse import OptionParser
from operator import itemgetter

from time import sleep
#### Variable Globale
adhcp_nets = {}
hash_adhcp = {}
hash_net = {}

al3_routers = {}
hash_al3 = {}
hash_router = {}

average_l3_by_ag = 0
average_net_by_ag = 0

check_action_net = {}
check_action_router = {}

stop_file="/tmp/rebalancing_agents_load.stop"
dryrun = False

nb_network = 0
nb_router = 0

nb_net_max = -1
nb_router_max= -1

logdir="/tmp/"
log = None

ssh_cmd = 'ssh %s -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" sudo ip netns'

## ssh helion-cp1-neut-m1-mgmt -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" ip netns
# stack@helion-cp1-neut-m1-mgmt:~$ ip netns
# snat-d2bdd02e-9953-4d64-a507-9933d12b0746
# snat-d037fa9c-305d-4642-a2e4-30c71950d04f
# snat-a95425eb-a0b6-4fee-a099-9afd925a0997
# snat-7e8af120-d25c-40d2-acb0-8e3a03e95805
# snat-56f5f0a4-b1ab-4d4d-9b9f-4df0cb7beb40
# qrouter-b5fec874-0475-49d2-b454-0de0d791ac06
# qrouter-d2bdd02e-9953-4d64-a507-9933d12b0746
# qrouter-654629e1-1880-4942-9656-8e84efa276d3
# qrouter-7e8af120-d25c-40d2-acb0-8e3a03e95805
# qrouter-56f5f0a4-b1ab-4d4d-9b9f-4df0cb7beb40
# qrouter-a95425eb-a0b6-4fee-a099-9afd925a0997
# qrouter-9d414124-57f1-4b0f-ba9e-8b1204f978b8
# qrouter-d037fa9c-305d-4642-a2e4-30c71950d04f

## Calcul le nombre de reseau ou routeur moyen par agent arrondie au chiffre superieur
def average(hash_agent):
    return math.ceil(sum(list(map((lambda x :len(hash_agent[x])), hash_agent)))/len(hash_agent))

def average_less_one(hash_agent):
    return math.ceil(sum(list(map((lambda x :len(hash_agent[x])), hash_agent)))/(len(hash_agent)-1))

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
    global log
    try:
        conn=openstack.connect()
        auth = conn.connect_as(username=os.environ["OS_USERNAME"], password=os.environ["OS_PASSWORD"], project_name='admin')
        return auth
    except Exception as e:
        print("Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return None

## Initialisation des tableaux de travail pour les agents DHCP
def init_data_dhcp(auth, action=True):
    global adhcp_nets,hash_adhcp,hash_net,log
    try:
        adhcp_nets = {}
        hash_adhcp = {}
        hash_net = {}
        dhcp_agents = list(auth.network.agents(agent_type="DHCP agent"))
        nb_gl_networks = 0
        for dhcp_agent in dhcp_agents:
            if "neut-m" not in dhcp_agent.host or dhcp_agent.is_alive is False:
                continue
            if action:
                check_action_net[dhcp_agent.host] = []            
            hash_adhcp[dhcp_agent.id] = dhcp_agent
            adhcp_nets[dhcp_agent.id] = {}
            for net in auth.network.dhcp_agent_hosting_networks(dhcp_agent):
                adhcp_nets[dhcp_agent.id][net.id] = net
                hash_net[net.id] = net
            nb_gl_networks += len(adhcp_nets[dhcp_agent.id])            
        average_net_by_ag = average(adhcp_nets)        
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)

## Initialisation des tableaux de travail pour les agents L3
def init_data_l3(auth, action=True):
    global al3_routers,hash_al3,hash_router,log
    try:
        al3_routers = {}
        hash_al3 = {}
        hash_router = {}
        l3_agents = list(auth.network.agents(agent_type="L3 agent"))
        nb_gl_routers = 0
        for l3_agent in l3_agents:
            if "neut-m" not in l3_agent.host or l3_agent.is_alive is False:
                continue
            if action:
                check_action_router[l3_agent.host] = []                        
            hash_al3[l3_agent.id] = l3_agent
            al3_routers[l3_agent.id] = {}
            for router in auth.network.agent_hosted_routers(l3_agent):
                al3_routers[l3_agent.id][router.id] = router
                hash_router[router.id] = router
            nb_gl_routers += len(al3_routers[l3_agent.id])

        average_l3_by_ag = average(al3_routers)
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        sys.exit(1)

## Get New agent possedant le moins de reseau et dont le reseau n'y est pas deja positionne 
def get_agent_network(agent, asc_agent, agent_net, average_network):
    global log
    try:
        for ag in asc_agent:
            if ag[1] >= average_network:
                print("In %s Can't find a new agent lower or egal to average %d" % (inspect.stack()[0][3],average_network))
                log.warning("In %s Can't find a new agent lower or egal to average %d" % (inspect.stack()[0][3],average_network))
                return None
            if agent != ag[0] and ag[0] not in agent_net:
                return ag[0]
        return None
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1

## Get New agent possedant le moins de routeur 
def get_agent_router(agent, asc_agent, average_router):
    global log
    try:
        for ag in asc_agent:
            if ag[1] >= average_router:
                print("In %s Can't find a new agent lower or egal to average %d" % (inspect.stack()[0][3],average_router))
                log.warning("In %s Can't find a new agent lower or egal to average %d" % (inspect.stack()[0][3],average_router))
                return None
            if agent != ag[0]:
                return ag[0]
        return None
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        return -1
    
## pour un agent on deplace les reseaux sur d'autres agent pour retomber en dessous de la moyenne
def adding_removing_network(auth, agent, average_network):
    global adhcp_nets, hash_net, dryrun, log, nb_net_max, nb_router_max, nb_network, check_action_net
    try:
        asc_agent = pair_list_nb_by_id_asc(adhcp_nets)

        exclude_net = []
        while len(adhcp_nets[agent]) > average_network:
            if os.path.exists(stop_file):
                print("Find file %s : stopping" % stop_file)
                log.error("Find file %s : stopping" % stop_file)
                return -2            
            keys = adhcp_nets[agent].keys()
            if len(keys) == 0:
                return  -1
            net = None
            for n in iter(keys):
                if n not in exclude_net:
                    net = n
            if net is None:
                print("Warning !!! Can't find Network to move")
                log.warning("Warning !!! Can't find Network to move")
                return 0

            if auth.network.get_network(net) is not None:
                agent_net =  get_agent_id_form_network(auth, hash_net[net])
                if len(agent_net) != 2:
                    print("Warning !!! Net %s On only one agent : %s" % (net, " ".join(agent_net)))
                    log.warning("Warning !!! Net %s On only one agent : %s" % (net, " ".join(agent_net)))
                    
                new_agent = get_agent_network(agent, asc_agent, agent_net, average_network)
                if new_agent is None:
                    exclude_net.append(net)
                    continue

                new_agent_state = auth.network.get_agent(new_agent)
                if new_agent_state.is_alive is False:
                    print("Error in adding_removing_network !!! Agent %s/%s state is not alive" % (new_agent, new_agent_state.host))
                    log.error("Error in adding_removing_network !!! Agent %s/%s state is not alive" % (new_agent, new_agent_state.host))
                    return -1

                if nb_net_max != -1 and nb_network >= nb_net_max:
                    break
                nb_network +=1

                print("Adding Net %s to Agent DHCP : %s" % (net, new_agent))
                log.info("Adding Net %s to Agent DHCP : %s" % (net, new_agent))            
                if not dryrun:
                    resp1 = auth.network.add_dhcp_agent_to_network(new_agent, hash_net[net])
                    check_action_net[hash_adhcp[new_agent].host].append(["Adding", "net", net])

                print("Removing Net %s to Agent DHCP : %s" % (net, agent))
                log.info("Removing Net %s to Agent DHCP : %s" % (net, agent))            
                if not dryrun:
                    resp2 = auth.network.remove_dhcp_agent_from_network(agent, hash_net[net])
                    check_action_net[hash_adhcp[agent].host].append(["Removing", "net", net])
                
            adhcp_nets[new_agent][net] = adhcp_nets[agent][net]
            del(adhcp_nets[agent][net])
            asc_agent = pair_list_nb_by_id_asc(adhcp_nets)

        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        sys.exit(1)

## pour un agent on deplace les routeurs sur d'autres agent pour retomber en dessous de la moyenne
def adding_removing_router(auth, agent, average_router):
    global al3_routers, hash_router, dryrun, log, nb_net_max, nb_router_max, nb_router
    try:
        asc_agent = pair_list_nb_by_id_asc(al3_routers)

        exclude_router = []        
        while len(al3_routers[agent]) > average_router:
            if os.path.exists(stop_file):
                print("Find file %s : stopping" % stop_file)
                log.error("Find file %s : stopping" % stop_file)                
                return -2            
            keys = al3_routers[agent].keys()
            if len(keys) == 0:
                return -1
            router = next(iter(keys))
            router = None
            for r in iter(keys):
                if r not in exclude_router:
                    router = r
            if router is None:
                print("Warning !!! Can't find Network to move")
                log.warning("Warning !!! Can't find Network to move")
                return 0
            if auth.network.get_router(router) is not None:
                new_agent = get_agent_router(agent, asc_agent, average_router)
                if new_agent is None:                
                    exclude_router.append(router)
                    continue

                new_agent_state = auth.network.get_agent(new_agent)
                if new_agent_state.is_alive is False:
                    print("Error in adding_removing_router!!! Agent %s/%s state is not alive" % (new_agent, new_agent_state.host))
                    log.error("Error in adding_removing_router !!! Agent %s/%s state is not alive" % (new_agent, new_agent_state.host))
                    return -1
                
                if nb_router_max != -1 and nb_router >= nb_router_max:
                    break
                nb_router +=1
                
                print("Removing Router %s to Agent L3 : %s" % (router, agent))
                log.info("Removing Router %s to Agent L3 : %s" % (router, agent))            
                if not dryrun:
                    resp2 = auth.network.remove_router_from_agent(agent, hash_router[router])
                    check_action_router[hash_al3[agent].host].append(["Removing", "router", router])
                    
                print("Adding Router %s to Agent L3 : %s" % (router, new_agent))    
                log.info("Adding Router %s to Agent L3 : %s" % (router, new_agent))            
                if not dryrun:
                    resp1 = auth.network.add_router_to_agent(new_agent, hash_router[router])
                    check_action_router[hash_al3[new_agent].host].append(["Adding", "router", router])
            al3_routers[new_agent][router] = al3_routers[agent][router]
            del(al3_routers[agent][router])
            asc_agent = pair_list_nb_by_id_asc(al3_routers)
 
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        sys.exit(1)

## On balance les agents les plus charges en reseau 
def balancing_network(auth):
    global adhcp_nets, log, nb_network, nb_net_max
    try:
        average_network = average(adhcp_nets)
        dsc_agent = pair_list_nb_by_id_dsc(adhcp_nets)
        while [ 1 ]:
            if nb_net_max != -1 and nb_network >= nb_net_max:
                break
            if os.path.exists(stop_file):
                print("Find file %s : stopping" % stop_file)
                log.error("Find file %s : stopping" % stop_file)                
                return -2
            if dsc_agent[0][1] <= average_network:
                break
            else:
                ret = adding_removing_network(auth, dsc_agent[0][0], average_network)
                if ret != 0:
                    return -1
            dsc_agent = pair_list_nb_by_id_dsc(adhcp_nets)
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        return -1

## On balance les agents les plus charges en routeur
def balancing_router(auth):
    global al3_routers, log, nb_router_max, nb_router
    try:
        average_router = average(al3_routers)
        dsc_agent = pair_list_nb_by_id_dsc(al3_routers)
        while [ 1 ]:
            if nb_router_max != -1 and nb_router >= nb_router_max:
                break
            if os.path.exists(stop_file):
                print("Find file %s : stopping" % stop_file)
                return -2
            if dsc_agent[0][1] <= average_router:
                break
            else:
                ret = adding_removing_router(auth, dsc_agent[0][0], average_router)
                if ret != 0:
                    return -1
            dsc_agent = pair_list_nb_by_id_dsc(al3_routers)            
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        return -1

## Retourne l'UUID de l'agent DHCP pour le noeud
def get_agent_dhcp_from_node(node):
    global hash_adhcp, log
    try:
        for agent in hash_adhcp.keys():
            if hash_adhcp[agent].host == node:
                return agent
        return None
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        return -1
    
## Retourne l'UUID de l'agent L3 pour le noeud
def get_agent_l3_from_node(node):
    global hash_al3, log
    try:
        for agent in hash_al3.keys():
            if hash_al3[agent].host == node:
                return agent
        return None
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        return -1

## Evacue les reseaux sur les autres agents
def evacuate_network(auth, node):
    global adhcp_nets, hash_net, dryrun, log, nb_net_max, nb_router_max, nb_network, check_action_net
    try:
        average_network = average_less_one(adhcp_nets)
        agent = get_agent_dhcp_from_node(node)
        if agent is None:
            print("Exit Can't find agent DHCP for node %s" % node)
            log.error("Exit Can't find agent DHCP for node %s" % node)            
            return -1
        data_agent = adhcp_nets[agent]
        del(adhcp_nets[agent])

        asc_agent = pair_list_nb_by_id_asc(adhcp_nets)
        
        for net in data_agent.keys():
            if nb_net_max != -1 and nb_network >= nb_net_max:
                break
            if os.path.exists(stop_file):
                print("Find file %s : stopping" % stop_file)
                log.error("Find file %s : stopping" % stop_file)                
                return -2
            if auth.network.get_network(net) is not None:
                agent_net =  get_agent_id_form_network(auth, hash_net[net])
                new_agent = get_agent_network(agent, asc_agent, agent_net, average_network)
                if new_agent is None:                
                    continue
                
                new_agent_state = auth.network.get_agent(new_agent)
                if new_agent_state.is_alive is False:
                    print("Error in evacuate_network !!! Agent %s/%s state is not alive" % (new_agent, new_agent_state.host))
                    log.error("Error in evacuate_network !!! Agent %s/%s state is not alive" % (new_agent, new_agent_state.host))
                    return -1
                
                nb_network +=1            
                print("Adding Net %s to Agent DHCP : %s" % (net, new_agent))
                log.info("Adding Net %s to Agent DHCP : %s" % (net, new_agent))            
                if not dryrun:
                    resp1 = auth.network.add_dhcp_agent_to_network(new_agent, hash_net[net])
                    check_action_net[hash_adhcp[new_agent].host].append(["Adding", "net", net])

                print("Removing Net %s to Agent DHCP : %s" % (net, agent))
                log.info("Removing Net %s to Agent DHCP : %s" % (net, agent))            
                if not dryrun:
                    resp2 = auth.network.remove_dhcp_agent_from_network(agent, hash_net[net])
                    check_action_net[hash_adhcp[agent].host].append(["Removing", "net", net])

            adhcp_nets[new_agent][net] = data_agent[net]
            asc_agent = pair_list_nb_by_id_asc(adhcp_nets)
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        return -1

## Evacue les routeurs sur les autres agents
def evacuate_router(auth, node):
    global al3_routers, hash_router, dryrun, log, nb_net_max, nb_router_max, nb_router
    try:
        average_router = average_less_one(al3_routers)
        agent = get_agent_l3_from_node(node)
        if agent is None:
            print("Exit Can't find agent L3 for node %s" % node)
            log.error("Exit Can't find agent L3 for node %s" % node)            
            return -1
        data_agent = al3_routers[agent]
        del(al3_routers[agent])

        asc_agent = pair_list_nb_by_id_asc(al3_routers)
            
        for router in data_agent.keys():
            if nb_router_max != -1 and nb_router >= nb_router_max:
                break
            if os.path.exists(stop_file):
                print("Find file %s : stopping" % stop_file)
                return -2
            if auth.network.get_router(router) is not None:
                new_agent = get_agent_router(agent, asc_agent, average_router)
                if new_agent is None:                
                    continue

                new_agent_state = auth.network.get_agent(new_agent)
                if new_agent_state.is_alive is False:
                    print("Error in adding_removing_router!!! Agent %s/%s state is not alive" % (new_agent, new_agent_state.host))
                    log.error("Error in adding_removing_router !!! Agent %s/%s state is not alive" % (new_agent, new_agent_state.host))
                    return -1

                nb_router +=1            

                print("Removing Router %s to Agent L3 : %s" % (router, agent))
                log.info("Removing Router %s to Agent L3 : %s" % (router, agent))            
                if not dryrun:
                    resp2 = auth.network.remove_router_from_agent(agent, hash_router[router])
                    check_action_router[hash_al3[agent].host].append(["Removing", "router", router])

                print("Adding Router %s to Agent L3 : %s" % (router, new_agent))
                log.info("Adding Router %s to Agent L3 : %s" % (router, new_agent))            
                if not dryrun:
                    resp1 = auth.network.add_router_to_agent(new_agent, hash_router[router])
                    check_action_router[hash_al3[new_agent].host].append(["Removing", "router", router])                
            al3_routers[new_agent][router] = data_agent[router]
            asc_agent = pair_list_nb_by_id_asc(al3_routers)
        return 0
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        return -1

## Bilan du placements des reseaux et routeurs sur les agents
def check_load():
    global adhcp_nets, al3_routers, log, hash_adhcp, hash_al3
    try:
            print("\n\n")
            log.info("\n\n")            
        
            print("# Network by agent:\n")
            log.info("# Network by agent:\n")            
            asc_agent = pair_list_nb_by_id_asc(adhcp_nets)

            for ag in asc_agent:
                print("Agent: %s/%s # Network : %d" % (ag[0], hash_adhcp[ag[0]].host, ag[1]))
                log.info("Agent: %s/%s # Network : %d" % (ag[0], hash_adhcp[ag[0]].host, ag[1]))                

            print("\n\n# Router by agent:\n")
            log.info("\n\n# Router by agent:\n")            
            asc_agent = pair_list_nb_by_id_asc(al3_routers)

            for ag in asc_agent:
                print("Agent: %s/%s # Router : %d" % (ag[0], hash_al3[ag[0]].host, ag[1]))
                log.info("Agent: %s/%s # Router : %d" % (ag[0], hash_al3[ag[0]].host, ag[1]))                

            print("\n\n")
            log.info("\n\n")            
                
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        sys.exit(1)
            
## Checking namesapce on neutron node
def check_namespace(auth):
    global log, hash_adhcp, hash_al3, check_action_router, check_action_net
    try:
        sleep(30)evacuate_router
        hosts = set()
        for k in hash_adhcp.keys():
            hosts.add(hash_adhcp[k].host)

        for k in hash_al3.keys():
            hosts.add(hash_al3[k].host)

        ipnetns_h = {}
        for h in hosts:
            
            exe = subprocess.Popen(ssh_cmd % h, shell=True, stdout= subprocess.PIPE, stderr=subprocess.STDOUT, executable='/bin/bash')
            ##### recupere les outputs ########
            stdout, stderr = exe.communicate()
            ###### recupere le return code #####
            rc=exe.wait()
            ##### si processus ok on recupere Base lid
            if rc == 0:
                ipnetns_h[h] = str(stdout)

        status = 0
        for h in check_action_net.keys():
            for action in check_action_net[h]:
                dhcp = False
                for s in hash_net[action[2]].subnet_ids:
                    if auth.network.get_subnet(s).is_dhcp_enabled:
                        dhcp = True
                        break
                if dhcp :
                    qdhcp = re.findall("(qdhcp-%s)" % action[2], ipnetns_h[h])
                    if action[0] == "Adding" and len(qdhcp) == 0:
                        print("Missing qdhcp-%s on node %s but was added" % (action[2], h))
                        log.error("Missing qdhcp-%s on node %s but was added" % (action[2], h))
                        status = 1
                    if action[0] == "Removing" and len(qdhcp) != 0:
                        print("Existing qdhcp-%s on node %s but was removed" % (action[2], h))
                        log.error("Existing qdhcp-%s on node %s but was removed" % (action[2], h))
                        status = 1                        

        for h in check_action_router.keys():
            for action in check_action_router[h]:
                qrouter_snat = re.findall("((snat|qrouter)-%s)" % action[2], ipnetns_h[h])
                if action[0] == "Adding" and len(qrouter_snat) != 2:
                    print("Missing qrouter-{uuid}/snat-{uuid} on node {host} but was added".format(uuid=action[2], host=h))
                    log.error("Missing qrouter-{uuid}/snat-{uuid} on node {host} but was added".format(uuid=action[2], host=h))
                    status = 1
                snat = re.findall("(snat-%s)" % action[2], ipnetns_h[h])                    
                if action[0] == "Removing" and len(snat) != 0:
                    print("Existing snat-{uuid} on node {host} but was removed".format(uuid=action[2], host=h))
                    log.error("Existing snat-{uuid} on node {host} but was removed".format(uuid=action[2], host=h))
                    status = 1
        return status
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        return 1
        
def main():
    global dryrun, logdir, log, nb_net_max, nb_router_max
    try:

        # LOG HANDLER
        date = datetime.datetime.today().strftime("%Y%m%d%H%M")
        logfile = "%s/rebalancing_load_%s.log" % (logdir, date)
 
        log = logging.getLogger()
        log.setLevel(logging.INFO)
        fh = logging.FileHandler(logfile)
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
        fh.setFormatter(formatter)
        log.addHandler(fh)

        #### Argument Parser in Python 
        parser = argparse.ArgumentParser(description="Requilibrage de charge des agents/evacuation des routeurs/reseau sur un agent")

        ### Specification du noeud Neutron pour l'evacuation
        parser.add_argument("-n", "--node", action= "store", dest="node", \
                            default=None, \
                            help="Neutron node for evacuate")

        ### Specification du nombe de reseau maximum a evacuer/balancer
        parser.add_argument("--nb_net_max", action= "store", dest="nb_net_max", \
                            default=-1, \
                            help="Nombre de reseaux maximum a evacuer/balancer (default 0:no limit)")

        ### Specification du nombe de routeur maximum a evacuer/balancer
        parser.add_argument("--nb_router_max", action= "store", dest="nb_router_max", \
                            default=-1, \
                            help="Nombre de routeurs maximum a evacuer/balancer (default 0:no limit)")

        ### Action Balancing ou evacuation des reseaux et routeurs
        parser.add_argument("--action", action= "store", dest="action", \
                            default=None, choices = [ "balancing", "evacuate"],\
                            help="action to perform choices balancing or evacuate")

        ### Dry run
        parser.add_argument('--dryrun', dest='dryrun', action='store_true', help="Dry Run option")

        ### Stat Only
        parser.add_argument('--statonly', dest='stat', action='store_true', help="Stat Only option")
                      
        args = parser.parse_args()

        ### recuperation des paramtres
        node = args.node
        action = args.action
        dryrun = args.dryrun
        statonly = args.stat

        nb_net_max = int(args.nb_net_max)
        nb_router_max = int(args.nb_router_max)

        
        ### Check stop file
        if os.path.exists(stop_file):
            log.error("Find file %s : stopping" % stop_file)
            print("Find file %s : stopping" % stop_file)
            sys.exit(1)

        ### Initialisation de la connection
        auth = init_conn()

        ### Etat initial Agent DHCP
        init_data_dhcp(auth)

        ### Etat initial Agent L3        
        init_data_l3(auth)

        ### Check de l'equilibrage au demarrage
        check_load()

        if statonly:
            sys.exit(0)

        ### verfication des arguments
        if action not in ["balancing", "evacuate"]:
            log.error("Syntaxe is Wrong !!! action is not balancing or evacuate Value %s" % action)
            print("Syntaxe is Wrong !!! action is not balancing or evacuate Value %s" % action)
            sys.exit(1)

        if action == "evacuate" and node is None:
            log.error("Syntaxe is Wrong for action evacuate missing Node")
            print("Syntaxe is Wrong for action evacuate missing Node")
            sys.exit(1)

        if action == "evacuate" and "neut-m" not in node:
            log.error("Syntaxe is Wrong !!! action evacuate Wrong node name expecting name containing neut-m")
            print("Syntaxe is Wrong !!! action evacuate Wrong node name expecting name containing neut-m")
            sys.exit(1)
        
        ### Balancing des reseaux et routeurs
        if action == "balancing":
            if balancing_network(auth) != 0:
                log.error("Exit !!! something is wrong in balancing_network")
                print("Exit !!! something is wrong in balancing_network")
                sys.exit(1)
            if balancing_router(auth) != 0:
                log.error("Exit !!! something is wrong in balancing_router")
                print("Exit !!! something is wrong in balancing_router")
                sys.exit(1)

        ### Evacuation des reseaux et routeurs
        if action == "evacuate":
            if evacuate_network(auth, node) != 0:
                log.error("Exit !!! something is wrong in evacuate_network")
                print("Exit !!! something is wrong in evacuate_network")
                sys.exit(1)

            if evacuate_router(auth, node) != 0:
                log.error("Exit !!! something is wrong in evacuate_router")
                print("Exit !!! something is wrong in evacuate_router")
                sys.exit(1)

        ### Etat initial Agent DHCP
        init_data_dhcp(auth, action=False)

        ### Etat initial Agent L3        
        init_data_l3(auth, action=False)

        ### Check de l'equilibrage a la fin
        check_load()        

        ## Check Namespace
        if check_namespace(auth) != 0:
            print("Warning !!! Something is not correct in Namespace")
            log.warning("Warning !!! Something is not correct in Namespace")
            sys.exit(1)

        sys.exit(0)
    except Exception as e:
        print("Error in main Err : %s" % e)
        if log is not None:
            log.error("Error in main Err : %s" % e)
        sys.exit(1)

#################################### MAIN #####################################

if __name__ == '__main__':
    main()


#!/opt/openstackclient-3.9.0/bin/python
 
import openstack, inspect, math
import sys, os, re, threading, queue, argparse

ssh_cmd = 'ssh %s -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" sudo ip netns'

######### FUNCTIONS ############

def get_agent_id_form_router(auth, router):
    return list(map((lambda x : "%s/%s" %(x.id,x.host)), auth.network.routers_hosting_l3_agents(router)))
 
def get_agent_id_form_network(auth, network):
    return list(map((lambda x : "%s/%s" %(x.id,x.host)), auth.network.network_hosting_dhcp_agents(network)))

## Checking namesapce on neutron node
def check_namespace(auth, list_networks, list_routers):
    try:
        agent_dhcp = list(auth.network.agents(agent_type="DHCP agent"))
        hosts = set()
        for k in agent_dhcp:
            hosts.add(k.host)

        agent_l3 = list(auth.network.agents(agent_type="L3 agent"))
        for k in agent_l3:
            hosts.add(k.host)

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
        for n in list_networks:

            agents = list(auth.network.network_hosting_dhcp_agents(n))

            if len(agents) == 0:
                print("Error !!! Network %s is not owned by an agent" % n.id)
                status = 1
                break

            if len(agent) > 2:
                printe("Error !!! Network %s is owned by more than 2 agents" % r.id)
                status = 1
            
            for ag in agents:
                dhcp = False
                for s in n.subnet_ids:
                    if auth.network.get_subnet(s).is_dhcp_enabled:
                        dhcp = True
                        break
                if dhcp :
                    qdhcp = re.findall("(qdhcp-%s)" % n.id, ipnetns_h[ag.host])
                    if len(qdhcp) == 0:
                        print("Missing qdhcp-%s on node %s incoherence between namespace vs Database" % (n.id, ag.host))
                        status = 1

        for r in list_routers:
            agent= list(auth.network.agent_hosted_routers(r))
            if len(agent) == 0:
                print("Error !!! Routeur %s is not owned by an agent" % r.id)
                status = 1
                break
            
            if len(agent) > 1:
                printe("Error !!! Routeur %s is owned by more than one agent" % r.id)
                status = 1
                
            qrouter_snat = re.findall("((snat|qrouter)-%s)" % r.id, ipnetns_h[agent[0].host])
            if len(qrouter_snat) != 2:
                print("Missing qrouter-{uuid}/snat-{uuid} on node {host} inoherence between namespace vs Database".format(uuid=r.id, host=agent[0].host))
                status = 1
        return status
    except Exception as e:
        print("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))
        log.error("Fatal Error in %s Err : %s" % (inspect.stack()[0][3], e))        
        return 1


########### MAIN ################

conn=openstack.connect()
auth = conn.connect_as(username=os.environ["OS_USERNAME"], password=os.environ["OS_PASSWORD"], project_name='admin')
 
list_routers = list(auth.network.routers())
list_networks = list(auth.network.networks())
 
print("Networks:\n\n")
for n in list_networks:
        print ("Network UUID %s Agent DHCP : %s" % (n.id, "   ".join(get_agent_id_form_network(auth,n))))
 
print("\n\nRouter:\n\n")
for r in list_routers:
        print ("Router UUID %s Agent L3 : %s" % (r.id, "   ".join(get_agent_id_form_router(auth,r))))

print("\n\nCheck Namespace on neutron nodes:\n\n")
if check_namespace(auth, list_networks, list_routers) != 0:
    print("Something is Wrong !!")
        

#!/opt/openstackclient-3.9.0/bin/python
 
import openstack, inspect, math
import sys, os, re, threading, queue, argparse
 
def get_agent_id_form_router(auth, router):
    return list(map((lambda x : "%s/%s" %(x.id,x.host)), auth.network.routers_hosting_l3_agents(router)))
 
def get_agent_id_form_network(auth, network):
    return list(map((lambda x : "%s/%s" %(x.id,x.host)), auth.network.network_hosting_dhcp_agents(network)))
 
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

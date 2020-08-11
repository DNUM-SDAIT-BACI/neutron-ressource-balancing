#!/opt/openstackclient-3.9.0/bin/python

import openstack, inspect, math
import sys, os, re, threading, queue, argparse

def get_agent_id_form_network(auth, network):
    return list(map((lambda x : x.id), auth.network.network_hosting_dhcp_agents(network)))

def get_agent_id_form_list(agents):
    return list(map((lambda x : x.id), agents))

conn=openstack.connect()
auth = conn.connect_as(username=os.environ["OS_USERNAME"], password=os.environ["OS_PASSWORD"], project_name='admin')

dhcp_agents = list(auth.network.agents(agent_type="DHCP agent"))

net = list(auth.network.dhcp_agent_hosting_networks(dhcp_agents[0]))

for n in net:
   s1 = get_agent_id_form_network(auth, n)
   s2 = get_agent_id_form_list(dhcp_agents)

   s3 = list(set(s2) - set(s1))
   resp2=auth.network.add_dhcp_agent_to_network(s3[0], n)
   resp1=auth.network.remove_dhcp_agent_from_network(dhcp_agents[0], n)


l3_agents = list(auth.network.agents(agent_type="L3 agent"))
l3=[]
for l3a in l3_agents:
   if "neut-m" in l3a.host:
      l3.append(l3a)

routers = list(auth.network.agent_hosted_routers(l3[0]))

for r in routers:
   resp3=auth.network.add_router_to_agent(l3[1], r)
   resp4=auth.network.remove_router_from_agent(l3[0], r)

routers = list(auth.network.agent_hosted_routers(l3[2]))


resp3=auth.network.add_router_to_agent(l3[0], routers[0])
resp4=auth.network.remove_router_from_agent(l3[2], routers[0])
   



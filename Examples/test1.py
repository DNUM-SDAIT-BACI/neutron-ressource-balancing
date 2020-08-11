#!/opt/openstackclient-3.9.0/bin/python

import openstack, inspect, math
import sys, os, re, threading, queue, argparse

conn=openstack.connect()
auth = conn.connect_as(username=os.environ["OS_USERNAME"], password=os.environ["OS_PASSWORD"], project_name='admin')


dhcp_agents = list(auth.network.agents(agent_type="DHCP agent"))
agent = None
for ag in dhcp_agents:
   if ag.id =="9d1a915d-1e7d-4b33-b594-b511b1009230":
      agent = ag
      break

net = list(auth.network.dhcp_agent_hosting_networks(agent))

#net_uuid=["298396b5-e1b3-4ba8-8bf2-6876b63932c9", "37a3c6c3-4729-421a-97f6-f2ed0740d363", "3cdf4ad7-d0f4-4ea5-af97-828e88306c74", "3d2ce7e8-344b-4300-bad0-a33768ffaa8a", "c9868ec7-dcfe-46a6-b414-0e62b74924ec11" ]
net_uuid=["c9868ec7-dcfe-46a6-b414-0e62b74924ec"]

for n in net:
   if n.id in net_uuid:
      print("Removing UUID net : %s UUID Agent %s" % (agent.id, n.id))
      resp1=auth.network.remove_dhcp_agent_from_network(agent.id, n)

print("Adding UUID net : %s UUID Agent %s" % (n.id, agent.id))      
n = auth.network.get_network("37a3c6c3-4729-421a-97f6-f2ed0740d363")

resp1=auth.network.add_dhcp_agent_to_network(agent.id, n)
      
# print("Adding UUID net : %s UUID Agent %s" % (dhcp_agents[0].id, net[0].id)) 
# resp2=auth.network.add_dhcp_agent_to_network(dhcp_agents[0], net[0])

sys.exit(0)
print("Removing UUID net : %s UUID Agent %s" % (agent.id, net[0].id))
resp1=auth.network.remove_dhcp_agent_from_network(agent.id, net[0])



l3_agents = list(auth.network.agents(agent_type="L3 agent"))
l3=[]
for l3a in l3_agents:
   if "neut-m" in l3a.host:
      l3.append(l3a)

routers = list(auth.network.agent_hosted_routers(l3[0]))

print("Adding UUID Router : %s UUID Agent %s" % (routers[0].id, l3[1].id))
resp3=auth.network.add_router_to_agent(l3[1], routers[0])
print("Removing UUID Router : %s UUID Agent %s" % (routers[0].id, l3[1].id))
resp4=auth.network.remove_router_from_agent(l3[0], routers[0])

print("Adding UUID Router : %s UUID Agent %s" % (routers[0].id, l3[1].id))
resp5=auth.network.add_router_to_agent(l3[0], routers[0])
print("Removing UUID Router : %s UUID Agent %s" % (routers[0].id, l3[1].id))
resp6=auth.network.remove_router_from_agent(l3[1], routers[0])


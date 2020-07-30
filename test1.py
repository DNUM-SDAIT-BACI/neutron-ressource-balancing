#!/opt/openstackclient-3.9.0/bin/python

import openstack, inspect, math
import sys, os, re, threading, queue, argparse

conn=openstack.connect()
auth = conn.connect_as(username=os.environ["OS_USERNAME"], password=os.environ["OS_PASSWORD"], project_name='admin')


dhcp_agents = list(auth.network.agents(agent_type="DHCP agent"))
net = list(auth.network.dhcp_agent_hosting_networks(dhcp_agents[0]))

resp1=auth.network.remove_dhcp_agent_from_network(dhcp_agents[0], net[0])
resp2=auth.network.add_dhcp_agent_to_network(dhcp_agents[0], net[0])


l3_agents = list(auth.network.agents(agent_type="L3 agent"))
l3=[]
for l3a in l3_agents:
   if "neut-m" in l3a.host:
      l3.append(l3a)

routers = list(auth.network.agent_hosted_routers(l3[0]))

resp3=auth.network.add_router_to_agent(l3[1], routers[0])
resp4=auth.network.remove_router_from_agent(l3[0], routers[0])

resp5=auth.network.add_router_to_agent(l3[0], routers[0])
resp6=auth.network.remove_router_from_agent(l3[1], routers[0])

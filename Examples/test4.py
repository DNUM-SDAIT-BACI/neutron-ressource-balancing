#!/opt/openstackclient-3.9.0/bin/python

import openstack, inspect, math
import sys, os, re, threading, queue, argparse

def get_agent_id_form_network(auth, network):
    return list(map((lambda x : x.id), auth.network.network_hosting_dhcp_agents(network)))

def get_agent_id_form_list(agents):
    return list(map((lambda x : x.id), agents))

conn=openstack.connect()
auth = conn.connect_as(username=os.environ["OS_USERNAME"], password=os.environ["OS_PASSWORD"], project_name='admin')

routers = [ "0f00835d-e966-46c8-b85b-949e6f872e64",
            "1905f311-d1c4-4072-87b6-9e85c1e8cdaa",
            "3dd3f9e6-3bfc-442e-ab59-ba0f67b01274",
            "56f5f0a4-b1ab-4d4d-9b9f-4df0cb7beb40",
            "5ccfc9e6-e796-44c6-96ba-e998d874102e",
            "654629e1-1880-4942-9656-8e84efa276d3",
            "7e8af120-d25c-40d2-acb0-8e3a03e95805",
            "9d414124-57f1-4b0f-ba9e-8b1204f978b8",
            "a95425eb-a0b6-4fee-a099-9afd925a0997",
            "b5fec874-0475-49d2-b454-0de0d791ac06",
            "d037fa9c-305d-4642-a2e4-30c71950d04f",
            "d2bdd02e-9953-4d64-a507-9933d12b0746"]


l3_agents = list(auth.network.agents(agent_type="L3 agent"))
l3=[]
for l3a in l3_agents:
   if "neut-m" in l3a.host:
      l3.append(l3a)

   
#routers = list(auth.network.agent_hosted_routers(l3[0]))

for r in routers:
   router = auth.network.get_router(r)

   try:
      agents = list(auth.network.routers_hosting_l3_agents(router))
      print("UUID: %s agents %s" % (r, agents[0].id))   
   except Exception as e:      
      print("XXXX UUID: %s agents %s" % (r, l3[0].id))   
      resp3=auth.network.add_router_to_agent(l3[0], router)

   



# Pré-requis

```
source ~/services.osrc
```

# check_net_rout.py

Affiche les affectations réseaux/agent DHCP 

```
Network UUID 298396b5-e1b3-4ba8-8bf2-6876b63932c9 Agent DHCP : 89b7754d-d549-46d3-ae26-d518dc826006/helion-cp1-neut-m3-mgmt   9d1a915d-1e7d-4b33-b594-b511b1009230/helion-cp1-neut-m2-mgmt
```

Affiche les affectations routeurs/agent L3
```
Router UUID 0f00835d-e966-46c8-b85b-949e6f872e64 Agent L3 : 0b6b6bea-7dae-4b4c-8119-e8071e7c2eeb/helion-cp1-neut-m3-mgmt
```

# ./rebalancing_agents_load.py -h

```
usage: rebalancing_agents_load.py [-h] [-n NODE] [--nb_net_max NB_NET_MAX]
                                  [--nb_router_max NB_ROUTER_MAX]
                                  [--action {balancing,evacuate}] [--dryrun]
                                  [--statonly]

Requilibrage de charge des agents/evacuation des routeurs/reseau sur un agent

optional arguments:
  -h, --help            show this help message and exit
  -n NODE, --node NODE  Neutron node for evacuate
  --nb_net_max NB_NET_MAX
                        Nombre de reseaux maximum a evacuer/balancer (default
                        -1:no limit)
  --nb_router_max NB_ROUTER_MAX
                        Nombre de routeurs maximum a evacuer/balancer (default
                        -1:no limit)
  --action {balancing,evacuate}
                        action to perform choices balancing or evacuate
  --dryrun              Dry Run option
  --statonly            Stat Only option
```

# Fonctionnalitées attendues
## Lot 1
- [ ] Ré-équilibrage de la charge (namespace snat, namespace qdhcp, etc..) lorsque tous les nœuds neutron tournent.

Le script devra inclure les fonctionnalités suivantes : 
*  Pour chacun des nodes neutron, lister les réseaux/routeur présent
*  Calculer la moyenne des réseaux/routers de l'ensemble des nodes
*  Migrer/répartir chacun des ces réseaux/routers sur les nodes n’excédant pas la valeur moyenne de réseaux/routers précédemment calculé
*  En cas d'erreur alors arrêter le script
*  Prévoir un fichier de log permettant le suivis en temps réel des opérations du script


## Lot 2
- [ ] Répartition de la charge d'un nœud neutron vers les 8 autres nœuds avant un redémarrage.

Le script devra inclure les fonctionnalités suivantes : 
*  Pour chacun des nodes neutron, lister les réseaux/routeur présent
*  Calculer la moyenne des réseaux/routers de l'ensemble des nodes
*  Migrer/répartir les réseaux/routers du node à redémarrer vers les autres nodes en veillant à ne pas excéder la valeur moyenne de réseaux/routers précédemment calculé
*  En cas d'erreur alors arrêter le script
*  Prévoir un fichier de log permettant le suivis en temps réel des opérations du script


# Contraintes 
- [ ] L'outil doit intégrer un arrêt sur erreur pour ne pas casser la totalité des réseaux.
- [ ] L'outil sera développé en Python afin de s'appuyer sur les api OpenStack et optimisé les échanges.
  - Utilisation d'un seul token keystone
  - Utilisation directe des endpoints nova, neutron, etc...
- [ ] Prévoir le multithreading
- [ ] Les réseaux neutron étant associés à deux agents DHCP, il faudra bien vérifier que ce soit le cas avant et après l’opération de migration/répartition 

# Qualification
- [ ] Qualification Lot 1
- [ ] Qualification Lot 2

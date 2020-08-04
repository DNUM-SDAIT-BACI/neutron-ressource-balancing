# Fonctionnalitées attendues
## Lot 1
- [ ] Ré-équilibrage de la charge des objets Openstack "Network" et "routeur" (namespace snat, namespace qdhcp, namespace qrouter) lorsque tous les nœuds neutron tournent.

Le script devra inclure les fonctionnalités suivantes : 
*  Pour chacun des nodes neutron, lister les réseaux/routeur présent
*  Calculer la moyenne des réseaux/routers de l'ensemble des nodes
*  Migrer/répartir chacun des ces réseaux/routers sur les nodes n’excédant pas la valeur moyenne de réseaux/routers précédemment calculé
*  En cas d'erreur alors arrêter le script
  * Un fichier d'arrêt est créé à la première erreur
*  il est possible de limiter le nombre d'objet à ré-équilibrer (par réseau ou par routeur)
*  un fichier de log permettant le suivis en temps réel des opérations du script
*  Vérification des actions réalisés (objets bien déplacé)
  *  Un sleep de 30 secondes est en place pour permettre de laisser le temps au namespace d'être créé. Il faudra peut être adapter ce temps.
*  exécution en mode "dry-run"

## Lot 1 Bis
- [ ] Mise en place de thread pour le script du lot 1

Par défaut, 1 seul thread est créé


## Lot 2
- [ ] Répartition de la charge d'un nœud neutron vers les 8 autres nœuds avant un redémarrage.

Le même script est utilisable avec l'option balancing/evacuate

# Contraintes 
- [x] L'outil doit intégrer un arrêt sur erreur pour ne pas casser la totalité des réseaux.
- [x] L'outil sera développé en Python afin de s'appuyer sur les api OpenStack et optimisé les échanges.
  - Utilisation d'un seul token keystone
  - Utilisation directe des endpoints nova, neutron, etc...
- [x] Prévoir le multithreading
- [ ] Les réseaux neutron étant associés à deux agents DHCP, il faudra bien vérifier que ce soit le cas ~~avant~~ et après l’opération de migration/répartition 

## Lot 3
Un troisième script permet de lister les affectations des objets Openstack réél.

- [x] Vérification de la base de donnée
- [ ] Vérification des namespaces


# Qualification
- [ ] Qualification Lot 1
- [ ] Qualification Lot 2

# Problèmes identifiés
- Le bug connu sur la suppression de router (boucle infinie). Corrigé en 5.0.8.
- il arrive que des namespace qdhcp ne soit pas à la cible.

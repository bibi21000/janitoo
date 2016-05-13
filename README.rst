.. image:: https://travis-ci.org/bibi21000/janitoo.svg?branch=master
    :target: https://travis-ci.org/bibi21000/janitoo
    :alt: Travis status

.. image:: https://circleci.com/gh/bibi21000/janitoo.png?style=shield
    :target: https://circleci.com/gh/bibi21000/janitoo
    :alt: Circle status

.. image:: https://coveralls.io/repos/bibi21000/janitoo/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/bibi21000/janitoo?branch=master
    :alt: Coveralls results

.. image:: https://img.shields.io/imagelayers/image-size/bibi21000/janitoo_base/latest.svg
    :target: https://hub.docker.com/r/bibi21000/janitoo_base/
    :alt: Docker size

.. image:: https://img.shields.io/imagelayers/layers/bibi21000/janitoo_base/latest.svg
    :target: https://hub.docker.com/r/bibi21000/janitoo_base/
    :alt: Docker size

.. image:: https://badges.gitter.im/bibi21000/janitoo.svg
    :alt: Join the chat at https://gitter.im/bibi21000/janitoo
    :target: https://gitter.im/bibi21000/janitoo?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

==================
Welcome to Janitoo
==================

Not another Home Automation software ... a full protocol

A video of presentation is available on youtube : https://www.youtube.com/watch?v=S3Gqj32sJ-Q

Documentation
=============
You can browse online documentation here : https://bibi21000.github.io/janitoo/.


What is Janitoo
===============

Network
-------

A network in Janitoo is holded by Mosquitto.
It use the Dynamic Home Configuration Protocol to allow nodes to communicate each other.

Each node on a network has its own HADD : xxxx/yyyy where 0 <= x,y <=9.

Nodes with an HADD ending in 0000 (ie 1234/0000) are called controllers.
They are responsible of the nodes in their subnetwork (ie 1234/0001).


Supervisors
-----------

Supervisors maintains a "map" of the network.
There are of 2 types : primaries and secondaries.

The primary will serve configuration parameters for the nodes.

The network is managed by a finish state machine. Only the fail mode can be considered as usuable.


Controllers, nodes and values
-----------------------------

A node holds values.

There is many genres of values :
 - system : needed by the protocol itself.
 - config : used to configure nodes and values
 - basic : base values. Used by nodes themselves and andvanced users.
 - user : for common users
 - command : to launch advanced commands ie pairing

Examples of nodes/values

- an ups is a node (janitoo_nut). battery_level, upsstate, ... are values
- a vacuum is a node (janitoo_roomba). baterry_level, dock state but also clean, dock commands are values
- an rrd source is a node
- an arduino is a node

...

If your familiar with openzwave and the zwave protocol, janitoo is a kind of zwave over mqtt.

Bus and components
------------------

Ths bus and components are the developpers API of the nodes in Janitoo.

A bus can hold components and is associated to a controller
A component is mapped to a node.
The map is done using a configuration file

Multi_hardware
--------------
Due to its low memory footprint, janitoo can be used on many hardwares :

- Arduino mega. Actually, it's impossible to install it on an Uno.
- Raspberry : the 0 will be supported (python). The janitoo_hostsensor with 7 nodes and about 100 values only takes 3% of memory and 7% of cpu on a Raspberry B.

...


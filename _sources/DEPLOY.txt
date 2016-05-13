==================
Welcome to Janitoo
==================


Deploying Janitoo
=================

Choose yours hosts
------------------

 - mqtt server
 - mysql server or sqlite
  ...

Mosquitto
---------

This is the mqtt server.

.. code:: bash

    sudo apt-get install mosquitto


By default, it will listen on all interfaces. Auth is actually not fully implmented.

On every computers
------------------

Create a directory for janitoo. It is highly recommended to put it in /opt/janitoo.

.. code:: bash

    sudo mkdir /opt/janitoo

    sudo chown me:me /opt/janitoo

    cd /opt/janitoo

    for dir in src home log run etc init; do
        mkdir $dir
    done


Go to the src directory :

.. code:: bash

    cd src


Clone janitoo repository from github

.. code:: bash

    git clone https://github.com/bibi21000/janitoo.git


Create a link to the makefile helper:

.. code:: bash

    ln -s janitoo/makefile.all Makefile


You can now "develop" janitoo. It use a lot of entry-points, so it MUST be developed:

.. code:: bash

    make develop module=janitoo

Installing mosquito
-------------------

.. code:: bash

    make clone module=janitoo_mosquitto

Installing suplementary modules
-------------------------------

You are now ready to install modules. You don't need to install all of them on the same host.

For example, if you want to monitor cpu speed and voltage on a raspberry, you must install :

.. code:: bash

    make clone module=janitoo_hostsensor_raspberry


Your admin password may be asked by sudo. Sometimes, it's necessary to install debian (or unduntu) dependencies.

If you want to monitor disks and processes, you can install the extension:

.. code:: bash

    make clone module=janitoo_hostsensor_psutil

On a laptop, you can use the lmsensor extension:

.. code:: bash

    make clone module=janitoo_hostsensor_lmsensor

You can now create you init script :

.. code:: bash

    cd /opt/janitoo/init

    vim jnt_hostsensor.sh

        #!/bin/bash
        JNT_HOME=/opt/janitoo/src
        SVC_NAME=raspberry

        cd ${JNT_HOME}/janitoo_${SVC_NAME}/src/scripts/ && ./jnt_${SVC_NAME} -c ${JNT_HOME}/janitoo_${SVC_NAME}/src/config/janitoo_${SVC_NAME}.conf $*

And your

    ln -s /opt/janitoo/src/janitoo_hostsensor/script

Actually, the protocol is not fully developped, so you must create nodes in your configuration files.


Support
=======

You can ask about support to google the google group : https://groups.google.com/d/forum/janitoo-dev


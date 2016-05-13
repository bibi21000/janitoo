:orphan:

==================================
Installing janitoo from repository
==================================

Create the directory
sudo mkdir /opt/janitoo
sudo chown sebastien:sebastien /opt/janitoo
mkdir /opt/janitoo/log

Install the needed tools
========================
You must install git and make to retrieve sources of janitoo and
openzwave.

On a debian like distribution :

.. code-block:: bash

    sudo apt-get install -y git make

Create the directory structure
==============================

.. code-block:: bash

    sudo mkdir /opt/janitoo
    sudo chown `whoami` /opt/janitoo
    mkdir /opt/janitoo/src
    mkdir /opt/janitoo/etc
    mkdir /opt/janitoo/log
    mkdir /opt/janitoo/home
    mkdir /opt/janitoo/run

Get sources of janitoo
======================

Change to janitoo source directory :

.. code-block:: bash

    cd /opt/janitoo/src

You are now ready to download sources of janitoo :

.. code-block:: bash

    git clone https://github.com/bibi21000/janitoo

Create a link to the makefile :

.. code-block:: bash

    ln -s janitoo/Makefile.all Makefile

Install modules
===============

Create the list of needed modules in Makefile.local (in src directory):

.. code-block:: bash

    vim Makefile.local

Add needed modules in a variable SUBMODULES, the order is important. For example :

.. code-block:: bash

    SUBMODULES = janitoo_nosetests janitoo janitoo_factory \
     janitoo_thermal janitoo_layouts \
     janitoo_hostsensor janitoo_hostsensor_psutil janitoo_hostsensor_raspberry \
     janitoo_raspberry janitoo_raspberry_dht janitoo_raspberry_gpio \
     janitoo_raspberry_i2c janitoo_raspberry_i2c_bmp janitoo_raspberry_i2c_pca9685 \
     janitoo_raspberry_1wire janitoo_raspberry_camera \
     janitoo_raspberry_lcdchar janitoo_raspberry_ili9341 \
     janitoo_raspberry_fishtank

.. code-block:: bash

    vim Makefile.local

Clone modules:

.. code-block:: bash

    make clone-all

Install dependencies
====================
You need some tools (a c++ compiler, headers dir python, ...) to build janitoo and openzwave library.

On a debian like distribution :

.. code-block:: bash

    sudo make repo-deps

For non-debian (fedora, ...), you can retrieve the packages needed in the Makefile.

Configure your server
=====================

In his section, we will install the fishtank server on your rapsberry.

.. code-block:: bash

    cp /opt/janitoo/src/janitoo_raspberry_fishtank/src/config/janitoo_raspberry_fishtank.conf /opt/janitoo/etc/janitoo_fishtank.conf


Update the configuration file

.. code-block:: bash

    vim /opt/janitoo/etc/janitoo_fishtank.conf

You need some tools (a c++ compiler, headers dir python, ...) to build janitoo and openzwave library.

You can now start, stop your server :

.. code-block:: bash

    jnt_fishtank -c /opt/janitoo/etc/janitoo_fishtank.conf start

    jnt_fishtank -c /opt/janitoo/etc/janitoo_fishtank.conf status

    jnt_fishtank -c /opt/janitoo/etc/janitoo_fishtank.conf stop

You can also start the server in foreground (for development) :

.. code-block:: bash

    jnt_fishtank -c /opt/janitoo/etc/janitoo_fishtank.conf start

    jnt_fishtank -c /opt/janitoo/etc/janitoo_fishtank.conf status

    jnt_fishtank -c /opt/janitoo/etc/janitoo_fishtank.conf stop

Start your server at boot
=========================

You can also start your server at boot

.. code-block:: bash

    sudo cp /opt/janitoo/src/janitoo_raspberry_fishtank/src/scripts/jnt_fishtank.init /etc/init.d/jnt_fishtank

    sudo update-rc.d jnt_fishtank defaults


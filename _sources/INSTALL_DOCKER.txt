:orphan:

==============================
Installing janitoo from docker
==============================


Install docker.io
=================



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


Get sources of janitoo
===============================
You are now ready to download sources of janitoo :

.. code-block:: bash

    git clone https://github.com/bibi21000/janitoo

The previous command will create a copy of the official repository on your
computer in a directory called janitoo.


Install dependencies
====================
You need some tools (a c++ compiler, headers dir python, ...) to build janitoo and openzwave library.

On a debian like distribution :

.. code-block:: bash

    sudo make repo-deps

For non-debian (fedora, ...), you can retrieve the packages needed in the Makefile.


Update and build process
========================
Go to the previously created directory

.. code-block:: bash

    cd janitoo

The following command will update your local repository to the last release
of janitoo and openzwave.

.. code-block:: bash

    make update

When update process is done, you can compile sources

.. code-block:: bash

    make build

Or if you have already build janitoo in a previous installation, you can use the clean target to remove old builds.

.. code-block:: bash

    sudo make clean


Installation
============
You can now ready to install the eggs using the following command :

.. code-block:: bash

    sudo make install

You can also remove janitoo using :

.. code-block:: bash

    sudo make uninstall


Running tests
=============
You can launch the regression tests using :

.. code-block:: bash

    make tests

Keep in mind that the tests will "play" with your nodes : switching on and off, dimming, adding and removing scenes, ...


About the repositroy
====================
This repository is a development tool, so it might be "unstable" ... yeah, sometimes it won't build anymore :)

If you want to retrieve the last "good" commit, look at https://github.com/bibi21000/janitoo/commits/master.
The commits names "Auto-commit for docs" are done after the full process : build + test + docs, so they might be "working" (almost for me).

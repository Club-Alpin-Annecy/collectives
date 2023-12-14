Deployment for production
==========================

This document is meant to help the deployment of the collectives application on an host provider
for production. 

However, don't hesitate to adapt scripts and definitions to your own needs. These 
indications are merely hints on how to install it. Especially, it might not be updated and
become obsolete in the future.

.. warning::
  Please note that you have to keep an informed eye  while performing thoses indications. 
  CAF Annecy or the collectives project cannot and will not be held accountable for any 
  dommages or costs that may occurs from this how to.

Three solutions are suggested:

* The fancy and expensive `Kubernetes installation`_
* The effective and cheap `Microk8s installation`_
* The robust and hard to maintain `Bare metal installation`_


Kubernetes installation
-------------------------

Managed Kubernetes is the method of choice, but might be more expensive than microk8s or 
bare metal. However, it should be more resilient and more scalable.

For this How To, we will explain an OVH installation. But you can deploy the app on other
providers.

Installation
.............

Requirements : `kubectl <https://kubernetes.io/fr/docs/tasks/tools/install-kubectl/>`_ and 
`helm <https://helm.sh/docs/intro/install/>`_ 

#. Go to OVH and purchase a Public Cloud Managed Kubernetes. The cheapest with one node is OK.
#. Setup ``collectives.yaml`` by copy ``deployment/k8s/collectives.exemple.yaml`` with your 
   hostnames and secrets: look for the 4 ``--to-be-replaced--``
#. Download the ``kubeconfig.yml`` file, and set it up for kubectl and helm
#. Install `cert-manager <https://help.ovhcloud.com/csm/en-public-cloud-kubernetes-install-cert-manager?id=kb_article_view&sysparm_article=KB0049779>`_ 
   and `nginx ingress <https://help.ovhcloud.com/csm/fr-public-cloud-kubernetes-secure-nginx-ingress-cert-manager?id=kb_article_view&sysparm_article=KB0055580>`_ : 

   .. code-block:: bash

     helm repo add jetstack https://charts.jetstack.io
     helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
     helm repo update 
     helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --set installCRDs=true
     helm -n ingress-nginx install ingress-nginx ingress-nginx/ingress-nginx --create-namespace

#. Get the external IP with ``kubectl get svc -n ingress-nginx ingress-nginx-controller`` and setup your DNS record
#. Apply ``collectives.yaml`` : ``kubectl apply -f collectives.yaml`` 
#. After a while, the website should be available on ``https://your-hostname.com``

.. warning::
  The file ``collectives.yaml`` contains secrets and it should not be shared publicly!!


Microk8s installation
----------------------

Less expensive than a managed Kubernetes, it still leverages Kubernetes flexibility.
It can be installed on any VPS with Ubuntu.

Installation
.............

Requirement : an ssh client to connect to the VPS

#. Purchase a VPS at any host provider. Install it with latest Ubuntu version.
#. Update your DNS record with the VPS IP.
#. Setup ``collectives.yaml`` by copy ``deployment/k8s/collectives.example.yaml`` with your 
   hostnames and secrets: look for the 4 ``--to-be-replaced--``. Your file will be referred as
   ``collectives.yaml``
#. Remove from ``collectives.yaml`` the lines with ``storageClassName`` 
#. Install ``microk8s``:
   
   .. code-block:: bash

    sudo snap install microk8s --classic
    sudo microk8s enable ingress
    sudo microk8s enable cert-manager
    sudo microk8s enable hostpath-storage

#. Apply collectives.yaml ``sudo microk8s kubectl apply -f collectives.yaml`` 
#. After a while, the website should be available on ``https://your-hostname.com``

.. warning::
  The file ``collectives.yaml`` contains secrets and it should not be shared publicly!!


Note on Kubernetes deployment structure
------------------------------------------

`nginx <https://www.nginx.com/>`_ is used as an ingress.

It automatically loads a `Let's Encrypt <https://letsencrypt.org/fr/>`_ free certificate for TLS.

It works with the `collectives <https://hub.docker.com/repository/docker/cafannecy/collectives/general>`_ docker
published by the `CAF Annecy <https://www.cafannecy.fr/>`_ on DockerHub.

Data persistence is achieved by :

- block storages for files
- a pod of `MariaDB <https://mariadb.org/>`_ for database, itself using block storage.

No auto-scaling, replication, or load balancing is configured.

For more resilience, a managed mariadb/mysql is the way to go.

Bare metal installation
--------------------------

This deployment works, but is less modern than a Kubernetes and is the same costs as a microk8s.

Installation
..............
For development, you can run `FLASK_APP=collectives:create_app flask run`. 
However, it is not the recommended method for production environment.

You can choose any production method you like, however, you can use waitress
behind an nginx for SSL offloading. Waitress can be install with a pip
`pip install waitress`, and a systemd service be created easily by adding
`deployment/systemd/collectives.service` into `/etc/systemd/system`. In this
case, please edit the file to update user and directory.

Configuration
..............
Flask and DB related configuration should be in `instance/config.py`. This file 
should be readable only by flask user (chmod 600). 

However, more basic configuration that can be put into DB should be put
`collectives/configuration.yaml`. File architecture is loaded at every reboot
into db. Then, it can be modified by a site technician into the HMI. 

Database
.........
For production, a more robust database than the default sqlite is recommended.
pymysql is recommended for its full python compatibility.

``SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/db_name'``
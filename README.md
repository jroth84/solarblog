# ansible-saedyn-stack
Ansible scripts for creating EC2 configs for SAE and Building Dynamics

# Usage notes

This repo houses the Terraform scripts and Ansible scripts that were used to create the new "saedyn" EC2 instance that will run SAE as well as Building Dynamics.

## Playbook organization
Refer to the README.md file in [Ameresco/ansible-dsr-stack ](https://github.com/Ameresco/ansible-dsr-stack). The organization here is identical, except that a separate /inventories directory was created to clarify which hosts were being referred to in the playbooks.

## Quick intro for using Ansible

Major steps for using ansible to deploy are shown below. These are demonstrated on the test servers as indicated by the "--inventory=inventories/inventory-dev" flag.

##### 0) First, after setting up your ec2 instance update the APT list and upgrade the distro. You've logged in as the 'ubuntu' user so you must use the sudo command.

    sudo apt update; sudo apt upgrade; sudo su -; sync sync reboot

##### 1) The next command executes the init_config.yml file, to create the users and groups for the applications.


    ansible-playbook --inventory=inventories/inventory-dev -vv --private-key=~/Downloads/jrothsolar-deployer.pem ./init_config.yml

##### 2) Next, the webanddatabase.yml file is the workhorse for setting up the rest of the configuration.

It contains 3 sets of roles, starting with the combination of the common and webserver roles. So to start,  make sure only the "apply webserver config to server" is activated, leaving the remaining 2 commented out. Then, comment out the first block and uncomment the "apply database config to server" section. Finally, leave only the "apply redis config to server" section uncommented to install the redis server.

    ansible-playbook --inventory=inventories/inventory-dev -vv --private-key=~/Downloads/jrothsolar-deployer.pem ./webanddatabase.yml

##### 3) Notice that the "webserver" role imports 5 different yaml files in doing its work.

Therefore, if you wish to only execute certain of these, then comment out the `import_tasks:` directive that has already been successfully executed, as shown below for an example.

    ansible-playbook --inventory=inventories/inventory-dev -vv --private-key=~/Downloads/jrothsolar-deployer.pem ./webanddatabase.yml

Contents of the main.yml file of the "webserver" role:

    - import_tasks: security.yml
    # - import_tasks: nginx.yml
    - import_tasks: git.yml <
    - import_tasks: dependencies.yml
    # - import_tasks: wsgi.yml

##### 4) Here are some miscellaneous commands that can be used with Ansible:

* Here's how to start the playbook at a specific task:

```
ansible-playbook --inventory=inventories/inventory-dev -vv --private-key=~/Downloads/jrothsolar-deployer.pem ./webanddatabase.yml --start-at-task="Create symlinks for Systemd config files for dynamics"
```

* Using the new inventory file organization:

```
ansible-playbook --inventory=inventories/inventory-prod -vv --private-key=~/Downloads/jroth-ameresco-uswest2.pem ./webanddatabase.yml --tags="ssl" --limit=webserver --list-hosts
```

Explanation:

    --limit: limit the command to a specific host in the specified group.
    --list-hosts: use this to see a list of hosts that would be affected by your playbook before you actually run it.
    --tags="ssl": execute only those tasks having the tag "ssl"
     -vv: two levels of verboseness; can go to 4.
* And a great switch to use if you're not sure of what a playbook will do, is the `--check` switch. When ansible-playbook is executed with `--check` it will not make any changes on remote systems. 

##### 5) Following are manual steps taken during the creation of this aws instance for the EBS volumes. The steps were *not* handled by Ansible, hence I made note of all of them here.

Here is web1 (from Rackspace) block storage status for guidance in setting up EBS storage on AWS:

```
    root@web-server-i:~# df -h
```
    Filesystem                   Size  Used Avail Use% Mounted on
    udev                         7.4G  8.0K  7.4G   1% /dev
    tmpfs                        1.5G  472K  1.5G   1% /run
    /dev/xvda1                    50G   41G  6.3G  87% /        ===============> go 100G
    none                         4.0K     0  4.0K   0% /sys/fs/cgroup
    none                         5.0M     0  5.0M   0% /run/lock
    none                         7.4G   16K  7.4G   1% /run/shm
    none                         100M     0  100M   0% /run/user
    /dev/xvdb                     50G   20G   28G  42% /var/lib/postgresql ====> go 75 Gb
    /dev/xvdc                     74G   22G   49G  32% /srv/.bricks
    localhost:/shared_datastore   74G   22G   49G  32% /srv/shared_datastore ==> go 75 Gb


Have run 'terraform apply' by now, and here is the rest of what is needed:

A reference guide is in the [AWS documentation archive](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-using-volumes.html_)

As root, type `lsblk`, and hit ENTER 

And out pukes this to stdout:


    NAME        MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
    loop0         7:0    0  89.1M  1 loop /snap/core/8039
    loop1         7:1    0    18M  1 loop /snap/amazon-ssm-agent/1480
    nvme1n1     259:0    0   100G  0 disk 
    └─nvme1n1p1 259:1    0   100G  0 part /
    nvme0n1     259:2    0 139.7G  0 disk 
    nvme2n1     259:3    0   100G  0 disk 
    nvme3n1     259:4    0   100G  0 disk

Then, confirm that there is no file system on any of the last 2 devices, which are the 2 100Gb EBS volumes we created. (The 139Gb device is the one given for free)

    sudo file -s /dev/nvme2n1
    /dev/nvme2n1: data

    sudo file -s /dev/nvme3n1
    /dev/nvme3n1: data

Both commands just show 'data', meaning a file system has to be created.

Next, the following sequence of commands creates ext4 file systems on these EBS volumes:

```bash
sudo mkfs -t ext4 /dev/nvme2n1
sudo mkfs -t ext4 /dev/nvme3n1
sudo mkdir /data
sudo mount /dev/nvme2n1 /data
sudo mkdir /srv/shared_datastore
sudo mount /dev/nvme3n1 /srv/shared_datastore
sudo cp /etc/fstab /etc/fstab.orig
```

Next, execute the `lsblk` command to get the UUIDs of the new devices.
```
ubuntu@ip-10-0-101-215:~$ sudo lsblk -o +UUID
```
    NAME        MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT                  UUID
    loop0         7:0    0  89.1M  1 loop /snap/core/8039 
    loop1         7:1    0    18M  1 loop /snap/amazon-ssm-agent/1480 
    nvme1n1     259:0    0   100G  0 disk
    └─nvme1n1p1 259:1    0   100G  0 part /                           ec61fe50-1758-4214-9855-6d2b1e007ec1
    nvme0n1     259:2    0 139.7G  0 disk
    nvme2n1     259:3    0   100G  0 disk /data                       061fa568-095a-44ab-a8ec-f8b4beb25140
    nvme3n1     259:4    0   100G  0 disk /srv/shared_datastore       8a8a20eb-ee2f-424e-8e6d-e63568dcbd4f


With the UUID data, perform this next procedure for modifying the /etc/fstab file (just change the UUID field to one of the correct values as revealed above) The text below is from the AWS doco:

>Add the following entry to /etc/fstab to mount the device at the specified mount point. The fields are the UUID value returned by blkid (or lsblk for Ubuntu 18.04), the mount point, the file system, and the recommended file system mount options. For more information, see the manual page for fstab (run man fstab).

```
UUID=aebf131c-6957-451e-8d34-ec978d9581ae  /data  xfs  defaults,nofail  0  2
```

__Note__

If you ever boot your instance without this volume attached (for example, after moving the volume to another instance), the `nofail` mount option enables the instance to boot even if there are errors mounting the volume. Debian derivatives, including Ubuntu versions earlier than 16.04, must also add the nobootwait mount option.

Next, backed up databases from web1.seldera.com, as the 'postgres' user:

```postgresql
pg_dumpall --host 104.239.207.126 --port 5432 --username "postgres" --no-password --globals-only > pg_globals.sql

pg_dump dynamics --host 104.239.207.126 --port 5432 --username "postgres" --no-password --verbose --format custom --file "/data/pg_backup/dynamics_db"

pg_dump handprint --host 104.239.207.126 --port 5432 --username "postgres" --no-password --verbose --format custom --file "/data/pg_backup/handprint_db"

pg_dump sae --host 104.239.207.126 --port 5432 --username "postgres" --no-password --verbose --format custom --file "/data/pg_backup/sae_db"
```


On the new saedyn box, restored the globals first, then restored the 3 databases after creating a password (\password) for the "postgres" user in psql (letmein);  used the following commands from the 'ubuntu' user:

```
sudo -u postgres psql -f /data/pg_backup/pg_globals.sql postgres
sudo -u postgres pg_restore -h localhost -p 5432 -C -d postgres --verbose /data/pg_backup/handprint_db
sudo -u postgres pg_restore -h localhost -p 5432 -C -d postgres --verbose /data/pg_backup/dynamics_db
sudo -u postgres pg_restore -h localhost -p 5432 -C -d postgres --verbose  /data/pg_backup/sae_db
```

Next, brought over the /opt config files from web1.

Steps are:
As root on the new ec2 instance:

```bash
cd /opt
mkdir /sae
chown sae:sae /opt/sae/
cd /opt/sae
scp -P 22022 root@web1.seldera.com:/opt/sae/sae.config.json .
```

Did the same for the dynamics /opt file, which is called `/opt/seldera/dynamics/dynamics.config.json`

Brought over the static.tar file from web1.

First, created it like this (note that the . is significant in these commands):

As dynamics user on the `web1` Rackspace instance: 
```bash
cd ~/dynamics/static
tar cvf static.tar .
```

then brought it over to ec2, again as dynamics user in the `~/dynamics/static directory`.

```bash
scp -P 22022 dynamics@web1.seldera.com:~/dynamics/static/static.tar .
```

and untarred it with: `tar xvf static.tar`

As sae user on the `web1` Rackspace instance: 
```bash
cd ~/sae/static
tar cvf sae_static.tar .
```

then brought it over to ec2, again as sae user in the `~sae/static directory`.

```bash
scp -P 22022 sae@web1.seldera.com:~/sae/static/sae_static.tar .
```

In dynamics, copied over all of the report templates, which are soft-linked to a directory on the `/srv/shared_datastore` mount point:
```
report_templates -> /srv/shared_datastore/static_files/dynamics/report_templates/
```
```bash
scp -P 22022 dynamics@web1.seldera.com:/srv/shared_datastore/static_files/dynamics/report_templates/report_templates.tar .
```

In dynamics, created the directory for the maintenance_off.html file and copied it over from web1 on Rackspace.


Approaching the finish line, worked with Deepak to cure the missing symbol problems in ujson.

In dynamics, copied over all of the image files from the shared_datastore

On the web1 instance, I did this:

```bash
~/dynamics/static/seldera/Content/images$ tar cvf buildings.tar buildings/*
```
And then from the ec2 instance, I did this, as the dynamics user:

```bash
cd /srv/shared_datastore/static_files/dynamics
scp -P 22022 -pv dynamics@web1.seldera.com:~/dynamics/static/seldera/Content/images/buildings.tar .
tar xvf buildings.tar
```

Copied over the axis_logs/ directory from web1

on web1:
```bash
cd /srv/shared_datastore/static_files/dynamics/axis_logs
tar cvf axis_logs.tar *
```

on 10.0.101.213 as dynamics user:
```bash
cd /srv/shared_datastore/static_files/dynamics
mkdir axis_logs
cd axis_logs
scp -P 22022 -pv dynamics@web1.seldera.com:/srv/shared_datastore/static_files/dynamics/axis_logs/axis_logs.tar .
```

Copied over all of the report instances from sae

 On web1, as sae user:

```bash
cd /srv/shared_datastore/static_files/sae/reports
tar --ignore-failed-read -cvf reports.tar *
```
Some directories were corrupt, so use of the `--ignore-failed-read` switch allowed it to complete...

On 10.0.101.213 as sae user:

```bash 
cd /srv/shared_datastore/static_files/sae/reports
scp -P 22022 -pv sae@web1.seldera.com:/srv/shared_datastore/static_files/sae/reports/reports.tar .
```
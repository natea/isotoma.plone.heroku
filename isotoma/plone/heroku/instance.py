# Copyright 2011 Isotoma Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This is a startup command to run from Procfile (on heroku or foreman)
# It will let you run a Zope instance from virtualenv, too.
# It expects to be passed a port to listen to on the command line
# It expects that DATABASE_URL is available.

import os, sys, optparse, urlparse

# Zope configuration to poke variables into when web process is started
rel_storage = """
    <relstorage>
      <postgresql>
        dsn dbname='%(db_name)s' user='%(db_username)s' host='%(db_host)s' password='%(db_password)s'
      </postgresql>
    </relstorage>
    """

temp_storage = """
    <temporarystorage>
      name temporary storage for main data
    </temporarystorage>
    container-class Products.TemporaryFolder.TemporaryContainer
    """

zope_conf = """
instancehome %(instance_home)s

<http-server>
  address %(port)s
</http-server>

%%import relstorage
<zodb_db main>
    %(storage)s

    mount-point /
</zodb_db>

<zodb_db temporary>
    <temporarystorage>
      name temporary storage for sessioning
    </temporarystorage>
    mount-point /temp_folder
    container-class Products.TemporaryFolder.TemporaryContainer
</zodb_db>

"""

class Instance(object):

    def __init__(self, rootdir=None, port=None, database_url=None):
        if rootdir:
            self.rootdir = rootdir
        else:
            self.rootdir = os.getcwd()
        
        # Figure out directory structure based on where this script is
        self.instance_home = os.path.join(self.rootdir, "zope")
        self.conf_file = os.path.join(self.instance_home, "etc", "zope.conf")
        self.zdctl = os.path.join(self.rootdir, "bin", "zopectl")

        # If there is no zope instance, create one
        if not os.path.exists(self.conf_file):
            os.system("%(root_dir)s/bin/mkzopeinstance -u admin:admin -d %(instance_home)s" % dict(root_dir=self.rootdir, instance_home=self.instance_home))

        # Generate a zope conf for '/' - either RelStorage or temporarystorage
        if 'VCAP_SERVICES' in os.environ:
            import json
            vcap_services = json.loads(os.environ['VCAP_SERVICES'])
            # XXX: avoid hardcoding here
            srv = vcap_services['postgresql-8.4'][0]
        #    srv = vcap_services['mysql-5.1'][0]
            cred = srv['credentials']

            port = cred['port']

            storage = rel_storage % dict(
                db_username = cred['user'],
                db_password = cred['password'],
                db_host = cred['hostname'],
                db_name = cred['name'],
                )

        else:
            storage = temp_storage

        # Rewrite zope.conf according to the port we are supposed to listen on and storage backend
        
        if 'VMC_APP_PORT' in os.environ:
            port = int(os.getenv('VMC_APP_PORT', '8000'))
        else:
            port = self.port
            
        open(self.conf_file, "w").write(zope_conf % dict(
            instance_home=self.instance_home,
            port=port,
            storage=storage,
            ))


    def run(self, *args):
        # Actually start zope - think i might prefer to import things by hand here long term
        os.environ["INSTANCE_HOME"] = self.instance_home
        os.environ["PYTHON"] = sys.executable
        os.execvp(self.zdctl, [self.zdctl, "-C", self.conf_file] + list(args))




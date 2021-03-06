# Authors:
#     Endi S. Dewata <edewata@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright (C) 2013 Red Hat, Inc.
# All rights reserved.
#

from __future__ import absolute_import
import os
import shutil
from lxml import etree

import pki
import pki.server.upgrade


class ReplaceRandomNumberGenerator(
        pki.server.upgrade.PKIServerUpgradeScriptlet):

    def __init__(self):
        super(ReplaceRandomNumberGenerator, self).__init__()
        self.message = 'Replace random number generator'

        self.context_xml = '/usr/share/pki/%s/webapps/%s/META-INF/context.xml'
        self.parser = etree.XMLParser(remove_blank_text=True)

    def upgrade_subsystem(self, instance, subsystem):

        meta_inf = os.path.join(
            instance.base_dir,
            'webapps',
            subsystem.name,
            'META-INF')
        self.backup(meta_inf)

        self.create_meta_inf(instance, meta_inf)

        context_xml = os.path.join(meta_inf, 'context.xml')
        self.backup(context_xml)

        self.create_context_xml(
            instance,
            self.context_xml % (subsystem.name, subsystem.name),
            context_xml)

        document = etree.parse(context_xml, self.parser)

        self.add_manager(document)
        if instance.version >= 10:
            self.update_authenticator(document)
        else:
            self.remove_authenticator(document)
            self.remove_realm(document)

        with open(context_xml, 'wb') as f:
            document.write(f, pretty_print=True, encoding='utf-8')

    def upgrade_instance(self, instance):

        self.update_root_context_xml(instance)
        self.update_pki_context_xml(instance)

    def update_root_context_xml(self, instance):

        meta_inf = os.path.join(
            instance.base_dir,
            'webapps',
            'ROOT',
            'META-INF')
        self.backup(meta_inf)

        self.create_meta_inf(instance, meta_inf)

        context_xml = os.path.join(meta_inf, 'context.xml')
        self.backup(context_xml)

        self.create_context_xml(
            instance,
            self.context_xml % ('server', 'ROOT'),
            context_xml)

        document = etree.parse(context_xml, self.parser)

        self.add_manager(document)

        with open(context_xml, 'wb') as f:
            document.write(f, pretty_print=True, encoding='utf-8')

    def update_pki_context_xml(self, instance):

        meta_inf = os.path.join(
            instance.base_dir,
            'webapps',
            'pki',
            'META-INF')
        self.backup(meta_inf)

        self.create_meta_inf(instance, meta_inf)

        context_xml = os.path.join(meta_inf, 'context.xml')
        self.backup(context_xml)

        self.create_context_xml(
            instance,
            self.context_xml % ('server', 'pki'),
            context_xml)

        document = etree.parse(context_xml, self.parser)

        self.add_manager(document)

        with open(context_xml, 'wb') as f:
            document.write(f, pretty_print=True, encoding='utf-8')

    def create_meta_inf(self, instance, path):

        if not os.path.exists(path):
            os.mkdir(path)

        os.chown(path, instance.uid, instance.gid)
        os.chmod(path, 0o770)

    def create_context_xml(self, instance, source, target):

        if not os.path.exists(target):
            shutil.copyfile(source, target)

        os.chown(target, instance.uid, instance.gid)
        os.chmod(target, 0o660)

    def add_manager(self, document):

        # Find existing manager
        context = document.getroot()
        manager = context.find('Manager')

        if manager is None:

            # Create new manager
            manager = etree.SubElement(context, 'Manager')

        # Update manager's attributes
        manager.set('secureRandomProvider', 'Mozilla-JSS')
        manager.set('secureRandomAlgorithm', 'pkcs11prng')

    def update_authenticator(self, document):

        context = document.getroot()
        valves = context.findall('Valve')
        authenticator = None

        # Find existing authenticator
        for valve in valves:
            className = valve.get('className')
            if className != 'com.netscape.cms.tomcat.SSLAuthenticatorWithFallback':
                continue

            # Found existing authenticator
            authenticator = valve
            break

        if authenticator is None:

            # Create new authenticator'
            authenticator = etree.SubElement(authenticator, 'Valve')
            authenticator.set('className',
                              'com.netscape.cms.tomcat.SSLAuthenticatorWithFallback')

        # Update authenticator's attributes
        authenticator.set('secureRandomProvider', 'Mozilla-JSS')
        authenticator.set('secureRandomAlgorithm', 'pkcs11prng')

    def remove_authenticator(self, document):

        context = document.getroot()
        valves = context.findall('Valve')

        for valve in valves:
            className = valve.get('className')
            if className != 'com.netscape.cms.tomcat.SSLAuthenticatorWithFallback':
                continue
            context.remove(valve)

    def remove_realm(self, document):

        context = document.getroot()
        realms = context.findall('Realm')

        for realm in realms:
            className = realm.get('className')
            if className != 'com.netscape.cms.tomcat.ProxyRealm':
                continue
            context.remove(realm)

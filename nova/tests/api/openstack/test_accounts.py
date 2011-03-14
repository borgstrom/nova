# Copyright 2010 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import json

import stubout
import webob

import nova.api
import nova.api.openstack.auth
from nova import context
from nova import flags
from nova import test
from nova.auth.manager import User
from nova.tests.api.openstack import fakes


FLAGS = flags.FLAGS
FLAGS.verbose = True


def fake_init(self):
    self.manager = fakes.FakeAuthManager()


def fake_admin_check(self, req):
    return True


class AccountsTest(test.TestCase):
    def setUp(self):
        super(AccountsTest, self).setUp()
        self.stubs = stubout.StubOutForTesting()
        self.stubs.Set(nova.api.openstack.accounts.Controller, '__init__',
                       fake_init)
        self.stubs.Set(nova.api.openstack.accounts.Controller, '_check_admin',
                       fake_admin_check)
        fakes.FakeAuthManager.clear_fakes()
        fakes.FakeAuthDatabase.data = {}
        fakes.stub_out_networking(self.stubs)
        fakes.stub_out_rate_limiting(self.stubs)
        fakes.stub_out_auth(self.stubs)

        self.allow_admin = FLAGS.allow_admin_api
        FLAGS.allow_admin_api = True
        fakemgr = fakes.FakeAuthManager()
        joeuser = User('guy1', 'guy1', 'acc1', 'fortytwo!', False)
        superuser = User('guy2', 'guy2', 'acc2', 'swordfish', True)
        fakemgr.add_user(joeuser.access, joeuser)
        fakemgr.add_user(superuser.access, superuser)
        fakemgr.create_project('test1', joeuser)
        fakemgr.create_project('test2', superuser)

    def tearDown(self):
        self.stubs.UnsetAll()
        FLAGS.allow_admin_api = self.allow_admin
        super(AccountsTest, self).tearDown()

    def test_get_account(self):
        req = webob.Request.blank('/v1.0/accounts/test1')
        res = req.get_response(fakes.wsgi_app())
        res_dict = json.loads(res.body)

        self.assertEqual(res_dict['account']['id'], 'test1')
        self.assertEqual(res_dict['account']['name'], 'test1')
        self.assertEqual(res_dict['account']['manager'], 'guy1')
        self.assertEqual(res.status_int, 200)

    def test_account_delete(self):
        req = webob.Request.blank('/v1.0/accounts/test1')
        req.method = 'DELETE'
        res = req.get_response(fakes.wsgi_app())
        self.assertTrue('test1' not in fakes.FakeAuthManager.projects)
        self.assertEqual(res.status_int, 200)

    def test_account_create(self):
        body = dict(account=dict(description='test account',
                              manager='guy1'))
        req = webob.Request.blank('/v1.0/accounts/newacct')
        req.headers["Content-Type"] = "application/json"
        req.method = 'PUT'
        req.body = json.dumps(body)

        res = req.get_response(fakes.wsgi_app())
        res_dict = json.loads(res.body)

        self.assertEqual(res.status_int, 200)
        self.assertEqual(res_dict['account']['id'], 'newacct')
        self.assertEqual(res_dict['account']['name'], 'newacct')
        self.assertEqual(res_dict['account']['description'], 'test account')
        self.assertEqual(res_dict['account']['manager'], 'guy1')
        self.assertTrue('newacct' in
                        fakes.FakeAuthManager.projects)
        self.assertEqual(len(fakes.FakeAuthManager.projects.values()), 3)

    def test_account_update(self):
        body = dict(account=dict(description='test account',
                              manager='guy2'))
        req = webob.Request.blank('/v1.0/accounts/test1')
        req.headers["Content-Type"] = "application/json"
        req.method = 'PUT'
        req.body = json.dumps(body)

        res = req.get_response(fakes.wsgi_app())
        res_dict = json.loads(res.body)

        self.assertEqual(res.status_int, 200)
        self.assertEqual(res_dict['account']['id'], 'test1')
        self.assertEqual(res_dict['account']['name'], 'test1')
        self.assertEqual(res_dict['account']['description'], 'test account')
        self.assertEqual(res_dict['account']['manager'], 'guy2')
        self.assertEqual(len(fakes.FakeAuthManager.projects.values()), 2)

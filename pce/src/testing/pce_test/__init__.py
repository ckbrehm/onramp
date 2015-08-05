"""Unit testing and testing environment setup for OnRamp PCE.

Exports:
    setup: Setup the testing environment.
    pce_url: Build the full URL for the resource at a specified endpoint.
    pce_post: Execute a POST request to a given endpoint with given params.
    pce_get: Execute a GET request to a given endpoint with given params.
    ModulesTest: Unit tests for the PCE modules resource.
    JobsTest: Unit tests for the PCE jobs resource.
    ClusterTest: Unit tests for the PCE cluster resource.
"""
import json
import os
import requests
import shutil
import time
import unittest

from configobj import ConfigObj
from validate import Validator

from PCE import pce_root
from PCE.tools.jobs import JobState
from PCE.tools.modules import ModState

def setup():
    """Setup the testing environment."""
    global onramp_ini
    global test_ini

    onramp_ini = ConfigObj('../../onramp_pce_config.ini',
                           configspec='../onramp_config.inispec')
    onramp_ini.validate(Validator())
    test_ini = ConfigObj('test_pce_config.ini',
                         configspec='test_pce_config.inispec')
    test_ini.validate(Validator())

def pce_url(endpoint):
    """Build the full URL for the resource at the specified endpoint.

    Args:
        enpoint (str): Endpoint of the resource reqested.
    """
    return ('http://%s:%d/%s' % (onramp_ini['server']['socket_host'],
                                 onramp_ini['server']['socket_port'],
                                 endpoint))

def pce_get(endpoint, **kwargs):
    """Execute a GET to the specified endpoint.

    Args:
        enpoint (str): Endpoint of the resource reqested.

    Kwargs: Keys/vals encode as JSON and send with request.
    """
    return requests.get(pce_url(endpoint), params=kwargs)

def pce_post(endpoint, **kwargs):
    """Execute a POST to the specified endpoint.

    Args:
        enpoint (str): Endpoint of the resource reqested.

    Kwargs: Keys/vals encode as JSON and send with request.
    """
    return requests.post(pce_url(endpoint), data=json.dumps(kwargs),
                         headers={'content-type': 'application/json'})

def pce_put(endpoint, **kwargs):
    """Execute a PUT to the specified endpoint.

    Args:
        enpoint (str): Endpoint of the resource reqested.

    Kwargs: Keys/vals encode as JSON and send with request.
    """
    return requests.put(pce_url(endpoint), data=json.dumps(kwargs),
                        headers={'content-type': 'application/json'})

def pce_delete(endpoint, **kwargs):
    """Execute a DELETE to the specified endpoint.

    Args:
        enpoint (str): Endpoint of the resource reqested.

    Kwargs: Keys/vals encode as JSON and send with request.
    """
    return requests.delete(pce_url(endpoint), data=json.dumps(kwargs),
                        headers={'content-type': 'application/json'})


class PCEBase(unittest.TestCase):
    def setUp(self):
        self.ret_dir = os.getcwd()
        os.chdir(pce_root)
        self.source_dir = '../modules'
        self.mod_state_dir = 'src/state/modules'
        self.job_state_dir = 'src/state/jobs'
        self.install_dir = 'modules'
        self.avail_mods = ['template', 'mpi-ring', 'pi']

        def not_hidden(x):
            return not x.startswith('.')

        time.sleep(2)
        for name in os.listdir(self.install_dir):
            shutil.rmtree('%s/%s' % (self.install_dir, name))
        for name in filter(not_hidden, os.listdir(self.mod_state_dir)):
            os.remove('%s/%s' % (self.mod_state_dir, name))
        for name in filter(not_hidden, os.listdir(self.job_state_dir)):
            os.remove('%s/%s' % (self.job_state_dir, name))

    def tearDown(self):
        os.chdir(self.ret_dir)

    def check_json(self, d, good=False):
        self.assertIsNotNone(d)
        self.assertIn('status_code', d.keys())
        self.assertIn('status_msg', d.keys())

        if good:
            self.assertEqual(d['status_code'], 0)
            self.assertEqual(d['status_msg'], 'Success')

class ModulesTest(PCEBase):
    __test__ = False
    def verify_mod_install(self, id, name):
        with ModState(id) as mod_state:
            temp_path = os.path.join(pce_root, self.install_dir)
            installed_path = os.path.join(temp_path, '%s_%s' %(name, id))
            temp_path = os.path.join(pce_root, self.source_dir)
            source_path = os.path.normpath(os.path.join(temp_path, name))

            self.assertEqual(mod_state['mod_id'], id)
            self.assertEqual(mod_state['mod_name'], name)
            self.assertEqual(mod_state['state'], 'Installed')
            self.assertIsNone(mod_state['error'])
            self.assertEqual(mod_state['installed_path'], installed_path)
            self.assertEqual(mod_state['source_location']['type'], 'local')
            self.assertEqual(mod_state['source_location']['path'], source_path)

    def verify_avail_mod(self, mod):
        src_dir_root = os.path.normpath(os.path.abspath(self.source_dir))
        self.assertEqual(mod['source_location'],
                         {'type': 'local',
                          'path': os.path.join(src_dir_root, mod['mod_name'])})
        self.assertEqual(mod['state'], 'Available')
        self.assertIsNone(mod['installed_path'])
        self.assertIsNone(mod['error'])
        self.assertIsNone(mod['mod_id'])

    def test_GET(self):
        template_path = os.path.normpath(os.path.join(pce_root,
                                                      '../modules/template'))
        mpi_ring_path = os.path.normpath(os.path.join(pce_root,
                                                      '../modules/mpi-ring'))
        location = {
            'type': 'local',
            'path': template_path
        }

        installed_mods = {
            1: {
                'mod_id': 1,
                'mod_name': 'template',
                'source_location': {
                    'type': 'local',
                    'path': template_path
                }
            },
            2: {
                'mod_id': 2,
                'mod_name': 'template',
                'source_location': {
                    'type': 'local',
                    'path': template_path
                }
            },
            3: {
                'mod_id': 3,
                'mod_name': 'mpi-ring',
                'source_location': {
                    'type': 'local',
                    'path': mpi_ring_path
                }
            },
            4: {
                'mod_id': 4,
                'mod_name': 'mpi-ring',
                'source_location': {
                    'type': 'local',
                    'path': mpi_ring_path
                }
            }
        }

        mod_state_files = filter(lambda x: not x.startswith('.'),
                                 os.listdir(self.mod_state_dir))
        self.assertEqual(mod_state_files, [])

        # Check installed mods. Should be empty.
        r = pce_get('modules/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)
        self.assertListEqual(d['modules'], [])

        # Check available mods. Should be shipped modules only.
        r = pce_get('modules/', state='Available')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)
        self.assertEqual(len(d['modules']), len(self.avail_mods))
        for mod in d['modules']:
            self.assertIn(mod['mod_name'], self.avail_mods)
            self.verify_avail_mod(mod)

        # Install some mods.
        for k in installed_mods.keys():
            r = pce_post('modules/', **installed_mods[k])
            self.assertEqual(r.status_code, 200)
            d = r.json()
            self.check_json(d)
            self.assertEqual(d['status_code'], 0)
            self.assertEqual(d['status_msg'], 'Checkout initiated')
        time.sleep(10)

        # Get installed mods.
        r = pce_get('modules/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)
        self.assertEqual(len(d['modules']), len(installed_mods.keys()))
        rxd_mods = {mod['mod_id']: mod for mod in d['modules']}
        self.assertEqual(len(rxd_mods.keys()), len(installed_mods.keys()))

        # Verify each mod has proper attrs and that attrs match result rxd
        # on GET modules/.
        install_dir = os.path.normpath(os.path.join(pce_root, self.install_dir))
        for k in installed_mods.keys():
            install_path = os.path.join(
                install_dir, '%s_%s' % (installed_mods[k]['mod_name'], k)
            )
            r = pce_get('modules/%d/' % k)
            self.assertEqual(r.status_code, 200)
            d = r.json()
            self.check_json(d, good=True)
            mod = d['module']
            self.assertEqual(mod['mod_id'], k)
            self.assertEqual(mod['mod_name'], installed_mods[k]['mod_name'])
            self.assertEqual(mod['source_location'],
                             installed_mods[k]['source_location'])
            self.assertEqual(mod['state'], 'Installed')
            self.assertEqual(mod['installed_path'], install_path)
            self.assertIsNone(mod['error'])
            self.assertEqual(mod, rxd_mods[k])

        # Bad URL
        r = pce_get('modules/45/99/')
        self.assertEqual(r.status_code, 404)

    def test_POST(self):
        missing_msg_prefix = ('An invalid value or no value was received for the '
                              'following required parameter(s): ')

        template_path = os.path.normpath(os.path.join(pce_root,
                                                      '../modules/template'))
        location = {
            'type': 'local',
            'path': template_path
        }

        # Good post of new mod
        r = pce_post('modules/', mod_id=3, mod_name='template',
                     source_location=location)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Checkout initiated')

        # Good post of 2nd new mod
        r = pce_post('modules/', mod_id=4, mod_name='template',
                     source_location=location)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Checkout initiated')

        # Verify stored state for new mods
        time.sleep(10)
        self.verify_mod_install(3, 'template')
        self.verify_mod_install(4, 'template')

        # Attempt to post with already existing id
        r = pce_post('modules/', mod_id=3, mod_name='template',
                     source_location=location)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Checkout initiated')
        self.verify_mod_install(3, 'template')

        # Attempt to post with already existing id, but different mod name
        r = pce_post('modules/', mod_id=3, mod_name='mpi-ring',
                     source_location=location)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Checkout initiated')
        self.verify_mod_install(3, 'template')

        # Attempt with bad source type
        location['type'] = 'bad'
        r = pce_post('modules/', mod_id=5, mod_name='template',
                     source_location=location)
        self.assertEqual(r.status_code, 400)

        # Attempt with bad source path
        location['type'] = 'local'
        location['path'] = os.path.normpath(
                            os.path.join(pce_root, '../modules/bad_path'))
        r = pce_post('modules/', mod_id=5, mod_name='template',
                     source_location=location)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Checkout initiated')
        time.sleep(10)
        with ModState(5) as mod_state:
            self.assertEqual(mod_state['mod_id'], 5)
            self.assertEqual(mod_state['mod_name'], 'template')
            self.assertEqual(mod_state['state'], 'Checkout failed')
            self.assertEqual(mod_state['error'],
                             'Source path %s does not exist' % location['path'])
            self.assertIsNone(mod_state['installed_path'])
            self.assertEqual(mod_state['source_location']['type'], 'local')
            self.assertEqual(mod_state['source_location']['path'], location['path'])
        
        # Reattempt previous with good source path, ensure mod state gets
        # updated
        location['path'] = template_path
        r = pce_post('modules/', mod_id=5, mod_name='template',
                     source_location=location)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Checkout initiated')
        time.sleep(10)
        self.verify_mod_install(5, 'template')

        # Attempt deploy that should work
        r = pce_post('modules/5/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Deployment initiated')
        mod_path = os.path.normpath(os.path.join(pce_root,
                                                 'modules/template_5'))
        time.sleep(10)
        with ModState(5) as mod_state:
            self.assertEqual(mod_state['state'], 'Module ready')
            self.assertIsNone(mod_state['error'])
            self.assertEqual(mod_state['source_location']['type'], 'local')
            self.assertEqual(mod_state['source_location']['path'],
                             location['path'])
            self.assertEqual(mod_state['installed_path'], mod_path)
            self.assertEqual(mod_state['mod_id'], 5)
            self.assertEqual(mod_state['mod_name'], 'template')

        # Re-attempt deploy that already happened.
        r = pce_post('modules/5/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Deployment initiated')
        mod_path = os.path.normpath(os.path.join(pce_root,
                                                 'modules/template_5'))
        time.sleep(10)
        with ModState(5) as mod_state:
            self.assertEqual(mod_state['state'], 'Module ready')
            self.assertIsNone(mod_state['error'])
            self.assertEqual(mod_state['source_location']['type'], 'local')
            self.assertEqual(mod_state['source_location']['path'],
                             location['path'])
            self.assertEqual(mod_state['installed_path'], mod_path)
            self.assertEqual(mod_state['mod_id'], 5)
            self.assertEqual(mod_state['mod_name'], 'template')

        # Attempt deployment of non-existent mod_id.
        r = pce_post('modules/15/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -2)
        self.assertEqual(d['status_msg'], 'Module 15 not installed')
        mod_path = os.path.normpath(os.path.join(pce_root,
                                                 'modules/template_15'))

        # Attempt with missing mod_id
        r = pce_post('modules/', mod_name='testname',
                     source_location={'type':0, 'path':'test/path'})
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('mod_id', missing_params)

        # Attempt with missing mod_name
        r = pce_post('modules/', mod_id=3,
                     source_location={'type': 'local', 'path':'test/path'})
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('mod_name', missing_params)

        # Attempt with missing source_location
        r = pce_post('modules/', mod_id=3, mod_name='testname')
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('source_location', missing_params)

        # Attempt with missing source_location['type']
        r = pce_post('modules/', mod_id=3, mod_name='testname',
                     source_location={'path':'test/path'})
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('[source_location]type', missing_params)

        # Attempt with missing source_location['path']
        r = pce_post('modules/', mod_id=3, mod_name='testname',
                     source_location={'type': 'local'})
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('[source_location]path', missing_params)

        # Attempt with empty source_location
        r = pce_post('modules/', mod_id=3, mod_name='testname', source_location={})
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('[source_location]type', missing_params)
        self.assertIn('[source_location]path', missing_params)

        # Attempt with missing mod_id, mod_name, and source_location['type']
        r = pce_post('modules/', source_location={'path':'test/path'})
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('mod_id', missing_params)
        self.assertIn('mod_name', missing_params)
        self.assertIn('[source_location]type', missing_params)

        # Attempt with none of the required params
        r = pce_post('modules/')
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('mod_id', missing_params)
        self.assertIn('mod_name', missing_params)
        self.assertIn('source_location', missing_params)

        # Attempt with bad URL
        r = pce_post('modules/1/1/')
        self.assertEqual(r.status_code, 404)

    def test_PUT(self):
        r = pce_put('modules/')
        self.assertEqual(r.status_code, 404)

        r = pce_put('modules/1/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)

        r = pce_put('modules/1/1/')
        self.assertEqual(r.status_code, 404)

    def test_DELETE(self):
        r = pce_delete('modules/')
        self.assertEqual(r.status_code, 404)

        r = pce_delete('modules/1/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)

        r = pce_delete('modules/1/1/')
        self.assertEqual(r.status_code, 404)


class JobsTest(PCEBase):
    __test__ = False
    def setUp(self):
        super(JobsTest, self).setUp()

        template_path = os.path.normpath(os.path.join(pce_root,
                                                      '../modules/template'))
        location = {
            'type': 'local',
            'path': template_path
        }

        # Install and deploy a module for use
        r = pce_post('modules/', mod_id=1, mod_name='template',
                     source_location=location)
        self.assertEqual(r.status_code, 200)
        time.sleep(3)
        r = pce_post('modules/1/')
        time.sleep(3)

    def verify_launch(self, job_id, mod_id, username, run_name,
                      script_should_exist=True):
        with JobState(job_id) as job_state:
            self.assertEqual(job_state['job_id'], job_id)
            self.assertEqual(job_state['mod_id'], mod_id)
            self.assertEqual(job_state['state'], 'Scheduled')
            self.assertEqual(job_state['username'], username)
            self.assertEqual(job_state['run_name'], run_name)
            self.assertTrue(isinstance(job_state['scheduler_job_num'], int))
            self.assertIsNone(job_state['error'])

        with ModState(mod_id) as mod_state:
            mod_name = '%s_%d' % (mod_state['mod_name'], mod_id)

        folders = (username, mod_name, run_name)
        run_dir = os.path.join(pce_root, 'users/%s/%s/%s' % folders)
        self.assertTrue(os.path.isdir(run_dir))
        script_exists = os.path.isfile(os.path.join(run_dir, 'script.sh'))
        if script_should_exist:
            self.assertTrue(script_exists)
        else:
            self.assertFalse(script_exists)

    def check_job(self, job, username='testuser', job_id=1, error=None,
                  state='Done', run_name='testrun1', mod_id=1):
        keys = job.keys()
        self.assertIn('username', keys)
        self.assertIn('job_id', keys)
        self.assertIn('error', keys)
        self.assertIn('scheduler_job_num', keys)
        self.assertIn('state', keys)
        self.assertIn('run_name', keys)
        self.assertIn('mod_id', keys)
        self.assertEqual(job['username'], username)
        self.assertEqual(job['job_id'], job_id)
        self.assertEqual(job['error'], error)
        self.assertEqual(job['state'], state)
        self.assertEqual(job['run_name'], run_name)
        self.assertEqual(job['mod_id'], mod_id)

    def test_GET(self):
        # Launch a job
        r = pce_post('jobs/', mod_id=1, job_id=1, username='testuser',
                     run_name='testrun1')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Job launched')
        time.sleep(3)
        self.verify_launch(1, 1, 'testuser', 'testrun1')

        r = pce_get('jobs/1/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)
        self.assertIn('job', d.keys())
        self.check_job(d['job'], state='Postprocessing')

        time.sleep(2)
        r = pce_get('jobs/1/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)
        self.assertIn('job', d.keys())
        self.check_job(d['job'])
        self.assertIn('mod_status_output', d['job'].keys())

        r = pce_get('jobs/1/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)
        self.assertIn('job', d.keys())
        self.check_job(d['job'])

        r = pce_get('jobs/')
        self.assertEqual(r.status_code, 404)

        r = pce_get('jobs/45/99/')
        self.assertEqual(r.status_code, 404)

    def test_POST(self):
        missing_msg_prefix = ('An invalid value or no value was received for the '
                              'following required parameter(s): ')

        mod_state_files = filter(lambda x: not x.startswith('.'),
                                 os.listdir(self.mod_state_dir))
        self.assertEqual(mod_state_files, ['1'])
        job_state_files = filter(lambda x: not x.startswith('.'),
                                 os.listdir(self.job_state_dir))
        self.assertEqual(job_state_files, [])

        # Good post to jobs/
        r = pce_post('jobs/', mod_id=1, job_id=1, username='testuser',
                     run_name='testrun1')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Job launched')

        # Second good post to jobs/
        r = pce_post('jobs/', mod_id=1, job_id=2, username='testuser',
                     run_name='testrun2')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Job launched')

        # Verify stored state for launched jobs
        time.sleep(10)
        self.verify_launch(1, 1, 'testuser', 'testrun1')
        self.verify_launch(2, 1, 'testuser', 'testrun2')

        # Post to jobs/ with previously posted attrs
        run_dir = os.path.join(pce_root, 'users/testuser/template_1/testrun1')
        os.remove(os.path.join(run_dir, 'script.sh'))
        os.remove(os.path.join(run_dir, 'output.txt'))
        time.sleep(5)
        r = pce_post('jobs/', mod_id=1, job_id=1, username='testuser',
                     run_name='testrun1')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], 0)
        self.assertEqual(d['status_msg'], 'Job launched')

        # Verify stored state for relaunched job
        time.sleep(10)
        self.verify_launch(1, 1, 'testuser', 'testrun1',
                           script_should_exist=False)

        r = pce_post('jobs/', job_id=1, username='testuser')
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('mod_id', missing_params)

        r = pce_post('jobs/', mod_id=1, username='testuser')
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('job_id', missing_params)

        r = pce_post('jobs/', mod_id=1, job_id=1)
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('username', missing_params)

        r = pce_post('jobs/', mod_id=1)
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('job_id', missing_params)
        self.assertIn('username', missing_params)

        r = pce_post('jobs/', job_id=1)
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('mod_id', missing_params)
        self.assertIn('username', missing_params)

        r = pce_post('jobs/', username='testuser')
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('mod_id', missing_params)
        self.assertIn('job_id', missing_params)

        r = pce_post('jobs/')
        self.assertEqual(r.status_code, 400)
        d = r.json()
        self.check_json(d)
        self.assertEqual(d['status_code'], -8)
        self.assertTrue(d['status_msg'].startswith(missing_msg_prefix))
        missing_params = d['status_msg'].split(missing_msg_prefix)[1].split(', ')
        self.assertIn('mod_id', missing_params)
        self.assertIn('job_id', missing_params)
        self.assertIn('username', missing_params)

        r = pce_post('jobs/45/')
        self.assertEqual(r.status_code, 404)

    def test_PUT(self):
        r = pce_put('jobs/')
        self.assertEqual(r.status_code, 404)

        r = pce_put('jobs/1/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)

        r = pce_put('jobs/1/1/')
        self.assertEqual(r.status_code, 404)

    def test_DELETE(self):
        r = pce_delete('jobs/')
        self.assertEqual(r.status_code, 404)

        r = pce_delete('jobs/1/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)

        r = pce_delete('jobs/1/1/')
        self.assertEqual(r.status_code, 404)


class ClusterTest(PCEBase):
    __test__ = False
    def test_GET(self):
        r = pce_get('cluster/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.check_json(d, good=True)

        r = pce_get('cluster/1/')
        self.assertEqual(r.status_code, 404)

    def test_POST(self):
        r = pce_post('cluster/')
        self.assertEqual(r.status_code, 405)

        r = pce_post('cluster/1/')
        self.assertEqual(r.status_code, 405)

    def test_PUT(self):
        r = pce_put('cluster/1/')
        self.assertEqual(r.status_code, 405)

        r = pce_put('cluster/1/')
        self.assertEqual(r.status_code, 405)

    def test_DELETE(self):
        r = pce_delete('cluster/1/')
        self.assertEqual(r.status_code, 405)

        r = pce_delete('cluster/1/')
        self.assertEqual(r.status_code, 405)


class ModuleJobFlowTest(PCEBase):
    def setUp(self):
        super(ModuleJobFlowTest, self).setUp()
        self.testmodule_path = os.path.join(pce_root, '../modules/testmodule')
        self.testmodule_path = os.path.normpath(self.testmodule_path)
        shutil.rmtree(self.testmodule_path, ignore_errors=True)
        time.sleep(2)
        shutil.copytree(os.path.join(pce_root, 'src/testing/testmodule'),
                        self.testmodule_path)

    def tearDown(self):
        super(ModuleFlowTest, self).tearDown()
        shutil.rmtree(self.testmodule_path, ignore_errors=True)

    def test_module_job_flow(self):
        location = {
            'type': 'local',
            'path': self.testmodule_path
        }

        # Launch against non-existant module.
        pce_post('jobs/', mod_id=1, job_id=1, username='testuser',
               run_name='testrun1')
        job_no_mod_response = pce_get('jobs/1/')

        # Checkout.
        pce_post('modules/', mod_id=1, mod_name='testmodule',
               source_location=location)
        mod_installing_response = pce_get('modules/1/')

        # Launch against module currently being installed.
        pce_post('jobs/', mod_id=1, job_id=1, username='testuser',
               run_name='testrun1')
        job_mod_not_installed_response = pce_get('jobs/1/')

        # Let install finish.
        time.sleep(10)
        mod_installed_response = pce_get('modules/1/')

        # Launch against module installed but not deployed.
        pce_post('jobs/', mod_id=1, job_id=1, username='testuser',
               run_name='testrun1')
        job_mod_not_deployed_response = pce_get('jobs/1/')

        # Deploy.
        pce_post('modules/1/')
        mod_deploying_response = pce_get('modules/1/')

        # Laucnh agains module currently being deployed.
        pce_post('jobs/', mod_id=1, job_id=1, username='testuser',
               run_name='testrun1')
        job_mod_not_deployed_response = pce_get('jobs/1/')

        # Let deploy finish.
        time.sleep(10)
        mod_deployed_response = pce_get('modules/1/')

        # Launch against ready module.
        pce_post('jobs/', mod_id=1, job_id=1, username='testuser',
               run_name='testrun1')
        job_launching_response = pce_get('jobs/1/')

        # Wait a bit and check again.
        time.sleep(2)
        job_still_launching_response = pce_get('jobs/1/')

        # Wait and check again.
        time.sleep(2)
        job_more_launching_response = pce_get('jobs/1/')

        # Let job finish.
        time.sleep(10)
        job_postprocessing_response = pce_get('jobs/1/')

        # Wait a bit and check again.
        time.sleep(2)
        job_still_postprocessing_response = pce_get('jobs/1/')

        # Let postprocessing finish.
        time.sleep(10)
        job_done_response = pce_get('jobs/1/')

        print job_no_mod_response.text
        print '---------------------------------'
        print mod_installing_response.text
        print '---------------------------------'
        print job_mod_not_installed_response.text
        print '---------------------------------'
        print mod_installed_response.text
        print '---------------------------------'
        print job_mod_not_deployed_response.text
        print '---------------------------------'
        print mod_deploying_response.text
        print '---------------------------------'
        print job_mod_not_deployed_response.text
        print '---------------------------------'
        print mod_deployed_response.text
        print '---------------------------------'
        print job_launching_response.text
        print '---------------------------------'
        print job_still_launching_response.text
        print '---------------------------------'
        print job_more_launching_response.text
        print '---------------------------------'
        print job_postprocessing_response.text
        print '---------------------------------'
        print job_still_postprocessing_response.text
        print '---------------------------------'
        print job_done_response.text

        self.assertTrue(False)

import json
import os
import subprocess
import time

import pytest

import siliconcompiler


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_gcd_server_authenticated(gcd_chip, unused_tcp_port):
    '''Basic sc-server test: Run a local instance of a server, and build the GCD
       example using loopback network calls to that server.
       Use authentication and encryption features.
    '''

    # Create a JSON file with a test user / key.
    user_pwd = 'insecure_ci_password'
    os.mkdir('local_server_work')
    with open('local_server_work/users.json', 'w') as f:
        # Passwords should never be stored in plaintext in a production
        # environment, but the development server is a minimal
        # implementation of the API, intended only for testing.
        f.write(json.dumps({'users': [{
            'username': 'test_user',
            'password': user_pwd,
        }]}))

    # Start running an sc-server instance.
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfsmount', './local_server_work',
                                 '-cluster', 'local',
                                 '-port', str(unused_tcp_port),
                                 '-auth'])
    time.sleep(10)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost',
                                        'port': unused_tcp_port,
                                        'username': 'test_user',
                                        'password': user_pwd
                                        }))
    gcd_chip.set('option', 'remote', True)
    gcd_chip.set('option', 'credentials', tmp_creds)

    gcd_chip.set('option', 'nodisplay', True)

    # Run remote build.
    gcd_chip.run()

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS file was generated and returned.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')


###########################
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_gcd_server_not_authenticated(gcd_chip, unused_tcp_port):
    '''Basic sc-server test: Run a local instance of a server, and attempt to
       authenticate a user with an invalid key. The remote run should fail.
    '''

    # Create a JSON file with a test user / key.
    # This key is random, so it shouldn't match the stored test keypair.
    user_pwd = 'insecure_ci_password'
    os.mkdir('local_server_work')
    with open('local_server_work/users.json', 'w') as f:
        f.write(json.dumps({'users': [{
            'username': 'test_user',
            'password': user_pwd,
        }]}))

    # Start running an sc-server instance.
    srv_proc = subprocess.Popen(['sc-server',
                                 '-nfsmount', './local_server_work',
                                 '-cluster', 'local',
                                 '-port', str(unused_tcp_port),
                                 '-auth'])
    time.sleep(10)

    # Ensure that klayout doesn't open its GUI after results are retrieved.
    gcd_chip.set('option', 'nodisplay', True)

    # Create the temporary credentials file, and set the Chip to use it.
    tmp_creds = '.test_remote_cfg'
    with open(tmp_creds, 'w') as tmp_cred_file:
        tmp_cred_file.write(json.dumps({'address': 'localhost',
                                        'port': unused_tcp_port,
                                        'username': 'test_user',
                                        'password': user_pwd + '1'
                                        }))

    # Add remote parameters.
    gcd_chip.set('option', 'remote', True)
    gcd_chip.set('option', 'credentials', tmp_creds)

    # Run remote build. It should fail, so catch the expected exception.
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()

    # Kill the server process.
    srv_proc.kill()

    # Verify that GDS was not generated.
    assert (not os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds'))

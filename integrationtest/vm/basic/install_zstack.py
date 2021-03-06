'''

@author: Youyk
'''

import os
import zstackwoodpecker.setup_actions as setup_actions
import zstackwoodpecker.test_lib as test_lib
import zstackwoodpecker.test_util as test_util

USER_PATH = os.path.expanduser('~')
EXTRA_SUITE_SETUP_SCRIPT = '%s/.zstackwoodpecker/extra_suite_setup_config.sh' % USER_PATH
def test():
    setup = setup_actions.SetupAction()
    setup.plan = test_lib.all_config
    setup.run()

    if os.path.exists(EXTRA_SUITE_SETUP_SCRIPT):
        os.system("bash %s" % EXTRA_SUITE_SETUP_SCRIPT)
    test_util.test_pass('ZStack Installation Success')


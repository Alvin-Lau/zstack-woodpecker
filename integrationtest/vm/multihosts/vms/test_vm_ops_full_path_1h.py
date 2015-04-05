'''

@author: Youyk
'''
import zstackwoodpecker.action_select as action_select
import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.test_state as test_state
import zstackwoodpecker.test_lib as test_lib
import zstackwoodpecker.header.vm as vm_header
import os
import time

_config_ = {
        'timeout' : 4000,
        'noparallel' : False
        }

test_stub = test_lib.lib_get_test_stub()
test_dict = test_state.TestStateDict()
    
def test():
    test_util.test_dsc('''
    will only do vm operations robot testing. It will use pathselector to do 
    full path coverage testing.
    ''')
    vm_create_option = test_util.VmOption()

    test_util.test_dsc('Random Test Begin. Test target: 1hour full path test.')
    robot_test_obj = test_util.Robot_Test_Object()
    robot_test_obj.set_test_dict(test_dict)
    robot_test_obj.set_vm_creation_option(vm_create_option)
    priority_actions = [test_state.TestAction.sg_rule_operations]*2
    priority_action_obj = action_select.ActionPriority()
    priority_action_obj.add_priority_action_list(priority_actions)
    robot_test_obj.set_priority_actions(priority_action_obj)
    robot_test_obj.set_exclusive_actions_list(\
            test_state.TestAction.volume_actions \
            + test_state.TestAction.image_actions \
            + test_state.TestAction.vip_actions \
            + test_state.TestAction.sg_actions \
            + test_state.TestAction.snapshot_actions)

    robot_test_obj.set_random_type(action_select.path_strategy)

    rounds = 1
    current_time = time.time()
    timeout_time = current_time + 3600 
    while time.time() <= timeout_time:
        test_util.test_dsc('New round %s starts: random operation pickup.' % rounds)
        test_lib.lib_vm_random_operation(robot_test_obj)
        test_util.test_dsc('===============Round %s finished. Begin status checking.================' % rounds)
        rounds += 1
        test_lib.lib_robot_status_check(test_dict)

    test_util.test_dsc('Reach test pass exit criterial.')
    test_lib.lib_robot_cleanup(test_dict)
    test_util.test_pass('VM Ops Full Path Test Success')

#Will be called only if exception happens in test().
def error_cleanup():
    test_lib.lib_robot_cleanup(test_dict)

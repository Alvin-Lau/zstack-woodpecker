'''
This case can not execute parallelly
@author: Youyk
'''
import os
import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.test_lib as test_lib
import zstackwoodpecker.test_state as test_state
import zstackwoodpecker.operations.host_operations as host_ops
import zstackwoodpecker.operations.resource_operations as res_ops
import zstackwoodpecker.operations.vm_operations as vm_ops

_config_ = {
        'timeout' : 1000,
        'noparallel' : True
        }

test_stub = test_lib.lib_get_test_stub()
test_obj_dict = test_state.TestStateDict()
new_offering_uuid = None

def test():
    global new_offering_uuid
    test_util.test_dsc('Test VM network outbound & inbound bandwidth QoS by 1MB')

    #unit is KB
    net_bandwidth = 1024
    new_offering = test_lib.lib_create_instance_offering(net_outbound_bandwidth = net_bandwidth, \
            net_inbound_bandwidth = net_bandwidth)

    new_offering_uuid = new_offering.uuid

    vm1 = test_stub.create_vm(vm_name = 'vm_net_inbound_outbound_qos', \
            instance_offering_uuid = new_offering.uuid)
    test_obj_dict.add_vm(vm1)
    vm1.check()
    vm1_inv = vm1.get_vm()
    test_stub.make_ssh_no_password(vm1_inv)
    vm1_ip = vm1_inv.vmNics[0].ip

    vm2 = test_stub.create_vm(vm_name = 'vm_net_inbound_outbound_qos', \
            instance_offering_uuid = new_offering.uuid)
    test_obj_dict.add_vm(vm2)
    vm2.check()
    vm2_inv = vm2.get_vm()
    vm2_ip = vm2_inv.vmNics[0].ip

    test_stub.make_ssh_no_password(vm2_inv)
    test_stub.copy_key_file(vm1_inv)
    test_stub.copy_key_file(vm2_inv)
    test_stub.create_test_file(vm1_inv, net_bandwidth)
    test_stub.create_test_file(vm2_inv, net_bandwidth)
    l3_name = os.environ.get('l3VlanNetworkName1')
    l3_net_uuid = test_lib.lib_get_l3_by_name(l3_name).uuid
    vm1.add_nic(l3_net_uuid)
    vm2.add_nic(l3_net_uuid)
    ssh_cmd = 'ssh -oStrictHostKeyChecking=no -oCheckHostIP=no -oUserKnownHostsFile=/dev/null'
    cmd = "pkill dhclient"
    os.system("%s %s %s" % (ssh_cmd, vm1_ip, cmd))
    os.system("%s %s %s" % (ssh_cmd, vm2_ip, cmd))
    cmd = "dhclient eth1"
    os.system("%s %s %s" % (ssh_cmd, vm1_ip, cmd))
    os.system("%s %s %s" % (ssh_cmd, vm2_ip, cmd))

    #test_util.test_fail('for debug')
    test_stub.test_scp_outbound_speed(vm1_ip, test_lib.lib_get_vm_nic_by_l3(vm2.get_vm(), l3_net_uuid).ip, net_bandwidth)
#    test_stub.test_scp_vm_outbound_speed(vm_inv, net_bandwidth)
#    test_stub.test_scp_vm_inbound_speed(vm_inv, net_bandwidth)
    vm_ops.delete_instance_offering(new_offering_uuid)
    test_lib.lib_robot_cleanup(test_obj_dict)

    test_util.test_pass('VM Network Outbound QoS Test Pass')

#Will be called only if exception happens in test().
def error_cleanup():
    test_lib.lib_error_cleanup(test_obj_dict)
    if new_offering_uuid:
        vm_ops.delete_instance_offering(new_offering_uuid)

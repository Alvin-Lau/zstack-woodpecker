'''
Created on Apr. 4 , 2014

Test 2 Port Forwarding TCP Rules with same VIP and same target vm_nic

@author: Youyk
'''
import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.test_lib as test_lib
import zstackwoodpecker.test_state as test_state
import zstackwoodpecker.operations.net_operations as net_ops
import zstackwoodpecker.zstack_test.zstack_test_vm as zstack_vm_header
import zstackwoodpecker.zstack_test.zstack_test_port_forwarding as zstack_pf_header
import zstackwoodpecker.zstack_test.zstack_test_vip as zstack_vip_header
import apibinding.inventory as inventory

import os

_config_ = {
        'timeout' : 1000,
        'noparallel' : True
        }

PfRule = test_state.PfRule
Port = test_state.Port
test_stub = test_lib.lib_get_test_stub()
test_obj_dict = test_state.TestStateDict()

def test():
    '''
        PF test needs at least 3 VR existence. Besides of PF_VM's VR, there 
        are needed another 2 VR VMs. 1st VR public IP address will be set as 
        allowedCidr. The 1st VR VM should be able to access PF_VM. The 2nd VR
        VM should not be able to access PF_VM.
    '''
    pf_vm = test_stub.create_dnat_vm()
    test_obj_dict.add_vm(pf_vm)
    
    l3_name = os.environ.get('l3VlanNetworkName1')
    vr1 = test_stub.create_vr_vm(test_obj_dict, l3_name)
    
    l3_name = os.environ.get('l3NoVlanNetworkName1')
    vr2 = test_stub.create_vr_vm(test_obj_dict, l3_name)
    
    vr1_pub_ip = test_lib.lib_find_vr_pub_ip(vr1)
    vr2_pub_ip = test_lib.lib_find_vr_pub_ip(vr2)
    
    pf_vm.check()
    
    vm_nic = pf_vm.vm.vmNics[0]
    vm_nic_uuid = vm_nic.uuid
    pri_l3_uuid = vm_nic.l3NetworkUuid
    vr = test_lib.lib_find_vr_by_l3_uuid(pri_l3_uuid)[0]
    vr_pub_nic = test_lib.lib_find_vr_pub_nic(vr)
    l3_uuid = vr_pub_nic.l3NetworkUuid
    vip = test_stub.create_vip('2 pfs with same vip', l3_uuid)
    test_obj_dict.add_vip(vip)
    vip_uuid = vip.get_vip().uuid
    
    #pf_creation_opt = PfRule.generate_pf_rule_option(vr1_pub_ip, protocol=inventory.TCP, vip_target_rule=Port.rule1_ports, private_target_rule=Port.rule1_ports)
    pf_creation_opt1 = PfRule.generate_pf_rule_option(vr1_pub_ip, \
            protocol=inventory.TCP, \
            vip_target_rule=Port.rule1_ports, \
            private_target_rule=Port.rule1_ports, \
            vip_uuid=vip_uuid, \
            vm_nic_uuid=vm_nic_uuid)

    test_pf1 = zstack_pf_header.ZstackTestPortForwarding()
    test_pf1.set_creation_option(pf_creation_opt1)
    test_pf1.create(pf_vm)
    vip.attach_pf(test_pf1)
    
    pf_creation_opt2 = PfRule.generate_pf_rule_option(vr1_pub_ip, \
            protocol=inventory.TCP, \
            vip_target_rule=Port.rule2_ports, \
            private_target_rule=Port.rule2_ports, \
            vip_uuid=vip_uuid, \
            vm_nic_uuid=vm_nic_uuid)

    test_pf2 = zstack_pf_header.ZstackTestPortForwarding()
    test_pf2.set_creation_option(pf_creation_opt2)
    test_pf2.create(pf_vm)
    vip.attach_pf(test_pf2)
    
    pf_vm.check()
    vip.check()
    
    test_pf1.delete()
    test_pf2.delete()
    vip.check()
    pf_vm.destroy()
    test_obj_dict.rm_vm(pf_vm)
    
    vip.delete()
    test_obj_dict.rm_vip(vip)
    test_util.test_pass("Test 2 Port Forwarding Rules with same VIP and same vm_nic Successfully")

#Will be called only if exception happens in test().
def error_cleanup():
    test_lib.lib_error_cleanup(test_obj_dict)

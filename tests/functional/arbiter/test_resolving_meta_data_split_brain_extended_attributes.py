"""
Copyright (C) 2015-2020  Red Hat, Inc. <http://www.redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

Description:
    Arbiter Test cases related to
    healing in default configuration of the volume
"""

# disruptive;dist-arb
# TODO: nfs, cifs

import traceback
from tests.d_parent_test import DParentTest


class TestCase(DParentTest):

    def run_test(self, redant):
        """
        - Create a file test_file.txt
        - Find out which brick the file resides on and kill arbiter brick
        in the replica pair
        - Modify the permissions of the file
        - Bring back the killed brick
        - Kill the other brick in the replica pair
        - Modify the permissions of the file
        - Bring back the killed brick
        - Trigger heal
        - Check if heal is completed
        - Check for split-brain
        """
        # Creating files on client side
        file_to_create = 'test_file.txt'
        for mount_obj in self.mounts:
            g.log.info("Generating data for %s:%s",
                       mount_obj.client_system, mount_obj.mountpoint)
            # Create file
            g.log.info('Creating file...')
            command = ("cd %s ; "
                       "touch %s"
                       % (mount_obj.mountpoint, file_to_create))

            proc = g.run_async(mount_obj.client_system, command,
                               user=mount_obj.user)
            self.all_mounts_procs.append(proc)
        self.io_validation_complete = False

        # Validate IO
        self.assertTrue(
            validate_io_procs(self.all_mounts_procs, self.mounts),
            "IO failed on some of the clients"
        )
        self.io_validation_complete = True

        # get bricks with file
        g.log.info('Getting bricks with file...')
        subvols_dict = get_subvols(self.mnode, self.volname)
        brick_list_with_file = []
        for subvol in subvols_dict['volume_subvols']:
            for brick in subvol:
                node, brick_path = brick.split(':')
                ret, brick_file_list, _ = g.run(node, 'ls %s' % brick_path)
                if 'test_file.txt' in brick_file_list:
                    brick_list_with_file.append(brick)
        g.log.info('Bricks with file: %s', brick_list_with_file)

        # Bring arbiter brick offline
        bricks_to_bring_offline = [brick_list_with_file[-1]]
        g.log.info('Bringing bricks %s offline...', bricks_to_bring_offline)
        ret = bring_bricks_offline(self.volname, bricks_to_bring_offline)
        self.assertTrue(ret, 'Failed to bring bricks %s offline' %
                        bricks_to_bring_offline)

        ret = are_bricks_offline(self.mnode, self.volname,
                                 bricks_to_bring_offline)
        self.assertTrue(ret, 'Bricks %s are not offline'
                        % bricks_to_bring_offline)
        g.log.info('Bringing bricks %s offline is successful',
                   bricks_to_bring_offline)

        # Modify the data
        self.all_mounts_procs = []
        for mount_obj in self.mounts:
            g.log.info("Modifying data for %s:%s",
                       mount_obj.client_system, mount_obj.mountpoint)
            # Modify the permissions
            g.log.info('Modifying the permissions of the file...')
            command = ("cd %s ; "
                       "chmod 600 %s"
                       % (mount_obj.mountpoint, file_to_create))

            proc = g.run_async(mount_obj.client_system, command,
                               user=mount_obj.user)
            self.all_mounts_procs.append(proc)
        self.io_validation_complete = False

        # Validate IO
        self.assertTrue(
            validate_io_procs(self.all_mounts_procs, self.mounts),
            "IO failed on some of the clients"
        )
        self.io_validation_complete = True

        # Bring arbiter brick online
        g.log.info('Bringing bricks %s online...', bricks_to_bring_offline)
        ret = bring_bricks_online(self.mnode, self.volname,
                                  bricks_to_bring_offline)
        self.assertTrue(ret, 'Failed to bring bricks %s online' %
                        bricks_to_bring_offline)
        g.log.info('Bringing bricks %s online is successful',
                   bricks_to_bring_offline)

        # Bring 1-st data brick offline
        bricks_to_bring_offline = [brick_list_with_file[0]]
        g.log.info('Bringing bricks %s offline...', bricks_to_bring_offline)
        ret = bring_bricks_offline(self.volname, bricks_to_bring_offline)
        self.assertTrue(ret, 'Failed to bring bricks %s offline' %
                        bricks_to_bring_offline)

        ret = are_bricks_offline(self.mnode, self.volname,
                                 bricks_to_bring_offline)
        self.assertTrue(ret, 'Bricks %s are not offline'
                        % bricks_to_bring_offline)
        g.log.info('Bringing bricks %s offline is successful',
                   bricks_to_bring_offline)

        # Modify the data
        self.all_mounts_procs = []
        for mount_obj in self.mounts:
            g.log.info("Modifying data for %s:%s",
                       mount_obj.client_system, mount_obj.mountpoint)
            # Modify the permissions
            g.log.info('Modifying the permissions of the file...')
            command = ("cd %s ; "
                       "chmod 644 %s"
                       % (mount_obj.mountpoint, file_to_create))

            proc = g.run_async(mount_obj.client_system, command,
                               user=mount_obj.user)
            self.all_mounts_procs.append(proc)
        self.io_validation_complete = False

        # Validate IO
        self.assertTrue(
            validate_io_procs(self.all_mounts_procs, self.mounts),
            "IO failed on some of the clients"
        )
        self.io_validation_complete = True

        # Bring 1-st data brick online
        g.log.info('Bringing bricks %s online...', bricks_to_bring_offline)
        ret = bring_bricks_online(self.mnode, self.volname,
                                  bricks_to_bring_offline)
        self.assertTrue(ret, 'Failed to bring bricks %s online' %
                        bricks_to_bring_offline)
        g.log.info('Bringing bricks %s online is successful',
                   bricks_to_bring_offline)

        # Start healing
        ret = trigger_heal(self.mnode, self.volname)
        self.assertTrue(ret, 'Heal is not started')
        g.log.info('Healing is started')

        # Monitor heal completion
        ret = monitor_heal_completion(self.mnode, self.volname)
        self.assertTrue(ret, 'Heal has not yet completed')

        # Check if heal is completed
        ret = is_heal_complete(self.mnode, self.volname)
        self.assertTrue(ret, 'Heal is not complete')
        g.log.info('Heal is completed successfully')

        # Check for split-brain
        ret = is_volume_in_split_brain(self.mnode, self.volname)
        self.assertFalse(ret, 'Volume is in split-brain state')
        g.log.info('Volume is not in split-brain state')

# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Exscript.protocols import get_protocol_from_name
from Exscript.CustomAction import CustomAction
from Exscript.Connection import Connection
from Exscript.AccountProxy import AccountProxy

class HostAction(CustomAction):
    """
    An action that automatically opens a network connection to a host
    before calling the associated function.
    """
    def __init__(self, accm, function, host, **conn_args):
        """
        Constructor.

        @type  accm: multiprocessing.Connection
        @param accm: A pipe to the associated account manager.
        @type  function: function
        @param function: Called when the Action is executed.
        @type  conn: Connection
        @param conn: The associated connection.
        """
        CustomAction.__init__(self, accm, function, host.get_address())
        self.host      = host
        self.account   = host.get_account()
        self.conn_args = conn_args

        # Find the right protocol class for connecting to the host.
        protocol_name     = host.get_protocol()
        self.protocol_cls = get_protocol_from_name(protocol_name)

    def get_host(self):
        return self.host

    def acquire_account(self, account = None):
        # Specific account requested?
        if account:
            return AccountProxy.for_account(self.accm, account)

        # Is a default account defined for this connection?
        if self.account:
            return AccountProxy.for_account(self.accm, self.account)

        # Else, let the account manager assign an account.
        return AccountProxy.for_host(self.accm, self.host)

    def get_logname(self):
        logname = self.host.get_logname()
        if self.attempt > 1:
            logname += '_retry%d' % (self.attempt - 1)
        return logname + '.log'

    def _create_connection(self):
        protocol = self.protocol_cls(**self.conn_args)

        # Define the behaviour of the pseudo protocol adapter.
        if self.host.get_protocol() == 'pseudo':
            filename = self.host.get_address()
            protocol.device.add_commands_from_file(filename)

        conn = Connection(self, protocol)
        conn.data_received_event.listen(self.log_event)
        return conn

    def execute(self):
        try:
            conn = self._create_connection()
            self.function(conn)
        finally:
            self.accm.close()

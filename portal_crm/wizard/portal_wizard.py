# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from openerp.osv import osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class wizard_user(osv.osv_memory):
    _inherit = 'portal.wizard.user'

    def get_error_messages(self, cr, uid, ids, context=None):
        error_msg = super(wizard_user, self).get_error_messages(cr, uid, ids, context)
        if error_msg:
            error_msg[-1] = '%s %s' % (error_msg[-1], _("Use the partner merge action (more option of the contacts list) to merge the identical partners."))
        return error_msg

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

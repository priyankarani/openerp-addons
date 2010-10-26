# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import osv
from tools.translate import _

class pos_close_statement(osv.osv_memory):
    _name = 'pos.close.statement'
    _description = 'Close Statements'

    def close_statement(self, cr, uid, ids, context=None):
        """
             Close the statements
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : Blank Dictionary
        """
        mod_obj = self.pool.get('ir.model.data')
        statement_obj = self.pool.get('account.bank.statement')
        journal_obj = self.pool.get('account.journal')
        cr.execute("SELECT DISTINCT journal_id FROM pos_journal_users "
                    "WHERE user_id=%s ORDER BY journal_id", (uid, ))
        j_ids = map(lambda x1: x1[0], cr.fetchall())
        journal_ids = journal_obj.search(cr, uid, [('auto_cash', '=', True), ('type', '=', 'cash'), ('id', 'in', j_ids)], context=context)
        ids = statement_obj.search(cr, uid, [('state', '!=', 'confirm'), ('user_id', '=', uid), ('journal_id', 'in', journal_ids)], context=context)
        for journal in journal_obj.browse(cr, uid, journal_ids, context=context):
            if not ids:
                raise osv.except_osv(_('Message'), _('Registers are already closed.'))
            else:
                if not journal.check_dtls:
                    statement_obj.button_confirm_cash(cr, uid, ids, context=context)

        id2 = mod_obj._get_id(cr, uid, 'account', 'view_bank_statement_tree')
        id3 = mod_obj._get_id(cr, uid, 'account', 'view_bank_statement_form2')
        result = mod_obj._get_id(cr, uid, 'point_of_sale', 'view_pos_confirm_cash_statement_filter')
        search_id = mod_obj.read(cr, uid, result, ['res_id'], context=context)
        if id2:
            id2 = mod_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = mod_obj.browse(cr, uid, id3, context=context).res_id
        return {
            'domain': "[('id', 'in', " + str(ids) + ")]",
            'name': 'Close Statements',
            'view_type': 'form',
            'view_mode': 'tree, form',
            'search_view_id': search_id['res_id'],
            'res_model': 'account.bank.statement',
            'views': [(id2, 'tree'), (id3, 'form')],
            'type': 'ir.actions.act_window'
        }

pos_close_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

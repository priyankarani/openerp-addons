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

from osv import fields, osv
from tools.translate import _

class board_menu_create(osv.osv_memory):
    """
    Create Menu
    """
    def check_views(self, cr, uid, context):
        board = self.pool.get('board.board').browse(cr, uid, context['active_id'])
        if not board.line_ids:
            raise osv.except_osv(_('User Error!'), _('Please Insert Dashboard View(s) !'))    
        return False
    
    def board_menu_create(self, cr, uid, ids, context):
        """
        Create Menu.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Board Menu Create's IDs
        @return : Dictionary {}.
        """
        board = self.pool.get('board.board').browse(cr, uid, context['active_id'])
        action_id = self.pool.get('ir.actions.act_window').create(cr, uid, {
            'name': board.name,
            'view_type':'form',
            'view_mode':'form',
            'res_model': 'board.board',
            'view_id': board.view_id.id,
            })
        for data in self.read(cr, uid, ids):
            self.pool.get('ir.ui.menu').create(cr, uid, {
                'name': data['menu_name'],
                'parent_id': data['menu_parent_id'],
                'icon': 'STOCK_SELECT_COLOR',
                'action': 'ir.actions.act_window,'+str(action_id)
                }, context)
        
        return {}
    
    _name = "board.menu.create"
    _description = "Menu Create"
    _columns = {
             'menu_name':fields.char('Menu Name', size=64, required=True),
             'menu_parent_id':fields.many2one('ir.ui.menu', 'Parent Menu', required=True),
          }
    _defaults = {
            'menu_name':check_views,
          }

board_menu_create()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


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

from openerp.osv import fields, osv
from openerp.tools.translate import _

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime
import openerp

class procurement_group(osv.osv):
    _inherit = 'procurement.group'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner')
    }

class procurement_rule(osv.osv):
    _inherit = 'procurement.rule'

    def _get_action(self, cr, uid, context=None):
        result = super(procurement_rule, self)._get_action(cr, uid, context=context)
        return result + [('move', 'Move From Another Location')]

    def _get_rules(self, cr, uid, ids, context=None):
        res = []
        for route in self.browse(cr, uid, ids):
            res += [x.id for x in route.pull_ids]
        return res

    def _get_route(self, cr, uid, ids, context=None):
        #WARNING TODO route_id is not required, so a field related seems a bad idea >-< 
        if context is None:
            context = {}
        result = {}
        if context is None:
            context = {}
        context_with_inactive = context.copy()
        context_with_inactive['active_test']=False
        for route in self.pool.get('stock.location.route').browse(cr, uid, ids, context=context_with_inactive):
            for pull_rule in route.pull_ids:
                result[pull_rule.id] = True
        return result.keys()

    _columns = {
        'location_id': fields.many2one('stock.location', 'Procurement Location'),
        'location_src_id': fields.many2one('stock.location', 'Source Location',
            help="Source location is action=move"),
        'route_id': fields.many2one('stock.location.route', 'Route',
            help="If route_id is False, the rule is global"),
        'procure_method': fields.selection([('make_to_stock', 'Make to Stock'), ('make_to_order', 'Make to Order')], 'Procure Method', required=True, help="'Make to Stock': When needed, take from the stock or wait until re-supplying. 'Make to Order': When needed, purchase or produce for the procurement request."),
        'route_sequence': fields.related('route_id', 'sequence', string='Route Sequence',
            store={
                'stock.location.route': (_get_rules, ['sequence'], 10),
                'procurement.rule': (lambda self, cr, uid, ids, c={}: ids, ['route_id'], 10),
        }),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type',
            help="Picking Type determines the way the picking should be shown in the view, reports, ..."),
        'active': fields.related('route_id', 'active', type='boolean', string='Active', store={
                    'stock.location.route': (_get_route, ['active'], 20),
                    'procurement.rule': (lambda self, cr, uid, ids, c={}: ids, ['route_id'], 20)},
                help="If the active field is set to False, it will allow you to hide the rule without removing it."),
        'delay': fields.integer('Number of Days'),
        'partner_address_id': fields.many2one('res.partner', 'Partner Address'),
        'propagate': fields.boolean('Propagate cancel and split', help='If checked, when the previous move of the move (which was generated by a next procurement) is cancelled or split, the move generated by this move will too'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Served Warehouse', help='The warehouse this rule is for'),
        'propagate_warehouse_id': fields.many2one('stock.warehouse', 'Warehouse to Propagate', help="The warehouse to propagate on the created move/procurement, which can be different of the warehouse this rule is for (e.g for resupplying rules from another warehouse)"),
    }

    _defaults = {
        'procure_method': 'make_to_stock',
        'active': True,
        'propagate': True,
        'delay': 0,
    }

class procurement_order(osv.osv):
    _inherit = "procurement.order"
    _columns = {
        'location_id': fields.many2one('stock.location', 'Procurement Location'),  # not required because task may create procurements that aren't linked to a location with project_mrp
        'move_ids': fields.one2many('stock.move', 'procurement_id', 'Moves', help="Moves created by the procurement"),
        'move_dest_id': fields.many2one('stock.move', 'Destination Move', help="Move which caused (created) the procurement"),
        'route_ids': fields.many2many('stock.location.route', 'stock_location_route_procurement', 'procurement_id', 'route_id', 'Preferred Routes', help="Preferred route to be followed by the procurement order. Usually copied from the generating document (SO) but could be set up manually."),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', help="Warehouse to consider for the route selection"),
    }

    def write(self, cr, uid, ids, vals, context=None):
        move_obj = self.pool.get('stock.move')
        if vals.get('date_planned'):
            #propagation of a change in date_planned
            for procurement in self.browse(cr, uid, ids, context=context):
                if procurement.move_dest_id and procurement.move_dest_id.propagate:
                    current_date = datetime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S')
                    new_date = datetime.strptime(vals.get('date_planned'), '%Y-%m-%d %H:%M:%S')
                    delta = new_date - current_date
                    if abs(delta.days) >= procurement.company_id.propagation_minimum_delta:
                        #propagate the same delta in dates on the move that created the procurement
                        old_move_date = datetime.strptime(procurement.move_dest_id.date_expected, '%Y-%m-%d %H:%M:%S')
                        new_move_date = (old_move_date + relativedelta(days=delta.days or 0)).strftime('%Y-%m-%d %H:%M:%S')
                        move_obj.write(cr, uid, [procurement.move_dest_id.id], {'date_expected': new_move_date}, context=context)
        return super(procurement_order, self).write(cr, uid, ids, vals, context=context)

    def propagate_cancel(self, cr, uid, procurement, context=None):
        if procurement.rule_id.action == 'move' and procurement.move_ids:
            self.pool.get('stock.move').action_cancel(cr, uid, [m.id for m in procurement.move_ids], context=context)

    def cancel(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        #set the context for the propagation of the procurement cancelation
        ctx['cancel_procurement'] = True
        for procurement in self.browse(cr, uid, ids, context=ctx):
            if procurement.rule_id and procurement.rule_id.propagate:
                self.propagate_cancel(cr, uid, procurement, context=ctx)
        return super(procurement_order, self).cancel(cr, uid, ids, context=ctx)

    def _find_parent_locations(self, cr, uid, procurement, context=None):
        location = procurement.location_id
        res = [location.id]
        while location.location_id:
            location = location.location_id
            res.append(location.id)
        return res

    def change_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
        if warehouse_id:
            warehouse = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
            return {'value': {'location_id': warehouse.lot_stock_id.id}}
        return {}

    def _search_suitable_rule(self, cr, uid, procurement, domain, context=None):
        '''we try to first find a rule among the ones defined on the procurement order group and if none is found, we try on the routes defined for the product, and finally we fallback on the default behavior'''
        pull_obj = self.pool.get('procurement.rule')
        warehouse_route_ids = []
        if procurement.warehouse_id:
            domain += ['|', ('warehouse_id', '=', procurement.warehouse_id.id), ('warehouse_id', '=', False)]
            warehouse_route_ids = [x.id for x in procurement.warehouse_id.route_ids]
        product_route_ids = [x.id for x in procurement.product_id.route_ids + procurement.product_id.categ_id.total_route_ids]
        procurement_route_ids = [x.id for x in procurement.route_ids]
        res = pull_obj.search(cr, uid, domain + [('route_id', 'in', procurement_route_ids)], order='route_sequence, sequence', context=context)
        if not res:
            res = pull_obj.search(cr, uid, domain + [('route_id', 'in', product_route_ids)], order='route_sequence, sequence', context=context)
            if not res:
                res = warehouse_route_ids and pull_obj.search(cr, uid, domain + [('route_id', 'in', warehouse_route_ids)], order='route_sequence, sequence', context=context) or []
                if not res:
                    res = pull_obj.search(cr, uid, domain + [('route_id', '=', False)], order='sequence', context=context)
        return res

    def _find_suitable_rule(self, cr, uid, procurement, context=None):
        rule_id = super(procurement_order, self)._find_suitable_rule(cr, uid, procurement, context=context)
        if not rule_id:
            #a rule defined on 'Stock' is suitable for a procurement in 'Stock\Bin A'
            all_parent_location_ids = self._find_parent_locations(cr, uid, procurement, context=context)
            rule_id = self._search_suitable_rule(cr, uid, procurement, [('location_id', 'in', all_parent_location_ids)], context=context)
            rule_id = rule_id and rule_id[0] or False
        return rule_id

    def _run_move_create(self, cr, uid, procurement, context=None):
        ''' Returns a dictionary of values that will be sued to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'move') set on it.

        :param procurement: browse record
        :rtype: dictionary
        '''
        newdate = (datetime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S') - relativedelta(days=procurement.rule_id.delay or 0)).strftime('%Y-%m-%d %H:%M:%S')
        group_id = False
        if procurement.rule_id.group_propagation_option == 'propagate':
            group_id = procurement.group_id and procurement.group_id.id or False
        elif procurement.rule_id.group_propagation_option == 'fixed':
            group_id = procurement.rule_id.group_id and procurement.rule_id.group_id.id or False
        vals = {
            'name': procurement.name,
            'company_id': procurement.company_id.id,
            'product_id': procurement.product_id.id,
            'product_qty': procurement.product_qty,
            'product_uom': procurement.product_uom.id,
            'product_uom_qty': procurement.product_qty,
            'product_uos_qty': (procurement.product_uos and procurement.product_uos_qty) or procurement.product_qty,
            'product_uos': (procurement.product_uos and procurement.product_uos.id) or procurement.product_uom.id,
            'partner_id': procurement.group_id and procurement.group_id.partner_id and procurement.group_id.partner_id.id or False,
            'location_id': procurement.rule_id.location_src_id.id,
            'location_dest_id': procurement.rule_id.location_id.id,
            'move_dest_id': procurement.move_dest_id and procurement.move_dest_id.id or False,
            'procurement_id': procurement.id,
            'rule_id': procurement.rule_id.id,
            'procure_method': procurement.rule_id.procure_method,
            'origin': procurement.origin,
            'picking_type_id': procurement.rule_id.picking_type_id.id,
            'group_id': group_id,
            'route_ids': [(4, x.id) for x in procurement.route_ids],
            'warehouse_id': procurement.rule_id.propagate_warehouse_id and procurement.rule_id.propagate_warehouse_id.id or procurement.rule_id.warehouse_id.id,
            'date': newdate,
            'date_expected': newdate,
            'propagate': procurement.rule_id.propagate,
        }
        return vals

    def _run(self, cr, uid, procurement, context=None):
        if procurement.rule_id and procurement.rule_id.action == 'move':
            if not procurement.rule_id.location_src_id:
                self.message_post(cr, uid, [procurement.id], body=_('No source location defined!'), context=context)
                return False
            move_obj = self.pool.get('stock.move')
            move_dict = self._run_move_create(cr, uid, procurement, context=context)
            move_id = move_obj.create(cr, uid, move_dict, context=context)
            move_obj.action_confirm(cr, uid, [move_id], context=context)
            return move_id
        return super(procurement_order, self)._run(cr, uid, procurement, context)

    def _check(self, cr, uid, procurement, context=None):
        if procurement.rule_id and procurement.rule_id.action == 'move':
            done_test_list = []
            done_cancel_test_list = []
            for move in procurement.move_ids:
                done_test_list.append(move.state == 'done')
                done_cancel_test_list.append(move.state in ('done', 'cancel'))
            at_least_one_done = any(done_test_list)
            all_done_or_cancel = all(done_cancel_test_list)
            if not all_done_or_cancel:
                return False
            elif at_least_one_done and all_done_or_cancel:
                return True
            else:
                #all move are cancelled
                self.write(cr, uid, [procurement.id], {'state': 'exception'}, context=context)
                self.message_post(cr, uid, [procurement.id], body=_('All stock moves have been cancelled for this procurement.'), context=context)
                return False
            
        return super(procurement_order, self)._check(cr, uid, procurement, context)

    def do_view_pickings(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display the pickings of the procurements belonging
        to the same procurement group of given ids.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'stock', 'do_view_pickings')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        group_ids = set([proc.group_id.id for proc in self.browse(cr, uid, ids, context=context) if proc.group_id])
        result['domain'] = "[('group_id','in',[" + ','.join(map(str, list(group_ids))) + "])]"
        return result

    #
    # Scheduler
    # When stock is installed, it should also check for the different confirmed stock moves
    # if they can not be installed
    #
    #
    def run_scheduler(self, cr, uid, use_new_cursor=False, context=None):
        '''
        Call the scheduler in order to 

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param use_new_cursor: False or the dbname
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        '''

        super(procurement_order, self).run_scheduler(cr, uid, use_new_cursor=use_new_cursor, context=context)
        if context is None:
            context = {}
        try:
            if use_new_cursor:
                cr = openerp.registry(use_new_cursor).db.cursor()

            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            move_obj = self.pool.get('stock.move')
            #Minimum stock rules
            self. _procure_orderpoint_confirm(cr, uid, automatic=False,use_new_cursor=False, context=context, user_id=False)

            #Search all confirmed stock_moves and try to assign them
            confirmed_ids = move_obj.search(cr, uid, [('state', '=', 'confirmed'), ('company_id','=', company.id)], limit = None, context=context) #Type  = stockable product?
            for x in xrange(0, len(confirmed_ids), 100):
                move_obj.action_assign(cr, uid, confirmed_ids[x:x+100], context=context)
                if use_new_cursor:
                    cr.commit()
            
            
            if use_new_cursor:
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
        return {}

    def _prepare_automatic_op_procurement(self, cr, uid, product, warehouse, location_id, context=None):
        return {'name': _('Automatic OP: %s') % (product.name,),
                'origin': _('SCHEDULER'),
                'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'product_id': product.id,
                'product_qty': -product.virtual_available,
                'product_uom': product.uom_id.id,
                'location_id': location_id,
                'company_id': warehouse.company_id.id,
                }

    def create_automatic_op(self, cr, uid, context=None):
        """
        Create procurement of  virtual stock < 0

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        proc_obj = self.pool.get('procurement.order')
        warehouse_obj = self.pool.get('stock.warehouse')

        warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)
        products_ids = product_obj.search(cr, uid, [], order='id', context=context)

        for warehouse in warehouse_obj.browse(cr, uid, warehouse_ids, context=context):
            context['warehouse'] = warehouse
            # Here we check products availability.
            # We use the method 'read' for performance reasons, because using the method 'browse' may crash the server.
            for product_read in product_obj.read(cr, uid, products_ids, ['virtual_available'], context=context):
                if product_read['virtual_available'] >= 0.0:
                    continue

                product = product_obj.browse(cr, uid, [product_read['id']], context=context)[0]

                location_id = warehouse.lot_stock_id.id

                proc_id = proc_obj.create(cr, uid,
                            self._prepare_automatic_op_procurement(cr, uid, product, warehouse, location_id, context=context),
                            context=context)
                self.assign(cr, uid, [proc_id])
                self.run(cr, uid, [proc_id])
        return True

    def _get_orderpoint_date_planned(self, cr, uid, orderpoint, start_date, context=None):
        date_planned = start_date + \
                       relativedelta(days=orderpoint.product_id.seller_delay or 0.0)
        return date_planned.strftime(DEFAULT_SERVER_DATE_FORMAT)

    def _prepare_orderpoint_procurement(self, cr, uid, orderpoint, product_qty, context=None):
        return {'name': orderpoint.name,
                'date_planned': self._get_orderpoint_date_planned(cr, uid, orderpoint, datetime.today(), context=context),
                'product_id': orderpoint.product_id.id,
                'product_qty': product_qty,
                'company_id': orderpoint.company_id.id,
                'product_uom': orderpoint.product_uom.id,
                'location_id': orderpoint.location_id.id,
                'origin': orderpoint.name}

    def _product_virtual_get(self, cr, uid, order_point):
        product_obj = self.pool.get('product.product')
        return product_obj._product_available(cr, uid,
                [order_point.product_id.id],
                {'location': order_point.location_id.id})[order_point.product_id.id]['virtual_available']

    def _procure_orderpoint_confirm(self, cr, uid, automatic=False,\
            use_new_cursor=False, context=None, user_id=False):
        '''
        Create procurement based on Orderpoint
        use_new_cursor: False or the dbname

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param user_id: The current user ID for security checks
        @param context: A standard dictionary for contextual values
        @param param: False or the dbname
        @return:  Dictionary of values
        """
        '''
        if context is None:
            context = {}
        if use_new_cursor:
            cr = openerp.registry(use_new_cursor).db.cursor()
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        
        procurement_obj = self.pool.get('procurement.order')
        offset = 0
        ids = [1]
        if automatic:
            self.create_automatic_op(cr, uid, context=context)
        while ids:
            ids = orderpoint_obj.search(cr, uid, [], offset=offset, limit=100)
            for op in orderpoint_obj.browse(cr, uid, ids, context=context):
                prods = self._product_virtual_get(cr, uid, op)
                if prods is None:
                    continue
                if prods < op.product_min_qty:
                    qty = max(op.product_min_qty, op.product_max_qty)-prods

                    reste = qty % op.qty_multiple
                    if reste > 0:
                        qty += op.qty_multiple - reste

                    if qty <= 0:
                        continue
                    if op.product_id.type not in ('consu'):
                        procurement_draft_ids = orderpoint_obj.get_draft_procurements(cr, uid, op. id, context=context)
                        if procurement_draft_ids:
                            # Check draft procurement related to this order point
                            procure_datas = procurement_obj.read(
                                cr, uid, procurement_draft_ids, ['id', 'product_qty'], context=context)
                            to_generate = qty
                            for proc_data in procure_datas:
                                if to_generate >= proc_data['product_qty']:
                                    self.signal_button_confirm(cr, uid, [proc_data['id']])
                                    procurement_obj.write(cr, uid, [proc_data['id']],  {'origin': op.name}, context=context)
                                    to_generate -= proc_data['product_qty']
                                if not to_generate:
                                    break
                            qty = to_generate

                    if qty:
                        proc_id = procurement_obj.create(cr, uid,
                                                         self._prepare_orderpoint_procurement(cr, uid, op, qty, context=context),
                                                         context=context)
                        self.check(cr, uid, [proc_id])
                        self.run(cr, uid, [proc_id])
                        #TODO: check if we can remove this field because it doesn't seem used at all
                        #orderpoint_obj.write(cr, uid, [op.id],
                        #        {'procurement_id': proc_id}, context=context)
            offset += len(ids)
            if use_new_cursor:
                cr.commit()
        if use_new_cursor:
            cr.commit()
            cr.close()
        return {}

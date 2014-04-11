# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class Users(osv.Model):
    _inherit = 'res.users'

    def _get_user_badge_level(self, cr, uid, ids, name, args, context=None):
        """Return total badge per level of users"""
        result = dict.fromkeys(ids, False)
        badge_user_obj = self.pool['gamification.badge.user']
        for id in ids:
            result[id] = {
                'gold_badge': badge_user_obj.search(cr, uid, [('badge_id.level', '=', 'gold'), ('user_id', '=', id)], context=context, count=True),
                'silver_badge': badge_user_obj.search(cr, uid, [('badge_id.level', '=', 'silver'), ('user_id', '=', id)], context=context, count=True),
                'bronze_badge': badge_user_obj.search(cr, uid, [('badge_id.level', '=', 'bronze'), ('user_id', '=', id)], context=context, count=True),
            }
        return result

    _columns = {
        'create_date': fields.datetime('Create Date', select=True, readonly=True),
        # 'is_forum': fields.boolean('Is Forum Member'),
        'karma': fields.integer('Karma'),
        'badge_ids': fields.one2many('gamification.badge.user', 'user_id', 'Badges'),
        'gold_badge': fields.function(_get_user_badge_level, string="Number of gold badges", type='integer', multi='badge_level'),
        'silver_badge': fields.function(_get_user_badge_level, string="Number of silver badges", type='integer', multi='badge_level'),
        'bronze_badge': fields.function(_get_user_badge_level, string="Number of bronze badges", type='integer', multi='badge_level'),
    }

    _defaults = {
        # 'is_forum': False,
        'karma': 0,
    }

    def add_karma(self, cr, uid, ids, karma, context=None):
        for user in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [user.id], {'karma': user.karma + karma}, context=context)
        return True

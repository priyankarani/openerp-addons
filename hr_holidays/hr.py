# -*- encoding: utf-8 -*-
##################################################################################
#
# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com) All Rights Reserved.
#
# $Id: hr.py 4656 2006-11-24 09:58:42Z Cyp $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from mx import DateTime
import time
import pooler
import netsvc
import datetime
from osv import fields, osv


def _employee_get(obj,cr,uid,context={}):
    ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
    if ids:
        return ids[0]
    return False

def strToDate(dt):
    dt_date=datetime.date(int(dt[0:4]),int(dt[5:7]),int(dt[8:10]))
    return dt_date

class hr_holidays(osv.osv):
    _name = "hr.holidays"
    _inherit = 'hr.holidays'
    _description = "Holidays"
    _columns = {
        'name' : fields.char('Description', required=True, readonly=True, size=64, states={'draft':[('readonly',False)]}),
        'state': fields.selection([('draft', 'draft'), ('confirm', 'Confirmed'), ('refuse', 'Refused'), ('validate', 'Validate'), ('cancel', 'Cancel')], 'State', readonly=True),
        'date_from' : fields.datetime('Vacation start day', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'date_to' : fields.datetime('Vacation end day',required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'holiday_status' : fields.many2one("hr.holidays.status", "Holiday's Status", required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'employee_id' : fields.many2one('hr.employee', 'Employee', select=True, invisible=False, readonly=True, states={'draft':[('readonly',False)]}),
        'user_id':fields.many2one('res.users', 'Employee_id', states={'draft':[('readonly',False)]}, relate=True, select=True, readonly=True),
        'manager_id' : fields.many2one('hr.employee', 'Holiday manager', invisible=False, readonly=True),
        'notes' : fields.text('Notes',readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days': fields.float('Number of Days in this Holiday Request',required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'case_id':fields.many2one('crm.case', 'Case'),
    }
    _defaults = {
        'employee_id' : _employee_get ,
        'state' : lambda *a: 'draft',
        'user_id': lambda obj, cr, uid, context: uid
    }
    _order = 'date_from desc'
    def set_to_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'draft',
            'manager_id': False
        })
        return True

    def holidays_validate(self, cr, uid, ids, *args):
        self.check_holidays(cr,uid,ids)

        vals = {
            'state':'validate',
        }
        ids2 = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
        if ids2:
            print ids2
            vals['manager_id'] = ids2[0]

        self.write(cr, uid, ids, vals)
        return True

    def holidays_confirm(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'confirm'
        })
        return True

    def holidays_refuse(self, cr, uid, ids, *args):
        ids2 = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
        self.write(cr, uid, ids, {
            'state':'refuse',
            'manager_id':ids2[0]
        })
        return True

    def holidays_cancel(self, cr, uid, ids, *args):
        for record in self.browse(cr, uid, ids):
            if record.state=='validate':
                holiday_id=self.pool.get('hr.holidays.per.user').search(cr, uid, [('employee_id','=', record.employee_id.id),('holiday_status','=',record.holiday_status.id)])
                if holiday_id:
                    obj_holidays_per_user=self.pool.get('hr.holidays.per.user').browse(cr, uid,holiday_id[0])
                    self.pool.get('hr.holidays.per.user').write(cr,uid,obj_holidays_per_user.id,{'leaves_taken':obj_holidays_per_user.leaves_taken - record.number_of_days})
                if record.case_id:
                    self.pool.get('crm.case').unlink(cr,uid,record.case_id.id)
        self.write(cr, uid, ids, {
            'state':'cancel'
            })

        return True

    def holidays_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'draft'
        })
        return True

    def check_holidays(self,cr,uid,ids):

        for record in self.browse(cr, uid, ids):
            leave_asked = record.number_of_days
            holiday_id=self.pool.get('hr.holidays.per.user').search(cr, uid, [('employee_id','=', record.employee_id.id),('holiday_status','=',record.holiday_status.id)])
            if leave_asked>=0.00:
                if holiday_id:
                    obj_holidays_per_user=self.pool.get('hr.holidays.per.user').browse(cr, uid,holiday_id[0])
                    leaves_rest=obj_holidays_per_user.max_leaves - obj_holidays_per_user.leaves_taken
                    if leaves_rest < leave_asked:
                        raise osv.except_osv('Attention!','You Cannot Validate leaves while available leaves are less than asked leaves.')
                    self.pool.get('hr.holidays.per.user').write(cr,uid,obj_holidays_per_user.id,{'leaves_taken':obj_holidays_per_user.leaves_taken + leave_asked})
                if record.holiday_status.section_id:
                    vals={}
                    vals['name']=record.name
                    vals['section_id']=record.holiday_status.section_id.id

                    c= time.strptime(record.date_to,'%Y-%m-%d %H:%M:%S').tm_mday
                    d= time.strptime(record.date_from,'%Y-%m-%d %H:%M:%S').tm_mday
                    vals['duration']= (c-d) * 8
                    vals['note']=record.notes
                    vals['user_id']=record.user_id.id
                    vals['date']=record.date_from
                    case_id=self.pool.get('crm.case').create(cr,uid,vals)
                    self.write(cr, uid, ids, {'case_id':case_id})
            else:
                if holiday_id:
                    obj_holidays_per_user=self.pool.get('hr.holidays.per.user').browse(cr, uid,holiday_id[0])
                    note=obj_holidays_per_user.notes or ''
                    notes= note + '\n***' + time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + record.name
                    self.pool.get('hr.holidays.per.user').write(cr,uid,obj_holidays_per_user.id,{'max_leaves':obj_holidays_per_user.max_leaves + abs(leave_asked),'notes':notes})
                else:
                    vals={}
                    vals['employee_id']=record.employee_id.id
                    vals['holiday_status']=record.holiday_status.id
                    vals['max_leaves']=abs(leave_asked)
                    vals['leaves_taken']=0.00
                    self.pool.get('hr.holidays.per.user').create(cr,uid,vals)

        return True
hr_holidays()

class hr_holidays_status(osv.osv):
    _name = "hr.holidays.status"
    _inherit = 'hr.holidays.status'
    _description = "Holidays Status"
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Section'),
        'color_name' : fields.selection([('red', 'Red'), ('lightgreen', 'Light Green'), ('lightblue','Light Blue'), ('lightyellow', 'Light Yellow'), ('magenta', 'Magenta'),('lightcyan', 'Light Cyan'),('black', 'Black'),('lightpink', 'Light Pink'),('brown', 'Brown'),('violet', 'Violet'),('lightcoral', 'Light Coral'),('lightsalmon', 'Light Salmon'),('lavender', 'Lavender'),('wheat', 'Wheat'),('ivory', 'Ivory')],'Color of the status', required=True),
    }
    _defaults = {
        'color_name': lambda *args: 'red',
    }
hr_holidays_status()


class hr_holidays_per_user(osv.osv):
    _name = "hr.holidays.per.user"
    _description = "Holidays Per User"
    _columns = {
        'employee_id' : fields.many2one('hr.employee', 'Employee',required=True),
        'user_id' : fields.many2one('res.users','User'),
        'holiday_status' : fields.many2one("hr.holidays.status", "Holiday's Status", required=True),
        'max_leaves' : fields.float('Maximum Leaves Allowed',required=True),
        'leaves_taken' : fields.float('Leaves Already Taken',readonly=True),
        'notes' : fields.text('Notes'),
    }

    def create(self, cr, uid, vals, *args, **kwargs):

        if vals['employee_id']:
            obj_emp=self.pool.get('hr.employee').browse(cr,uid,vals['employee_id'])
            vals.update({'user_id': obj_emp.user_id.id})
        return super(osv.osv,self).create(cr, uid, vals, *args, **kwargs)

hr_holidays_per_user()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


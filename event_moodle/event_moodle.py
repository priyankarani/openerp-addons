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
import xmlrpclib
import string
import random
from random import sample


class event_moodle(osv.osv):
    """ Event Type """
    _name = 'event.moodle'
    _columns = {
        'moodle_username' : fields.char('Moodle username', 128),
        'moodle_password' : fields.char('Moodle password', 128),
        'moodle_token' : fields.char('Moodle token', 128),
        'serveur_moodle': fields.char('Moodle server', 128)
    }
    url='http://127.0.0.1/moodle/webservice/xmlrpc/server.php?wstoken=3ecfb383330044a884b1ee86e0872b47'
    def configure_moodle(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'id':1})
        #save information that you need to create the url
        
    def make_url(self,cr,uid,ids,context=None):
        config_moodle = self.browse(cr, uid, ids, context=context)
        if config_moodle[0].moodle_username and config_moodle[0].moodle_password:
            url='http://'+config_moodle[0].serveur_moodle+'/moodle/webservice/xmlrpc/simpleserver.php?wsusername='+config_moodle[0].moodle_username+'&wspassword='+config_moodle[0].moodle_password
            #connexion with password and username 
            #to do warning on special char 
        print config_moodle[0].moodle_token
        if config_moodle[0].moodle_token:
            url='http://'+config_moodle[0].serveur_moodle+'/moodle/webservice/xmlrpc/server.php?wstoken='+config_moodle[0].moodle_token
            #connexion with token 
        self.url = url
        return url


    #create a good url for xmlrpc connect
    def create_moodle_user(self,dic_user):
        """
        user is a list of dictionaries with every required datas for moodle
        """
        sock = xmlrpclib.ServerProxy(self.url)  
        #connect to moodle
    
        return sock.core_user_create_users(dic_user)
        #add user un moodle
        #return list of id and username

    def create_moodle_courses(self,courses):
        print self.url
        print'\n\n\n'
        sock = xmlrpclib.ServerProxy(self.url)  
        #connect to moodle
        return sock.core_course_create_courses(courses)
        #add course un moodle
                   
    def moodle_enrolled(self,enrolled):
        sock = xmlrpclib.ServerProxy(self.url)  
        #connect to moodle
        sock.enrol_manual_enrol_users(enrolled)
        #add enrolled un moodle
        
    def get_course(self,course_id):
        sock = xmlrpclib.ServerProxy(self.url)  
        #connect to moodle
        sock.core_course_get_courses(course_id)
    def create_password(self):
        rand = string.ascii_letters + string.digits
        length=8
        # exemple simple
        while length > len(rand):
            rand *= 2
        passwd = ''.join(sample(rand, length))
        passwd = passwd+'+'
        return passwd    
    # create a random password    
        
event_moodle()
  
    
class event_event(osv.osv):
    _inherit = "event.event"
    _columns={
    'moodle_id' :fields.integer('Moodle id'),
    }
    def button_confirm(self, cr, uid, ids, context=None):
        list_users=[]
        event = self.browse(cr, uid, ids, context=context)        
        name_event = event[0].name 
        dic_courses= [{'fullname' :name_event,'shortname' :'','summary':event[0].note,'categoryid':1}]
        #create a dict course
        moodle_pool = self.pool.get('event.moodle')
        response_courses = moodle_pool.create_moodle_courses(dic_courses)
        self.write(cr,uid,ids,{'moodle_id':response_courses[0]['id']})
        #create a course in moodle and keep the id
        for registration in event[0].registration_ids:
           if registration.name:
               name=registration.name
               name=name.replace(" ","_")
                   #remove space in the name
               name_user = name+"%d" % (response_courses[0]['id'],)+ "%d" % (random.randint(1,999999),) 
               #give an user name
           else:
               name_user = "%d" % (registration.id,)+"moodle_"+"%d" % (response_courses[0]['id'],)+ "%d" % (random.randint(1,999999),)
            
           email = registration.email
           if email:
               if (email.count('@')!=1 and email.count('.')<1):
                    email='test@test.com'
           else:
               email='test@test.com'
            #test email   
           passwd=moodle_pool.create_password()    
           dic_users={
           'username' : name_user,
           'password' : passwd,
           'city' : registration.city,
           'firstname' : registration.name , 
           'lastname': '',
           'email': email
           }
           #create a dictionary for an user
           list_users.append(dic_users)    
           #add the dictionary in a list 
           
           
           self.pool.get('event.registration').write(cr,uid,[registration.id],{'moodle_user_password':passwd,'moodle_users':name_user})
           #write in database the password and the username       
       
        response_user = moodle_pool.create_moodle_user(list_users)
        #create users in moodle
        enrolled =[]
        for dic in response_user:
            enrolled=[{
            'roleid' :'5',
            'userid' :dic['id'],
            'courseid' :response_courses[0]['id']
            }]
            moodle_pool.moodle_enrolled(enrolled)
        #link a course with users
        return super(event_event, self).button_confirm(cr, uid, ids, context)

event_event()    

class event_registration(osv.osv):
    _inherit = "event.registration"
    _columns={
    'moodle_user_password': fields.char('password for moodle user', 128),
    'moodle_users': fields.char('moodle username', 128)
    }
    def check_confirm(self, cr, uid, ids, context=None):
        register = self.browse(cr, uid, ids, context=context)
        if register[0].event_id.state =='done':
            name_user = register[0].name+"%d" % (register[0].event_id.moodle_id,)+ "%d" % (random.randint(1,999999),) 
            dic_users={
            'username' : name_user,
            'password' : passwd,
            'city' : register[0].city,
            'firstname' : register[0].name, 
            'lastname': '',
            'email': register[0].email
            }
            #create a dictionary for an use
            response_user = moodle_pool.create_moodle_user(dic_users)
            self.pool.get('event.registration').write(cr,uid,[registration.id],{'moodle_user_password':passwd,'moodle_users':name_user})
            #write in database the password and the username   
               
            enrolled=[{
            'roleid' :'5',
            'userid' :response_user[0]['id'],#use the response of the create user
            'courseid' :register[0].event_id.moodle_id
            }]   


        return super(event_registration, self).check_confirm(cr, uid, ids, context)

# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name" : "CCI Country",
    "version" : "1.0",
    "author" : "CCILV",
    "website" : "http://www.ccilv.be",
    "category" : "Generic Modules/CCI",
    "description": """
        For some applications in the OpenERP software used by some belgain Chamber of Commerce,
        we need a table regrouping countries and areas (group of countries). The table used by
        defaut in openERP doesn't answer to this need, because it's used in other and we need to
        specify if this code can be used in some cases or others
        This table is by evidence very specific to the Chamber of Commerce dedicated modules
    """,
    "depends" : ["base"],
    "init_xml" : [],
    "demo_xml" : [],

    "update_xml" : ["cci_country_view.xml"],
    "active": False,
    "installable": True
}


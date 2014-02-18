
from openerp.osv import osv, fields

class crm_lead_to_project_issue_wizard(osv.TransientModel):
    """ wizard to convert a Lead into a Project Issue and move the Mail Thread """

    def action_lead_to_project_issue(self, cr, uid, ids, context=None):
        # get the wizards and models
        wizards = self.browse(cr, uid, ids, context=context)
        Lead = self.pool["crm.lead"]
        Issue = self.pool["project.issue"]

        for wizard in wizards:
            # get the lead to transform
            lead = wizard.lead_id
            # create new project.issue
            vals = {"name": lead.name, 
                "description": lead.description, 
                "email_from": lead.email_from, 
                "partner_id": lead.partner_id.id, 
                "project_id": wizard.project_id.id
            }
            issue_id = Issue.create(cr, uid, vals, context=None) 
            # move the mail thread
            Lead.message_change_thread(cr, uid, lead.id, issue_id, "project.issue", context=context)
            # delete the lead
            Lead.unlink(cr, uid, [lead.id], context=None)
        # return the action to go to the form view of the new Issue
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[('model','=','project.issue'), ('name','=','project_issue_form_view')])
        return {
            'name': 'Issue created',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'project.issue',
            'type': 'ir.actions.act_window',
            'res_id': issue_id,
            'context' : context
        }


    _name = "crm.lead2projectissue.wizard"

    _columns = {
        "lead_id" : fields.many2one("crm.lead","Lead", domain=[("type","=","lead")]),
        "project_id" : fields.many2one("project.project", "Project", domain=[("use_issues","=",True)])
    }

    _defaults = {
        "lead_id" : lambda self, cr, uid, context=None: context.get('active_id')
    }
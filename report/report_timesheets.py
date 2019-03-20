# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2009-TODAY Cybrosys Technologies(<http://www.cybrosys.com>).
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api
import pdb

import datetime
from datetime import timedelta, date

def get_end_date_week(year, week):
     d = date(year,1,1)
     if(d.weekday()<= 3):
         d = d - timedelta(d.weekday())             
     else:
         d = d + timedelta(7-d.weekday())
     dlt = timedelta(days = (week-1)*7)
     return d + dlt + timedelta(days=6)


class ReportTimesheet(models.AbstractModel):
    _name = 'report.timesheets_by_employee.report_timesheets'

    def get_timesheets(self, docs):
        """input : name of employee and the starting date and ending date
        output: timesheets by that particular employee within that period and the total duration"""
        
        # make domain
        dom=[('user_id','=',docs.employee[0].id),('is_timesheet','=',True)] # this requires enterprise version
        if docs.from_date:
            dom.append(('date', '>=', docs.from_date))
        if docs.to_date:
            dom.append(('date', '<=', docs.to_date))
        if docs.projects:
            dom.append(('project_id','in',[p.id for p in docs.projects]))    
        #~ if docs.from_date and docs.to_date:
            #~ rec = self.env['account.analytic.line'].search([('user_id', '=', docs.employee[0].id),
                                                        #~ ('date', '>=', docs.from_date),('date', '<=', docs.to_date)])
        #~ elif docs.from_date:
            #~ rec = self.env['account.analytic.line'].search([('user_id', '=', docs.employee[0].id),
                                                        #~ ('date', '>=', docs.from_date)])
        #~ elif docs.to_date:
            #~ rec = self.env['account.analytic.line'].search([('user_id', '=', docs.employee[0].id),
                                                            #~ ('date', '<=', docs.to_date)])
        #~ else:
            #~ rec = self.env['account.analytic.line'].search([('user_id', '=', docs.employee[0].id)])
        rec  = self.env['account.analytic.line'].search(dom, order="date asc")
        records = []
        total = 0
        if docs.ag_lvl=='none': # we can include description
            for r in rec:
                vals = {'project': r.project_id.name,
                        'user': r.user_id.partner_id.name,
                        'task': r.task_id.name,
                        'descr': r.name,
                        'duration': r.unit_amount,
                        'date': r.date,
                        }
                total += r.unit_amount
                records.append(vals)
        else: 
            idx=0
            while idx<len(rec):
                # dt is last date in block
                if docs.ag_lvl=='day':
                    dt=rec[idx].date # dt is last date in block
                elif docs.ag_lvl=='week':
                    dt=fields.Date.to_string(get_end_date_week(fields.Date.from_string(rec[idx].date).isocalendar()[0], fields.Date.from_string(rec[idx].date).isocalendar()[1]))
                elif docs.ag_lvl=='month':
                    dt=fields.Date.to_string(date(fields.Date.from_string(rec[idx].date).year,fields.Date.from_string(rec[idx].date).month+1,1)-timedelta(days=1))
                else:
                    dt=fields.Date.to_string(date(fields.Date.from_string(rec[idx].date).year,12,31))        
                tasks={}                 
                while True:
                    if rec[idx].project_id not in tasks.keys():
                       tasks[rec[idx].project_id]={}
                    if rec[idx].task_id not in tasks[rec[idx].project_id].keys():
                       tasks[rec[idx].project_id][rec[idx].task_id]=0
                    tasks[rec[idx].project_id][rec[idx].task_id]+=rec[idx].unit_amount   
                    total+=rec[idx].unit_amount
                    idx+=1
                    if idx==len(rec) or rec[idx].date>dt:
                       p_o=tasks.keys()
                       p_o.sort(key=lambda x: x.sequence) # every time sheet is attached to a project but not necessarily to a task?
                       # convert date to week, month or year number
                       if docs.ag_lvl=='week':
                           dt=str(fields.Date.from_string(dt).isocalendar()[0])+'-'+str(fields.Date.from_string(dt).isocalendar()[1])
                       elif docs.ag_lvl=='month':
                           dt=str(fields.Date.from_string(dt).year)+'-'+str(fields.Date.from_string(dt).month)
                       elif docs.ag_lvl=='year':
                           dt=str(fields.Date.from_string(dt).year)    
                       for p in p_o:
                           t_o=tasks[p].keys()
                           t_o.sort(key=lambda x: (x is None,x.sequence)) # smart method to sort with nones
                           if docs.tasks:
                               for t in t_o:
                                    vals = {'project': p.name,
                                        'user': docs.employee[0].partner_id.name,
                                        'task': t.name if t else 'Not assigned to a task',
                                        'duration': tasks[p][t],
                                        'date': dt,
                                        }   
                                    records.append(vals)
                           else:
                                vals = {'project': p.name,
                                    'user': docs.employee[0].partner_id.name,
                                    'duration': sum(tasks[p].values()),
                                    'date': dt,
                                    } 
                                records.append(vals)
                       break
                           
                           
                             
        return [records, total]

    @api.model
    def render_html(self, docids, data=None):
        """we are overwriting this function because we need to show values from other models in the report
        we pass the objects in the docargs dictionary"""

        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        identification = []
        for i in self.env['hr.employee'].search([('user_id', '=', docs.employee[0].id)]):
            if i:
                identification.append({'id': i.identification_id, 'name': i.name_related})

        timesheets = self.get_timesheets(docs)
        period = None
        if docs.from_date and docs.to_date:
            period = "From " + str(docs.from_date) + " To " + str(docs.to_date)
        elif docs.from_date:
            period = "From " + str(docs.from_date)
        elif docs.from_date:
            period = " To " + str(docs.to_date)
        docargs = {
           'doc_ids': self.ids,
           'doc_model': self.model,
           'docs': docs,
           'timesheets': timesheets[0],
           'total': timesheets[1],
           'company': docs.employee[0].company_id.name,
           'identification': identification,
           'period': period,
           'date': date,
        }
        return self.env['report'].render('timesheets_by_employee.report_timesheets', docargs)

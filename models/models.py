# -*- coding: utf-8 -*-

from openerp import models, fields, api
import time
from datetime import datetime, timedelta
from openerp.exceptions import UserError
from openerp.exceptions import ValidationError
from openerp.tools.translate import _

class compraventa_divisas(models.Model):
	_name = 'compraventa.divisas'

	name = fields.Char('Nombre mostrado')
	date = fields.Date('Fecha', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
	journal_id = fields.Many2one('account.journal', "Metodo de pago")
	destination_journal_id = fields.Many2one('account.journal', "Destino")
	amount = fields.Float('Monto')
	operation_type = fields.Selection([('compra', 'Compra'), ('venta', 'Venta')], default='compra', string='Operacion')
	currency_id = fields.Many2one('res.currency', 'Divisa')
	rate = fields.Float('Tasa de cambio')
	communication = fields.Char('Circular')
	partner_id = fields.Many2one('res.partner', 'Cliente')
	state = fields.Selection([('borrador', 'Borrador'), ('publicado', 'Publicado')], default='borrador', readonly=True, string='Estado')
	move_id = fields.Many2one('account.move', 'Asiento del pago')
	destination_move_id = fields.Many2one('account.move', 'Asiento del cobro')

	@api.model
	def create(self, values):
		rec = super(compraventa_divisas, self).create(values)
		op_text = 'COMPRA/'
		if rec.operation_type == 'venta':
			op_text = 'VENTA/'
		rec.update({
			'name': 'OPERACION/' + op_text + str(rec.id).zfill(6),
			})
		return rec

	@api.one
	def confirmar(self):
		print "Confirm//////////*********"
		currency_id = self.env.user.company_id.currency_id.id
		transfer_account_id = self.env.user.company_id.transfer_account_id
		aml_ids = []
		communication = None
		if self.communication:
			communication = self.communication
		else:
			if self.operation_type == 'compra':
				communication = 'Compra de '
			else:
				communication = 'Venta de '
			communication += self.currency_id.name + ' ' + str(self.amount) + ' x ' + str(self.rate)

		if True:
			# Metodo de pago
			# Aqui registramos la salida de caja correspondiente
			aml = {
			    'name': communication,
			    'account_id': self.journal_id.default_debit_account_id.id,
			    'journal_id': self.journal_id.id,
			    'date': self.date,
			    'currency_id': self.currency_id.id,
			    'amount_currency': -self.amount,
			    'credit': self.amount * self.rate,
			    'partner_id': self.partner_id.id,
			}
			aml_ids.append((0,0,aml))
			# Transferimos momentaneamente a cuenta interna
			aml2 = {
			    'name': communication,
			    'account_id': transfer_account_id.id,
			    'journal_id': self.journal_id.id,
			    'date': self.date,
			    'currency_id': self.currency_id.id,
			    'amount_currency': self.amount,
			    'debit': self.amount * self.rate,
			    'partner_id': self.partner_id.id,
			}
			aml_ids.append((0,0,aml2))

			am_values = {
			    'journal_id': self.journal_id.id,
			    'partner_id': self.partner_id.id,
			    'state': 'draft',
			    'name': 'COMPRA-VENTA/PAGO/'+str(self.id),
			    'date': self.date,
			    'line_ids': aml_ids,
			}
			new_move_id = self.env['account.move'].create(am_values)
			new_move_id.post()
			self.move_id = new_move_id.id

			aml_ids = []
			# Destino
			# Aqui registramos el ingreso a la caja correspondiente
			aml = {
			    'name': communication,
			    'account_id': self.destination_journal_id.default_debit_account_id.id,
			    'journal_id': self.destination_journal_id.id,
			    'date': self.date,
			    'currency_id': self.currency_id.id,
			    'amount_currency': self.amount,
			    'debit': self.amount * self.rate,
			    'partner_id': self.partner_id.id,
			}
			aml_ids.append((0,0,aml))
			# Saldamos la cuenta interna
			aml2 = {
			    'name': communication,
			    'account_id': transfer_account_id.id,
			    'journal_id': self.destination_journal_id.id,
			    'date': self.date,
			    'currency_id': self.currency_id.id,
			    'amount_currency': -self.amount,
			    'credit': self.amount * self.rate,
			    'partner_id': self.partner_id.id,
			}
			aml_ids.append((0,0,aml2))

			am_values = {
			    'journal_id': self.destination_journal_id.id,
			    'partner_id': self.partner_id.id,
			    'state': 'draft',
			    'name': 'COMPRA-VENTA/COBRO/'+str(self.id),
			    'date': self.date,
			    'line_ids': aml_ids,
			}
			new_move_id = self.env['account.move'].create(am_values)
			new_move_id.post()
			self.destination_move_id = new_move_id.id
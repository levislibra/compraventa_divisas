# -*- coding: utf-8 -*-

from openerp import models, fields, api
import time
from datetime import datetime, timedelta
from openerp.exceptions import UserError
from openerp.exceptions import ValidationError
from openerp.tools.translate import _

class compraventa_divisas(models.Model):
	_name = 'compraventa.divisas'

	_order = 'id desc'
	name = fields.Char('Nombre mostrado')
	date = fields.Date('Fecha', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
	journal_id = fields.Many2one('account.journal', "Metodo de pago")
	destination_journal_id = fields.Many2one('account.journal', "Destino")
	amount = fields.Float('Monto')
	operation_type = fields.Selection([('compra', 'Compra'), ('venta', 'Venta')], default='compra', string='Operacion')
	currency_id = fields.Many2one('res.currency', 'Divisa')
	rate = fields.Float('Tasa de cambio')
	result = fields.Float('Resultado', compute="_compute_result")
	communication = fields.Char('Circular')
	partner_id = fields.Many2one('res.partner', 'Cliente')
	state = fields.Selection([('borrador', 'Borrador'), ('publicado', 'Publicado'), ('cancelado', 'Cancelado')], default='borrador', readonly=True, string='Estado')
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
	@api.onchange('amount', 'rate')
	def _compute_result(self):
		self.result = self.amount * self.rate

	@api.one
	def confirmar(self):
		currency_id = self.env.user.company_id.currency_id.id
		transfer_account_id = self.env.user.company_id.transfer_account_id
		aml_ids = []

		name_account_move_line = None
		if self.operation_type == 'compra':
			name_account_move_line = 'Compra de '
		else:
			name_account_move_line = 'Venta de '
		name_account_move_line += self.currency_id.name + ' ' + str(self.amount) + ' x ' + str(self.rate)

		if True:
			# Metodo de pago
			# Aqui registramos la salida de caja correspondiente
			aml = {
			    'name': name_account_move_line,
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
			    'name': name_account_move_line,
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
			    'ref': self.communication,
			    #'name': 'COMPRA-VENTA/PAGO/'+str(self.id),
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
			    'name': name_account_move_line,
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
			    'name': name_account_move_line,
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
			    'ref': self.communication,
			    #'name': 'COMPRA-VENTA/COBRO/'+str(self.id),
			    'date': self.date,
			    'line_ids': aml_ids,
			}
			new_move_id = self.env['account.move'].create(am_values)
			new_move_id.post()
			self.destination_move_id = new_move_id.id
			self.state = 'publicado'

	@api.one
	def cancelar(self):
		self.move_id.button_cancel()
		self.move_id.unlink()
		self.destination_move_id.button_cancel()
		self.destination_move_id.unlink()
		self.state = 'cancelado'
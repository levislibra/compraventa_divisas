# -*- coding: utf-8 -*-
#from openerp import http

# class CompraventaDivisas(http.Controller):
#     @http.route('/compraventa_divisas/compraventa_divisas/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/compraventa_divisas/compraventa_divisas/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('compraventa_divisas.listing', {
#             'root': '/compraventa_divisas/compraventa_divisas',
#             'objects': http.request.env['compraventa_divisas.compraventa_divisas'].search([]),
#         })

#     @http.route('/compraventa_divisas/compraventa_divisas/objects/<model("compraventa_divisas.compraventa_divisas"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('compraventa_divisas.object', {
#             'object': obj
#         })
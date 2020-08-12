# odoo_rpc_api
Simple Odoo xmlrpc library

If you're looking for something that's more abstracted, checkout the [odoo_rpc_client](https://pypi.org/project/odoo-rpc-client/) library.

This library was built to make the developer fully aware of how many rpc calls are being made, as to improve software efficiency.

Or maybe I'm just lazy while needlessly re-inventing the wheel idk.


Creating a Basic script
----

<i>Setup Odoo connection:</i>
```python
from odoo import Odoo
env = Odoo(
    database='odoo',
    username='admin',
    password='admin',
    url='http://localhost',
    port=8069
)
```
---
Model reads and writes use similar commands to Odoo's ORM API

Read
----
<i>Search (returns list of record ids):</i>
```python
env['sale.order'].search([('partner_id', '=', 4)])
# Optional arguments: 'offset' and 'limit'
env['sale.order'].search([('partner_id', '=', 4)], offset=10, limit=10)
```
<i>Browse (returns list of record dicts):</i>
```python
env['sale.order'].browse(13, ['name', 'partner_id'])
env['sale.order'].browse([13, 14, 15], ['name', 'partner_id'])
```
<i>Search + Browse (returns list of record dicts):</i>
```python
env['sale.order'].search_browse([('partner_id', '=', 4)], ['name', 'partner_id'])
# Optional arguments: 'offset' and 'limit'
env['sale.order'].search_browse([('partner_id', '=', 4)], ['name', 'partner_id'], offset=10, limit=10)
```
<i>Search Count (simple method to get the number of records in a domain):</i>
```python
env['sale.order'].search_count([('partner_id', '=', 4)])
```

Write
----
<i>Create single record:</i>
```python
env['res.partner'].create({'name': "RogueNAND"})
```
<i>Update record(s):</i>
```python
env['res.partner'].write(2, {'name': "RogueNAND"})
env['res.partner'].write([2, 3, 4], {'name': "RogueNAND"})
```
<i>Delete record(s):</i>
```python
env['res.partner'].delete(2)
env['res.partner'].delete([2, 3, 4])
```
<i>Call method:</i>
```python
env['res.partner'].call([2, 3], 'custom_method', arg1, arg2, kw1=5, kw2=12)
# For methods wrapped with @api.model
env['res.partner'].call_model('custom_method', arg1, arg2, kw1=5, kw2=12)
```

Fetching Relational Fields
----
For 'browse' and 'search_browse', X2many and One2many fields only return record ids by default. You can use 'x2m' and 'm2o' to fetch detailed records.

<i>(Note: every 'x2m' or 'o2m' field creates an additional call to Odoo)</i>
```python
from odoo import x2m, m2o
# Fetch a Many2one field
env['sale.order'].browse(5, ['name', m2o('partner_id', 'res.partner', ['name', 'email'])])
"""
[
    {
        'id': 5, 
        'name': 'S00005', 
        'partner_id': {
            'id': 10, 
            'name': 'Deco Addict',
            'email': 'deco.addict82@example.com'
        }
    }
]
"""

# Fetch a X2many field
env['sale.order'].browse(5, ['name', x2m('order_line', 'sale.order.line', ['name', 'product_uom_qty'])])
"""
[
    {
        'id': 5, 
        'name': 'S00005', 
        'order_line': [{
            'id': 12,
            'name': '[FURN_8888] Office Lamp', 
            'product_uom_qty': 1.0
        }]
    }
]
"""
```


License
----

MIT

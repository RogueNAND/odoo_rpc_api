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

License
----

MIT

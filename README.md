# odoo_rpc_api
Simple Odoo xmlrpc library

If you're looking for something that's more abstracted, checkout the [odoo_rpc_client](https://pypi.org/project/odoo-rpc-client/) library.

This library was built so that the developer is fully aware of how many rpc calls are being made, as to improve software efficiency.

Or maybe I'm just lazy while needlessly re-inventing the wheel idk.


Creating a Basic script
----

Setup Odoo connection:
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

Accessing Models and their read/write commands is similar to Odoo's ORM API
```python
# Search for ids
env['sale.order'].search([('partner_id', '=', 4)])
# Optional arguments: 'offset' and 'limit'
env['sale.order'].search([('partner_id', '=', 4)], offset=10, limit=10)

# Browse record(s) (return specified fields)
env['sale.order'].browse(13, ['name', 'partner_id'])
env['sale.order'].browse([13, 14, 15], ['name', 'partner_id'])

# Search and Browse (return specified fields)
env['sale.order'].search_browse([('partner_id', '=', 4)], ['name', 'partner_id'])
# Optional arguments: 'offset' and 'limit'
env['sale.order'].search_browse([('partner_id', '=', 4)], ['name', 'partner_id'], offset=10, limit=10)

# Only get record count
env['sale.order'].search_count([('partner_id', '=', 4)])



# Create single record
env['res.partner'].create({'name': "RogueNAND"})

# Update record(s)
env['res.partner'].write(2, {'name': "RogueNAND"})
env['res.partner'].write([2, 3, 4], {'name': "RogueNAND"})

# Delete record(s)
env['res.partner'].delete(2)
env['res.partner'].delete([2, 3, 4])



# Call method
env['res.partner'].call([2, 3], 'custom_method', arg1, arg2, kw1=5, kw2=12)
# For methods wrapped with @api.model
env['res.partner'].call_model('custom_method', arg1, arg2, kw1=5, kw2=12)
```

License
----

MIT

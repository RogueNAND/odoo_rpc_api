import xmlrpc.client, logging, time, socket, ssl
from typing import List, Tuple, Union, Dict

logger = logging.getLogger('odoo_connector')

DomainT = List[Tuple[str, str, any]]
IdsT = Union[int, List[int]]


class x2m:
    _type = 'x2m'

    def __init__(self, field: str, model: str, fields: List[str]):
        self.field_name = field
        self.model = model
        self.fields = fields

    def gather_ids_to_fetch(self, records: List[dict]) -> list:
        ids = set()
        for record in records:
            ids.update(record[self.field_name])
        return list(ids)

    def field_to_recordset(self, records: List[dict], field_records: Dict[str, dict]):
        for record in records:
            ids = record[self.field_name]
            record[self.field_name] = [
                field_records[id]
                for id in ids
            ]
        return records


class m2o(x2m):
    _type = 'm2o'

    def gather_ids_to_fetch(self, records: List[dict]) -> list:
        return [records[0][self.field_name][0]]

    def field_to_recordset(self, records: List[dict], field_records: Dict[str, dict]):
        for record in records:
            id = record[self.field_name][0]
            record[self.field_name] = field_records[id]
        return records


FieldsT = Union[List[str], x2m]


class Model:
    def __init__(self, env, model: str):
        self.env = env
        self.model = model

    def call(self, ids: IdsT, method: str, *args, **kwargs):
        """ Calls a method on selected record ids

        :param ids: ids to call the method on
        :param method: name of method to call
        :param args: method args
        :param kwargs: method kwargs
        :return: same as method return
        """

        if isinstance(ids, int):
            ids = [ids]

        logger.debug(f"Call_Records ({self.model}:{ids}): {args} {kwargs}")

        return self.env._exec(self.model, method, [ids] + list(args), kwargs)

    def call_model(self, method: str, *args, **kwargs):
        """ Calls a model method

        :param method: name of method to call
        :param args: method args
        :param kwargs: method kwargs
        :return: same as method return
        """

        logger.debug(f"Call_Model ({self.model}): {args} {kwargs}")

        return self.env._exec(self.model, method, args, kwargs)

    """ Read """

    def search(self, domain: DomainT, offset: int = None, limit: int = None) -> List[int]:
        """ Searches a model for specific attributes and returns ids

        :param domain: filter
        :param offset: number to offset the returned items by
        :param limit: limit the number of items by a specified amount
        :return: list of record ids
        """

        conditions = {}
        if offset:
            conditions.update({'offset': offset})
        if limit:
            conditions.update({'limit': limit})

        logger.debug(f"Search ({self.model}): {domain}")

        return self.env._exec(self.model, 'search', [domain], conditions)

    def browse(self, ids: IdsT, fields: FieldsT) -> List[dict]:
        """ Reads the specified records and returns specified fields

        :param ids: id OR list of ids to read
        :param fields: list of fields to return
        :return: list of record dicts
        """

        if isinstance(ids, int):
            ids = [ids]

        logger.debug(f"Read ({self.model}): {ids}")

        # Grab Many-fields for post processing
        fields, many_fields = extract_many_fields(fields)

        result = self.env._exec(self.model, 'read', [ids], {'fields': fields})

        return apply_many_fields(self.env, result, many_fields)

    def search_browse(self, domain: DomainT, fields: FieldsT, offset: int = None, limit: int = None) -> List[dict]:
        """ Searches for records and returns a specified records

        :param domain: filter
        :param fields: list of fields to return
        :param offset: number to offset the returned items by
        :param limit: limit the number of items by a specified amount
        :return: list of record dicts
        """

        logger.debug(f"Search_Read ({self.model}): {domain}")

        # Grab Many-fields for post processing
        fields, many_fields = extract_many_fields(fields)

        fields = {'fields': fields}
        if offset:
            fields.update({'offset': offset})
        if limit:
            fields.update({'limit': limit})

        result = self.env._exec(self.model, 'search_read', [domain], fields)

        return apply_many_fields(self.env, result, many_fields)

    def search_count(self, domain: DomainT) -> int:
        """ Searches a model and returns the number of matching records

        :param domain: filter
        :return: number of matching records
        """

        logger.debug(f"Search_Count ({self.model}): {domain}")

        return self.env._exec(self.model, 'search_count', [domain])

    """ Write """

    def create(self, fields: Dict[str, any]) -> int:
        """ Creates a new record

        :param fields: field values to set in new record
            e.g.
                {'name': "Item 1", 'description': "Test 1"}
        :return: id of new record
        """

        logger.info(f"Create ({self.model}): {fields}")

        return self.env._exec(self.model, 'create', [fields])

    def write(self, ids: IdsT, fields: Dict[str, any]) -> bool:
        """ Updates existing records

        :param ids: list of ids to update
        :param fields: dict of fields and their values
        :return: True if fields were written successfully, otherwise False
        """

        if isinstance(ids, int):
            ids = [ids]

        logger.info(f"Write ({self.model}): {ids} - {fields}")

        return self.env._exec(self.model, 'write', [ids, fields])

    def delete(self, ids: IdsT) -> bool:
        """ Deletes specified ids

        :param ids: list of ids to delete
        :return: True if record was deleted successfully, otherwise False
        """

        if isinstance(ids, int):
            ids = [ids]

        logger.info(f"Unlink ({self.model}): {ids}")

        try:
            return self.env._exec(self.model, 'unlink', ids) or False
        # Return false if id doesn't exist
        except xmlrpc.client.Fault as e:
            # Record doesn't exist
            if e.faultCode == 2 and 'not exist' in e.faultString:
                logger.error(f"Could not delete records {ids}: does not exist")
                return False
            # Linked to other records
            elif e.faultCode == 1 and 'If possible, archive it instead' in e.faultString:
                logger.error(f"Could not delete records {ids}: other records rely on these")
                return False
            raise


class Odoo:
    """ CRUD """

    def __init__(self, database: str, username: str, password: str, url: str, port: int):
        """ Create connection """

        self.db = database
        self.username = username
        self.password = password
        self.port = port
        self.url_common = f"{url}:{port}/xmlrpc/2/common"
        self.url_models = f"{url}:{port}/xmlrpc/2/object"
        self.odoo_common = xmlrpc.client.ServerProxy(self.url_common)
        self.odoo_models = xmlrpc.client.ServerProxy(self.url_models)

        self._connect()

    def _connect(self):
        """ Connect and authenticate with Odoo """

        logger.info(f"Connecting to Odoo: {self.db}")

        self.uid = None
        retry_delay = 5
        while self.uid is None:
            try:
                self.uid = self.odoo_common.authenticate(
                    self.db,
                    self.username,
                    self.password,
                    {}
                )
                logger.info("Connection successful!")
            except ConnectionRefusedError:
                logging.critical(
                    f"Connection refused! (cannot access Odoo on port {self.port}) {self.url_common} Trying again in {retry_delay} seconds.")
            except TimeoutError:
                logging.critical(f"Connection timed out! {self.url_common} Trying again in {retry_delay} seconds.")
            # Database not found
            except xmlrpc.client.Fault as e:
                if f'database "{self.db}" does not exist' in e.faultString:
                    raise xmlrpc.client.Fault(e.faultCode, f"Database not found: {self.db}") from e
                raise
            # URL error
            except socket.gaierror as e:
                if e.errno == 11001:
                    raise socket.gaierror(e.errno, f"Bad url: {self.url_common}")
            # Using https on http port
            except ssl.SSLError as e:
                if e.reason == 'WRONG_VERSION_NUMBER':
                    raise Exception("Bad SSL (Probably need http. Are you using https?)") from e
                raise
            # using http on https port
            except xmlrpc.client.ProtocolError as e:
                raise Exception("ProtocolError (e.g. make sure you're using https on an https port)") from e
            time.sleep(retry_delay)
            retry_delay = min(30, retry_delay + 5)

    def _exec(self, *args):
        """ Abstracted communication with Odoo """

        try:
            return self.odoo_models.execute_kw(
                self.db,
                self.uid,
                self.password,
                *args
            )
        except xmlrpc.client.Fault as e:
            if 'security.check(db,uid,passwd)' in e.faultString:
                raise xmlrpc.client.Fault(e.faultCode, f"Wrong username or password!")
            raise
        except Exception as e:
            logger.error(f"Error in _exec(): {args}\n{e}")
            raise

    def __getitem__(self, model: str) -> Model:
        return Model(self, model)


def extract_many_fields(fields: FieldsT) -> Tuple[List[str], List[x2m]]:
    """ Separate 'string' fields from 'Many' fields
    Every 'many' field requires a call to Odoo AFTER the parent model call

    EXAMPLE:
    A call to Odoo using a 'many' field would work something like this:
        fields_to_get = ['name', Many('partner_id', 'res.partner', ['name', 'email'])]
        customer = odoo['sale.order'].browse(5, fields_to_get)
    The following operations will be performed:
        Fetch sale.order id=5 with fields 'name' and 'partner_id'
        Fetch res.partner ids=(determined by previous fetch) with fields 'name' and 'email'
        Merge res.partner records into the sale.order record

    :param fields: list of fields
    :return: Tuple (fields_list, many_fields_list)
    """

    many_fields = []
    for i, field in enumerate(fields):
        if isinstance(field, x2m):
            # Save Many-field for post-processing
            many_fields.append(field)
            # Replace Many-field with string
            fields[i] = field.field_name

    return fields, many_fields


def apply_many_fields(odoo: Odoo, fetched_records: List[dict], many_fields: List[x2m]) -> List[dict]:
    """ fetches additional required model data

    :param odoo: used to fetch new data from odoo
    :param fetched_records: recordset to update fields
    :param many_fields: list of 'Many' objects
    :return: modified fetched_records
    """

    for many_field in many_fields:
        model = many_field.model

        # Gather list of ids to fetch
        ids = many_field.gather_ids_to_fetch(fetched_records)

        # Fetch record dicts
        field_records = odoo[model].browse(ids, many_field.fields)

        # Organize records into a dict (key=id)
        field_records = {
            record['id']: record
            for record in field_records
        }

        # Apply field_records to each record in fetched_records
        fetched_records = many_field.field_to_recordset(fetched_records, field_records)

    return fetched_records

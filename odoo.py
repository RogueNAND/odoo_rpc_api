import xmlrpc.client, logging, time, socket, ssl
from typing import List, Tuple, Union, Dict

logger = logging.getLogger('odoo_connector')

DomainType = List[Tuple[str, str, any]]
IdsType = Union[int, List[int]]


class Model:
    def __init__(self, env, model: str):
        self.env = env
        self.model = model

    def call(self, ids: IdsType, method: str, *args, **kwargs):
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

    def search(self, domain: DomainType, offset: int = None, limit: int = None) -> List[int]:
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

    def browse(self, ids: IdsType, fields: List[str]) -> List[dict]:
        """ Reads the specified records and returns specified fields

        :param ids: id OR list of ids to read
        :param fields: list of fields to return
        :return: list of record dicts
        """

        if isinstance(ids, int):
            ids = [ids]

        logger.debug(f"Read ({self.model}): {ids}")

        return self.env._exec(self.model, 'read', [ids], {'fields': fields})

    def search_browse(self, domain: DomainType, fields: List[str], offset: int = None, limit: int = None) -> List[dict]:
        """ Searches for records and returns a specified records

        :param domain: filter
        :param fields: list of fields to return
        :param offset: number to offset the returned items by
        :param limit: limit the number of items by a specified amount
        :return: list of record dicts
        """

        fields = {'fields': fields}
        if offset:
            fields.update({'offset': offset})
        if limit:
            fields.update({'limit': limit})

        logger.debug(f"Search_Read ({self.model}): {domain}")

        return self.env._exec(self.model, 'search_read', [domain], fields)

    def search_count(self, domain: DomainType) -> int:
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

    def write(self, ids: IdsType, fields: Dict[str, any]) -> bool:
        """ Updates existing records

        :param ids: list of ids to update
        :param fields: dict of fields and their values
        :return: True if fields were written successfully, otherwise False
        """

        if isinstance(ids, int):
            ids = [ids]

        logger.info(f"Write ({self.model}): {ids} - {fields}")

        return self.env._exec(self.model, 'write', [ids, fields])

    def delete(self, ids: IdsType) -> bool:
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
                print(e.reason)
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

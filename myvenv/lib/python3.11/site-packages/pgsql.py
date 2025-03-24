# Copyright (c) 2010-2024 Antti Heinonen <antti@heinonen.cc>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from struct import unpack
from operator import methodcaller
from dataclasses import make_dataclass

types = {
    16:     lambda x: x == b"t",    # bool
    20:     int,                    # int8
    21:     int,                    # int2
    23:     int,                    # int4
    26:     int,                    # oid
    700:    float,                  # float4
    701:    float,                  # float8
    1700:   float,                  # numeric
}

_UTF_8 = methodcaller("decode")

def _authentication_request(data):
    return int.from_bytes(data[:4], signed = True), data[4:]

def _error_response(data):
    details = { field[0]: field[1:].decode() for field in data[:-2].split(b"\x00") }
    match details[86]:
        case "ERROR": exception = Error
        case "FATAL": exception = Fatal
        case "PANIC": exception = Panic
    return exception(f"{details[77]} ({details[67]})")

def _row_description(data):
    count = int.from_bytes(data[:2], signed = True)
    data = data[2:]
    field_names = []
    field_types = []
    for i in range(count):
        name, data = data.split(b"\x00", 1)
        desc = unpack("!ihihih", data[:18])
        data = data[18:]
        field_names.append(f"_{i}" if name[0] == 63 else name.decode().replace(" ", "_"))
        field_types.append(types.get(desc[2], _UTF_8))
    return field_names, field_types

class _DataRow(bytes):
    def __call__(self, types):
        count = int.from_bytes(self[:2], signed = True)
        i = 2
        for n in range(count):
            size = int.from_bytes(self[i:i + 4], signed = True)
            i += 4
            if size == -1:
                yield None
            else:
                yield types[n](self[i:i + size])
                i += size

class Statement:
    def __init__(self, connection, statement, named, dataclass):
        self._get_ready = connection._get_ready
        self._send_message = connection._send_message
        self._read_message = connection._read_message
        self._name = str(hash(statement)).encode() + b"\x00" if named else b"\x00"
        p_msg = self._name + statement.encode() + b"\x00\x00\x00"
        self._send_message(
            b"P" + (len(p_msg) + 4).to_bytes(4, signed = True) + p_msg +
            b"D" + (len(self._name) + 5).to_bytes(4, signed = True) + b"S" + self._name +
            b"S\x00\x00\x00\x04H\x00\x00\x00\x04"
        ) # Parse + Describe + Sync + Flush
        self._get_ready(ready = False)
        self._read_message() # ParseComplete
        self._read_message() # ParameterDescription
        msg = self._read_message() # RowDescription
        if msg == 110: # NoData
            self._factory = None
        else:
            self._factory = make_dataclass(
                dataclass.__name__,
                msg[0],
                bases = (dataclass,),
                slots = True
            ) if dataclass else make_dataclass(
                "Row",
                msg[0],
                slots = True
            )
            self._types = msg[1]
        self._read_message() # ReadyForQuery

    def __enter__(self):
        return self

    def __exit__(self, error, value, traceback):
        self.close()
        if error:
            raise

    def __call__(self, *args):
        """
        Execute the statement and return a row generator or None. Returns an
        iterator of dataclass instances or None.

        Arguments:
            *args: Arguments for the prepared SQL statement. Must be representable as strings.
        """
        b_msg = b"\x00" + self._name + b"\x00\x00" + len(args).to_bytes(2, signed = True)
        for arg in args:
            if arg is None:
                b_msg += b"\xff\xff\xff\xff"
            else:
                arg = str(arg).encode()
                b_msg += len(arg).to_bytes(4, signed = True) + arg
        b_msg +=  b"\x00\x00"
        self._send_message(
            b"B" + (len(b_msg) + 4).to_bytes(4, signed = True) + b_msg +
            b"E\x00\x00\x00\t\x00\x00\x00\x00\x00S\x00\x00\x00\x04H\x00\x00\x00\x04"
        ) # Bind + Execute + Sync + Flush
        self._get_ready(ready = False)
        self._read_message() # BindComplete
        if self._factory:
            return self
        self._read_message() # ReadyForQuery

    def __iter__(self):
        while (row := self._read_message()): # DataRow
            yield self._factory(*row(self._types))

    def row(self):
        """
        Return the first row. Returns a dataclass instance or None.
        """
        row = self._read_message() # DataRow
        if row:
            return self._factory(*row(self._types))

    def col(self):
        """
        Return the first column of the first row. Returns a single value or None.
        """
        row = self._read_message() # DataRow
        if row:
            return next(row(self._types))

    def close(self):
        """
        Close the statement.
        """
        self._send_message(
            b"C" + (len(self._name) + 5).to_bytes(4, signed = True) + b"S" + self._name +
            b"H\x00\x00\x00\x04"
        ) # Close + Flush
        self._get_ready()
        self._read_message() # CloseComplete

class Transaction:
    def __init__(self, connection):
        self.begin = connection.begin
        self.commit = connection.commit
        self.rollback = connection.rollback

    def __enter__(self):
        self.begin()

    def __exit__(self, error, value, traceback):
        if error:
            self.rollback()
            raise
        self.commit()

class Connection:
    def __init__(self,
            address: tuple[str, int] | str = ("localhost", 5432),
            user: str = "postgres",
            password: str | None = None,
            database: str | None = None,
            tls: bool = False,
            tls_cert: str | None = None,
            tls_ca: str | None = None
        ) -> None:
        """
        Create a database connection.

        Arguments:
            address: Server address. Either a tuple (host, port) or a string denoting a Unix domain socket.
            user: Name of the database user.
            password: Password of the database user.
            database: Name of the database if different from user.
            tls: Use TLS. If either tls_cert or tls_ca is set, True is implied and this setting has no effect.
            tls_cert: Path to a PEM-format file containing the private key and certificate used for certificate authentication.
            tls_ca: Path to a PEM-format file containing the certificates of trusted certificate authorities. If None, system defaults are loaded instead.
        """
        if isinstance(address, str):
            from socket import socket, AF_UNIX
            self._sock = socket(AF_UNIX)
        else:
            from socket import socket, IPPROTO_TCP, TCP_NODELAY
            self._sock = socket()
            self._sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self._sock.connect(address)
        if tls or tls_cert or tls_ca:
            self._send_message(
                b"\x00\x00\x00\x08\x04\xd2\x16/"
            ) # SSLRequest
            if self._receive(1) != b"S":
                raise Fatal("server denied the TLS request")
            from ssl import SSLContext, PROTOCOL_TLS_CLIENT
            context = SSLContext(PROTOCOL_TLS_CLIENT)
            if tls_cert:
                context.load_cert_chain(tls_cert)
            if tls_ca:
                context.load_verify_locations(tls_ca)
            else:
                context.load_default_certs()
            self._sock = context.wrap_socket(self._sock, server_hostname = address[0])
        s_msg = b"\x00\x03\x00\x00user\x00" + user.encode() + b"\x00"
        if database:
            s_msg += b"database\x00" + database.encode() + b"\x00"
        s_msg += b"client_encoding\x00UTF8\x00\x00"
        self._send_message(
            (len(s_msg) + 4).to_bytes(4, signed = True) + s_msg
        ) # StartupMessage
        code, data = self._read_message()
        if code in (3, 5, 10):
            if not password:
                raise Fatal("server requested a password but none was provided")
            match code:
                case 3: self._auth_password(password) # AuthenticationCleartextPassword
                case 5: self._auth_md5(user, password, data) # AuthenticationMD5Password
                case 10: self._auth_scram_sha_256(user, password) # AuthenticationSASL
        elif code != 0: # AuthenticationOk
            raise Fatal("server requested an unsupported authentication method")
        while self._read_message(): pass # ReadyForQuery
        self.begin = self.prepare("BEGIN")
        self.commit = self.prepare("COMMIT")
        self.rollback = self.prepare("ROLLBACK")

    def __enter__(self):
        return self

    def __exit__(self, error, value, traceback):
        self.close()
        if error:
            raise

    def __call__(self, statement, *args, dataclass = None):
        """
        Execute a one-time statement. Returns an iterator of dataclass instances or None.

        Arguments:
            statement: The SQL statement to execute.
            *args: Arguments for the SQL statement. Must be representable as strings.
            dataclass: A base for the dataclass used for generating rows.
        """
        return Statement(self, statement, False, dataclass)(*args)

    def prepare(self, statement, dataclass = None):
        """
        Prepare a statement. Returns an pgsql.Statement instance.

        Arguments:
            statement: The SQL statement to prepare.
            dataclass: A base for the dataclass used for generating rows.
        """
        return Statement(self, statement, True, dataclass)

    def explain(self, statement, *args, analyze = False):
        """
        Show the execution plan of a statement. Returns the execution plan in JSON format.

        Arguments:
            statement: The SQL statement to explain.
            *args: Arguments for the SQL statement. Must be representable as strings.
            analyze: Include run time statistics by executing the statement.
        """
        return Statement(
            self,
            "EXPLAIN (FORMAT JSON" + (", ANALYZE) " if analyze else ") ") + statement,
            False,
            None
        )(*args).col()

    def execute(self, string = None, file = None):
        """
        Execute one or more statements as a single transaction. Don't retrieve data. Returns None.

        Arguments:
            string: A string containing one or more SQL statements to execute. Ignored if file is set.
            file: A path to a file containing one or more SQL statements to execute.
        """
        if file:
            with open(file) as f:
                string = f.read()
        q_msg = string.encode() + b"\x00"
        self._send_message(
            b"Q" + (len(q_msg) + 4).to_bytes(4, signed = True) + q_msg
        ) # Query
        self._get_ready(ready = False)
        self._get_ready()

    def transaction(self):
        """
        Begin a transaction in a with statement context. Returns a pgsql.Transaction instance
        that executes BEGIN on entry and COMMIT (or ROLLBACK in case of an exception) on
        exit from a with statement.
        """
        return Transaction(self)

    def close(self):
        """
        Close the database connection.
        """
        self._send_message(
            b"X\x00\x00\x00\x04"
        ) # Terminate
        self._sock.close()

    def _receive(self, size):
        data = self._sock.recv(size)
        while(len(data) < size):
            data += self._sock.recv(size - len(data))
        return data

    def _read_message(self):
        code, size = unpack("!bi", self._receive(5))
        if size > 4:
            data = self._receive(size - 4)
        match code:
            case 68: return _DataRow(data) # DataRow
            case 84: return _row_description(data) # RowDescription
            case 90: # ReadyForQuery
                self._ready = True
                return
            case 67: return self._read_message() # CommandComplete
            case 73: return self._read_message() # EmptyQueryResponse
            case 83: return self._read_message() # ParameterStatus
            case 78: return self._read_message() # NoticeResponse
            case 82: return _authentication_request(data)
            case 69: raise _error_response(data) # ErrorResponse
            case 65: raise Fatal("LISTEN not supported") # NotificationResponse
            case 71: raise Fatal("COPY between client and server not supported") # CopyInResponse
            case 72: raise Fatal("COPY between client and server not supported") # CopyOutResponse
            case 87: raise Fatal("COPY between client and server not supported") # CopyBothResponse
        return code

    def _send_message(self, data):
        self._sock.sendall(data)

    def _get_ready(self, ready = True):
        if not self._ready:
            while self._read_message(): pass # ReadyForQuery
        self._ready = ready

    def _auth_password(self, password):
        p_msg = password.encode() + b"\x00"
        self._send_message(
            b"p" + (len(p_msg) + 4).to_bytes(4, signed = True) + p_msg
        ) # PasswordMessage

    def _auth_md5(self, user, password, salt):
        from hashlib import md5
        p_msg = md5(password.encode() + user.encode()).hexdigest().encode()
        p_msg = b"md5" + md5(p_msg + salt).hexdigest().encode() + b"\x00"
        self._send_message(
            b"p" + (len(p_msg) + 4).to_bytes(4, signed = True) + p_msg
        ) # PasswordMessage

    def _auth_scram_sha_256(self, user, password):
        from base64 import standard_b64decode, standard_b64encode
        from hashlib import pbkdf2_hmac, sha256
        from hmac import digest, compare_digest
        from os import urandom
        if not (user.isascii() and password.isascii()):
            raise Fatal("user and password must consist of ASCII characters only")
        user = user.replace(",", "=2C").replace("=", "=3D")
        sasl_auth_mechanism = b"SCRAM-SHA-256\x00"
        client_nonce = standard_b64encode(urandom(24))
        client_first_bare = b"n=" + user.encode() + b",r=" + client_nonce
        client_first_message = b"n,," + client_first_bare
        self._send_message(
            b"p" +
            (len(sasl_auth_mechanism) + len(client_first_message) + 8).to_bytes(4, signed = True) +
            sasl_auth_mechanism +
            len(client_first_message).to_bytes(4, signed = True) +
            client_first_message
        ) # SASLInitialResponse
        code, server_first_message = self._read_message()
        if code != 11: # AuthenticationSASLContinue
            raise Fatal("server didn't respond with an AuthenticationSASLContinue message")
        parsed = dict(item.split(b"=", 1) for item in server_first_message.split(b","))
        if not parsed[b"r"].startswith(client_nonce):
            raise Fatal("server returned an invalid nonce")
        without_proof = b"c=biws,r=" + parsed[b"r"]
        auth_message = b",".join((client_first_bare, server_first_message, without_proof))
        salted_password = pbkdf2_hmac(
            "sha256",
            password.encode(),
            standard_b64decode(parsed[b"s"]),
            int(parsed[b"i"])
        )
        client_key = digest(salted_password, b"Client Key", "sha256")
        client_sig = digest(sha256(client_key).digest(), auth_message, "sha256")
        client_proof = bytes(x ^ y for x, y in zip(client_key, client_sig))
        client_final_message = without_proof + b",p=" + standard_b64encode(client_proof)
        self._send_message(
            b"p" +
            (len(client_final_message) + 4).to_bytes(4, signed = True) +
            client_final_message
        ) # SASLResponse
        code, server_final_message = self._read_message()
        if code != 12: # AuthenticationSASLFinal
            raise Fatal("server didn't respond with an AuthenticationSASLFinal message")
        parsed = dict(item.split(b"=", 1) for item in server_final_message.split(b","))
        server_key = digest(salted_password, b"Server Key", "sha256")
        server_sig = digest(server_key, auth_message, "sha256")
        if not compare_digest(parsed[b"v"], standard_b64encode(server_sig)):
            raise Fatal("server returned an invalid signature")

class Error(Exception):
    """An error that caused the current command to abort."""
    pass

class Fatal(Exception):
    """An error that caused the current session to abort."""
    pass

class Panic(Exception):
    """An error that caused all sessions to abort."""
    pass
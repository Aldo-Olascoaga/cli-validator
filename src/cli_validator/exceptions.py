class UnknownTypeException(Exception):
    def __init__(self, typ):
        self.msg = f'Unknown Type: {typ}.'


class ValidateFailureException(Exception):
    def __init__(self, msg):
        self.msg = msg


class ParserFailureException(ValidateFailureException):
    def __init__(self, msg):
        super().__init__(msg)


class ParserHelpException(ValidateFailureException):
    def __init__(self):
        super().__init__('The user inputs `-h/--help`. This is not a real exception.')


class EmptyCommandException(ValidateFailureException):
    def __init__(self):
        super().__init__('The input command is empty.')


class NonAzCommandException(ValidateFailureException):
    def __init__(self):
        super().__init__('The input command is not an Azure CLI command.')


class CommandTreeCorruptedException(ValidateFailureException):
    def __init__(self, tree_type):
        super().__init__(f'The {tree_type} CommandTree is Corrupted. Fail to find parent module/extension of command.')


class UnknownCommandException(ValidateFailureException):
    def __init__(self, command):
        super().__init__(f'Unknown Command: {command}.')

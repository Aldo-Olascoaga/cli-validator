import argparse
from typing import NoReturn

from cli_validator.exceptions import ParserHelpException, UnknownTypeException, ParserFailureException


class CustomHelpAction(argparse.Action):
    """
    The new help action to overwrite the origin help implementation.\n
    Now the help will raise an Exception to avoid the check of required arguments.
    """

    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        raise ParserHelpException()


class CLIParser(argparse.ArgumentParser):
    DEBUG_FLAG = '--debug'
    VERBOSE_FLAG = '--verbose'
    ONLY_SHOW_ERRORS_FLAG = '--only-show-errors'

    OUTPUT_DEST = '_output_format'

    _OUTPUT_FORMAT_DICT = {
        'json',
        'jsonc',
        'yaml',
        'yamlc',
        'table',
        'tsv',
        'none',
    }

    @staticmethod
    def jmespath_type(raw_query):
        """Compile the query with JMESPath and return the compiled result.
        JMESPath raises exceptions which subclass from ValueError.
        In addition, though, JMESPath can raise a KeyError.
        ValueErrors are caught by argparse so argument errors can be generated.
        """
        from jmespath import compile as compile_jmespath
        try:
            return compile_jmespath(raw_query)
        except KeyError as ex:
            # Raise a ValueError which argparse can handle
            raise ValueError from ex

    @staticmethod
    def convert_type(type_name):
        if type_name == 'String' or type_name == 'str' or type_name == 'List<String>':
            return str
        elif type_name == 'Boolean' or type_name == 'bool' or type_name == 'List<Boolean>':
            return bool
        elif type_name == 'Int' or type_name == 'int' or type_name == 'List<Int>':
            return int
        elif type_name == 'Float' or type_name == 'float' or type_name == 'List<Float>':
            return float
        elif type_name == 'custom_type':  # location
            return str
        elif type_name == 'file_type':
            return str
        elif type_name == 'Object':  # eventhubs namespace update --identity
            return str
        elif type_name == 'Dict<String,String>':  # tag(use shorthand syntax)
            return str
        elif type_name == 'List<Object>':  # eventhubs namespace update --identity
            return str
        elif type_name == 'Dict<String,Object>':  # monitor log-analytics cluster create --user-assigned
            return str
        elif type_name == 'Dict<String,List<String>>':
            return str
        elif type_name == 'Duration':  # monitor autoscale show-predictive-metric --interval
            return int
        elif type_name == 'DateTime':  # monitor autoscale show-predictive-metric --interval
            return str
        elif type_name == 'Password':  # monitor autoscale show-predictive-metric --interval
            return str
        else:
            raise UnknownTypeException(type_name)

    @staticmethod
    def create_global_parser():
        """
        Create a global Argument Parser for Global Arguments. This should be the parent of all subcommands.
        """
        global_parser = argparse.ArgumentParser(add_help=False)
        arg_group = global_parser.add_argument_group('global', 'Global Arguments')
        arg_group.add_argument(CLIParser.VERBOSE_FLAG, dest='_log_verbosity_verbose', action='store_true',
                               help='Increase logging verbosity. Use --debug for full debug logs.')
        arg_group.add_argument(CLIParser.DEBUG_FLAG, dest='_log_verbosity_debug', action='store_true',
                               help='Increase logging verbosity to show all debug logs.')
        arg_group.add_argument(CLIParser.ONLY_SHOW_ERRORS_FLAG, dest='_log_verbosity_only_show_errors',
                               action='store_true',
                               help='Only show errors, suppressing warnings.')
        arg_group.add_argument('--output', '-o', dest=CLIParser.OUTPUT_DEST,
                               choices=list(CLIParser._OUTPUT_FORMAT_DICT),
                               default='json',
                               help='Output format',
                               type=str.lower)
        arg_group.add_argument('--query', dest='_jmespath_query', metavar='JMESPATH',
                               help='JMESPath query string. See http://jmespath.org/ for more'
                                    ' information and examples.',
                               type=CLIParser.jmespath_type)
        return global_parser

    def __init__(self, **kwargs):
        self.subparsers = {}
        self.parents = kwargs.get('parents', [])
        # Overwrite the old help implement
        add_help = kwargs.get('add_help', True)
        kwargs['add_help'] = False
        super().__init__(**kwargs)
        self.register('action', 'help', CustomHelpAction)
        if add_help:
            self.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS)

    def load_meta(self, meta):
        """
        Load metadata of a module
        :param meta: loaded metadata dict
        """
        for param in meta['parameters']:
            kwargs = {
                'choices': param.get('choices'),
                'nargs': param.get('nargs'),
                'dest': param.get('name'),
                'default': param.get('default'),
                'type': self.convert_type(param.get('type')) if param.get('type') else None,
            }
            self.add_argument(*param['options'], **kwargs)

    def error(self, message: str) -> NoReturn:
        """
        Raise an exception when parse fails.
        :param message: error message
        """
        raise ParserFailureException(message)

from cli_validator.cmd_meta.loader import load_metas, build_command_tree
from cli_validator.cmd_meta.parser import CLIParser
from cli_validator.cmd_tree import parse_command
from cli_validator.exceptions import ValidateFailureException


class CommandMetaValidator(object):
    """A validator using Command Metadata generated from breaking change tool"""

    def __init__(self, version: str, cache_dir: str = './cmd_meta'):
        """
        :param version: the version of `azure-cli` that provides the metadata
        :param cache_dir: cache directory that store the downloaded metadata
        """
        self.metas = load_metas(version, cache_dir)
        self.command_tree = build_command_tree(self.metas)
        self._global_parser = CLIParser.create_global_parser()

    def validate_command(self, command, comments=True):
        """
        Validate a command to check if the command is valid
        :param command: command to be validated
        :param comments: whether parse comments in the given command
        :return: parsed namespace
        """
        cmd = parse_command(self.command_tree, command, comments)
        meta = self.load_command_meta(cmd.signature, cmd.module)
        parser = self.build_parser(meta)
        namespace = parser.parse_args(cmd.parameters)
        missing_args = []

        if namespace.ids is not None:
            for param in meta['parameters']:
                if 'id_part' in param:
                    continue
                else:
                    if 'required' in param and namespace.__getattribute__(param['name']) is None:
                        missing_args.append('/'.join(param['options']))
        else:
            for param in meta['parameters']:
                if 'required' in param and namespace.__getattribute__(param['name']) is None:
                    missing_args.append('/'.join(param['options']))

        if len(missing_args) > 0:
            raise ValidateFailureException(f"the following arguments are required: {', '.join(missing_args)} ")

    def load_command_meta(self, signature, module):
        """
        Load metadata of specific command.
        :param signature: command signature
        :param module:
        :return:
        """
        module_meta = self.metas[f'az_{module}_meta.json']
        meta = module_meta
        for idx in range(len(signature) - 1):
            meta = meta['sub_groups'][' '.join(signature[:idx + 1])]
        return meta['commands'][' '.join(signature)]

    def build_parser(self, meta):
        parser = CLIParser(parents=[self._global_parser], add_help=False)
        parser.load_meta(meta)
        return parser


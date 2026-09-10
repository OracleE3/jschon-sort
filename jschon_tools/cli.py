import argparse
import json
from collections.abc import Mapping
from pathlib import Path

import jschon

from ._main import process_json_doc
from ._yaml import YamlIndent, create_yaml_processor


def _make_parser(*, prog: str, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
    )
    parser.add_argument('path', help='path to the JSON / YAML document')
    parser.add_argument(
        '--schema', required=True, type=Path, metavar='/path/to/schema.json', help='path to the JSON Schema document'
    )
    parser.add_argument(
        "-d",
        "--draft",
        type=str,
        default="https://json-schema.org/draft/2020-12/schema",
        help="The JSON schema draft version",
    )
    parser.add_argument('-l', '--library', type=Path, action='append', help='Schema library base URI(s)')
    parser.add_argument(
        '--dry-run',
        '-n',
        help='if set, result is not persisted back to the original file',
        action='store_true',
    )
    parser.add_argument('--indent', type=int, default=4, help='indent size')
    parser.add_argument(
        '--yaml-indent',
        type=lambda s: YamlIndent(*map(int, s.split(','))),
        metavar='MAPPING,SEQUENCE,OFFSET',
        default=YamlIndent(2, 4, 2),
        help='YAML indent size',
    )
    return parser


def _is_yaml_path(path: str) -> bool:
    return path.endswith(('.yaml', '.yml'))


def _load_doc_and_schema(
    args: argparse.Namespace,
) -> tuple[jschon.json.JSONCompatible, Mapping[str, jschon.json.JSONCompatible]]:
    with open(args.path) as f:
        if _is_yaml_path(args.path):
            yaml = create_yaml_processor(indent=args.yaml_indent)
            doc_data = yaml.load(f)
        else:
            doc_data = json.load(f)

    with open(args.schema) as f:
        schema_data = json.load(f)

    return doc_data, schema_data


def _maybe_persist(doc_data: jschon.json.JSONCompatible, args: argparse.Namespace) -> None:
    if args.dry_run:
        return

    if _is_yaml_path(args.path):
        with open(args.path, 'w') as f:
            yaml = create_yaml_processor(indent=args.yaml_indent)
            yaml.dump(doc_data, f)
    else:
        with open(args.path, 'w') as f:
            json.dump(doc_data, f, indent=args.indent)


def sort_main() -> None:
    parser = _make_parser(
        prog='jschon-sort',
        description="Sorts a JSON or YAML document to match a JSON Schema's order of properties",
    )
    args = parser.parse_args()

    catalog = jschon.create_catalog(args.draft.split("/")[4])
    for l in args.library or []:
        dir = l.name if l.is_dir() else l.parent.name
        file_uri = jschon.URI(f'file:///{dir}/')
        catalog.add_uri_source(
            file_uri,
            jschon.LocalSource(dir)
        )
        # for s in l.glob("**/*.json"):
        #     catalog.add_schema(
        #         file_uri,
        #         jschon.JSONSchema(json.loads(s.read_text()))
        #     )
        #     print(f"Current catalog of schemas: {catalog._schema_cache['default'].keys()}")
    doc_data, schema_data = _load_doc_and_schema(args)
    doc_data = process_json_doc(doc_data=doc_data, schema_data=schema_data, sort=True)
    _maybe_persist(doc_data, args)


def remove_additional_props_main() -> None:
    jschon.create_catalog('2020-12')

    parser = _make_parser(
        prog='jschon-remove-additional-props',
        description="Processes a JSON or YAML document to remove additional properties not defined in the schema",
    )
    args = parser.parse_args()

    doc_data, schema_data = _load_doc_and_schema(args)
    doc_data = process_json_doc(doc_data=doc_data, schema_data=schema_data, remove_additional_props=True)
    _maybe_persist(doc_data, args)

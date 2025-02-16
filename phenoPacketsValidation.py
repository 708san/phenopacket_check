import json
from jsonschema import validate, ValidationError, FormatChecker
import argparse
import os

def validation_json_files(json_schema_path, json_dir):
    try:
        with open(json_schema_path) as f:
            schema = json.load(f)

    except FileNotFoundError:
        print("json schemaファイルが見つかりません")
        return
    except json.JSONDecodeError:
        print("schemaファイルが不適切です")
        return

    invalid_files = []

    # os.walk を使ってサブディレクトリも走査
    for root, _, files in os.walk(json_dir):
        for file_name in files:
            if file_name.endswith(".json"):
                file_path = os.path.join(root, file_name)  # root を使う
                try:
                    with open(file_path, "r") as f:
                        loaded_json = json.load(f)
                    validate(instance=loaded_json, schema=schema, format_checker=FormatChecker())
                except FileNotFoundError:
                    print(f"{file_path}にファイルが存在しません")
                except json.JSONDecodeError:
                    print(f"{file_path}は不適切なjsonファイルです")
                    invalid_files.append(file_path) # file_pathを保存
                except ValidationError as e:
                    print(f"{file_path}はスキーマに即していません: {e}")
                    invalid_files.append(file_path) # file_pathを保存

    return invalid_files


def main():
    parser = argparse.ArgumentParser(description='json_schemaファイルのパスとjsonファイルが保存されているディレクトリのパスを受け取り、ディレクトリ内のjsonファイルをvalidationするプログラム')
    parser.add_argument('schema_path', help='jsonスキーマのパス')
    parser.add_argument('file_dir', help='jsonファイルが保存されているディレクトリのパス')
    args = parser.parse_args()
    invalid_files = validation_json_files(args.schema_path, args.file_dir)

    if invalid_files:
        print("\n以下のファイルがスキーマに準拠していません:")
        for file_path in invalid_files:
            print(file_path)


if __name__ == '__main__':
    main()
# pylint: disable-all
import json
import os
from glob import glob


def aggregate_json_files(input_dir, output_file):
    aggregated = []
    json_files = glob(os.path.join(input_dir, "*.json"))

    print(f"Found {len(json_files)} JSON files in '{input_dir}'")

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)  # Validate JSON
                aggregated.append(data)
                print(f"✔ Loaded: {file_path}")
        except json.JSONDecodeError as e:
            print(f"✘ Invalid JSON in {file_path}: {e}")
        except Exception as e:
            print(f"✘ Error reading {file_path}: {e}")

    # Write aggregated output
    try:
        with open(output_file, "w", encoding="utf-8") as out:
            json.dump(aggregated, out, indent=4, ensure_ascii=False)
        print(f"\n✅ Aggregated JSON saved to: {output_file}")
    except Exception as e:
        print(f"✘ Failed to write output file: {e}")


if __name__ == "__main__":
    INPUT_DIR = "./"         # folder containing .json files
    OUTPUT_FILE = "aggregated.json"

    aggregate_json_files(INPUT_DIR, OUTPUT_FILE)

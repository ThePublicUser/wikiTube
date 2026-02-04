import csv
import json
from datetime import datetime
import ast

def read_input():
    csv_file = 'input.csv'
    today = '2026-02-04'  # or datetime.today().strftime('%Y-%m-%d')
    filtered_data = []

    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        # Strip header spaces
        reader.fieldnames = [h.strip() for h in reader.fieldnames]

        for idx, row in enumerate(reader, start=1):
            # Strip spaces from all values
            row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}

            if row['date'] == today:
                # Convert columns to list where needed
                if 'bg_vedios' in row and row['bg_vedios']:
                    try:
                        row['bg_vedios'] = ast.literal_eval("[" + row['bg_vedios'] + "]")
                    except:
                        pass

                if 'keywords' in row and row['keywords']:
                    row['keywords'] = [k.strip() for k in row['keywords'].split(',')]

                if 'tags' in row and row['tags']:
                    row['tags'] = [t.strip() for t in row['tags'].split()]

                # Build a new dictionary in the desired order
                ordered_row = {
                    'id': idx,
                    'date': row.get('date', ''),
                    'title': row.get('title', ''),
                    'content': row.get('content', ''),
                    'description': row.get('description', ''),
                    'keywords': row.get('keywords', []),
                    'tags': row.get('tags', []),
                    'bg_vedios': row.get('bg_vedios', []),
                }

                filtered_data.append(ordered_row)

    # Dump JSON without escaping unicode
    json_data = json.dumps(filtered_data, indent=4, ensure_ascii=False)

    # Save JSON
    with open('output.json', 'w', encoding='utf-8') as f:
        f.write(json_data)

    return json_data



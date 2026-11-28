import os

backend_dir = os.path.dirname(os.path.abspath(__file__))

for root, dirs, files in os.walk(backend_dir):
    for f in files:
        if f.endswith('.py') and f not in ('database.py', 'Migrations.py', 'convert_placeholders.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as fh:
                content = fh.read()
            content = content.replace('?', '%s')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(content)

print("Done. All '?' replaced with '%s'.")
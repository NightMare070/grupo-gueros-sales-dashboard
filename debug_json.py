import json
with open(r'C:\Users\agente\dashboard_repo\dashboard_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f"Branches type: {type(data['branches'])}")
if isinstance(data['branches'], dict):
    print(f"First key: {list(data['branches'].keys())[0] if data['branches'] else 'Empty'}")
elif isinstance(data['branches'], list):
    print(f"First element: {data['branches'][0] if data['branches'] else 'Empty'}")

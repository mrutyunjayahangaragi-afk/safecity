import os

file1 = r'c:\safe\traffic-main\Backend\digital_twin_service.py'
file2 = r'c:\safe\traffic-main\Backend\city_metrics_service.py'

for fpath in [file1, file2]:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'import traffic_service as ts' in content:
        content = content.replace('import traffic_service as ts', 'import traffic_repository as tr')
    
    if 'ts.get_active_traffic_reports()' in content:
        content = content.replace('ts.get_active_traffic_reports()', 'tr.get_live_reports()')
        
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Patched digital_twin_service and city_metrics_service")

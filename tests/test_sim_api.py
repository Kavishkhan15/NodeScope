"""
tests/test_sim_api.py
Integration tests for Flask API endpoints and views.
"""


def test_api_network_lifecycle(client):
    # 1. Create Network
    res = client.post('/api/networks', json={
        'name': 'College Test Lab',
        'subnet': '192.168.10.0/24',
        'gateway': '192.168.10.1',
        'dhcp_enabled': True,
        'dhcp_start': '192.168.10.100',
        'dhcp_end': '192.168.10.150'
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    net_id = data['network_id']

    # 2. Get Topology (should have default router gateway)
    top_res = client.get(f'/api/networks/{net_id}/topology')
    assert top_res.status_code == 200
    top = top_res.get_json()
    assert top['success'] is True
    assert len(top['devices']) == 1
    assert top['devices'][0]['device_type'] == 'router'

    # 3. Add Switch and Desktop
    sw_res = client.post(f'/api/networks/{net_id}/devices', json={
        'name': 'Main Switch', 'device_type': 'switch'
    })
    sw_id = sw_res.get_json()['device']['id']

    pc_res = client.post(f'/api/networks/{net_id}/devices', json={
        'name': 'PC 01', 'device_type': 'desktop', 'ip_mode': 'dhcp'
    })
    pc_id = pc_res.get_json()['device']['id']

    # 4. Connect Switch and PC
    conn_res = client.post(f'/api/networks/{net_id}/connections', json={
        'device_a_id': sw_id, 'device_b_id': pc_id
    })
    assert conn_res.status_code == 200

    # 5. Load Views
    home_res = client.get('/')
    assert home_res.status_code == 200
    assert b'NodeScope' in home_res.data

    ws_res = client.get(f'/workspace/{net_id}')
    assert ws_res.status_code == 200
    assert b'College Test Lab' in ws_res.data

    hist_res = client.get(f'/history/{net_id}')
    assert hist_res.status_code == 200

    # 6. Delete Network
    del_res = client.delete(f'/api/networks/{net_id}')
    assert del_res.status_code == 200
    assert del_res.get_json()['success'] is True

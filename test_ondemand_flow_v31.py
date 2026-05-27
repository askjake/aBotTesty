from ondemand_flow_intelligence import analyze_purchase_flow, summarize_ppv_log


def run():
    text = '''dish On Demand Sun 5/24 | 2:09p The Jane Mysteries: Inheritance Lost
    Amateur detective Jane Da Silva takes on the case of a mother's untimely death years earlier.
    FREE TOP MOVIES FOR YOU FREE TV SHOWS Jodie Sweetin Stephen Huszar FREE PG 1h 24m 2023'''
    r = analyze_purchase_flow(text, {}, observed_at='2026-05-24T20:09:00+00:00')
    assert r['screen_stage'] == 'on_demand_landing', r
    assert r['asset_title'] == 'The Jane Mysteries: Inheritance Lost', r
    assert r['display_time_context']['found'], r
    assert r['is_free'], r

    text = '''dish Select Your Option The Super Mario Galaxy Movie Select a quality to complete this purchase.
    Rent Available for 48 hours after you begin watching. HD $24.99 Rent'''
    r = analyze_purchase_flow(text, {}, observed_at='2026-05-24T20:12:00+00:00')
    assert r['screen_stage'] == 'purchase_option', r
    assert r['asset_title'] == 'The Super Mario Galaxy Movie', r
    assert r['purchase_price'] == 24.99, r
    assert r['is_paid'], r

    text = '''On Demand Purchase Confirmation 992 You have indicated that you wish to order an On Demand Event. Is this correct? Yes No'''
    r = analyze_purchase_flow(text, {}, observed_at='2026-05-24T20:12:00+00:00')
    assert r['screen_stage'] == 'purchase_confirmation', r
    assert 'final_confirmation_screen' in r['flags'], r

    raw = {'events': [
        {'type':'operator_purchase_observation','key':'channel:1','purchase_flow': {'screen_stage':'on_demand_landing','asset_title':'The Jane Mysteries','displayed_time':'Sun 5/24 | 2:09p'}},
        {'type':'operator_purchase_observation','key':'select','before_purchase_flow': {'screen_stage':'on_demand_landing'}, 'purchase_flow': {'screen_stage':'asset_summary','asset_title':'The Jane Mysteries'}},
        {'type':'operator_purchase_observation','key':'select','before_purchase_flow': {'screen_stage':'asset_summary'}, 'purchase_flow': {'screen_stage':'purchase_option','asset_title':'The Jane Mysteries','price':'$0.00'}},
        {'type':'operator_purchase_observation','key':'select','before_purchase_flow': {'screen_stage':'purchase_option'}, 'purchase_flow': {'screen_stage':'purchase_confirmation','asset_title':'The Jane Mysteries'}},
    ]}
    s = summarize_ppv_log(raw)
    assert s['replication_readiness']['level'] == 'high', s
    assert s['operator_purchase_events'] == 4, s
    print('ONDEMAND_FLOW_V31_OK')

if __name__ == '__main__':
    run()

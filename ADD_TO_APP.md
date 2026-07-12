# Add these optional sections to `app.py`

Place these imports near the top:

```python
from alert_manager import recent_alerts
from economic_calendar import high_impact_events
from earnings_calendar import upcoming_earnings
from worker_health import read_heartbeat
```

Then place this section anywhere after `st.set_page_config(...)`:

```python
with st.expander("Market intelligence and worker health", expanded=False):
    heartbeat = read_heartbeat()
    if heartbeat.get("healthy"):
        st.success(f"24/7 worker online — last heartbeat {heartbeat.get('age_seconds', 0)} seconds ago")
    else:
        st.warning(f"Worker heartbeat not confirmed: {heartbeat.get('reason', 'stale heartbeat')}")

    left, right = st.columns(2)

    with left:
        st.subheader("High-impact economic events")
        events = high_impact_events(7)
        if events:
            st.dataframe(events, width="stretch", hide_index=True)
        else:
            st.info("Add FINNHUB_API_KEY to load the economic calendar.")

    with right:
        st.subheader("Upcoming earnings")
        earnings = upcoming_earnings(7)
        if earnings:
            st.dataframe(earnings, width="stretch", hide_index=True)
        else:
            st.info("No earnings loaded. Add FINNHUB_API_KEY or check again later.")

    st.subheader("Recent Oracle alerts")
    alerts = recent_alerts(25)
    if alerts:
        st.dataframe(alerts, width="stretch", hide_index=True)
    else:
        st.caption("No alerts have been recorded yet.")
```

## Requirements

Open your existing `requirements.txt` and make sure these are present:

```text
numpy>=1.26,<3
pandas>=2.2,<3
requests>=2.31,<3
```

Do not delete your existing dependencies.

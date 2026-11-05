# ParkFlow business-case deck

This folder generates the members-first ParkFlow business-case deck.

## Build

```powershell
python -m pip install -r presentation/requirements.txt
python presentation/build_deck.py
```

Output:

- `submission/ParkFlow-Priority-Zone-Business-Case-vNext.pptx`

The financial visuals use Plotly/Kaleido and Matplotlib. The product screenshots and visual tokens come from the extracted design reference in `references/parkflow-site-v2/`.

## Narrative decisions

- Accepted bookings are protected by deterministic available-to-promise control using gated entry/exit observations and the reservation ledger.
- Forecasting is advisory and covers the wider car park; it does not override the booking guarantee.
- Priority Zone booking is a member privilege. Non-members receive broad general-parking guidance only.
- The base case is an SDP-sponsored KL East lighthouse. External commercialisation is a gated Horizon 3 option, not assumed pilot revenue.
- Retention and GTO outputs are labelled as illustrative scenarios until measured in the pilot.


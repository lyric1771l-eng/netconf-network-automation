# NETCONF Network Automation

Python-based configuration collection and analysis for Cisco IOS XR and Nexus 9000v (NX-OS), developed for TELE9752 Network Operations and Control at UNSW.

**Author: Yan Liang.** This was a group coursework submission; I implemented all scripts and completed the collection, parsing and comparative analysis presented in this repository.

## What this project demonstrates

- Establishing NETCONF-over-SSH sessions using `ncclient`.
- Discovering server capabilities and retrieving running configurations.
- Using an NX-OS YANG subtree filter for configuration retrieval.
- Parsing namespace-aware IOS XR XML into structured JSON: model namespaces, interfaces and routing-related configuration.
- Distinguishing successful live collection from offline analysis and documenting limitations.

## Original results

| Platform | Evidence | Outcome |
| --- | --- | --- |
| Cisco Nexus 9000v / NX-OS | Live sandbox session | Capabilities and running configuration successfully collected and saved as XML. |
| Cisco IOS XR | Lecturer-provided XML after live authentication failed | 88 unique model namespaces, 36 interface records, 12 distinct logical interface names, one static route and eight routing-related sections. |

NX-OS advertised 11 capabilities: ten NETCONF protocol/operation capabilities and one vendor model. This is **not directly comparable** with the 88 namespaces extracted from IOS XR data. Multiple XML records can describe the same interface; 36 records do not mean 36 physical interfaces. Static/configuration data is not a complete operational routing table.

## Files

| File | Purpose |
| --- | --- |
| `iosxr_client.py` | Retrieve IOS XR capabilities, running configuration, interfaces and IPv4 routing data. |
| `inspect_iosxr_xml.py` | Inspect the top-level structure of the coursework XML input. |
| `parse_iosxr_xml.py` | Convert IOS XR configuration XML into structured JSON. |
| `nxos_netconf.py` | Collect NX-OS capabilities and running configuration using a subtree filter. |
| `nxos_capabilities.txt` | Capability list from the original successful sandbox session. |
| `iosxr_result_summary.json` | Non-sensitive summary and model namespace list from the original analysis. |

## Run locally

Requires Python 3.10+ and access to an authorised Cisco sandbox for live collection.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export NETCONF_USERNAME='your-current-sandbox-username'
python nxos_netconf.py
# Or, when IOS XR sandbox authentication is available:
python iosxr_client.py
```

Passwords are requested interactively, not stored in the source. Verify current sandbox hostnames and credentials before connecting. Scripts retrieve data; they do not push configuration changes.

For the original offline workflow, place your authorised coursework input named `iosxr_teacher_data.xml` in the repository directory, then run:

```bash
python inspect_iosxr_xml.py
python parse_iosxr_xml.py
```

Run from the repository directory. The original full XML input and full JSON output are deliberately not distributed, so the historical results cannot be reproduced from this public repository alone. A live-client wrapper XML is not assumed to be interchangeable with the original parser input.

## Security and publication notes

- Original ZIP archives are unchanged. Public copies replace the hard-coded username with `NETCONF_USERNAME` and the IOS XR password with an interactive prompt. Collection and parsing logic is retained.
- Raw configurations may contain accounts, credential hashes, SNMP community strings and other sensitive device information. They and the full report are excluded rather than relying on incomplete redaction.
- The original lab clients use `hostkey_verify=False`. This is retained to document the sandbox implementation, **not recommended for production**. Verify SSH host keys before adapting these clients to real infrastructure.
- Generated configuration files are ignored by Git. Review any new output before sharing it.
- Public packaging checks cover Python syntax and supplied JSON/XML structure; no new live device session was run during publication. Historical results are from the original coursework.

## Skills

Python · NETCONF · ncclient · YANG · XML/JSON · Cisco IOS XR · NX-OS · Configuration analysis · Technical documentation

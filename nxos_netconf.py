import os
from getpass import getpass
from pathlib import Path
import xml.etree.ElementTree as ET

from ncclient import manager


# ============================================================
# Nexus 9000 connection information
# ============================================================

HOST = "sbx-nxos-mgmt.cisco.com"
PORT = 830
USERNAME = os.environ.get("NETCONF_USERNAME", "")

# Save generated files in the same folder as this Python script
OUTPUT_FOLDER = Path(__file__).resolve().parent

CAPABILITIES_FILE = OUTPUT_FOLDER / "nxos_capabilities.txt"
RAW_CONFIG_FILE = OUTPUT_FOLDER / "nxos_config_reply.xml"
COMBINED_XML_FILE = OUTPUT_FOLDER / "nxos_data.xml"


def save_capabilities(capabilities: list[str]) -> None:
    """
    Save all NETCONF capabilities and available YANG modules
    into a text file.
    """
    with CAPABILITIES_FILE.open(
        mode="w",
        encoding="utf-8"
    ) as file:
        for number, capability in enumerate(capabilities, start=1):
            file.write(f"{number}. {capability}\n")


def save_raw_config(config_xml: str) -> None:
    """
    Save the original NETCONF get-config reply.
    """
    with RAW_CONFIG_FILE.open(
        mode="w",
        encoding="utf-8"
    ) as file:
        file.write(config_xml)


def create_combined_xml(
    capabilities: list[str],
    config_xml: str,
    session_id: str
) -> None:
    """
    Create one combined XML file containing:
    1. Device information
    2. NETCONF session ID
    3. Available NETCONF/YANG capabilities
    4. Running configuration reply
    """

    root = ET.Element("nxos-netconf-data")

    # Device information
    device_element = ET.SubElement(root, "device")

    ET.SubElement(
        device_element,
        "platform"
    ).text = "Cisco Nexus 9000 / NX-OS"

    ET.SubElement(
        device_element,
        "hostname"
    ).text = HOST

    ET.SubElement(
        device_element,
        "netconf-port"
    ).text = str(PORT)

    ET.SubElement(
        device_element,
        "session-id"
    ).text = str(session_id)

    # NETCONF capabilities and YANG modules
    capabilities_element = ET.SubElement(
        root,
        "available-netconf-yang-capabilities"
    )

    for number, capability in enumerate(capabilities, start=1):
        capability_element = ET.SubElement(
            capabilities_element,
            "capability"
        )

        capability_element.set("number", str(number))
        capability_element.text = capability

    # Running configuration reply
    configuration_element = ET.SubElement(
        root,
        "running-configuration"
    )

    try:
        config_reply_element = ET.fromstring(config_xml)
        configuration_element.append(config_reply_element)

    except ET.ParseError as error:
        # Preserve the reply as text if XML parsing unexpectedly fails
        configuration_element.text = config_xml
        print(
            "Warning: the configuration reply could not be embedded "
            f"as parsed XML: {error}"
        )

    tree = ET.ElementTree(root)

    # Pretty indentation; supported by modern Python versions
    try:
        ET.indent(tree, space="    ")
    except AttributeError:
        pass

    tree.write(
        COMBINED_XML_FILE,
        encoding="utf-8",
        xml_declaration=True
    )


def main() -> None:
    """
    Connect to Nexus 9000, retrieve capabilities and running
    configuration, and save the results.
    """

    password = getpass("Enter NXOS password: ")

    try:
        print("\nConnecting to Nexus 9000...")

        with manager.connect(
            host=HOST,
            port=PORT,
            username=USERNAME,
            password=password,
            hostkey_verify=False,
            allow_agent=False,
            look_for_keys=False,
            timeout=30
        ) as connection:

            print("\nNETCONF connection successful!")
            print("Session ID:", connection.session_id)

            # ------------------------------------------------
            # 1. Retrieve NETCONF capabilities / YANG modules
            # ------------------------------------------------

            capabilities = [
                str(capability)
                for capability in connection.server_capabilities
            ]

            print("\nAvailable NETCONF/YANG capabilities:")

            for number, capability in enumerate(
                capabilities,
                start=1
            ):
                print(f"{number}. {capability}")

            save_capabilities(capabilities)

            print(
                "\nCapabilities saved to:",
                CAPABILITIES_FILE.name
            )

            # ------------------------------------------------
            # 2. Retrieve the NX-OS running configuration
            # ------------------------------------------------
            #
            # NX-OS requires an explicit YANG namespace and
            # subtree filter for get and get-config requests.
            # ------------------------------------------------

            nxos_filter = """
<System xmlns="http://cisco.com/ns/yang/cisco-nx-os-device"/>
"""

            print(
                "\nRetrieving NX-OS running configuration..."
            )

            config_reply = connection.get_config(
                source="running",
                filter=("subtree", nxos_filter)
            )

            config_xml = config_reply.xml

            # Save original NETCONF RPC reply
            save_raw_config(config_xml)

            print(
                "Raw configuration reply saved to:",
                RAW_CONFIG_FILE.name
            )

            # Save capabilities and configuration in one XML
            create_combined_xml(
                capabilities=capabilities,
                config_xml=config_xml,
                session_id=str(connection.session_id)
            )

            print(
                "Combined XML data saved to:",
                COMBINED_XML_FILE.name
            )

            print("\nAll NX-OS NETCONF tasks completed successfully!")

    except Exception as error:
        print("\nNETCONF operation failed!")
        print("Error type:", type(error).__name__)
        print("Error message:", error)


if __name__ == "__main__":
    main()
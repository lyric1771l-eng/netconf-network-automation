from getpass import getpass
import os
from ncclient import manager
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom


# =========================================================
# 1. IOS XR Sandbox connection information
# =========================================================

HOST = "sandbox-iosxr-1.cisco.com"
PORT = 830

# Set NETCONF_USERNAME to your current sandbox username.
USERNAME = os.environ.get("NETCONF_USERNAME", "")
# Password is requested interactively in main().

# Name of the XML file generated after successful execution
OUTPUT_FILE = Path("iosxr_netconf_data.xml")


# =========================================================
# 2. Make the saved XML easier to read
# =========================================================

def format_xml(root):
    """
    Convert the XML element into formatted XML bytes.
    """

    rough_xml = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True
    )

    parsed_xml = minidom.parseString(rough_xml)

    return parsed_xml.toprettyxml(
        indent="    ",
        encoding="utf-8"
    )


# =========================================================
# 3. Add a NETCONF reply into the final XML file
# =========================================================

def add_reply_to_xml(parent, section_name, xml_content):
    """
    Add returned NETCONF XML data into one section
    of the final XML file.
    """

    section = ET.SubElement(parent, section_name)

    try:
        returned_xml = ET.fromstring(xml_content)
        section.append(returned_xml)

    except ET.ParseError as error:
        error_element = ET.SubElement(section, "parse-error")
        error_element.text = str(error)


# =========================================================
# 4. Main NETCONF program
# =========================================================

def main():

    password = getpass("Enter IOS XR password: ")

    print("=" * 60)
    print("Cisco IOS XR NETCONF Client")
    print("=" * 60)

    try:
        # -------------------------------------------------
        # Connect to the IOS XR router
        # -------------------------------------------------

        with manager.connect(
            host=HOST,
            port=PORT,
            username=USERNAME,
            password=password,
            hostkey_verify=False,
            device_params={"name": "iosxr"},
            allow_agent=False,
            look_for_keys=False,
            timeout=30
        ) as connection:

            print("NETCONF connection successful!")
            print("Session ID:", connection.session_id)

            # Create the root element of the output XML file
            root = ET.Element("iosxr-netconf-data")

            # -------------------------------------------------
            # Save device information
            # -------------------------------------------------

            device_information = ET.SubElement(
                root,
                "device-information"
            )

            ET.SubElement(
                device_information,
                "device"
            ).text = "Cisco IOS XR Router"

            ET.SubElement(
                device_information,
                "host"
            ).text = HOST

            ET.SubElement(
                device_information,
                "netconf-port"
            ).text = str(PORT)

            ET.SubElement(
                device_information,
                "session-id"
            ).text = str(connection.session_id)

            # -------------------------------------------------
            # Retrieve available NETCONF capabilities
            # These capabilities contain available YANG models
            # -------------------------------------------------

            print("\nRetrieving NETCONF capabilities...")

            capabilities_element = ET.SubElement(
                root,
                "server-capabilities"
            )

            capabilities = list(connection.server_capabilities)

            for capability in capabilities:
                capability_element = ET.SubElement(
                    capabilities_element,
                    "capability"
                )

                capability_element.text = str(capability)

            print(
                "Number of capabilities retrieved:",
                len(capabilities)
            )

            # -------------------------------------------------
            # Retrieve the current running configuration
            # -------------------------------------------------

            print("\nRetrieving running configuration...")

            running_configuration_reply = connection.get_config(
                source="running"
            )

            add_reply_to_xml(
                root,
                "running-configuration",
                running_configuration_reply.data_xml
            )

            print("Running configuration retrieved.")

            # -------------------------------------------------
            # Retrieve interface configurations
            # -------------------------------------------------

            print("\nRetrieving interface configurations...")

            interface_filter = (
                "subtree",
                """
                <interface-configurations
                    xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
                </interface-configurations>
                """
            )

            try:
                interface_reply = connection.get(
                    filter=interface_filter
                )

                add_reply_to_xml(
                    root,
                    "interface-configurations",
                    interface_reply.data_xml
                )

                print("Interface configurations retrieved.")

            except Exception as interface_error:

                interface_section = ET.SubElement(
                    root,
                    "interface-configurations"
                )

                interface_error_element = ET.SubElement(
                    interface_section,
                    "retrieval-error"
                )

                interface_error_element.text = str(
                    interface_error
                )

                print("Interface retrieval failed:")
                print(interface_error)

            # -------------------------------------------------
            # Retrieve IPv4 routing table
            # -------------------------------------------------

            print("\nRetrieving IPv4 routing table...")

            routing_filter = (
                "subtree",
                """
                <rib
                    xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ip-rib-ipv4-oper">
                </rib>
                """
            )

            try:
                routing_reply = connection.get(
                    filter=routing_filter
                )

                add_reply_to_xml(
                    root,
                    "routing-table",
                    routing_reply.data_xml
                )

                print("IPv4 routing table retrieved.")

            except Exception as routing_error:

                routing_section = ET.SubElement(
                    root,
                    "routing-table"
                )

                routing_error_element = ET.SubElement(
                    routing_section,
                    "retrieval-error"
                )

                routing_error_element.text = str(
                    routing_error
                )

                print("Routing table retrieval failed:")
                print(routing_error)

            # -------------------------------------------------
            # Save all retrieved information into an XML file
            # -------------------------------------------------

            formatted_xml = format_xml(root)

            OUTPUT_FILE.write_bytes(formatted_xml)

            print("\n" + "=" * 60)
            print("NETCONF data retrieval completed.")
            print("XML file saved as:", OUTPUT_FILE.resolve())
            print("=" * 60)

    except Exception as error:

        print("\nNETCONF connection failed!")
        print("Error type:", type(error).__name__)
        print("Error message:", error)

        print(
            "\nNo XML file was generated because "
            "the router connection was not established."
        )


# =========================================================
# 5. Start the program
# =========================================================

if __name__ == "__main__":
    main()
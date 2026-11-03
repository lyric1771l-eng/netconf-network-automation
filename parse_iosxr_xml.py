import json
import xml.etree.ElementTree as ET
from pathlib import Path


# =========================================================
# 1. Input and output file names
# =========================================================

XML_FILE = Path("iosxr_teacher_data.xml")
JSON_FILE = Path("iosxr_result.json")

NETCONF_NAMESPACE = "urn:ietf:params:xml:ns:netconf:base:1.0"


# =========================================================
# 2. Basic XML helper functions
# =========================================================

def get_local_name(tag):
    """
    Remove the namespace from an XML tag.

    Example:
    {http://openconfig.net/yang/interfaces}interface

    Result:
    interface
    """

    if "}" in tag:
        return tag.split("}", 1)[1]

    return tag


def get_namespace(tag):
    """
    Extract the namespace from an XML tag.

    Example:
    {http://openconfig.net/yang/interfaces}interface

    Result:
    http://openconfig.net/yang/interfaces
    """

    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]

    return ""


def get_first_text(element, possible_names):
    """
    Find the first matching XML value.
    """

    for child in element.iter():

        child_name = get_local_name(child.tag)

        if child_name in possible_names:

            if child.text and child.text.strip():
                return child.text.strip()

    return None


def get_all_text(element, possible_names):
    """
    Find all matching XML values without duplicates.
    """

    values = []

    for child in element.iter():

        child_name = get_local_name(child.tag)

        if child_name in possible_names:

            if child.text and child.text.strip():

                value = child.text.strip()

                if value not in values:
                    values.append(value)

    return values


def xml_element_to_dict(element):
    """
    Convert an XML element into a Python dictionary.
    """

    children = list(element)

    if not children:

        if element.text and element.text.strip():
            return element.text.strip()

        return None

    result = {}

    for child in children:

        child_name = get_local_name(child.tag)
        child_value = xml_element_to_dict(child)

        if child_name in result:

            if not isinstance(result[child_name], list):
                result[child_name] = [result[child_name]]

            result[child_name].append(child_value)

        else:
            result[child_name] = child_value

    return result


# =========================================================
# 3. Extract available YANG models
# =========================================================

def namespace_to_model_name(namespace):
    """
    Extract a readable YANG model name from the namespace.

    Example:
    http://tail-f.com/ns/mibs/SNMP-NOTIFICATION-MIB/202210140000Z

    Result:
    SNMP-NOTIFICATION-MIB
    """

    parts = namespace.rstrip("/").split("/")

    if not parts:
        return namespace

    last_part = parts[-1]

    # Some Tail-f namespaces end with a revision date,
    # for example: 202210140000Z
    if (
        last_part.endswith("Z")
        and last_part[:-1].isdigit()
        and len(parts) >= 2
    ):
        return parts[-2]

    # Some namespaces end with a version number,
    # for example: /aaa/1.1
    if (
        last_part.replace(".", "").isdigit()
        and len(parts) >= 2
    ):
        return parts[-2]

    return last_part


def extract_yang_models(root):
    """
    Extract unique YANG model namespaces from the XML file.
    """

    models = []
    seen_namespaces = set()

    for element in root.iter():

        namespace = get_namespace(element.tag)

        if not namespace:
            continue

        # Do not count the basic NETCONF namespace as a YANG model
        if namespace == NETCONF_NAMESPACE:
            continue

        if namespace in seen_namespaces:
            continue

        seen_namespaces.add(namespace)

        models.append(
            {
                "model_name": namespace_to_model_name(namespace),
                "namespace": namespace
            }
        )

    models.sort(
        key=lambda item: item["model_name"].lower()
    )

    return models


# =========================================================
# 4. Extract network interface configurations
# =========================================================

def extract_interfaces(root):
    """
    Extract Cisco IOS XR and OpenConfig interface information.
    """

    interfaces = []
    seen_records = set()

    for element in root.iter():

        element_name = get_local_name(element.tag)
        namespace = get_namespace(element.tag)

        # Cisco IOS XR normally uses interface-configuration.
        # OpenConfig normally uses interface.
        is_interface_record = (
            element_name == "interface-configuration"
            or (
                element_name == "interface"
                and "interfaces" in namespace.lower()
            )
        )

        if not is_interface_record:
            continue

        interface_name = get_first_text(
            element,
            {
                "interface-name",
                "name"
            }
        )

        if not interface_name:
            continue

        configuration = xml_element_to_dict(element)

        record_key = (
            interface_name,
            namespace,
            json.dumps(
                configuration,
                sort_keys=True,
                ensure_ascii=False
            )
        )

        if record_key in seen_records:
            continue

        seen_records.add(record_key)

        description = get_first_text(
            element,
            {
                "description"
            }
        )

        enabled = get_first_text(
            element,
            {
                "enabled",
                "shutdown"
            }
        )

        ipv4_addresses = get_all_text(
            element,
            {
                "ip-address",
                "address",
                "ipv4-address"
            }
        )

        subnet_masks = get_all_text(
            element,
            {
                "mask",
                "prefix-length",
                "subnet-mask"
            }
        )

        interfaces.append(
            {
                "interface_name": interface_name,
                "description": description,
                "enabled_or_shutdown_value": enabled,
                "ipv4_addresses": ipv4_addresses,
                "subnet_masks_or_prefix_lengths": subnet_masks,
                "model_namespace": namespace,
                "complete_configuration": configuration
            }
        )

    interfaces.sort(
        key=lambda item: item["interface_name"].lower()
    )

    return interfaces


# =========================================================
# 5. Extract static routing information
# =========================================================

def extract_static_routes(root):
    """
    Extract static routes from Cisco IOS XR XML.
    """

    routes = []
    seen_routes = set()

    for element in root.iter():

        element_name = get_local_name(element.tag)

        if element_name not in {
            "vrf-prefix",
            "route-entry"
        }:
            continue

        prefix = get_first_text(
            element,
            {
                "prefix",
                "network",
                "destination-prefix"
            }
        )

        prefix_length = get_first_text(
            element,
            {
                "prefix-length",
                "destination-prefix-length"
            }
        )

        if not prefix:
            continue

        if prefix_length:
            destination = f"{prefix}/{prefix_length}"
        else:
            destination = prefix

        next_hops = get_all_text(
            element,
            {
                "next-hop-address",
                "next-hop",
                "gateway-address"
            }
        )

        outgoing_interfaces = get_all_text(
            element,
            {
                "interface-name",
                "outgoing-interface"
            }
        )

        route_key = (
            destination,
            tuple(next_hops),
            tuple(outgoing_interfaces)
        )

        if route_key in seen_routes:
            continue

        seen_routes.add(route_key)

        routes.append(
            {
                "destination": destination,
                "next_hop_addresses": next_hops,
                "outgoing_interfaces": outgoing_interfaces,
                "route_type": "static"
            }
        )

    routes.sort(
        key=lambda item: item["destination"]
    )

    return routes


# =========================================================
# 6. Preserve other routing-related configurations
# =========================================================

def extract_routing_sections(root):
    """
    Extract major routing-related configuration sections,
    such as static routes, ISIS, VRF and routing instances.
    """

    routing_sections = []

    routing_keywords = {
        "router-static",
        "router",
        "isis",
        "vrfs",
        "rib",
        "ospf",
        "bgp",
        "network-instances"
    }

    for child in root:

        child_name = get_local_name(child.tag)
        namespace = get_namespace(child.tag)
        namespace_lower = namespace.lower()

        is_routing_section = (
            child_name in routing_keywords
            or "router" in namespace_lower
            or "routing" in namespace_lower
            or "rib" in namespace_lower
            or "isis" in namespace_lower
            or "ospf" in namespace_lower
            or "bgp" in namespace_lower
            or "network-instance" in namespace_lower
            or "vrf" in namespace_lower
        )

        if not is_routing_section:
            continue

        routing_sections.append(
            {
                "section_name": child_name,
                "model_name": namespace_to_model_name(namespace),
                "namespace": namespace,
                "configuration": xml_element_to_dict(child)
            }
        )

    return routing_sections


# =========================================================
# 7. Main program
# =========================================================

def main():

    print("=" * 60)
    print("Cisco IOS XR XML to JSON Parser")
    print("=" * 60)

    try:
        # Read the XML file
        tree = ET.parse(XML_FILE)
        root = tree.getroot()

        print("XML file loaded successfully:")
        print(XML_FILE.resolve())

        # Extract YANG models
        print("\nExtracting available YANG models...")
        yang_models = extract_yang_models(root)

        # Extract interface configurations
        print("Extracting network interface configurations...")
        interfaces = extract_interfaces(root)

        # Extract routing information
        print("Extracting routing table information...")
        static_routes = extract_static_routes(root)
        routing_sections = extract_routing_sections(root)

        # Create the final JSON structure
        output_data = {
            "device_information": {
                "device": "Cisco IOS XR Router",
                "operating_system": "Cisco IOS XR",
                "sandbox": "IOS XR Programmability - Always On",
                "data_source": "Provided NETCONF XML data",
                "source_xml_file": XML_FILE.name
            },

            "summary": {
                "yang_model_count": len(yang_models),
                "interface_record_count": len(interfaces),
                "static_route_count": len(static_routes),
                "routing_section_count": len(routing_sections)
            },

            "available_yang_models": yang_models,

            "network_interface_configurations": interfaces,

            "routing_table": {
                "static_routes": static_routes,
                "routing_related_sections": routing_sections
            }
        }

        # Write the information to JSON
        with JSON_FILE.open(
            "w",
            encoding="utf-8"
        ) as json_file:

            json.dump(
                output_data,
                json_file,
                indent=4,
                ensure_ascii=False
            )

        print("\n" + "=" * 60)
        print("XML parsing completed successfully.")
        print("YANG models extracted:", len(yang_models))
        print("Interface records extracted:", len(interfaces))
        print("Static routes extracted:", len(static_routes))
        print("Routing sections extracted:", len(routing_sections))
        print("JSON file saved as:", JSON_FILE.resolve())
        print("=" * 60)

    except FileNotFoundError:

        print("\nXML file was not found:")
        print(XML_FILE.resolve())

        print(
            "\nMake sure iosxr_teacher_data.xml "
            "is in the same folder as this Python script."
        )

    except ET.ParseError as error:

        print("\nXML parsing failed.")
        print("Error message:", error)

    except PermissionError as error:

        print("\nThe JSON file could not be written.")
        print("Close iosxr_result.json and run the script again.")
        print("Error message:", error)

    except Exception as error:

        print("\nUnexpected error:")
        print("Error type:", type(error).__name__)
        print("Error message:", error)


# =========================================================
# 8. Run the program
# =========================================================

if __name__ == "__main__":
    main()